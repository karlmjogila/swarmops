"""Backtest API routes."""

import asyncio
import json
import re
import subprocess
from typing import Dict, Optional, Literal
from datetime import datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.repositories.ohlcv import OHLCVRepository

router = APIRouter(prefix="/backtest", tags=["backtest"])

# Valid data source types
DataSourceType = Literal['hyperliquid', 'csv', 'auto']


# Store active backtest sessions
active_sessions: Dict[str, subprocess.Popen] = {}

# Strict validation patterns
SYMBOL_PATTERN = re.compile(r"^[A-Z]{2,10}(-[A-Z]{2,10})?$")
DATE_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")


class BacktestStartRequest(BaseModel):
    """Request to start a backtest."""
    
    symbol: str = Field(..., description="Trading symbol (e.g., BTC, ETH-USD)")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    initial_capital: float = Field(default=10000.0, gt=0, le=100_000_000)
    position_size_percent: float = Field(default=0.02, gt=0, le=1)
    max_open_trades: int = Field(default=3, ge=1, le=100)
    use_stop_orders: bool = Field(default=True)
    use_take_profits: bool = Field(default=True)
    emit_interval: int = Field(default=10, ge=1, le=1000)
    data_source: DataSourceType = Field(
        default='auto',
        description="Data source: 'hyperliquid' (API data), 'csv' (imported CSV), or 'auto' (prefer hyperliquid, fallback to csv)"
    )
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format to prevent injection."""
        v = v.upper().strip()
        if not SYMBOL_PATTERN.match(v):
            raise ValueError(
                "Symbol must be 2-10 uppercase letters, optionally followed by -SUFFIX "
                "(e.g., BTC, ETH-USD, DOGE-USDT)"
            )
        return v
    
    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Validate date format strictly."""
        v = v.strip()
        if not DATE_PATTERN.match(v):
            raise ValueError("Date must be in YYYY-MM-DD format")
        # Also validate it's a real date
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date: {v}")
        return v


class BacktestControlRequest(BaseModel):
    """Request to control a backtest."""
    
    command: str = Field(..., description="Command: pause, resume, stop, step, speed, seek")
    speed: Optional[float] = Field(default=None, description="Playback speed for 'speed' command")
    index: Optional[int] = Field(default=None, description="Candle index for 'seek' command")


class BacktestSession(BaseModel):
    """Backtest session info."""
    
    session_id: str
    symbol: str
    start_date: str
    end_date: str
    status: str
    created_at: datetime


