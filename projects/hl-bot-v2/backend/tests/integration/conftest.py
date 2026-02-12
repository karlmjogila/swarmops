"""Integration test fixtures and configuration."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.models import Base, OHLCVData
from app.db.session import get_db


# ==============================================================================
# Database Fixtures
# ==============================================================================

@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test function.
    
    Uses in-memory SQLite for fast, isolated tests.
    Each test gets a fresh database.
    Only creates the OHLCVData table (other tables use JSONB which SQLite doesn't support).
    """
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Only create the OHLCVData table (others have JSONB which isn't supported by SQLite)
    OHLCVData.__table__.create(bind=engine, checkfirst=True)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        OHLCVData.__table__.drop(bind=engine, checkfirst=True)


@pytest.fixture(scope="function")
def override_get_db(test_db: Session):
    """Override the get_db dependency with test database."""
    def _override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    return _override_get_db


@pytest_asyncio.fixture
async def client(test_db: Session, override_get_db):
    """Async HTTP client for testing FastAPI endpoints.
    
    Automatically uses test database instead of real database.
    """
    # Override the database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    # Clean up
    app.dependency_overrides.clear()


# ==============================================================================
# Data Fixtures
# ==============================================================================

@pytest.fixture
def sample_ohlcv_data(test_db: Session):
    """Create sample OHLCV data for testing.
    
    Creates 100 candles for BTC-USD 5m timeframe spanning 8+ hours.
    """
    candles = []
    base_timestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    base_price = 42000.0
    
    for i in range(100):
        timestamp = base_timestamp + timedelta(minutes=5 * i)
        
        # Generate realistic OHLC data with some price movement
        open_price = base_price + (i * 10) + ((i % 10) * 5)
        high = open_price + 50 + (i % 20)
        low = open_price - 30 - (i % 15)
        close = open_price + ((i % 5) - 2) * 10
        volume = 1000 + (i * 10)
        
        candle = OHLCVData(
            symbol="BTC-USD",
            timeframe="5m",
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            created_at=datetime.now(timezone.utc),
        )
        candles.append(candle)
    
    # Bulk insert
    test_db.bulk_save_objects(candles)
    test_db.commit()
    
    return candles


@pytest.fixture
def multi_symbol_data(test_db: Session):
    """Create sample data for multiple symbols and timeframes.
    
    Creates data for:
    - BTC-USD: 5m, 15m, 1h
    - ETH-USD: 5m, 1h
    - SOL-USD: 15m
    """
    candles = []
    base_timestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    configs = [
        ("BTC-USD", "5m", 5, 42000.0, 50),
        ("BTC-USD", "15m", 15, 42000.0, 30),
        ("BTC-USD", "1h", 60, 42000.0, 24),
        ("ETH-USD", "5m", 5, 2500.0, 50),
        ("ETH-USD", "1h", 60, 2500.0, 24),
        ("SOL-USD", "15m", 15, 100.0, 30),
    ]
    
    for symbol, timeframe, interval_minutes, base_price, count in configs:
        for i in range(count):
            timestamp = base_timestamp + timedelta(minutes=interval_minutes * i)
            
            open_price = base_price + (i * 5)
            high = open_price + (base_price * 0.01)
            low = open_price - (base_price * 0.008)
            close = open_price + ((i % 3) - 1) * (base_price * 0.005)
            volume = 1000 + (i * 10)
            
            candle = OHLCVData(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                created_at=datetime.now(timezone.utc),
            )
            candles.append(candle)
    
    test_db.bulk_save_objects(candles)
    test_db.commit()
    
    return candles


@pytest.fixture
def example_data():
    """Example data for testing (reusable across tests)."""
    return {
        "symbol": "BTC-USD",
        "timeframe": "5m",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "price": 42000.0,
        "volume": 1000.0,
    }


# ==============================================================================
# Mock Fixtures
# ==============================================================================

@pytest.fixture
def mock_csv_importer(mocker):
    """Mock CSV importer for testing without file I/O."""
    mock = mocker.patch("app.api.routes.data.CSVImporter")
    return mock


@pytest.fixture
def mock_subprocess(mocker):
    """Mock subprocess.Popen for testing backtest without actually running scripts."""
    mock = mocker.patch("app.api.routes.backtest.subprocess.Popen")
    mock_process = mocker.MagicMock()
    mock_process.poll.return_value = None  # Process is running
    mock.return_value = mock_process
    return mock


# ==============================================================================
# Utility Functions
# ==============================================================================

def create_test_candle(
    symbol: str = "BTC-USD",
    timeframe: str = "5m",
    timestamp: datetime = None,
    open_price: float = 42000.0,
) -> OHLCVData:
    """Helper function to create a test candle with defaults."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    return OHLCVData(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        open=open_price,
        high=open_price + 100,
        low=open_price - 50,
        close=open_price + 25,
        volume=1000.0,
        created_at=datetime.now(timezone.utc),
    )


def assert_valid_iso_timestamp(timestamp_str: str) -> bool:
    """Helper to validate ISO format timestamp strings."""
    try:
        datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False
