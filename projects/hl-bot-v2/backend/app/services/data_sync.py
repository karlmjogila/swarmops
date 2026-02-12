"""Data synchronization service.

Orchestrates fetching historical data from Hyperliquid and storing it in the database.
Supports initial sync, incremental sync, and scheduled background syncs.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Callable
from enum import StrEnum

from sqlalchemy.orm import Session

from app.db.repositories.ohlcv import OHLCVRepository
from app.db.repositories.sync_state import SyncStateRepository
from app.services.hyperliquid_data import (
    HyperliquidDataFetcher, 
    Candle, 
    SyncProgress,
    TIMEFRAME_MAP,
)


logger = logging.getLogger(__name__)


class SyncMode(StrEnum):
    """Sync operation modes."""
    FULL = "full"           # Fetch all available historical data
    INCREMENTAL = "incremental"  # Only fetch new data since last sync
    BACKFILL = "backfill"   # Fill gaps in existing data


@dataclass
class SyncResult:
    """Result of a sync operation."""
    symbol: str
    timeframe: str
    mode: SyncMode
    success: bool
    candles_fetched: int = 0
    candles_inserted: int = 0
    oldest_candle: Optional[datetime] = None
    newest_candle: Optional[datetime] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    @property
    def duration_seconds(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "mode": self.mode,
            "success": self.success,
            "candles_fetched": self.candles_fetched,
            "candles_inserted": self.candles_inserted,
            "oldest_candle": self.oldest_candle.isoformat() if self.oldest_candle else None,
            "newest_candle": self.newest_candle.isoformat() if self.newest_candle else None,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }


@dataclass
class SyncStatus:
    """Current status of a sync operation."""
    symbol: str
    timeframe: str
    is_syncing: bool
    progress: Optional[SyncProgress] = None
    last_sync_at: Optional[datetime] = None
    last_error: Optional[str] = None
    candle_count: int = 0
    oldest_candle: Optional[datetime] = None
    newest_candle: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "is_syncing": self.is_syncing,
            "progress": self.progress.to_dict() if self.progress else None,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_error": self.last_error,
            "candle_count": self.candle_count,
            "oldest_candle": self.oldest_candle.isoformat() if self.oldest_candle else None,
            "newest_candle": self.newest_candle.isoformat() if self.newest_candle else None,
        }


class DataSyncService:
    """Service for synchronizing market data from Hyperliquid.
    
    Features:
    - Full historical sync (up to 5000 candles)
    - Incremental sync (only new data)
    - Progress tracking and callbacks
    - Upsert logic to avoid duplicates
    - Sync state persistence
    """
    
    # Default timeframes to sync (all timeframes Karl wants)
    # 1m for scalping, 5m-1h for intraday, 4h-1d for swing, 1w-1M for position trading
    DEFAULT_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
    
    def __init__(
        self,
        db: Session,
        testnet: bool = False,
    ):
        """Initialize the sync service.
        
        Args:
            db: Database session
            testnet: Use Hyperliquid testnet
        """
        self.db = db
        self.ohlcv_repo = OHLCVRepository(db)
        self.sync_repo = SyncStateRepository(db)
        self.fetcher = HyperliquidDataFetcher(testnet=testnet)
        
        # Track active syncs
        self._active_syncs: Dict[str, SyncProgress] = {}
    
    def _sync_key(self, symbol: str, timeframe: str) -> str:
        """Generate a unique key for tracking sync operations."""
        return f"{symbol}:{timeframe}"
    
    def _store_candles(
        self,
        candles: List[Candle],
        symbol: str,
        timeframe: str,
        source: str = 'hyperliquid',
    ) -> int:
        """Store candles in the database with upsert logic.
        
        Args:
            candles: List of Candle objects
            symbol: Trading symbol
            timeframe: Candle timeframe
            source: Data source (default: 'hyperliquid')
            
        Returns:
            Number of candles inserted/updated
        """
        if not candles:
            return 0
        
        # Prepare candle dicts for bulk insert
        candle_dicts = [
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]
        
        # Use bulk insert with explicit source (handles duplicates gracefully)
        inserted = self.ohlcv_repo.bulk_insert_candles(candle_dicts, source=source)
        return inserted
    
    async def sync(
        self,
        symbol: str,
        timeframe: str,
        mode: SyncMode = SyncMode.INCREMENTAL,
        progress_callback: Optional[Callable[[SyncProgress], None]] = None,
    ) -> SyncResult:
        """Synchronize market data for a symbol/timeframe.
        
        Args:
            symbol: Trading symbol (e.g., "BTC")
            timeframe: Candle timeframe (e.g., "5m", "1h")
            mode: Sync mode (full, incremental, backfill)
            progress_callback: Optional callback for progress updates
            
        Returns:
            SyncResult with operation details
        """
        sync_key = self._sync_key(symbol, timeframe)
        
        # Check if already syncing
        if sync_key in self._active_syncs:
            raise ValueError(f"Sync already in progress for {symbol}/{timeframe}")
        
        result = SyncResult(
            symbol=symbol,
            timeframe=timeframe,
            mode=mode,
            success=False,
        )
        
        try:
            # Mark as syncing
            self.sync_repo.set_syncing(symbol, timeframe, True)
            self.db.commit()
            
            # Determine start time based on mode
            start_time = None
            if mode == SyncMode.INCREMENTAL:
                # Get last sync state
                state = self.sync_repo.get_sync_state(symbol, timeframe)
                if state and state.newest_timestamp:
                    # Start from last synced timestamp
                    start_time = state.newest_timestamp
                    logger.info(f"Incremental sync from {start_time}")
            
            # Track progress
            def track_progress(progress: SyncProgress):
                self._active_syncs[sync_key] = progress
                if progress_callback:
                    progress_callback(progress)
            
            self._active_syncs[sync_key] = SyncProgress(symbol=symbol, timeframe=timeframe)
            
            # Fetch candles
            if start_time and mode == SyncMode.INCREMENTAL:
                candles = await self.fetcher.fetch_incremental(
                    symbol=symbol,
                    interval=timeframe,
                    since=start_time,
                    progress_callback=track_progress,
                )
            else:
                candles = await self.fetcher.fetch_all_candles(
                    symbol=symbol,
                    interval=timeframe,
                    progress_callback=track_progress,
                )
            
            result.candles_fetched = len(candles)
            
            if candles:
                result.oldest_candle = candles[0].timestamp
                result.newest_candle = candles[-1].timestamp
                
                # Store in database
                result.candles_inserted = self._store_candles(candles, symbol, timeframe)
                self.db.commit()
                
                logger.info(
                    f"Sync complete: {symbol}/{timeframe}, "
                    f"fetched={result.candles_fetched}, inserted={result.candles_inserted}"
                )
            
            # Update sync state
            candle_count = self.ohlcv_repo.count_candles(symbol, timeframe)
            time_range = self.ohlcv_repo.get_time_range(symbol, timeframe)
            
            self.sync_repo.create_or_update_sync_state(
                symbol=symbol,
                timeframe=timeframe,
                last_sync_timestamp=result.newest_candle,
                oldest_timestamp=time_range[0] if time_range else None,
                newest_timestamp=time_range[1] if time_range else None,
                candle_count=candle_count,
                is_syncing=False,
                sync_error=None,
            )
            self.db.commit()
            
            result.success = True
            
        except Exception as e:
            logger.error(f"Sync failed for {symbol}/{timeframe}: {e}", exc_info=True)
            result.error = str(e)
            
            # Update sync state with error
            self.sync_repo.set_syncing(symbol, timeframe, False, error=str(e))
            self.db.commit()
        
        finally:
            # Cleanup
            self._active_syncs.pop(sync_key, None)
            result.completed_at = datetime.now(timezone.utc)
        
        return result
    
    async def sync_multiple(
        self,
        symbols: List[str],
        timeframes: Optional[List[str]] = None,
        mode: SyncMode = SyncMode.INCREMENTAL,
        progress_callback: Optional[Callable[[str, str, SyncProgress], None]] = None,
    ) -> List[SyncResult]:
        """Synchronize data for multiple symbols and timeframes.
        
        Syncs sequentially to respect rate limits.
        
        Args:
            symbols: List of trading symbols
            timeframes: List of timeframes (default: DEFAULT_TIMEFRAMES)
            mode: Sync mode
            progress_callback: Callback with (symbol, timeframe, progress)
            
        Returns:
            List of SyncResult for each symbol/timeframe
        """
        if timeframes is None:
            timeframes = self.DEFAULT_TIMEFRAMES
        
        results = []
        
        for symbol in symbols:
            for timeframe in timeframes:
                def cb(progress: SyncProgress):
                    if progress_callback:
                        progress_callback(symbol, timeframe, progress)
                
                try:
                    result = await self.sync(
                        symbol=symbol,
                        timeframe=timeframe,
                        mode=mode,
                        progress_callback=cb,
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to sync {symbol}/{timeframe}: {e}")
                    results.append(SyncResult(
                        symbol=symbol,
                        timeframe=timeframe,
                        mode=mode,
                        success=False,
                        error=str(e),
                        completed_at=datetime.now(timezone.utc),
                    ))
        
        return results
    
    async def get_available_symbols(self) -> List[str]:
        """Get list of available trading symbols from Hyperliquid.
        
        Returns:
            List of symbol names (e.g., ["BTC", "ETH", "SOL", ...])
        """
        return await self.fetcher.get_available_coins()
    
    def get_sync_status(
        self,
        symbol: str,
        timeframe: str,
    ) -> SyncStatus:
        """Get current sync status for a symbol/timeframe.
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            
        Returns:
            SyncStatus with current state
        """
        sync_key = self._sync_key(symbol, timeframe)
        state = self.sync_repo.get_sync_state(symbol, timeframe)
        progress = self._active_syncs.get(sync_key)
        
        return SyncStatus(
            symbol=symbol,
            timeframe=timeframe,
            is_syncing=sync_key in self._active_syncs,
            progress=progress,
            last_sync_at=state.last_sync_at if state else None,
            last_error=state.sync_error if state else None,
            candle_count=state.candle_count if state else 0,
            oldest_candle=state.oldest_timestamp if state else None,
            newest_candle=state.newest_timestamp if state else None,
        )
    
    def get_all_sync_statuses(self) -> List[SyncStatus]:
        """Get sync status for all tracked symbol/timeframe combinations.
        
        Returns:
            List of SyncStatus objects
        """
        states = self.sync_repo.get_all_sync_states(source='hyperliquid')
        statuses = []
        
        for state in states:
            sync_key = self._sync_key(state.symbol, state.timeframe)
            progress = self._active_syncs.get(sync_key)
            
            statuses.append(SyncStatus(
                symbol=state.symbol,
                timeframe=state.timeframe,
                is_syncing=state.is_syncing or sync_key in self._active_syncs,
                progress=progress,
                last_sync_at=state.last_sync_at,
                last_error=state.sync_error,
                candle_count=state.candle_count,
                oldest_candle=state.oldest_timestamp,
                newest_candle=state.newest_timestamp,
            ))
        
        return statuses
    
    def get_available_data(self) -> Dict[str, Any]:
        """Get summary of all available local data.
        
        Returns:
            Dict with symbols, timeframes, and per-symbol/timeframe details
        """
        symbols = self.ohlcv_repo.get_available_symbols()
        timeframes = self.ohlcv_repo.get_available_timeframes()
        
        # Get per-combination details
        details = []
        for state in self.sync_repo.get_all_sync_states(source='hyperliquid'):
            details.append({
                "symbol": state.symbol,
                "timeframe": state.timeframe,
                "candle_count": state.candle_count,
                "oldest": state.oldest_timestamp.isoformat() if state.oldest_timestamp else None,
                "newest": state.newest_timestamp.isoformat() if state.newest_timestamp else None,
                "last_sync": state.last_sync_at.isoformat() if state.last_sync_at else None,
            })
        
        return {
            "symbols": sorted(symbols),
            "timeframes": sorted(timeframes),
            "details": details,
        }


# Synchronous wrapper for CLI and Celery tasks
def run_sync(
    db: Session,
    symbol: str,
    timeframe: str,
    mode: str = "incremental",
    testnet: bool = False,
) -> Dict[str, Any]:
    """Synchronous wrapper for data sync.
    
    Useful for CLI and Celery tasks that can't use async directly.
    
    Args:
        db: Database session
        symbol: Trading symbol
        timeframe: Candle timeframe
        mode: "full" or "incremental"
        testnet: Use testnet
        
    Returns:
        Dict with sync result
    """
    sync_mode = SyncMode.FULL if mode == "full" else SyncMode.INCREMENTAL
    service = DataSyncService(db, testnet=testnet)
    
    result = asyncio.run(
        service.sync(symbol, timeframe, mode=sync_mode)
    )
    
    return result.to_dict()
