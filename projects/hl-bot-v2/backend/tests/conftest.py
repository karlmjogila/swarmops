"""Pytest configuration and shared fixtures."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.db.models import OHLCVData


# Create in-memory SQLite engine for unit tests
# Use StaticPool to share the connection across threads
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Enable foreign keys for SQLite
@event.listens_for(_test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=_test_engine,
)


@pytest.fixture(scope="function")
def db_session():
    """
    Create an isolated database session for each test.
    
    Uses SQLite in-memory database for fast, isolated tests.
    Creates only the OHLCVData table (not other models with PostgreSQL-specific types).
    """
    # Create only the OHLCVData table - this avoids PostgreSQL-specific type issues
    # with other models like StrategyRule (which uses JSONB, UUID, etc.)
    OHLCVData.__table__.create(bind=_test_engine, checkfirst=True)
    
    # Create session
    session = TestSessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Drop the table after test
        OHLCVData.__table__.drop(bind=_test_engine, checkfirst=True)


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def example_data():
    """Example data for testing."""
    return {
        "symbol": "BTC-USD",
        "side": "buy",
        "order_type": "limit",
        "quantity": 0.1,
        "price": 50000.0,
    }
