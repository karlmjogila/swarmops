"""Backtesting endpoints."""

import uuid
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, BackgroundTasks, Depends
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
import structlog

from ...database import get_db
from ...database.models import StrategyRuleDB
from ...config import settings

router = APIRouter()
logger = structlog.get_logger()


# In-memory backtest storage (replace with database in production)
_backtest_tasks = {}


class BacktestConfig(BaseModel):
    """Configuration for a backtest run."""
    name: str = Field(..., min_length=1, max_length=200)
    symbol: str = Field(..., min_length=1, max_length=20)
    timeframes: List[str] = Field(default=["4H", "1H", "15M", "5M"])
    start_date: str
    end_date: str
    initial_capital: float = Field(gt=0, default=10000)
    strategy_ids: List[str] = Field(..., min_items=1)
    max_concurrent_positions: int = Field(ge=1, le=20, default=5)
    risk_per_trade: float = Field(gt=0, le=0.1, default=0.02)
    
    @validator('timeframes')
    def validate_timeframes(cls, v):
        valid_tfs = ['1M', '5M', '15M', '30M', '1H', '4H', '1D']
        for tf in v:
            if tf not in valid_tfs:
                raise ValueError(f"Invalid timeframe '{tf}'. Must be one of: {', '.join(valid_tfs)}")
        return v
    
    @validator('start_date', 'end_date')
    def validate_date(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Invalid date format. Use ISO 8601 (e.g., '2024-01-01T00:00:00Z')")
        return v


class BacktestResult(BaseModel):
    """Backtest results summary."""
    backtest_id: str
    name: str
    status: str  # pending, running, completed, failed
    progress: float = Field(ge=0.0, le=1.0)
    config: BacktestConfig
    
    # Performance metrics (when completed)
    total_trades: int = 0
    winning_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_return: float = 0.0
    total_return_pct: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    avg_r_multiple: float = 0.0
    
    # Timestamps
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class BacktestTrade(BaseModel):
    """Individual trade from backtest."""
    trade_id: str
    strategy_id: str
    strategy_name: str
    symbol: str
    direction: str  # long, short
    entry_time: str
    entry_price: float
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # tp1, tp2, sl, breakeven
    quantity: float
    pnl: float
    pnl_r: float  # P&L in R multiples
    confluence_score: float
    reasoning: str


class EquityPoint(BaseModel):
    """Point in equity curve."""
    timestamp: str
    equity: float
    drawdown: float
    drawdown_pct: float


async def _run_backtest_task(backtest_id: str, config: BacktestConfig, db: Session):
    """Background task for running backtest."""
    try:
        # Lazy import to avoid loading dependencies on startup
        from ...backtest.backtest_engine import BacktestEngine
        from ...backtest.data_loader import DataLoader
        
        _backtest_tasks[backtest_id]['status'] = 'running'
        _backtest_tasks[backtest_id]['started_at'] = datetime.now(timezone.utc).isoformat()
        _backtest_tasks[backtest_id]['progress'] = 0.1
        
        # Validate strategies exist
        strategies = []
        for strategy_id in config.strategy_ids:
            strategy = db.query(StrategyRuleDB).filter(
                StrategyRuleDB.id == strategy_id
            ).first()
            
            if not strategy:
                raise ValueError(f"Strategy '{strategy_id}' not found")
            
            strategies.append(strategy)
        
        _backtest_tasks[backtest_id]['progress'] = 0.2
        
        # Initialize data loader
        data_loader = DataLoader()
        
        # Load historical data
        logger.info(
            "Loading historical data",
            backtest_id=backtest_id,
            symbol=config.symbol,
            start=config.start_date,
            end=config.end_date
        )
        
        market_data = await data_loader.load_data(
            symbol=config.symbol,
            timeframes=config.timeframes,
            start_date=config.start_date,
            end_date=config.end_date
        )
        
        _backtest_tasks[backtest_id]['progress'] = 0.4
        
        # Initialize backtest engine
        engine = BacktestEngine(
            initial_capital=config.initial_capital,
            risk_per_trade=config.risk_per_trade,
            max_concurrent_positions=config.max_concurrent_positions
        )
        
        # Load strategies into engine
        for strategy in strategies:
            engine.add_strategy(strategy)
        
        _backtest_tasks[backtest_id]['progress'] = 0.5
        
        # Run backtest
        logger.info("Running backtest", backtest_id=backtest_id)
        
        results = await engine.run(market_data)
        
        _backtest_tasks[backtest_id]['progress'] = 0.9
        
        # Store results
        _backtest_tasks[backtest_id]['total_trades'] = results.total_trades
        _backtest_tasks[backtest_id]['winning_trades'] = results.winning_trades
        _backtest_tasks[backtest_id]['win_rate'] = results.win_rate
        _backtest_tasks[backtest_id]['profit_factor'] = results.profit_factor
        _backtest_tasks[backtest_id]['total_return'] = results.total_return
        _backtest_tasks[backtest_id]['total_return_pct'] = results.total_return_pct
        _backtest_tasks[backtest_id]['max_drawdown'] = results.max_drawdown
        _backtest_tasks[backtest_id]['max_drawdown_pct'] = results.max_drawdown_pct
        _backtest_tasks[backtest_id]['sharpe_ratio'] = results.sharpe_ratio
        _backtest_tasks[backtest_id]['avg_r_multiple'] = results.avg_r_multiple
        _backtest_tasks[backtest_id]['trades'] = results.trades
        _backtest_tasks[backtest_id]['equity_curve'] = results.equity_curve
        
        _backtest_tasks[backtest_id]['status'] = 'completed'
        _backtest_tasks[backtest_id]['progress'] = 1.0
        _backtest_tasks[backtest_id]['completed_at'] = datetime.now(timezone.utc).isoformat()
        
        logger.info(
            "Backtest completed",
            backtest_id=backtest_id,
            total_trades=results.total_trades,
            win_rate=results.win_rate
        )
        
    except Exception as e:
        logger.error("Backtest failed", backtest_id=backtest_id, error=str(e))
        _backtest_tasks[backtest_id]['status'] = 'failed'
        _backtest_tasks[backtest_id]['error'] = str(e)


@router.post("/start", summary="Start new backtest", status_code=202)
async def start_backtest(
    config: BacktestConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Start a new backtest with the specified configuration.
    
    The backtest will:
    1. Load historical data for the specified symbol and timeframes
    2. Run pattern detection on each candle
    3. Generate trade signals using selected strategies
    4. Simulate trade execution with realistic fills
    5. Calculate performance metrics
    
    Processing happens asynchronously. Use GET /backtesting/{backtest_id} to track progress.
    """
    # Validate start date is before end date
    try:
        start_dt = datetime.fromisoformat(config.start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(config.end_date.replace('Z', '+00:00'))
        
        if start_dt >= end_dt:
            raise HTTPException(
                status_code=400,
                detail="start_date must be before end_date"
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    
    # Validate strategies exist
    for strategy_id in config.strategy_ids:
        strategy = db.query(StrategyRuleDB).filter(
            StrategyRuleDB.id == strategy_id
        ).first()
        
        if not strategy:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_id}' not found"
            )
    
    # Generate backtest ID
    backtest_id = f"bt_{uuid.uuid4().hex[:12]}"
    
    # Initialize task tracking
    _backtest_tasks[backtest_id] = {
        'backtest_id': backtest_id,
        'name': config.name,
        'status': 'pending',
        'progress': 0.0,
        'config': config.dict(),
        'total_trades': 0,
        'winning_trades': 0,
        'win_rate': 0.0,
        'profit_factor': 0.0,
        'total_return': 0.0,
        'total_return_pct': 0.0,
        'max_drawdown': 0.0,
        'max_drawdown_pct': 0.0,
        'sharpe_ratio': 0.0,
        'avg_r_multiple': 0.0,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'started_at': None,
        'completed_at': None,
        'error': None,
        'trades': [],
        'equity_curve': []
    }
    
    # Queue background task
    background_tasks.add_task(_run_backtest_task, backtest_id, config, db)
    
    logger.info("Backtest start requested", backtest_id=backtest_id, config=config.dict())
    
    return {
        "backtest_id": backtest_id,
        "status": "pending",
        "message": f"Backtest '{config.name}' queued for execution"
    }


@router.post("/upload-data", summary="Upload historical data")
async def upload_historical_data(
    file: UploadFile = File(..., description="CSV file with OHLCV data"),
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query(..., description="Timeframe (e.g., 1H, 4H)")
) -> Dict[str, Any]:
    """
    Upload historical price data for backtesting.
    
    Expected CSV format:
    ```
    timestamp,open,high,low,close,volume
    2024-01-01 00:00:00,50000,51000,49500,50500,1000
    ```
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported. Please upload a file with .csv extension"
        )
    
    # Validate timeframe
    valid_tfs = ['1M', '5M', '15M', '30M', '1H', '4H', '1D']
    if timeframe not in valid_tfs:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe. Must be one of: {', '.join(valid_tfs)}"
        )
    
    # Save uploaded file
    upload_dir = Path(settings.data_dir) / "historical" / symbol
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{timeframe}.csv"
    
    try:
        # Save file to disk
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        if len(contents) > 100 * 1024 * 1024:  # 100MB limit
            raise HTTPException(status_code=400, detail="File too large (max 100MB)")
        
        with open(file_path, 'wb') as f:
            f.write(contents)
        
        # Parse CSV to count rows
        import csv
        import io
        
        csv_data = contents.decode('utf-8')
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        
        logger.info(
            "Historical data uploaded",
            filename=file.filename,
            symbol=symbol,
            timeframe=timeframe,
            rows=len(rows)
        )
        
        return {
            "message": f"Data uploaded for {symbol} {timeframe}",
            "rows_processed": len(rows),
            "file_path": str(file_path)
        }
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 encoded CSV")
    except csv.Error as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")
    except Exception as e:
        logger.error("File upload failed", filename=file.filename, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process uploaded file")


@router.get("/", summary="List backtests")
async def list_backtests(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """List all backtests with their current status."""
    # Validate status filter
    if status and status not in ['pending', 'running', 'completed', 'failed']:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Must be one of: pending, running, completed, failed"
        )
    
    # Filter backtests
    backtests = list(_backtest_tasks.values())
    
    if status:
        backtests = [b for b in backtests if b['status'] == status]
    
    # Sort by creation time (newest first)
    backtests.sort(key=lambda b: b['created_at'], reverse=True)
    
    # Count total
    total = len(backtests)
    
    # Apply pagination
    backtests = backtests[offset:offset + limit]
    
    # Serialize (exclude detailed results from list)
    results = []
    for bt in backtests:
        result = {k: v for k, v in bt.items() if k not in ['trades', 'equity_curve']}
        results.append(BacktestResult(**result))
    
    logger.info("Backtest list requested", count=len(results), total=total)
    
    return {
        "data": results,
        "meta": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }
    }


