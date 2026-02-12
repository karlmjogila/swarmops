"""Position monitoring API endpoints.

Provides WebSocket streaming of live positions and REST endpoints for position queries.
"""

import asyncio
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from hl_bot.trading.position_monitor import PositionMonitor, PositionUpdate
from hl_bot.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/positions", tags=["positions"])


# Global position monitor instance (will be initialized in lifespan)
_position_monitor: PositionMonitor | None = None


def set_position_monitor(monitor: PositionMonitor) -> None:
    """Set the global position monitor instance.

    Args:
        monitor: Position monitor to use
    """
    global _position_monitor
    _position_monitor = monitor
    logger.info("Position monitor registered with API")


def get_position_monitor() -> PositionMonitor:
    """Get the position monitor dependency.

    Returns:
        Position monitor instance

    Raises:
        HTTPException: If monitor not initialized
    """
    if _position_monitor is None:
        raise HTTPException(
            status_code=503,
            detail="Position monitor not initialized",
        )
    return _position_monitor


@router.get("/summary")
async def get_position_summary(
    monitor: Annotated[PositionMonitor, Depends(get_position_monitor)]
) -> JSONResponse:
    """Get current position summary.

    Returns summary of all active positions with P&L metrics.

    Returns:
        Position summary with metrics
    """
    try:
        summary = monitor.get_position_summary()
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Failed to get position summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get position summary: {str(e)}",
        )


@router.get("/health")
async def position_monitor_health(
    monitor: Annotated[PositionMonitor, Depends(get_position_monitor)]
) -> dict:
    """Check position monitor health.

    Returns:
        Health status
    """
    return {
        "status": "healthy" if monitor.is_running else "stopped",
        "running": monitor.is_running,
    }


class ConnectionManager:
    """Manages WebSocket connections for position streaming."""

    def __init__(self):
        """Initialize connection manager."""
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection.

        Args:
            websocket: WebSocket connection to accept
        """
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)
        logger.info(f"WebSocket connected: {len(self._connections)} total")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)
        logger.info(f"WebSocket disconnected: {len(self._connections)} remaining")

    async def broadcast(self, message: dict) -> None:
        """Broadcast message to all connected clients.

        Args:
            message: Message to broadcast
        """
        if not self._connections:
            return

        # Convert to JSON
        json_message = json.dumps(message)

        # Send to all connections
        disconnected = []
        for connection in self._connections[:]:  # Copy list to avoid modification during iteration
            try:
                await connection.send_text(json_message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                for connection in disconnected:
                    if connection in self._connections:
                        self._connections.remove(connection)

    @property
    def connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._connections)


# Global connection manager
_connection_manager = ConnectionManager()


@router.websocket("/stream")
async def position_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time position updates.

    Streams position updates as they occur:
    - Fill events (position changes from order fills)
    - Price updates (unrealized P&L changes)
    - Position changes (from exchange sync)

    Message format:
    ```json
    {
        "type": "position_update",
        "event_type": "fill" | "price_update" | "position_change",
        "symbol": "BTC-USD",
        "timestamp": "2025-02-11T17:30:00Z",
        "position": {
            "symbol": "BTC-USD",
            "side": "long" | "short" | "flat",
            "quantity": "0.1",
            "entry_price": "50000.0",
            "current_price": "50500.0",
            "unrealized_pnl": "50.0",
            "realized_pnl": "0.0",
            "notional_value": "5050.0",
            "total_pnl": "50.0",
            "leverage": "1.0",
            "last_updated": "2025-02-11T17:30:00Z",
            "is_flat": false
        },
        "fill": {
            "symbol": "BTC-USD",
            "side": "buy" | "sell",
            "quantity": "0.1",
            "price": "50000.0",
            "timestamp": "2025-02-11T17:30:00Z",
            "order_id": "abc123",
            "fill_id": "fill123",
            "fee": "5.0"
        } | null
    }
    ```

    Also supports client commands:
    - `{"action": "subscribe"}` - Subscribe to position updates
    - `{"action": "get_summary"}` - Get current position summary
    """
    # Get position monitor
    try:
        monitor = get_position_monitor()
    except HTTPException:
        await websocket.close(code=1011, reason="Position monitor not available")
        return

    # Connect to manager
    await _connection_manager.connect(websocket)

    # Send initial position summary
    try:
        summary = monitor.get_position_summary()
        await websocket.send_json({
            "type": "initial_state",
            **summary
        })
    except Exception as e:
        logger.error(f"Failed to send initial state: {e}")

    try:
        # Handle client messages
        while True:
            try:
                # Receive message with timeout
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Parse client message
                try:
                    message = json.loads(data)
                    action = message.get("action")

                    if action == "get_summary":
                        # Send current position summary
                        summary = monitor.get_position_summary()
                        await websocket.send_json({
                            "type": "summary",
                            **summary
                        })
                    elif action == "ping":
                        # Respond to ping
                        await websocket.send_json({"type": "pong"})
                    else:
                        logger.warning(f"Unknown action: {action}")

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client: {data[:100]}")

            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        await _connection_manager.disconnect(websocket)


async def broadcast_position_update(update: PositionUpdate) -> None:
    """Broadcast position update to all connected clients.

    This is called by the position monitor when positions change.

    Args:
        update: Position update to broadcast
    """
    await _connection_manager.broadcast(update.to_dict())


def initialize_position_streaming(monitor: PositionMonitor) -> None:
    """Initialize position streaming with the monitor.

    Registers the broadcast callback with the position monitor.

    Args:
        monitor: Position monitor instance
    """
    # Register broadcast callback
    monitor.on_position_update(broadcast_position_update)
    logger.info("Position streaming initialized")
