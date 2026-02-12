"""
Database configuration and utilities for the Hyperliquid Trading Bot Suite.
"""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .models import Base, create_additional_indexes


class DatabaseConfig:
    """Database configuration settings."""
    
    def __init__(self):
        # PostgreSQL connection settings
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', '5432'))
        self.database = os.getenv('DB_NAME', 'hyperliquid_bot')
        self.username = os.getenv('DB_USER', 'hyperliquid_user')
        self.password = os.getenv('DB_PASSWORD', 'hyperliquid_pass')
        
        # Connection pool settings
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '10'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '20'))
        self.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        self.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))  # 1 hour
        
        # SSL settings
        self.ssl_mode = os.getenv('DB_SSL_MODE', 'prefer')
        
    @property
    def database_url(self) -> str:
        """Construct database URL from settings."""
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
            f"?sslmode={self.ssl_mode}"
        )


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig()
        self._engine = None
        self._session_factory = None
        
    @property
    def engine(self) -> Engine:
        """Get or create database engine."""
        if self._engine is None:
            self._engine = create_engine(
                self.config.database_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=os.getenv('DB_ECHO', 'false').lower() == 'true',
                future=True
            )
        return self._engine
    
    @property 
    def session_factory(self) -> sessionmaker:
        """Get or create session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
        return self._session_factory
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_tables(self, drop_existing: bool = False):
        """Create all database tables."""
        if drop_existing:
            Base.metadata.drop_all(bind=self.engine)
        
        Base.metadata.create_all(bind=self.engine)
        
        # Create additional performance indexes
        create_additional_indexes(self.engine)
        
        print("Database tables and indexes created successfully")
    
    def drop_tables(self):
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)
        print("Database tables dropped successfully")
    
    def check_connection(self) -> bool:
        """Test database connection."""
        try:
            from sqlalchemy import text
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions
def get_session() -> Generator[Session, None, None]:
    """Get a database session (convenience function)."""
    return db_manager.get_session()

def get_engine() -> Engine:
    """Get database engine (convenience function)."""
    return db_manager.engine

def create_tables(drop_existing: bool = False):
    """Create database tables (convenience function)."""
    return db_manager.create_tables(drop_existing)

def drop_tables():
    """Drop database tables (convenience function)."""
    return db_manager.drop_tables()

def check_connection() -> bool:
    """Check database connection (convenience function)."""
    return db_manager.check_connection()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for getting database sessions.
    
    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    session = db_manager.session_factory()
    try:
        yield session
    finally:
        session.close()


__all__ = [
    "DatabaseConfig",
    "DatabaseManager", 
    "db_manager",
    "get_session",
    "get_db",
    "get_engine",
    "create_tables",
    "drop_tables", 
    "check_connection",
]