@router.get("/{backtest_id}", summary="Get backtest details")
async def get_backtest(backtest_id: str) -> BacktestResult:
    """Get detailed information about a specific backtest."""
    # Validate backtest ID format
    if not backtest_id.startswith('bt_'):
        raise HTTPException(status_code=400, detail="Invalid backtest ID format")
    
    backtest_data = _backtest_tasks.get(backtest_id)
    
    if not backtest_data:
        raise HTTPException(
            status_code=404,
            detail=f"Backtest '{backtest_id}' not found"
        )
    
    # Serialize (exclude trades and equity curve from summary)
    result_data = {k: v for k, v in backtest_data.items() if k not in ['trades', 'equity_curve']}
    
    logger.info("Backtest details requested", backtest_id=backtest_id)
    
    return BacktestResult(**result_data)


@router.get("/{backtest_id}/trades", summary="Get backtest trades")
async def get_backtest_trades(
    backtest_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of trades to return"),
    offset: int = Query(0, ge=0, description="Number of trades to skip")
) -> Dict[str, Any]:
    """Get all trades from a backtest."""
    # Validate backtest ID format
    if not backtest_id.startswith('bt_'):
        raise HTTPException(status_code=400, detail="Invalid backtest ID format")
    
    backtest_data = _backtest_tasks.get(backtest_id)
    
    if not backtest_data:
        raise HTTPException(
            status_code=404,
            detail=f"Backtest '{backtest_id}' not found"
        )
    
    if backtest_data['status'] != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Backtest is {backtest_data['status']}, not completed"
        )
    
    # Get trades
    all_trades = backtest_data.get('trades', [])
    total = len(all_trades)
    
    # Apply pagination
    trades = all_trades[offset:offset + limit]
    
    logger.info(
        "Backtest trades requested",
        backtest_id=backtest_id,
        count=len(trades),
        total=total
    )
    
    return {
        "data": trades,
        "meta": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }
    }