@router.post("/start")
async def start_backtest(request: BacktestStartRequest) -> Dict:
    """Start a new backtest session.
    
    Args:
        request: Backtest configuration
        
    Returns:
        Session ID and WebSocket URL
    """
    import uuid
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Additional validation: ensure dates are logical
    start_dt = datetime.strptime(request.start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(request.end_date, "%Y-%m-%d")
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")
    
    # Build command with validated/sanitized inputs
    # All inputs are validated by Pydantic validators above
    cmd = [
        "python",
        "scripts/run_backtest_stream.py",
        "--session-id", session_id,
        "--symbol", request.symbol,  # Validated: uppercase letters only
        "--start-date", request.start_date,  # Validated: YYYY-MM-DD
        "--end-date", request.end_date,  # Validated: YYYY-MM-DD
        "--initial-capital", str(int(request.initial_capital)),  # Sanitize to int
        "--position-size-percent", str(round(request.position_size_percent, 4)),
        "--max-open-trades", str(int(request.max_open_trades)),
        "--use-stop-orders", "true" if request.use_stop_orders else "false",
        "--use-take-profits", "true" if request.use_take_profits else "false",
        "--emit-interval", str(int(request.emit_interval)),
        "--data-source", request.data_source,  # Validated: literal type
    ]
    
    try:
        # Start subprocess - NEVER use shell=True with user input
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            shell=False,  # Explicit: no shell interpretation
        )
        
        # Store session
        active_sessions[session_id] = process
        
        return {
            "session_id": session_id,
            "websocket_url": f"/backtest/ws/{session_id}",
            "status": "started",
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start backtest: {e}")


@router.post("/control/{session_id}")
async def control_backtest(session_id: str, request: BacktestControlRequest) -> Dict:
    """Send control command to backtest.
    
    Args:
        session_id: Backtest session ID
        request: Control command
        
    Returns:
        Command status
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    process = active_sessions[session_id]
    
    if process.poll() is not None:
        # Process has terminated
        del active_sessions[session_id]
        raise HTTPException(status_code=410, detail="Session has ended")
    
    # Build command
    command = {"command": request.command}
    
    if request.command == "speed" and request.speed is not None:
        command["speed"] = request.speed
    elif request.command == "seek" and request.index is not None:
        command["index"] = request.index
    
    try:
        # Send command to stdin
        process.stdin.write(json.dumps(command) + "\n")
        process.stdin.flush()
        
        return {"status": "sent", "command": request.command}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {e}")


@router.get("/sessions")
async def list_sessions() -> Dict:
    """List active backtest sessions.
    
    Returns:
        List of active sessions
    """
    sessions = []
    
    # Clean up dead sessions
    dead_sessions = []
    for session_id, process in active_sessions.items():
        if process.poll() is not None:
            dead_sessions.append(session_id)
    
    for session_id in dead_sessions:
        del active_sessions[session_id]
    
    return {
        "sessions": list(active_sessions.keys()),
        "count": len(active_sessions),
    }


@router.delete("/sessions/{session_id}")
async def stop_session(session_id: str) -> Dict:
    """Stop a backtest session.
    
    Args:
        session_id: Session to stop
        
    Returns:
        Stop status
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    process = active_sessions[session_id]
    
    try:
        # Send stop command
        process.stdin.write(json.dumps({"command": "stop"}) + "\n")
        process.stdin.flush()
        
        # Wait for process to terminate (with timeout)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill if it doesn't stop gracefully
            process.kill()
        
        del active_sessions[session_id]
        
        return {"status": "stopped", "session_id": session_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop session: {e}")


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for backtest streaming.
    
    Args:
        websocket: WebSocket connection
        session_id: Backtest session ID
    """
    await websocket.accept()
    
    if session_id not in active_sessions:
        await websocket.send_json({"type": "error", "error": "Session not found"})
        await websocket.close()
        return
    
    process = active_sessions[session_id]
    
    try:
        # Stream stdout to WebSocket
        while process.poll() is None:
            # Read line from stdout
            line = process.stdout.readline()
            
            if line:
                try:
                    # Parse JSON and send to client
                    data = json.loads(line.strip())
                    await websocket.send_json(data)
                except json.JSONDecodeError:
                    # Not JSON, might be error or log
                    await websocket.send_json({
                        "type": "log",
                        "message": line.strip(),
                    })
            else:
                # No data, small delay to avoid busy loop
                await asyncio.sleep(0.01)
            
            # Check for client disconnect
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.001)
            except asyncio.TimeoutError:
                pass  # No message from client
            except WebSocketDisconnect:
                break
        
        # Process ended, send completion message
        await websocket.send_json({
            "type": "completed",
            "session_id": session_id,
        })
        
    except WebSocketDisconnect:
        pass  # Client disconnected
    except Exception as e:
        await websocket.send_json({"type": "error", "error": str(e)})
    finally:
        # Clean up
        if session_id in active_sessions:
            del active_sessions[session_id]
        
        try:
            await websocket.close()
        except:
            pass


class DataAvailabilityResponse(BaseModel):
    """Response model for data availability."""
    
    symbol: str
    timeframe: str
    sources: Dict


@router.get("/data-availability")
async def get_data_availability(
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query(default="1h", description="Candle timeframe"),
    db: Session = Depends(get_db),
) -> DataAvailabilityResponse:
    """Get data availability information for each source.
    
    Returns which data sources have data available for the given symbol
    and timeframe, including date ranges and candle counts.
    
    Args:
        symbol: Trading symbol (e.g., BTC-USD)
        timeframe: Candle timeframe (e.g., 5m, 15m, 1h)
        db: Database session (injected)
        
    Returns:
        Data availability for each source (hyperliquid, csv)
        
    Example:
        ```bash
        curl "http://localhost:8000/backtest/data-availability?symbol=BTC-USD&timeframe=1h"
        ```
    """
    repo = OHLCVRepository(db)
    
    # Normalize symbol
    symbol = symbol.upper().strip()
    
    availability = repo.get_data_availability_by_source(symbol, timeframe)
    
    return DataAvailabilityResponse(
        symbol=symbol,
        timeframe=timeframe,
        sources=availability,
    )
