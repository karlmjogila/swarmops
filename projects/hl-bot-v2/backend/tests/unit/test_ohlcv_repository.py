"""Unit tests for OHLCV repository."""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.db.models import OHLCVData
from app.db.repositories.ohlcv import OHLCVRepository


@pytest.fixture
def sample_candles():
    """Generate sample candle data for testing."""
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    candles = []
    
    for i in range(10):
        timestamp = base_time + timedelta(minutes=5 * i)
        candles.append({
            "symbol": "BTC-USD",
            "timeframe": "5m",
            "timestamp": timestamp,
            "open": 50000.0 + i * 10,
            "high": 50100.0 + i * 10,
            "low": 49900.0 + i * 10,
            "close": 50050.0 + i * 10,
            "volume": 100.0 + i,
        })
    
    return candles


def test_insert_single_candle(db_session: Session):
    """Test inserting a single candle."""
    repo = OHLCVRepository(db_session)
    
    candle = repo.insert_candle(
        symbol="BTC-USD",
        timeframe="5m",
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        open_price=50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=100.0,
    )
    
    assert candle is not None
    assert candle.symbol == "BTC-USD"
    assert candle.open == 50000.0
    db_session.commit()


def test_insert_duplicate_candle(db_session: Session):
    """Test that duplicate candles are silently ignored."""
    repo = OHLCVRepository(db_session)
    
    # Insert first candle
    candle1 = repo.insert_candle(
        symbol="BTC-USD",
        timeframe="5m",
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        open_price=50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=100.0,
    )
    db_session.commit()
    assert candle1 is not None
    
    # Try to insert duplicate
    candle2 = repo.insert_candle(
        symbol="BTC-USD",
        timeframe="5m",
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        open_price=51000.0,  # Different price
        high=51100.0,
        low=50900.0,
        close=51050.0,
        volume=200.0,
    )
    
    # Should return None for duplicate
    assert candle2 is None


def test_bulk_insert_candles(db_session: Session, sample_candles):
    """Test bulk inserting multiple candles."""
    repo = OHLCVRepository(db_session)
    
    count = repo.bulk_insert_candles(sample_candles)
    db_session.commit()
    
    assert count == 10
    
    # Verify data was inserted
    all_candles = db_session.query(OHLCVData).filter_by(
        symbol="BTC-USD",
        timeframe="5m",
    ).all()
    assert len(all_candles) == 10


def _strip_tz(dt):
    """Strip timezone info for SQLite compatibility in comparisons."""
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def test_get_candles_in_range(db_session: Session, sample_candles):
    """Test retrieving candles within a time range."""
    repo = OHLCVRepository(db_session)
    repo.bulk_insert_candles(sample_candles)
    db_session.commit()
    
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2024, 1, 1, 0, 20, tzinfo=timezone.utc)
    
    candles = repo.get_candles("BTC-USD", "5m", start_time, end_time)
    
    # Should get 5 candles (0:00, 0:05, 0:10, 0:15, 0:20)
    assert len(candles) == 5
    # SQLite doesn't preserve timezone, so compare naive timestamps
    assert _strip_tz(candles[0].timestamp) == _strip_tz(start_time)
    assert _strip_tz(candles[-1].timestamp) == _strip_tz(end_time)


def test_get_latest_candle(db_session: Session, sample_candles):
    """Test retrieving the latest candle."""
    repo = OHLCVRepository(db_session)
    repo.bulk_insert_candles(sample_candles)
    db_session.commit()
    
    latest = repo.get_latest_candle("BTC-USD", "5m")
    
    assert latest is not None
    # SQLite doesn't preserve timezone, so compare naive timestamps
    assert _strip_tz(latest.timestamp) == _strip_tz(sample_candles[-1]["timestamp"])


def test_get_last_n_candles(db_session: Session, sample_candles):
    """Test retrieving last N candles."""
    repo = OHLCVRepository(db_session)
    repo.bulk_insert_candles(sample_candles)
    db_session.commit()
    
    last_3 = repo.get_last_n_candles("BTC-USD", "5m", 3)
    
    assert len(last_3) == 3
    # Should be in ascending order (oldest first)
    assert last_3[0].timestamp < last_3[1].timestamp < last_3[2].timestamp
    # Should be the last 3 candles - SQLite doesn't preserve timezone
    assert _strip_tz(last_3[-1].timestamp) == _strip_tz(sample_candles[-1]["timestamp"])