@router.get("/{backtest_id}/equity-curve", summary="Get equity curve data")
async def get_equity_curve(backtest_id: str) -> Dict[str, Any]:
    """Get equity curve data for plotting."""
    # Validate backtest ID format
    if not backtest_id.startswith('bt_'):
        raise HTTPException(status_code=400, detail="Invalid backtest ID format")
    
    backtest_data = _backtest_tasks.get(backtest_id)
    
    if not backtest_data:
        raise HTTPException(
            status_code=404,
            detail=f"Backtest '{backtest_id}' not found"
        )
    
    if backtest_data['status'] != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Backtest is {backtest_data['status']}, not completed"
        )
    
    equity_curve = backtest_data.get('equity_curve', [])
    
    logger.info("Equity curve requested", backtest_id=backtest_id, points=len(equity_curve))
    
    return {
        "backtest_id": backtest_id,
        "equity_curve": equity_curve,
        "initial_capital": backtest_data['config']['initial_capital']
    }


@router.delete("/{backtest_id}", summary="Delete backtest")
async def delete_backtest(backtest_id: str) -> Dict[str, Any]:
    """Delete a backtest and all associated data."""
    # Validate backtest ID format
    if not backtest_id.startswith('bt_'):
        raise HTTPException(status_code=400, detail="Invalid backtest ID format")
    
    if backtest_id not in _backtest_tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Backtest '{backtest_id}' not found"
        )
    
    # Remove backtest
    del _backtest_tasks[backtest_id]
    
    logger.info("Backtest deleted", backtest_id=backtest_id)
    
    return {"message": "Backtest deleted successfully", "backtest_id": backtest_id}
