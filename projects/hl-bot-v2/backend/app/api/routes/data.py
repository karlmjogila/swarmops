"""API routes for data import and management.

Provides endpoints for:
- CSV import (TradingView format)
- Data query and retrieval
- Data statistics
"""
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
import tempfile
import logging

from app.db.session import get_db
from app.db.repositories.ohlcv import OHLCVRepository
from app.core.market.importer import CSVImporter
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/data", tags=["data"])


class ImportCSVRequest(BaseModel):
    """Request model for CSV import from raw content."""
    csv_content: str = Field(..., description="CSV content as string")
    symbol: str = Field(..., description="Trading symbol (e.g., BTC-USD)", min_length=1)
    timeframe: str = Field(..., description="Candle timeframe (e.g., 5m, 1h)", pattern=r"^\d+[mhd]$")


class ImportCSVResponse(BaseModel):
    """Response model for CSV import."""
    success: bool
    message: str
    stats: dict
    dlq_file: Optional[str] = None


class DataRangeResponse(BaseModel):
    """Response model for data range query."""
    symbol: str
    timeframe: str
    earliest: Optional[str] = None
    latest: Optional[str] = None
    candle_count: int


class AvailableDataResponse(BaseModel):
    """Response model for available data listing."""
    symbols: list[str]
    timeframes: list[str]


