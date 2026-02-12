"""
Tests for the data loader module.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os

from src.backtest.data_loader import DataLoader, BacktestDataManager, DataRange
from src.database.models import Base, CandleDataDB
from src.types import CandleData, Timeframe, BacktestConfig


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
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
        
        candle = CandleDataDB(
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


class TestDataLoader:
    """Test cases for DataLoader class."""
    
    def test_load_candles_basic(self, populated_db):
        """Test basic candle loading functionality."""
        session, _ = populated_db
        loader = DataLoader(session)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)
        
        candles = loader.load_candles(
            asset="BTC-USD",
            timeframe=Timeframe.M15,
            start_date=start_date,
            end_date=end_date
        )
        
        assert len(candles) > 0
        assert all(isinstance(c, CandleData) for c in candles)
        assert all(c.timeframe == Timeframe.M15 for c in candles)
        
        # Check ordering
        timestamps = [c.timestamp for c in candles]
        assert timestamps == sorted(timestamps)
    
    def test_load_candles_empty_result(self, populated_db):
        """Test loading candles when no data exists."""
        session, _ = populated_db
        loader = DataLoader(session)
        
        # Query for non-existent asset
        candles = loader.load_candles(
            asset="ETH-USD",
            timeframe=Timeframe.M15,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2)
        )
        
        assert len(candles) == 0
    
    def test_cache_functionality(self, populated_db):
        """Test data caching functionality."""
        session, _ = populated_db
        loader = DataLoader(session, cache_size=50)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)
        
        # First load (should hit database)
        candles1 = loader.load_candles(
            asset="BTC-USD",
            timeframe=Timeframe.M15,
            start_date=start_date,
            end_date=end_date,
            use_cache=True
        )
        
        # Second load (should use cache)
        candles2 = loader.load_candles(
            asset="BTC-USD",
            timeframe=Timeframe.M15,
            start_date=start_date,
            end_date=end_date,
            use_cache=True
        )
        
        assert len(candles1) == len(candles2)
        assert len(candles1) > 0
        
        # Check cache info
        cache_info = loader.get_cache_info()
        assert cache_info['cached_series'] > 0
        assert cache_info['total_cached_candles'] > 0
    
    def test_streaming_data_load(self, populated_db):
        """Test streaming data loading."""
        session, _ = populated_db
        loader = DataLoader(session)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)  # Longer range
        
        all_candles = []
        batch_count = 0
        
        for batch in loader.load_candles_streaming(
            asset="BTC-USD",
            timeframe=Timeframe.M15,
            start_date=start_date,
            end_date=end_date,
            batch_size=10
        ):
            assert len(batch) <= 10
            assert all(isinstance(c, CandleData) for c in batch)
            all_candles.extend(batch)
            batch_count += 1
        
        assert batch_count > 0
        assert len(all_candles) > 0
    
    def test_get_latest_candle(self, populated_db):
        """Test getting the latest candle."""
        session, _ = populated_db
        loader = DataLoader(session)
        
        latest = loader.get_latest_candle("BTC-USD", Timeframe.M15)
        
        assert latest is not None
        assert isinstance(latest, CandleData)
        assert latest.timeframe == Timeframe.M15
    
    def test_get_data_availability(self, populated_db):
        """Test data availability checking."""
        session, _ = populated_db
        loader = DataLoader(session)
        
        availability = loader.get_data_availability("BTC-USD", Timeframe.M15)
        
        assert availability is not None
        earliest, latest = availability
        assert isinstance(earliest, datetime)
        assert isinstance(latest, datetime)
        assert earliest <= latest
    
    def test_data_validation(self, populated_db):
        """Test data quality validation."""
        session, _ = populated_db
        loader = DataLoader(session)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)
        
        quality_metrics = loader.validate_data_quality(
            asset="BTC-USD",
            timeframe=Timeframe.M15,
            start_date=start_date,
            end_date=end_date
        )
        
        assert 'total_candles' in quality_metrics
        assert 'data_completeness' in quality_metrics
        assert 'quality_score' in quality_metrics
        assert 'gaps' in quality_metrics
        
        assert quality_metrics['total_candles'] >= 0
        assert 0.0 <= quality_metrics['data_completeness'] <= 1.0
        assert 0.0 <= quality_metrics['quality_score'] <= 1.0


class TestBacktestDataManager:
    """Test cases for BacktestDataManager class."""
    
    def test_prepare_backtest_data(self, populated_db):
        """Test backtest data preparation."""
        session, _ = populated_db
        manager = BacktestDataManager(session)
        
        config = BacktestConfig(
            name="Test Backtest",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            assets=["BTC-USD"],
            timeframes=[Timeframe.M15],
            strategy_rules=["test-rule-1"]
        )
        
        report = manager.prepare_backtest_data(config)
        
        assert 'config' in report
        assert 'availability' in report
        assert 'quality' in report
        assert report['data_loaded'] is True
        
        # Check availability report structure
        availability = report['availability']
        assert 'BTC-USD' in availability
        assert Timeframe.M15.value in availability['BTC-USD']
    
    def test_get_candles_at_time(self, populated_db):
        """Test getting candles at a specific time."""
        session, _ = populated_db
        manager = BacktestDataManager(session)
        
        config = BacktestConfig(
            name="Test Backtest",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 3),
            assets=["BTC-USD"],
            timeframes=[Timeframe.M15],
            strategy_rules=["test-rule-1"]
        )
        
        manager.prepare_backtest_data(config)
        
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        candles = manager.get_candles_at_time(
            asset="BTC-USD",
            timeframe=Timeframe.M15,
            timestamp=timestamp,
            lookback_count=10
        )
        
        assert len(candles) <= 10
        assert all(c.timestamp <= timestamp for c in candles)
        assert all(isinstance(c, CandleData) for c in candles)
    
    def test_available_assets_and_timeframes(self, populated_db):
        """Test getting available assets and timeframes."""
        session, _ = populated_db
        manager = BacktestDataManager(session)
        
        config = BacktestConfig(
            name="Test Backtest",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            assets=["BTC-USD"],
            timeframes=[Timeframe.M15],
            strategy_rules=["test-rule-1"]
        )
        
        manager.prepare_backtest_data(config)
        
        assets = manager.get_available_assets()
        assert "BTC-USD" in assets
        
        timeframes = manager.get_available_timeframes("BTC-USD")
        assert Timeframe.M15 in timeframes


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


class TestIntegration:
    """Integration tests for the data loader components."""
    
    def test_full_backtest_data_workflow(self, populated_db):
        """Test complete workflow from config to data access."""
        session, _ = populated_db
        
        # Create backtest configuration
        config = BacktestConfig(
            name="Integration Test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            assets=["BTC-USD"],
            timeframes=[Timeframe.M15],
            initial_balance=10000.0,
            strategy_rules=["test-rule"]
        )
        
        # Initialize data loader
        loader = DataLoader(session)
        
        # Load data for backtest
        backtest_data = loader.load_data_for_backtest(config)
        
        # Verify data structure
        assert "BTC-USD" in backtest_data
        assert Timeframe.M15 in backtest_data["BTC-USD"]
        
        candles = backtest_data["BTC-USD"][Timeframe.M15]
        assert len(candles) > 0
        assert all(isinstance(c, CandleData) for c in candles)
        
        # Test data manager workflow
        manager = BacktestDataManager(session)
        report = manager.prepare_backtest_data(config)
        
        assert report['data_loaded'] is True
        
        # Test time-based access
        test_time = datetime(2024, 1, 1, 6, 0, 0)
        historical_candles = manager.get_candles_at_time(
            "BTC-USD", Timeframe.M15, test_time, 20
        )
        
        assert all(c.timestamp <= test_time for c in historical_candles)
        assert len(historical_candles) <= 20


if __name__ == "__main__":
    pytest.main([__file__])