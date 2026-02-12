"""Database session management.

Following Database Excellence principles:
- Connection pooling
- Pre-ping for connection health
- Proper session lifecycle management
"""

from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

# Import from the existing app/db structure where models are defined
import sys
sys.path.insert(0, '/opt/swarmops/projects/hl-bot-v2/backend')
from app.config import settings
from app.db.models import Base

# Synchronous engine (for migrations and sync operations)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.is_development,  # Log SQL in development
    pool_size=10,  # Connection pool size
    max_overflow=20,  # Max connections beyond pool_size
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """Get database session for dependency injection.
    
    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Model).all()
    
    Yields:
        Database session that is automatically closed after use
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a database session for manual management.
    
    Note: Caller is responsible for closing the session.
    Prefer get_db() for FastAPI dependency injection.
    
    Returns:
        Database session
    """
    return SessionLocal()
