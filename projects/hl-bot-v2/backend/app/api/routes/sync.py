"""API routes for Hyperliquid data synchronization.

Provides endpoints for:
- Triggering data sync from Hyperliquid
- Checking sync status
- Listing available data
"""
import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from app.db.session import get_db
from app.services.data_sync import DataSyncService, SyncMode
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/data/sync", tags=["sync"])


class SyncRequest(BaseModel):
    """Request model for triggering a sync."""
    symbol: str = Field(..., description="Trading symbol (e.g., BTC)", min_length=1)
    timeframe: str = Field(..., description="Candle timeframe (e.g., 5m, 1h)", pattern=r"^\d+[mhMdw]$")
    mode: str = Field(
        default="incremental",
        description="Sync mode: 'full' for all history, 'incremental' for new data only",
        pattern=r"^(full|incremental)$"
    )


class BulkSyncRequest(BaseModel):
    """Request model for bulk sync."""
    symbols: List[str] = Field(..., description="List of trading symbols", min_length=1)
    timeframes: Optional[List[str]] = Field(
        default=None,
        description="List of timeframes (default: 5m, 15m, 30m, 1h, 4h, 1d)"
    )
    mode: str = Field(default="incremental", pattern=r"^(full|incremental)$")


class SyncResponse(BaseModel):
    """Response model for sync operations."""
    success: bool
    message: str
    task_id: Optional[str] = None
    result: Optional[dict] = None


class SyncStatusResponse(BaseModel):
    """Response model for sync status."""
    symbol: str
    timeframe: str
    is_syncing: bool
    candle_count: int
    oldest_candle: Optional[str] = None
    newest_candle: Optional[str] = None
    last_sync_at: Optional[str] = None
    last_error: Optional[str] = None


class AvailableDataResponse(BaseModel):
    """Response model for available data."""
    symbols: List[str]
    timeframes: List[str]
    details: List[dict]


class AvailableSymbolsResponse(BaseModel):
    """Response model for available Hyperliquid symbols."""
    symbols: List[str]
    count: int


# Background task storage (simple in-memory for now)
_sync_tasks: dict = {}


async def _run_sync_task(
    db: Session,
    symbol: str,
    timeframe: str,
    mode: SyncMode,
    task_id: str,
):
    """Background task for running sync."""
    try:
        service = DataSyncService(db)
        result = await service.sync(symbol, timeframe, mode=mode)
        _sync_tasks[task_id] = {
            "status": "completed" if result.success else "failed",
            "result": result.to_dict(),
        }
    except Exception as e:
        logger.error(f"Sync task {task_id} failed: {e}", exc_info=True)
        _sync_tasks[task_id] = {
            "status": "failed",
            "error": str(e),
        }


