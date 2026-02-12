"""Integration tests for data sync service."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.conftest_db import TestBase
from app.db.repositories.ohlcv import OHLCVRepository
from app.db.repositories.sync_state import SyncStateRepository
from app.services.data_sync import DataSyncService, SyncMode, SyncResult
from app.services.hyperliquid_data import Candle


# Use SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    engine = create_engine(TEST_DATABASE_URL)
    TestBase.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    TestBase.metadata.drop_all(engine)


@pytest.fixture
def ohlcv_repo(db_session):
    """Create OHLCV repository."""
    return OHLCVRepository(db_session)


@pytest.fixture
def sync_repo(db_session):
    """Create sync state repository."""
    return SyncStateRepository(db_session)


class TestSyncStateRepository:
    """Tests for SyncStateRepository."""
    
    def test_create_sync_state(self, sync_repo, db_session):
        """Test creating a new sync state."""
        state = sync_repo.create_or_update_sync_state(
            symbol="BTC",
            timeframe="5m",
            candle_count=100,
        )
        db_session.commit()
        
        assert state.symbol == "BTC"
        assert state.timeframe == "5m"
        assert state.candle_count == 100
        assert state.is_syncing is False
    
    def test_update_sync_state(self, sync_repo, db_session):
        """Test updating existing sync state."""
        # Create initial state
        sync_repo.create_or_update_sync_state(
            symbol="BTC",
            timeframe="5m",
            candle_count=100,
        )
        db_session.commit()
        
        # Update it
        state = sync_repo.create_or_update_sync_state(
            symbol="BTC",
            timeframe="5m",
            candle_count=200,
            newest_timestamp=datetime.now(timezone.utc),
        )
        db_session.commit()
        
        assert state.candle_count == 200
        assert state.newest_timestamp is not None
    
    def test_get_sync_state(self, sync_repo, db_session):
        """Test retrieving sync state."""
        sync_repo.create_or_update_sync_state(
            symbol="ETH",
            timeframe="1h",
            candle_count=50,
        )
        db_session.commit()
        
        state = sync_repo.get_sync_state("ETH", "1h")
        
        assert state is not None
        assert state.symbol == "ETH"
        assert state.candle_count == 50
    
    def test_get_nonexistent_sync_state(self, sync_repo):
        """Test getting non-existent state returns None."""
        state = sync_repo.get_sync_state("FAKE", "1m")
        assert state is None
    
    def test_set_syncing_status(self, sync_repo, db_session):
        """Test setting syncing status."""
        sync_repo.set_syncing("BTC", "5m", True)
        db_session.commit()
        
        state = sync_repo.get_sync_state("BTC", "5m")
        assert state.is_syncing is True
        
        sync_repo.set_syncing("BTC", "5m", False, error="Test error")
        db_session.commit()
        
        state = sync_repo.get_sync_state("BTC", "5m")
        assert state.is_syncing is False
        assert state.sync_error == "Test error"
    
    def test_get_all_sync_states(self, sync_repo, db_session):
        """Test getting all sync states."""
        sync_repo.create_or_update_sync_state("BTC", "5m")
        sync_repo.create_or_update_sync_state("ETH", "1h")
        sync_repo.create_or_update_sync_state("SOL", "4h")
        db_session.commit()
        
        states = sync_repo.get_all_sync_states()
        assert len(states) == 3
    
    def test_delete_sync_state(self, sync_repo, db_session):
        """Test deleting sync state."""
        sync_repo.create_or_update_sync_state("BTC", "5m")
        db_session.commit()
        
        result = sync_repo.delete_sync_state("BTC", "5m")
        db_session.commit()
        
        assert result is True
        assert sync_repo.get_sync_state("BTC", "5m") is None


class TestDataSyncService:
    """Tests for DataSyncService."""
    
    @pytest.fixture
    def mock_candles(self):
        """Create mock candle data."""
        base_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        return [
            Candle(
                timestamp=base_time + timedelta(minutes=5 * i),
                open=100.0 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.5 + i,
                volume=1000.0,
            )
            for i in range(10)
        ]
    
    @pytest.mark.asyncio
    async def test_sync_full(self, db_session, mock_candles):
        """Test full sync operation."""
        with patch('app.services.data_sync.HyperliquidDataFetcher') as MockFetcher:
            # Setup mock
            mock_fetcher_instance = MagicMock()
            mock_fetcher_instance.fetch_all_candles = AsyncMock(return_value=mock_candles)
            MockFetcher.return_value = mock_fetcher_instance
            
            service = DataSyncService(db_session)
            
            result = await service.sync(
                symbol="BTC",
                timeframe="5m",
                mode=SyncMode.FULL,
            )
            
            assert result.success is True
            assert result.candles_fetched == 10
            assert result.candles_inserted > 0
    
    @pytest.mark.asyncio
    async def test_sync_incremental(self, db_session, mock_candles):
        """Test incremental sync."""
        # First, do a full sync
        with patch('app.services.data_sync.HyperliquidDataFetcher') as MockFetcher:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_all_candles = AsyncMock(return_value=mock_candles[:5])
            mock_fetcher.fetch_incremental = AsyncMock(return_value=mock_candles[5:])
            MockFetcher.return_value = mock_fetcher
            
            service = DataSyncService(db_session)
            
            # Full sync first
            await service.sync("BTC", "5m", mode=SyncMode.FULL)
            
            # Then incremental
            result = await service.sync("BTC", "5m", mode=SyncMode.INCREMENTAL)
            
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_sync_error_handling(self, db_session):
        """Test sync error handling."""
        with patch('app.services.data_sync.HyperliquidDataFetcher') as MockFetcher:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_all_candles = AsyncMock(side_effect=Exception("API Error"))
            MockFetcher.return_value = mock_fetcher
            
            service = DataSyncService(db_session)
            
            result = await service.sync("BTC", "5m", mode=SyncMode.FULL)
            
            assert result.success is False
            assert "API Error" in result.error
    
    @pytest.mark.asyncio
    async def test_get_sync_status(self, db_session, mock_candles):
        """Test getting sync status."""
        with patch('app.services.data_sync.HyperliquidDataFetcher') as MockFetcher:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_all_candles = AsyncMock(return_value=mock_candles)
            MockFetcher.return_value = mock_fetcher
            
            service = DataSyncService(db_session)
            await service.sync("BTC", "5m", mode=SyncMode.FULL)
            
            status = service.get_sync_status("BTC", "5m")
            
            assert status.symbol == "BTC"
            assert status.timeframe == "5m"
            assert status.candle_count > 0
    
    @pytest.mark.asyncio
    async def test_get_available_symbols(self, db_session):
        """Test getting available symbols from Hyperliquid."""
        with patch('app.services.data_sync.HyperliquidDataFetcher') as MockFetcher:
            mock_fetcher = MagicMock()
            mock_fetcher.get_available_coins = AsyncMock(return_value=["BTC", "ETH", "SOL"])
            MockFetcher.return_value = mock_fetcher
            
            service = DataSyncService(db_session)
            symbols = await service.get_available_symbols()
            
            assert "BTC" in symbols
            assert "ETH" in symbols
            assert "SOL" in symbols
    
    def test_get_available_data(self, db_session, ohlcv_repo, sync_repo):
        """Test getting available local data summary."""
        # Add some test data
        now = datetime.now(timezone.utc)
        ohlcv_repo.insert_candle("BTC", "5m", now, 100, 101, 99, 100.5, 1000)
        ohlcv_repo.insert_candle("ETH", "1h", now, 200, 201, 199, 200.5, 500)
        
        sync_repo.create_or_update_sync_state(
            "BTC", "5m",
            candle_count=1,
            oldest_timestamp=now,
            newest_timestamp=now,
        )
        sync_repo.create_or_update_sync_state(
            "ETH", "1h",
            candle_count=1,
            oldest_timestamp=now,
            newest_timestamp=now,
        )
        db_session.commit()
        
        service = DataSyncService(db_session)
        data = service.get_available_data()
        
        assert "BTC" in data["symbols"]
        assert "ETH" in data["symbols"]
        assert "5m" in data["timeframes"]
        assert "1h" in data["timeframes"]
        assert len(data["details"]) >= 2


class TestSyncResult:
    """Tests for SyncResult."""
    
    def test_to_dict(self):
        """Test result serialization."""
        result = SyncResult(
            symbol="BTC",
            timeframe="5m",
            mode=SyncMode.FULL,
            success=True,
            candles_fetched=100,
            candles_inserted=95,
        )
        result.completed_at = datetime.now(timezone.utc)
        
        data = result.to_dict()
        
        assert data["symbol"] == "BTC"
        assert data["timeframe"] == "5m"
        assert data["success"] is True
        assert data["candles_fetched"] == 100
        assert data["candles_inserted"] == 95
        assert "duration_seconds" in data