@router.post("/import", response_model=ImportCSVResponse)
async def import_csv_file(
    file: UploadFile = File(..., description="CSV file in TradingView format"),
    symbol: str = Query(..., description="Trading symbol (e.g., BTC-USD)"),
    timeframe: str = Query(..., description="Candle timeframe (e.g., 5m, 1h)", pattern=r"^\d+[mhd]$"),
    db: Session = Depends(get_db),
) -> ImportCSVResponse:
    """Import OHLCV data from uploaded CSV file.
    
    Accepts TradingView CSV format with columns:
    - time (Unix timestamp or ISO format)
    - open
    - high
    - low
    - close
    - volume (optional)
    
    The import process:
    1. Validates CSV format and schema
    2. Checks data quality (price relationships, timestamps)
    3. Stores valid records in database
    4. Logs invalid records to dead letter queue
    5. Returns detailed statistics
    
    The import is idempotent - running multiple times with the same data
    will not create duplicates.
    
    Args:
        file: Uploaded CSV file
        symbol: Trading symbol (e.g., "BTC-USD", "ETH-USD")
        timeframe: Candle timeframe (e.g., "5m", "15m", "1h", "4h", "1d")
        db: Database session (injected)
        
    Returns:
        Import statistics including number of records processed,
        inserted, and any validation errors
        
    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/data/import?symbol=BTC-USD&timeframe=5m" \\
             -F "file=@btc_5m.csv"
        ```
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV file"
        )
    
    try:
        # Read file content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Create importer
        dlq_dir = Path("./data/dlq")
        importer = CSVImporter(dlq_dir=dlq_dir)
        
        # Create repository
        repo = OHLCVRepository(db)
        
        # Import data
        logger.info(f"Starting CSV import: symbol={symbol}, timeframe={timeframe}, file={file.filename}")
        stats = importer.import_from_string(csv_content, symbol, timeframe, repo)
        
        # Commit transaction
        db.commit()
        
        logger.info(f"CSV import complete: {stats.to_dict()}")
        
        # Prepare response
        success = stats.inserted > 0
        
        if stats.invalid > 0:
            message = (
                f"Imported {stats.inserted} candles. "
                f"{stats.invalid} invalid records logged to dead letter queue. "
                f"{stats.duplicates} duplicates skipped."
            )
            dlq_file = f"dlq-{stats.run_id}.jsonl"
        else:
            message = f"Successfully imported {stats.inserted} candles. {stats.duplicates} duplicates skipped."
            dlq_file = None
        
        return ImportCSVResponse(
            success=success,
            message=message,
            stats=stats.to_dict(),
            dlq_file=dlq_file,
        )
        
    except ValueError as e:
        logger.error(f"CSV import validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"CSV import failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/import/raw", response_model=ImportCSVResponse)
async def import_csv_raw(
    request: ImportCSVRequest,
    db: Session = Depends(get_db),
) -> ImportCSVResponse:
    """Import OHLCV data from raw CSV content (JSON body).
    
    Alternative to file upload - useful for programmatic access.
    
    Args:
        request: CSV content and metadata
        db: Database session (injected)
        
    Returns:
        Import statistics
        
    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/data/import/raw" \\
             -H "Content-Type: application/json" \\
             -d '{
                "csv_content": "time,open,high,low,close,volume\\n...",
                "symbol": "BTC-USD",
                "timeframe": "5m"
             }'
        ```
    """
    try:
        # Create importer
        dlq_dir = Path("./data/dlq")
        importer = CSVImporter(dlq_dir=dlq_dir)
        
        # Create repository
        repo = OHLCVRepository(db)
        
        # Import data
        logger.info(f"Starting raw CSV import: symbol={request.symbol}, timeframe={request.timeframe}")
        stats = importer.import_from_string(request.csv_content, request.symbol, request.timeframe, repo)
        
        # Commit transaction
        db.commit()
        
        logger.info(f"Raw CSV import complete: {stats.to_dict()}")
        
        # Prepare response
        success = stats.inserted > 0
        
        if stats.invalid > 0:
            message = (
                f"Imported {stats.inserted} candles. "
                f"{stats.invalid} invalid records logged to dead letter queue. "
                f"{stats.duplicates} duplicates skipped."
            )
            dlq_file = f"dlq-{stats.run_id}.jsonl"
        else:
            message = f"Successfully imported {stats.inserted} candles. {stats.duplicates} duplicates skipped."
            dlq_file = None
        
        return ImportCSVResponse(
            success=success,
            message=message,
            stats=stats.to_dict(),
            dlq_file=dlq_file,
        )
        
    except ValueError as e:
        logger.error(f"Raw CSV import validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Raw CSV import failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/range", response_model=DataRangeResponse)
async def get_data_range(
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query(..., description="Candle timeframe (e.g., 5m, 1h)", pattern=r"^\d+[mhdwM]$"),
    db: Session = Depends(get_db),
) -> DataRangeResponse:
    """Get the time range of available data for a symbol and timeframe.
    
    Args:
        symbol: Trading symbol
        timeframe: Candle timeframe
        db: Database session (injected)
        
    Returns:
        Earliest and latest timestamps, and total candle count
        
    Example:
        ```bash
        curl "http://localhost:8000/api/data/range?symbol=BTC-USD&timeframe=5m"
        ```
    """
    try:
        repo = OHLCVRepository(db)
        
        # Get time range
        time_range = repo.get_time_range(symbol, timeframe)
        
        # Get count
        count = repo.count_candles(symbol, timeframe)
        
        if time_range:
            earliest, latest = time_range
            return DataRangeResponse(
                symbol=symbol,
                timeframe=timeframe,
                earliest=earliest.isoformat(),
                latest=latest.isoformat(),
                candle_count=count,
            )
        else:
            return DataRangeResponse(
                symbol=symbol,
                timeframe=timeframe,
                earliest=None,
                latest=None,
                candle_count=0,
            )
            
    except Exception as e:
        logger.error(f"Failed to get data range: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get data range: {str(e)}")


@router.get("/available", response_model=AvailableDataResponse)
async def get_available_data(
    db: Session = Depends(get_db),
) -> AvailableDataResponse:
    """Get list of all available symbols and timeframes in the database.
    
    Args:
        db: Database session (injected)
        
    Returns:
        Lists of available symbols and timeframes
        
    Example:
        ```bash
        curl "http://localhost:8000/api/data/available"
        ```
    """
    try:
        repo = OHLCVRepository(db)
        
        symbols = repo.get_available_symbols()
        timeframes = repo.get_available_timeframes()
        
        return AvailableDataResponse(
            symbols=sorted(symbols),
            timeframes=sorted(timeframes),
        )
        
    except Exception as e:
        logger.error(f"Failed to get available data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get available data: {str(e)}")


@router.delete("/clear")
async def clear_data(
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query(..., description="Candle timeframe"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Delete candles for a symbol and timeframe.
    
    WARNING: This operation is irreversible. Use with caution.
    
    Args:
        symbol: Trading symbol
        timeframe: Candle timeframe
        start_time: Optional start of time range (ISO format)
        end_time: Optional end of time range (ISO format)
        db: Database session (injected)
        
    Returns:
        Number of candles deleted
        
    Example:
        ```bash
        # Delete all BTC-USD 5m data
        curl -X DELETE "http://localhost:8000/api/data/clear?symbol=BTC-USD&timeframe=5m"
        
        # Delete data in time range
        curl -X DELETE "http://localhost:8000/api/data/clear?symbol=BTC-USD&timeframe=5m&start_time=2024-01-01T00:00:00Z&end_time=2024-01-31T23:59:59Z"
        ```
    """
    try:
        repo = OHLCVRepository(db)
        
        # Parse timestamps if provided
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00')) if start_time else None
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')) if end_time else None
        
        # Delete candles
        deleted_count = repo.delete_candles(symbol, timeframe, start_dt, end_dt)
        
        # Commit transaction
        db.commit()
        
        logger.info(f"Deleted {deleted_count} candles: symbol={symbol}, timeframe={timeframe}")
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Deleted {deleted_count} candles",
                "deleted_count": deleted_count,
            }
        )
        
    except ValueError as e:
        logger.error(f"Invalid timestamp format: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete data: {str(e)}")