@router.post("/hyperliquid", response_model=SyncResponse)
async def trigger_hyperliquid_sync(
    request: SyncRequest,
    background: bool = Query(
        default=False,
        description="Run sync in background (returns immediately)"
    ),
    db: Session = Depends(get_db),
) -> SyncResponse:
    """Trigger a data sync from Hyperliquid for a symbol/timeframe.
    
    This fetches OHLCV candle data from Hyperliquid's API and stores it locally.
    
    **Sync Modes:**
    - `incremental`: Only fetch new data since last sync (faster)
    - `full`: Fetch all available history (up to ~5000 candles)
    
    **Rate Limits:**
    - Hyperliquid allows ~100 requests/minute
    - We use conservative rate limiting to avoid hitting limits
    
    **Example:**
    ```bash
    # Sync BTC 5-minute candles (incremental)
    curl -X POST "http://localhost:8000/api/data/sync/hyperliquid" \\
         -H "Content-Type: application/json" \\
         -d '{"symbol": "BTC", "timeframe": "5m"}'
    
    # Full sync in background
    curl -X POST "http://localhost:8000/api/data/sync/hyperliquid?background=true" \\
         -H "Content-Type: application/json" \\
         -d '{"symbol": "ETH", "timeframe": "1h", "mode": "full"}'
    ```
    """
    mode = SyncMode.FULL if request.mode == "full" else SyncMode.INCREMENTAL
    
    try:
        service = DataSyncService(db)
        
        # Check if already syncing
        status = service.get_sync_status(request.symbol, request.timeframe)
        if status.is_syncing:
            return SyncResponse(
                success=False,
                message=f"Sync already in progress for {request.symbol}/{request.timeframe}",
            )
        
        if background:
            # Generate task ID and run in background
            import uuid
            task_id = str(uuid.uuid4())
            _sync_tasks[task_id] = {"status": "running"}
            
            # Note: In production, use Celery instead of BackgroundTasks
            asyncio.create_task(_run_sync_task(db, request.symbol, request.timeframe, mode, task_id))
            
            return SyncResponse(
                success=True,
                message=f"Sync started in background for {request.symbol}/{request.timeframe}",
                task_id=task_id,
            )
        
        # Run sync synchronously
        result = await service.sync(request.symbol, request.timeframe, mode=mode)
        
        return SyncResponse(
            success=result.success,
            message=(
                f"Synced {result.candles_inserted} candles for {request.symbol}/{request.timeframe}"
                if result.success
                else f"Sync failed: {result.error}"
            ),
            result=result.to_dict(),
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/hyperliquid/bulk", response_model=SyncResponse)
async def trigger_bulk_sync(
    request: BulkSyncRequest,
    db: Session = Depends(get_db),
) -> SyncResponse:
    """Trigger sync for multiple symbols and timeframes.
    
    This runs syncs sequentially to respect rate limits.
    For large syncs, consider using the Celery background task.
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/data/sync/hyperliquid/bulk" \\
         -H "Content-Type: application/json" \\
         -d '{
            "symbols": ["BTC", "ETH", "SOL"],
            "timeframes": ["5m", "1h", "4h"],
            "mode": "incremental"
         }'
    ```
    """
    mode = SyncMode.FULL if request.mode == "full" else SyncMode.INCREMENTAL
    
    try:
        service = DataSyncService(db)
        results = await service.sync_multiple(
            symbols=request.symbols,
            timeframes=request.timeframes,
            mode=mode,
        )
        
        successful = sum(1 for r in results if r.success)
        total_candles = sum(r.candles_inserted for r in results)
        
        return SyncResponse(
            success=successful > 0,
            message=f"Synced {successful}/{len(results)} combinations, {total_candles} total candles",
            result={
                "successful": successful,
                "failed": len(results) - successful,
                "total_candles": total_candles,
                "results": [r.to_dict() for r in results],
            }
        )
    
    except Exception as e:
        logger.error(f"Bulk sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bulk sync failed: {str(e)}")


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query(..., description="Candle timeframe"),
    db: Session = Depends(get_db),
) -> SyncStatusResponse:
    """Get sync status for a specific symbol/timeframe.
    
    Returns information about:
    - Whether a sync is currently running
    - Number of candles stored locally
    - Time range of available data
    - When last sync completed
    
    **Example:**
    ```bash
    curl "http://localhost:8000/api/data/sync/status?symbol=BTC&timeframe=5m"
    ```
    """
    try:
        service = DataSyncService(db)
        status = service.get_sync_status(symbol, timeframe)
        
        return SyncStatusResponse(
            symbol=status.symbol,
            timeframe=status.timeframe,
            is_syncing=status.is_syncing,
            candle_count=status.candle_count,
            oldest_candle=status.oldest_candle.isoformat() if status.oldest_candle else None,
            newest_candle=status.newest_candle.isoformat() if status.newest_candle else None,
            last_sync_at=status.last_sync_at.isoformat() if status.last_sync_at else None,
            last_error=status.last_error,
        )
    
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/all")
async def get_all_sync_statuses(
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Get sync status for all tracked symbol/timeframe combinations.
    
    **Example:**
    ```bash
    curl "http://localhost:8000/api/data/sync/status/all"
    ```
    """
    try:
        service = DataSyncService(db)
        statuses = service.get_all_sync_statuses()
        
        return JSONResponse(content={
            "statuses": [s.to_dict() for s in statuses],
            "count": len(statuses),
        })
    
    except Exception as e:
        logger.error(f"Failed to get sync statuses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available", response_model=AvailableDataResponse)
async def get_available_data(
    db: Session = Depends(get_db),
) -> AvailableDataResponse:
    """Get summary of all available local data.
    
    Lists all symbols and timeframes that have been synced,
    along with details like candle count and time range.
    
    **Example:**
    ```bash
    curl "http://localhost:8000/api/data/sync/available"
    ```
    """
    try:
        service = DataSyncService(db)
        data = service.get_available_data()
        
        return AvailableDataResponse(
            symbols=data["symbols"],
            timeframes=data["timeframes"],
            details=data["details"],
        )
    
    except Exception as e:
        logger.error(f"Failed to get available data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols", response_model=AvailableSymbolsResponse)
async def get_hyperliquid_symbols(
    db: Session = Depends(get_db),
) -> AvailableSymbolsResponse:
    """Get list of all trading symbols available on Hyperliquid.
    
    This fetches the current list of tradeable perpetual assets
    from Hyperliquid's API.
    
    **Example:**
    ```bash
    curl "http://localhost:8000/api/data/sync/symbols"
    ```
    """
    try:
        service = DataSyncService(db)
        symbols = await service.get_available_symbols()
        
        return AvailableSymbolsResponse(
            symbols=sorted(symbols),
            count=len(symbols),
        )
    
    except Exception as e:
        logger.error(f"Failed to get Hyperliquid symbols: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
) -> JSONResponse:
    """Get status of a background sync task.
    
    **Example:**
    ```bash
    curl "http://localhost:8000/api/data/sync/task/abc-123"
    ```
    """
    if task_id not in _sync_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return JSONResponse(content=_sync_tasks[task_id])
