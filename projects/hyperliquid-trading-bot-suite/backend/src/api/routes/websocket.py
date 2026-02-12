"""WebSocket endpoints for real-time streaming."""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, status
from datetime import datetime, timezone
import structlog
import json
import asyncio

from ..services.websocket_manager import WebSocketManager, StreamType
from ..security.websocket_auth import (
    authenticate_websocket,
    WebSocketAuthenticator,
    AuthenticatedWebSocket
)
from ..security.auth import UserInDB, UserRole

router = APIRouter()
logger = structlog.get_logger()

# Global WebSocket manager instance
ws_manager = WebSocketManager()


async def require_websocket_auth(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT access token")
) -> Optional[AuthenticatedWebSocket]:
    """
    Dependency for authenticated WebSocket connections.
    
    Returns None if authentication fails (connection will be closed).
    """
    authenticator = WebSocketAuthenticator(require_auth=True)
    user = await authenticator.authenticate_from_query(websocket, token)
    
    if not user:
        return None
    
    return AuthenticatedWebSocket(websocket, user)


@router.websocket("/stream/backtest/{backtest_id}")
async def stream_backtest(
    websocket: WebSocket,
    backtest_id: str,
    token: Optional[str] = Query(None, description="JWT access token")
):
    """
    Stream real-time backtest execution data.
    
    Requires authentication via token query parameter.
    
    Streams:
    - Backtest progress updates
    - Trade execution events
    - Equity curve updates
    - Performance metrics
    - Error notifications
    
    Message format:
    {
        "type": "progress|trade|equity|metrics|error|complete",
        "timestamp": "ISO-8601 timestamp",
        "data": { ... }
    }
    """
    # Authenticate
    authenticator = WebSocketAuthenticator(require_auth=True)
    user = await authenticator.authenticate_from_query(websocket, token)
    
    if not user:
        return  # Connection closed by authenticator
    
    # Accept connection after authentication
    await websocket.accept()
    
    # Create authenticated wrapper
    auth_ws = AuthenticatedWebSocket(websocket, user)
    
    # Register with manager
    await ws_manager.connect(websocket, StreamType.BACKTEST, backtest_id)
    
    try:
        logger.info(
            "Authenticated WebSocket connected",
            backtest_id=backtest_id,
            user=user.username,
            client=websocket.client
        )
        
        # Send initial connection confirmation
        await auth_ws.send_json({
            "type": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "backtest_id": backtest_id,
                "user": user.username,
                "message": "Connected to backtest stream"
            }
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages (mostly for keepalive or commands)
                data = await auth_ws.receive_text()
                
                try:
                    message = json.loads(data)
                    
                    # Handle commands
                    if message.get("type") == "ping":
                        await auth_ws.send_json({
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    elif message.get("type") == "pause":
                        # Future: implement pause/resume
                        logger.info("Pause requested", backtest_id=backtest_id, user=user.username)
                        await auth_ws.send_json({
                            "type": "pause_ack",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    elif message.get("type") == "stop":
                        # Future: implement graceful stop
                        logger.info("Stop requested", backtest_id=backtest_id, user=user.username)
                        await auth_ws.send_json({
                            "type": "stop_ack",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                        break
                        
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON received", data=data)
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error("Error receiving message", error=str(e))
                break
                
    except Exception as e:
        logger.error(
            "WebSocket error",
            backtest_id=backtest_id,
            user=user.username,
            error=str(e),
            exc_info=e
        )
    finally:
        await ws_manager.disconnect(websocket, StreamType.BACKTEST, backtest_id)
        logger.info("WebSocket disconnected", backtest_id=backtest_id, user=user.username)


@router.websocket("/stream/live-trading")
async def stream_live_trading(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT access token"),
    symbols: Optional[str] = Query(None, description="Comma-separated list of symbols to watch")
):
    """
    Stream live trading data.
    
    Requires authentication via token query parameter.
    Requires 'trader' role.
    
    Streams:
    - Position updates
    - Order execution
    - Risk metrics
    - P&L updates
    - Market data (optional)
    
    Message format:
    {
        "type": "position|order|risk|pnl|market",
        "timestamp": "ISO-8601 timestamp",
        "data": { ... }
    }
    """
    # Authenticate
    authenticator = WebSocketAuthenticator(require_auth=True)
    user = await authenticator.authenticate_from_query(websocket, token)
    
    if not user:
        return  # Connection closed by authenticator
    
    # Check role (trader required for live trading)
    if UserRole.TRADER.value not in user.roles and UserRole.ADMIN.value not in user.roles:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Trader role required for live trading stream"
        )
        return
    
    # Accept connection after authentication
    await websocket.accept()
    
    stream_id = f"live_{user.id}_{datetime.now(timezone.utc).timestamp()}"
    
    # Register with manager
    await ws_manager.connect(websocket, StreamType.LIVE_TRADING, stream_id)
    
    try:
        logger.info(
            "Live trading WebSocket connected",
            stream_id=stream_id,
            user=user.username,
            symbols=symbols,
            client=websocket.client
        )
        
        # Parse symbols filter
        symbol_list = symbols.split(",") if symbols else []
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "stream_id": stream_id,
                "user": user.username,
                "symbols": symbol_list,
                "message": "Connected to live trading stream"
            }
        })
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    
                    # Handle commands
                    if message.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    elif message.get("type") == "subscribe":
                        # Subscribe to additional symbols
                        new_symbols = message.get("data", {}).get("symbols", [])
                        logger.info("Symbol subscription", symbols=new_symbols, user=user.username)
                        await websocket.send_json({
                            "type": "subscribe_ack",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "data": {"symbols": new_symbols}
                        })
                        
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON received", data=data)
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error("Error receiving message", error=str(e))
                break
                
    except Exception as e:
        logger.error(
            "WebSocket error",
            stream_id=stream_id,
            user=user.username,
            error=str(e),
            exc_info=e
        )
    finally:
        await ws_manager.disconnect(websocket, StreamType.LIVE_TRADING, stream_id)
        logger.info("Live trading WebSocket disconnected", stream_id=stream_id, user=user.username)


@router.websocket("/stream/market-data/{symbol}")
async def stream_market_data(
    websocket: WebSocket,
    symbol: str,
    token: Optional[str] = Query(None, description="JWT access token")
):
    """
    Stream real-time market data for a specific symbol.
    
    Requires authentication via token query parameter.
    
    Streams:
    - Candle updates (multiple timeframes)
    - Pattern detection results
    - Market structure updates
    - Confluence scores
    
    Message format:
    {
        "type": "candle|pattern|structure|confluence",
        "timestamp": "ISO-8601 timestamp",
        "data": { ... }
    }
    """
    # Authenticate
    authenticator = WebSocketAuthenticator(require_auth=True)
    user = await authenticator.authenticate_from_query(websocket, token)
    
    if not user:
        return  # Connection closed by authenticator
    
    # Validate symbol format
    symbol = symbol.upper().strip()
    if not all(c.isalnum() or c == '-' for c in symbol):
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid symbol format"
        )
        return
    
    # Accept connection after authentication
    await websocket.accept()
    
    # Register with manager
    await ws_manager.connect(websocket, StreamType.MARKET_DATA, symbol)
    
    try:
        logger.info(
            "Market data WebSocket connected",
            symbol=symbol,
            user=user.username,
            client=websocket.client
        )
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "symbol": symbol,
                "user": user.username,
                "message": f"Connected to market data stream for {symbol}"
            }
        })
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    
                    if message.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                        
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON received", data=data)
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error("Error receiving message", error=str(e))
                break
                
    except Exception as e:
        logger.error(
            "WebSocket error",
            symbol=symbol,
            user=user.username,
            error=str(e),
            exc_info=e
        )
    finally:
        await ws_manager.disconnect(websocket, StreamType.MARKET_DATA, symbol)
        logger.info("Market data WebSocket disconnected", symbol=symbol, user=user.username)


@router.get("/stream/status", summary="Get active stream status")
async def get_stream_status() -> Dict[str, Any]:
    """
    Get status of all active WebSocket streams.
    
    This endpoint is public for health monitoring purposes.
    """
    stats = ws_manager.get_stats()
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_connections": {
            "backtest": stats["backtest"],
            "live_trading": stats["live_trading"],
            "market_data": stats["market_data"],
            "total": stats["total"]
        },
        "streams": stats["streams"]
    }
