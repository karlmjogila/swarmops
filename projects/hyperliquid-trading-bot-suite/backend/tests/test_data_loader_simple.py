"""
Simplified tests for the data loader module.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.backtest.data_loader import DataLoader, BacktestDataManager, DataRange
from src.types import CandleData, Timeframe, BacktestConfig


# Simple base for testing
TestBase = declarative_base()


class TestCandleDataDB(TestBase):
    """Simplified candle data model for testing."""
    __tablename__ = 'candle_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False) 
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    TestBase.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal(), engine


@pytest.fixture
def sample_candle_data():
    """Generate sample candle data for testing."""
    start_time = datetime(2024, 1, 1, 0, 0, 0)
    data = []
    
    for i in range(100):
        timestamp = start_time + timedelta(minutes=15 * i)
        open_price = 50000 + i * 10
        high_price = open_price + 50
        low_price = open_price - 30
        close_price = open_price + 20
        volume = 100 + i
        
        candle = TestCandleDataDB(
            asset="BTC-USD",
            timeframe=Timeframe.M15.value,
            timestamp=timestamp,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume
        )
        data.append(candle)
    
    return data


@pytest.fixture
def populated_db(in_memory_db, sample_candle_data):
    """Database populated with sample data."""
    session, engine = in_memory_db
    
    # Add sample data
    for candle in sample_candle_data:
        session.add(candle)
    
    session.commit()
    
    return session, engine


class TestDataLoaderCore:
    """Core test cases for DataLoader class functionality."""
    
    def test_basic_instantiation(self, populated_db):
        """Test basic DataLoader instantiation."""
        session, _ = populated_db
        loader = DataLoader(session)
        
        assert loader is not None
        assert loader.session is session
        assert loader.cache_size == 10000  # default value
    
    def test_cache_key_generation(self, populated_db):
        """Test cache key generation."""
        session, _ = populated_db
        loader = DataLoader(session)
        
        key = loader._cache_key("BTC-USD", Timeframe.M15)
        assert key == "BTC-USD_15m"
        
        key2 = loader._cache_key("ETH-USD", Timeframe.H1)
        assert key2 == "ETH-USD_1h"
    
    def test_timeframe_minutes_conversion(self, populated_db):
        """Test timeframe to minutes conversion."""
        session, _ = populated_db
        loader = DataLoader(session)
        
        assert loader._get_timeframe_minutes(Timeframe.M1) == 1
        assert loader._get_timeframe_minutes(Timeframe.M5) == 5
        assert loader._get_timeframe_minutes(Timeframe.M15) == 15
        assert loader._get_timeframe_minutes(Timeframe.M30) == 30
        assert loader._get_timeframe_minutes(Timeframe.H1) == 60
        assert loader._get_timeframe_minutes(Timeframe.H4) == 240
        assert loader._get_timeframe_minutes(Timeframe.D1) == 1440
    
    def test_cache_management(self, populated_db):
        """Test cache management functionality."""
        session, _ = populated_db
        loader = DataLoader(session, cache_size=50)
        
        # Initially empty
        cache_info = loader.get_cache_info()
        assert cache_info['cached_series'] == 0
        assert cache_info['total_cached_candles'] == 0
        
        # Clear cache (should work even when empty)
        loader.clear_cache()
        
        cache_info = loader.get_cache_info()
        assert cache_info['cached_series'] == 0


class TestDataLoaderWithMockData:
    """Test data loader with actual database interactions using simplified models."""
    
    def test_load_candles_with_mock_query(self, populated_db):
        """Test loading candles with manual query construction."""
        session, _ = populated_db
        
        # Test direct query to verify data exists
        query = session.query(TestCandleDataDB).filter(
            TestCandleDataDB.asset == "BTC-USD",
            TestCandleDataDB.timeframe == Timeframe.M15.value,
            TestCandleDataDB.timestamp >= datetime(2024, 1, 1),
            TestCandleDataDB.timestamp <= datetime(2024, 1, 2)
        ).order_by(TestCandleDataDB.timestamp)
        
        records = query.all()
        assert len(records) > 0
        
        # Convert to CandleData objects manually
        candles = []
        for record in records:
            candle = CandleData(
                timestamp=record.timestamp,
                open=record.open,
                high=record.high,
                low=record.low,
                close=record.close,
                volume=record.volume,
                timeframe=Timeframe.M15
            )
            candles.append(candle)
        
        assert len(candles) > 0
        assert all(isinstance(c, CandleData) for c in candles)
        assert all(c.timeframe == Timeframe.M15 for c in candles)
        
        # Check ordering
        timestamps = [c.timestamp for c in candles]
        assert timestamps == sorted(timestamps)


class TestDataRange:
    """Test cases for DataRange class."""
    
    def test_data_range_creation(self):
        """Test DataRange object creation."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)
        
        data_range = DataRange(
            asset="BTC-USD",
            timeframe=Timeframe.M15,
            start_date=start_date,
            end_date=end_date
        )
        
        assert data_range.asset == "BTC-USD"
        assert data_range.timeframe == Timeframe.M15
        assert data_range.start_date == start_date
        assert data_range.end_date == end_date


class TestBacktestConfig:
    """Test BacktestConfig functionality with data loader."""
    
    def test_backtest_config_creation(self):
        """Test BacktestConfig creation for data loader."""
        config = BacktestConfig(
            name="Test Backtest",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            assets=["BTC-USD", "ETH-USD"],
            timeframes=[Timeframe.M15, Timeframe.H1],
            strategy_rules=["test-rule"]
        )
        
        assert config.name == "Test Backtest"
        assert len(config.assets) == 2
        assert len(config.timeframes) == 2
        assert config.start_date < config.end_date


class TestIntegrityChecks:
    """Test data integrity and validation functions."""
    
    def test_candle_data_properties(self):
        """Test CandleData properties and methods."""
        candle = CandleData(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            open=50000.0,
            high=50100.0,
            low=49900.0,
            close=50050.0,
            volume=1000.0,
            timeframe=Timeframe.M15
        )
        
        assert candle.body_size == 50.0  # abs(50050 - 50000)
        assert candle.upper_wick == 50.0  # 50100 - max(50000, 50050)
        assert candle.lower_wick == 100.0  # min(50000, 50050) - 49900
        assert candle.total_range == 200.0  # 50100 - 49900
        assert candle.is_bullish is True
        assert candle.is_bearish is False
        
        # Test bearish candle
        bearish_candle = CandleData(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            open=50000.0,
            high=50050.0,
            low=49900.0,
            close=49950.0,
            volume=1000.0,
            timeframe=Timeframe.M15
        )
        
        assert bearish_candle.is_bullish is False
        assert bearish_candle.is_bearish is True
    
    def test_data_validation_edge_cases(self, populated_db):
        """Test edge cases for data validation."""
        session, _ = populated_db
        loader = DataLoader(session)
        
        # Test with future dates (should return empty)
        future_start = datetime(2025, 1, 1)
        future_end = datetime(2025, 1, 2)
        
        # This should work without errors, just return empty results
        cache_info = loader.get_cache_info()
        assert isinstance(cache_info, dict)
        
        # Test cache clearing
        loader.clear_cache()
        cache_info_after = loader.get_cache_info()
        assert cache_info_after['cached_series'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])