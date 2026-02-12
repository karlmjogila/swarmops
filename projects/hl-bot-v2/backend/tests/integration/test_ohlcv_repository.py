"""Integration tests for OHLCV repository using PostgreSQL.

Tests database operations against the actual PostgreSQL + TimescaleDB instance.
These tests require a running PostgreSQL database and are skipped if not available.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import os
from typing import TYPE_CHECKING

import pytest

# Import types that don't require database connection
from hl_bot.types import Candle, Timeframe

# For type hints only - avoids import at module level
if TYPE_CHECKING:
    from hl_bot.repositories import OHLCVRepository


def _check_postgres_available():
    """Check if PostgreSQL database is available for testing."""
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith("postgresql"):
        return False
    try:
        # Try to connect to the database
        from sqlalchemy import create_engine, text
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


# Skip all tests in this module if PostgreSQL is not available
pytestmark = pytest.mark.skipif(
    not _check_postgres_available(),
    reason="PostgreSQL database not available - set DATABASE_URL and ensure DB is running"
)


@pytest.fixture
def ohlcv_repo():
    """Create OHLCV repository with real database.
    
    Imports are done inside the fixture to avoid loading database
    modules when tests are skipped.
    """
    from app.db.session import get_db
    from hl_bot.repositories import OHLCVRepository
    
    db = next(get_db())
    repo = OHLCVRepository(db)
    
    # Clean up test data before and after
    test_symbol = "TEST-USD"
    for tf in Timeframe:
        repo.delete_candles(test_symbol, tf)
    
    yield repo
    
    # Clean up after test
    for tf in Timeframe:
        repo.delete_candles(test_symbol, tf)
    
    db.close()


@pytest.fixture
def sample_candle() -> Candle:
    """Create a sample test candle."""
    return Candle(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        symbol="TEST-USD",
        timeframe=Timeframe.H1,
        open=50000.0,
        high=51000.0,
        low=49500.0,
        close=50500.0,
        volume=1000.0,
    )


def test_insert_and_retrieve_candle(ohlcv_repo: OHLCVRepository, sample_candle: Candle):
    """Test basic insert and retrieval."""
    # Insert
    result = ohlcv_repo.insert_candle(sample_candle)
    assert result.symbol == "TEST-USD"
    
    # Retrieve
    candles = ohlcv_repo.get_candles("TEST-USD", Timeframe.H1)
    assert len(candles) == 1
    assert candles[0].close == 50500.0


def test_batch_insert(ohlcv_repo: OHLCVRepository):
    """Test batch insertion."""
    base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    candles = [
        Candle(
            timestamp=base_time + timedelta(hours=i),
            symbol="TEST-USD",
            timeframe=Timeframe.H1,
            open=50000.0,
            high=51000.0,
            low=49500.0,
            close=50500.0,
            volume=1000.0,
        )
        for i in range(10)
    ]
    
    inserted = ohlcv_repo.insert_candles_batch(candles)
    assert inserted == 10
    
    # Verify count
    count = ohlcv_repo.count_candles("TEST-USD", Timeframe.H1)
    assert count == 10


def test_time_range_queries(ohlcv_repo: OHLCVRepository):
    """Test time-based filtering."""
    base_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    # Insert 24 hours of data
    candles = [
        Candle(
            timestamp=base_time + timedelta(hours=i),
            symbol="TEST-USD",
            timeframe=Timeframe.H1,
            open=50000.0,
            high=51000.0,
            low=49500.0,
            close=50500.0,
            volume=1000.0,
        )
        for i in range(24)
    ]
    ohlcv_repo.insert_candles_batch(candles)
    
    # Query with time range
    start = base_time + timedelta(hours=10)
    end = base_time + timedelta(hours=15)
    
    results = ohlcv_repo.get_candles(
        "TEST-USD", Timeframe.H1, start_time=start, end_time=end
    )
    
    assert len(results) == 6  # Hours 10-15 inclusive
    assert results[0].timestamp == start
    assert results[-1].timestamp == end


def test_latest_candle(ohlcv_repo: OHLCVRepository):
    """Test retrieving the latest candle."""
    base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    candles = [
        Candle(
            timestamp=base_time + timedelta(hours=i),
            symbol="TEST-USD",
            timeframe=Timeframe.H1,
            open=50000.0,
            high=51000.0,
            low=49500.0,
            close=50500.0 + i,  # Different close prices
            volume=1000.0,
        )
        for i in range(5)
    ]
    ohlcv_repo.insert_candles_batch(candles)
    
    latest = ohlcv_repo.get_latest_candle("TEST-USD", Timeframe.H1)
    
    assert latest is not None
    assert latest.close == 50504.0  # Last candle
    assert latest.timestamp == base_time + timedelta(hours=4)


def test_upsert_operation(ohlcv_repo: OHLCVRepository, sample_candle: Candle):
    """Test insert-or-update behavior."""
    # First insert
    ohlcv_repo.upsert_candle(sample_candle)
    
    # Verify insert
    candles = ohlcv_repo.get_candles("TEST-USD", Timeframe.H1)
    assert len(candles) == 1
    assert candles[0].close == 50500.0
    
    # Update with new price
    updated = Candle(
        timestamp=sample_candle.timestamp,
        symbol=sample_candle.symbol,
        timeframe=sample_candle.timeframe,
        open=50000.0,
        high=52000.0,
        low=49500.0,
        close=51500.0,  # Changed
        volume=1500.0,  # Changed
    )
    ohlcv_repo.upsert_candle(updated)
    
    # Verify update (still only 1 candle)
    candles = ohlcv_repo.get_candles("TEST-USD", Timeframe.H1)
    assert len(candles) == 1
    assert candles[0].close == 51500.0
    assert candles[0].volume == 1500.0


def test_delete_candles(ohlcv_repo: OHLCVRepository):
    """Test deletion of candles."""
    base_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    # Insert data
    candles = [
        Candle(
            timestamp=base_time + timedelta(hours=i),
            symbol="TEST-USD",
            timeframe=Timeframe.H1,
            open=50000.0,
            high=51000.0,
            low=49500.0,
            close=50500.0,
            volume=1000.0,
        )
        for i in range(20)
    ]
    ohlcv_repo.insert_candles_batch(candles)
    
    # Delete specific range
    start = base_time + timedelta(hours=5)
    end = base_time + timedelta(hours=10)
    deleted = ohlcv_repo.delete_candles(
        "TEST-USD", Timeframe.H1, start_time=start, end_time=end
    )
    
    assert deleted == 6
    
    # Verify remaining
    remaining = ohlcv_repo.count_candles("TEST-USD", Timeframe.H1)
    assert remaining == 14


def test_get_time_range(ohlcv_repo: OHLCVRepository):
    """Test retrieving the time range of available data."""
    base_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    candles = [
        Candle(
            timestamp=base_time + timedelta(days=i),
            symbol="TEST-USD",
            timeframe=Timeframe.D1,
            open=50000.0,
            high=51000.0,
            low=49500.0,
            close=50500.0,
            volume=1000.0,
        )
        for i in range(30)  # 30 days
    ]
    ohlcv_repo.insert_candles_batch(candles)
    
    time_range = ohlcv_repo.get_time_range("TEST-USD", Timeframe.D1)
    
    assert time_range is not None
    earliest, latest = time_range
    assert earliest == base_time
    assert latest == base_time + timedelta(days=29)


def test_multiple_timeframes(ohlcv_repo: OHLCVRepository):
    """Test handling multiple timeframes for the same symbol."""
    base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    # Insert different timeframes
    for tf in [Timeframe.M5, Timeframe.M15, Timeframe.H1]:
        candle = Candle(
            timestamp=base_time,
            symbol="TEST-USD",
            timeframe=tf,
            open=50000.0,
            high=51000.0,
            low=49500.0,
            close=50500.0,
            volume=1000.0,
        )
        ohlcv_repo.insert_candle(candle)
    
    # Verify each timeframe is isolated
    assert ohlcv_repo.count_candles("TEST-USD", Timeframe.M5) == 1
    assert ohlcv_repo.count_candles("TEST-USD", Timeframe.M15) == 1
    assert ohlcv_repo.count_candles("TEST-USD", Timeframe.H1) == 1
    
    # Get available timeframes
    timeframes = ohlcv_repo.get_available_timeframes("TEST-USD")
    assert len(timeframes) == 3
    assert "5m" in timeframes
    assert "15m" in timeframes
    assert "1h" in timeframes
