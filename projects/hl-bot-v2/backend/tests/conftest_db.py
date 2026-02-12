"""Test database configuration - SQLite-compatible models."""
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text, 
    CheckConstraint, Index, JSON
)
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

TestBase = declarative_base()


class OHLCVDataTest(TestBase):
    """
    OHLCV candlestick data - Test-compatible version.
    """
    __tablename__ = "ohlcv_data"
    
    # Primary key: composite of timestamp, symbol, timeframe, and source
    timestamp = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    symbol = Column(String(20), primary_key=True, nullable=False)
    timeframe = Column(String(10), primary_key=True, nullable=False)
    source = Column(String(20), primary_key=True, nullable=False, default='csv')
    
    # OHLCV fields
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False, default=0.0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class DataSyncStateTest(TestBase):
    """
    Track sync state - Test-compatible version.
    """
    __tablename__ = "data_sync_state"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Identification
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    source = Column(String(50), nullable=False, default='hyperliquid')
    
    # Sync state
    last_sync_timestamp = Column(DateTime(timezone=True))
    last_sync_at = Column(DateTime(timezone=True))
    oldest_timestamp = Column(DateTime(timezone=True))
    newest_timestamp = Column(DateTime(timezone=True))
    candle_count = Column(Integer, default=0)
    
    # Sync status
    is_syncing = Column(Boolean, default=False)
    sync_error = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