def test_get_candles_since(db_session: Session, sample_candles):
    """Test retrieving candles after a specific timestamp."""
    repo = OHLCVRepository(db_session)
    repo.bulk_insert_candles(sample_candles)
    db_session.commit()
    
    since_time = datetime(2024, 1, 1, 0, 20, tzinfo=timezone.utc)
    candles = repo.get_candles_since("BTC-USD", "5m", since_time)
    
    # Should get candles after 0:20 (0:25, 0:30, 0:35, 0:40, 0:45)
    assert len(candles) == 5
    # SQLite doesn't preserve timezone, so strip for comparison
    since_naive = _strip_tz(since_time)
    assert all(_strip_tz(c.timestamp) > since_naive for c in candles)


def test_count_candles(db_session: Session, sample_candles):
    """Test counting candles."""
    repo = OHLCVRepository(db_session)
    repo.bulk_insert_candles(sample_candles)
    db_session.commit()
    
    count = repo.count_candles("BTC-USD", "5m")
    assert count == 10
    
    # Count with time range
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2024, 1, 1, 0, 20, tzinfo=timezone.utc)
    count_range = repo.count_candles("BTC-USD", "5m", start_time, end_time)
    assert count_range == 5


def test_get_time_range(db_session: Session, sample_candles):
    """Test getting time range for symbol and timeframe."""
    repo = OHLCVRepository(db_session)
    repo.bulk_insert_candles(sample_candles)
    db_session.commit()
    
    time_range = repo.get_time_range("BTC-USD", "5m")
    
    assert time_range is not None
    earliest, latest = time_range
    # SQLite doesn't preserve timezone, so strip for comparison
    assert _strip_tz(earliest) == _strip_tz(sample_candles[0]["timestamp"])
    assert _strip_tz(latest) == _strip_tz(sample_candles[-1]["timestamp"])


def test_get_available_symbols(db_session: Session, sample_candles):
    """Test getting list of available symbols."""
    repo = OHLCVRepository(db_session)
    repo.bulk_insert_candles(sample_candles)
    
    # Add candles for another symbol
    eth_candles = [{**c, "symbol": "ETH-USD"} for c in sample_candles[:3]]
    repo.bulk_insert_candles(eth_candles)
    db_session.commit()
    
    symbols = repo.get_available_symbols()
    assert "BTC-USD" in symbols
    assert "ETH-USD" in symbols
    assert len(symbols) == 2


def test_get_available_timeframes(db_session: Session, sample_candles):
    """Test getting list of available timeframes."""
    repo = OHLCVRepository(db_session)
    repo.bulk_insert_candles(sample_candles)
    
    # Add candles for another timeframe
    tf_15m = [{**c, "timeframe": "15m"} for c in sample_candles[:3]]
    repo.bulk_insert_candles(tf_15m)
    db_session.commit()
    
    timeframes = repo.get_available_timeframes("BTC-USD")
    assert "5m" in timeframes
    assert "15m" in timeframes
    assert len(timeframes) == 2


def test_delete_candles(db_session: Session, sample_candles):
    """Test deleting candles."""
    repo = OHLCVRepository(db_session)
    repo.bulk_insert_candles(sample_candles)
    db_session.commit()
    
    # Delete candles in a range
    start_time = datetime(2024, 1, 1, 0, 10, tzinfo=timezone.utc)
    end_time = datetime(2024, 1, 1, 0, 20, tzinfo=timezone.utc)
    deleted = repo.delete_candles("BTC-USD", "5m", start_time, end_time)
    db_session.commit()
    
    # Should delete 3 candles (0:10, 0:15, 0:20)
    assert deleted == 3
    
    # Verify remaining candles
    remaining = repo.count_candles("BTC-USD", "5m")
    assert remaining == 7


def test_get_ohlc_aggregates(db_session: Session, sample_candles):
    """Test getting OHLC aggregate statistics."""
    repo = OHLCVRepository(db_session)
    repo.bulk_insert_candles(sample_candles)
    db_session.commit()
    
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2024, 1, 1, 0, 45, tzinfo=timezone.utc)
    
    aggregates = repo.get_ohlc_aggregates("BTC-USD", "5m", start_time, end_time)
    
    assert aggregates is not None
    assert "min_low" in aggregates
    assert "max_high" in aggregates
    assert "total_volume" in aggregates
    assert "candle_count" in aggregates
    assert aggregates["candle_count"] == 10


def test_no_data_returns_none(db_session: Session):
    """Test that queries return None/empty when no data exists."""
    repo = OHLCVRepository(db_session)
    
    latest = repo.get_latest_candle("BTC-USD", "5m")
    assert latest is None
    
    time_range = repo.get_time_range("BTC-USD", "5m")
    assert time_range is None
    
    symbols = repo.get_available_symbols()
    assert symbols == []
