"""FastAPI dependency injection utilities."""

from functools import lru_cache
from typing import Generator

from sqlalchemy.orm import Session

from hl_bot.config import Settings, get_settings
from hl_bot.db.session import get_db as get_db_session
from hl_bot.repositories import OHLCVRepository


@lru_cache
def get_settings_cached() -> Settings:
    """Get cached settings instance for dependency injection."""
    return get_settings()


def get_db() -> Generator[Session, None, None]:
    """Get database session for dependency injection.
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    yield from get_db_session()


def get_ohlcv_repository(db: Session) -> OHLCVRepository:
    """Get OHLCV repository instance.
    
    Usage:
        @app.get("/candles")
        def get_candles(
            repo: OHLCVRepository = Depends(get_ohlcv_repository),
        ):
            ...
    """
    return OHLCVRepository(db)
