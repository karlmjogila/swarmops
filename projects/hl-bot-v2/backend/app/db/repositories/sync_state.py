"""Data sync state repository.

Tracks sync state for historical data fetching to support incremental syncs.
"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import DataSyncState


class SyncStateRepository:
    """Repository for managing data sync state.
    
    Tracks when data was last synced per symbol/timeframe to enable
    incremental updates rather than full re-syncs.
    """
    
    def __init__(self, db: Session):
        """Initialize repository with database session.
        
        Args:
            db: SQLAlchemy session from dependency injection
        """
        self._db = db
    
    def get_sync_state(
        self,
        symbol: str,
        timeframe: str,
        source: str = 'hyperliquid',
    ) -> Optional[DataSyncState]:
        """Get sync state for a symbol/timeframe combination.
        
        Args:
            symbol: Trading pair (e.g., "BTC")
            timeframe: Candle timeframe (e.g., "5m", "15m", "1h")
            source: Data source (default: 'hyperliquid')
            
        Returns:
            DataSyncState or None if not synced yet
        """
        return (
            self._db.query(DataSyncState)
            .filter(
                and_(
                    DataSyncState.symbol == symbol,
                    DataSyncState.timeframe == timeframe,
                    DataSyncState.source == source,
                )
            )
            .first()
        )
    
    def create_or_update_sync_state(
        self,
        symbol: str,
        timeframe: str,
        source: str = 'hyperliquid',
        last_sync_timestamp: Optional[datetime] = None,
        oldest_timestamp: Optional[datetime] = None,
        newest_timestamp: Optional[datetime] = None,
        candle_count: int = 0,
        is_syncing: bool = False,
        sync_error: Optional[str] = None,
    ) -> DataSyncState:
        """Create or update sync state for a symbol/timeframe.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            source: Data source
            last_sync_timestamp: Timestamp of last candle synced
            oldest_timestamp: Oldest candle timestamp
            newest_timestamp: Newest candle timestamp
            candle_count: Total candles stored
            is_syncing: Whether sync is currently running
            sync_error: Last error message if any
            
        Returns:
            Created or updated DataSyncState
        """
        state = self.get_sync_state(symbol, timeframe, source)
        now = datetime.now(timezone.utc)
        
        if state is None:
            state = DataSyncState(
                symbol=symbol,
                timeframe=timeframe,
                source=source,
                created_at=now,
            )
            self._db.add(state)
        
        # Update fields
        if last_sync_timestamp is not None:
            state.last_sync_timestamp = last_sync_timestamp
        if oldest_timestamp is not None:
            state.oldest_timestamp = oldest_timestamp
        if newest_timestamp is not None:
            state.newest_timestamp = newest_timestamp
        if candle_count is not None:
            state.candle_count = candle_count
        
        state.is_syncing = is_syncing
        state.sync_error = sync_error
        state.last_sync_at = now
        state.updated_at = now
        
        self._db.flush()
        return state
    
    def set_syncing(
        self,
        symbol: str,
        timeframe: str,
        is_syncing: bool,
        source: str = 'hyperliquid',
        error: Optional[str] = None,
    ) -> Optional[DataSyncState]:
        """Update syncing status for a symbol/timeframe.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            is_syncing: Whether sync is running
            source: Data source
            error: Error message if sync failed
            
        Returns:
            Updated DataSyncState or None
        """
        state = self.get_sync_state(symbol, timeframe, source)
        
        if state is None:
            # Create new state if doesn't exist
            state = DataSyncState(
                symbol=symbol,
                timeframe=timeframe,
                source=source,
                is_syncing=is_syncing,
                sync_error=error,
                created_at=datetime.now(timezone.utc),
            )
            self._db.add(state)
        else:
            state.is_syncing = is_syncing
            state.sync_error = error
            state.updated_at = datetime.now(timezone.utc)
        
        self._db.flush()
        return state
    
    def get_all_sync_states(
        self,
        source: Optional[str] = None,
        is_syncing: Optional[bool] = None,
    ) -> List[DataSyncState]:
        """Get all sync states, optionally filtered.
        
        Args:
            source: Filter by data source
            is_syncing: Filter by syncing status
            
        Returns:
            List of DataSyncState objects
        """
        query = self._db.query(DataSyncState)
        
        if source is not None:
            query = query.filter(DataSyncState.source == source)
        if is_syncing is not None:
            query = query.filter(DataSyncState.is_syncing == is_syncing)
        
        return query.all()
    
    def get_stale_syncs(
        self,
        max_age_hours: int = 24,
        source: str = 'hyperliquid',
    ) -> List[DataSyncState]:
        """Get sync states that haven't been updated in a while.
        
        Useful for finding data that needs refreshing.
        
        Args:
            max_age_hours: Max hours since last sync
            source: Data source
            
        Returns:
            List of stale DataSyncState objects
        """
        from datetime import timedelta
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        return (
            self._db.query(DataSyncState)
            .filter(
                and_(
                    DataSyncState.source == source,
                    DataSyncState.last_sync_at < cutoff,
                )
            )
            .all()
        )
    
    def delete_sync_state(
        self,
        symbol: str,
        timeframe: str,
        source: str = 'hyperliquid',
    ) -> bool:
        """Delete sync state for a symbol/timeframe.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            source: Data source
            
        Returns:
            True if deleted, False if not found
        """
        state = self.get_sync_state(symbol, timeframe, source)
        
        if state:
            self._db.delete(state)
            self._db.flush()
            return True
        return False
