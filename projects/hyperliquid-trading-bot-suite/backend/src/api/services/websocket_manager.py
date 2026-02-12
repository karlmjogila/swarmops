"""WebSocket connection manager for real-time streaming."""

from typing import Dict, List, Set, Any, Optional
from enum import Enum
from fastapi import WebSocket
from collections import defaultdict
import asyncio
import json
from datetime import datetime
import structlog

logger = structlog.get_logger()


class StreamType(str, Enum):
    """Types of data streams."""
    BACKTEST = "backtest"
    LIVE_TRADING = "live_trading"
    MARKET_DATA = "market_data"


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting.
    
    Organizes connections by stream type and stream ID, enabling
    targeted message delivery (e.g., all clients watching a specific backtest).
    
    Features:
    - Multiple concurrent streams per type
    - Broadcast to specific stream or all streams of a type
    - Connection health monitoring
    - Automatic cleanup on disconnect
    """
    
    def __init__(self):
        # Structure: {StreamType: {stream_id: Set[WebSocket]}}
        self._connections: Dict[StreamType, Dict[str, Set[WebSocket]]] = {
            StreamType.BACKTEST: defaultdict(set),
            StreamType.LIVE_TRADING: defaultdict(set),
            StreamType.MARKET_DATA: defaultdict(set),
        }
        
        # Reverse lookup: WebSocket -> (StreamType, stream_id)
        self._socket_to_stream: Dict[WebSocket, tuple[StreamType, str]] = {}
        
        # Connection metadata
        self._connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        logger.info("WebSocketManager initialized")
    
    async def connect(
        self,
        websocket: WebSocket,
        stream_type: StreamType,
        stream_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection instance
            stream_type: Type of stream (backtest, live_trading, market_data)
            stream_id: Unique identifier for the stream
            metadata: Optional connection metadata
        """
        await websocket.accept()
        
        # Register connection
        self._connections[stream_type][stream_id].add(websocket)
        self._socket_to_stream[websocket] = (stream_type, stream_id)
        
        # Store metadata
        if metadata:
            self._connection_metadata[websocket] = metadata
        
        logger.info(
            "WebSocket registered",
            stream_type=stream_type.value,
            stream_id=stream_id,
            total_connections=self._count_total_connections(),
            stream_connections=len(self._connections[stream_type][stream_id])
        )
    
    async def disconnect(
        self,
        websocket: WebSocket,
        stream_type: StreamType,
        stream_id: str
    ) -> None:
        """
        Unregister and clean up a WebSocket connection.
        
        Args:
            websocket: WebSocket connection instance
            stream_type: Type of stream
            stream_id: Stream identifier
        """
        # Remove from main registry
        if stream_id in self._connections[stream_type]:
            self._connections[stream_type][stream_id].discard(websocket)
            
            # Clean up empty stream buckets
            if not self._connections[stream_type][stream_id]:
                del self._connections[stream_type][stream_id]
        
        # Remove reverse lookup
        self._socket_to_stream.pop(websocket, None)
        
        # Remove metadata
        self._connection_metadata.pop(websocket, None)
        
        logger.info(
            "WebSocket unregistered",
            stream_type=stream_type.value,
            stream_id=stream_id,
            total_connections=self._count_total_connections()
        )
    
    async def send_to_stream(
        self,
        stream_type: StreamType,
        stream_id: str,
        message: Dict[str, Any]
    ) -> int:
        """
        Send a message to all connections watching a specific stream.
        
        Args:
            stream_type: Type of stream
            stream_id: Stream identifier
            message: Message dictionary to send
            
        Returns:
            Number of clients that received the message
        """
        if stream_id not in self._connections[stream_type]:
            return 0
        
        connections = self._connections[stream_type][stream_id].copy()
        sent_count = 0
        failed_sockets = []
        
        # Broadcast to all connections
        for websocket in connections:
            try:
                await websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.error(
                    "Failed to send message",
                    stream_type=stream_type.value,
                    stream_id=stream_id,
                    error=str(e)
                )
                failed_sockets.append(websocket)
        
        # Clean up failed connections
        for websocket in failed_sockets:
            await self.disconnect(websocket, stream_type, stream_id)
        
        return sent_count
    
    async def broadcast_to_type(
        self,
        stream_type: StreamType,
        message: Dict[str, Any]
    ) -> int:
        """
        Broadcast a message to all connections of a specific stream type.
        
        Args:
            stream_type: Type of stream
            message: Message dictionary to send
            
        Returns:
            Total number of clients that received the message
        """
        total_sent = 0
        
        for stream_id in list(self._connections[stream_type].keys()):
            sent = await self.send_to_stream(stream_type, stream_id, message)
            total_sent += sent
        
        return total_sent
    
    async def send_progress(
        self,
        backtest_id: str,
        progress: float,
        current_time: datetime,
        metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send backtest progress update.
        
        Args:
            backtest_id: Backtest identifier
            progress: Progress percentage (0-100)
            current_time: Current backtest simulation time
            metrics: Optional interim performance metrics
        """
        message = {
            "type": "progress",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "backtest_id": backtest_id,
                "progress": progress,
                "current_time": current_time.isoformat(),
                "metrics": metrics or {}
            }
        }
        
        await self.send_to_stream(StreamType.BACKTEST, backtest_id, message)
    
    async def send_trade(
        self,
        backtest_id: str,
        trade_data: Dict[str, Any]
    ) -> None:
        """
        Send trade execution event.
        
        Args:
            backtest_id: Backtest identifier
            trade_data: Trade execution details
        """
        message = {
            "type": "trade",
            "timestamp": datetime.utcnow().isoformat(),
            "data": trade_data
        }
        
        await self.send_to_stream(StreamType.BACKTEST, backtest_id, message)
    
    async def send_equity_update(
        self,
        backtest_id: str,
        equity: float,
        balance: float,
        drawdown: float,
        timestamp: datetime
    ) -> None:
        """
        Send equity curve update.
        
        Args:
            backtest_id: Backtest identifier
            equity: Current equity value
            balance: Current balance
            drawdown: Current drawdown percentage
            timestamp: Simulation timestamp
        """
        message = {
            "type": "equity",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "backtest_id": backtest_id,
                "time": timestamp.isoformat(),
                "equity": equity,
                "balance": balance,
                "drawdown": drawdown
            }
        }
        
        await self.send_to_stream(StreamType.BACKTEST, backtest_id, message)
    
    async def send_metrics(
        self,
        backtest_id: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Send performance metrics update.
        
        Args:
            backtest_id: Backtest identifier
            metrics: Performance metrics dictionary
        """
        message = {
            "type": "metrics",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "backtest_id": backtest_id,
                **metrics
            }
        }
        
        await self.send_to_stream(StreamType.BACKTEST, backtest_id, message)
    
    async def send_error(
        self,
        stream_type: StreamType,
        stream_id: str,
        error: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send error notification.
        
        Args:
            stream_type: Type of stream
            stream_id: Stream identifier
            error: Error message
            details: Optional error details
        """
        message = {
            "type": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "error": error,
                "details": details or {}
            }
        }
        
        await self.send_to_stream(stream_type, stream_id, message)
    
    async def send_complete(
        self,
        backtest_id: str,
        final_metrics: Dict[str, Any]
    ) -> None:
        """
        Send backtest completion notification.
        
        Args:
            backtest_id: Backtest identifier
            final_metrics: Final performance metrics
        """
        message = {
            "type": "complete",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "backtest_id": backtest_id,
                "metrics": final_metrics
            }
        }
        
        await self.send_to_stream(StreamType.BACKTEST, backtest_id, message)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active connections.
        
        Returns:
            Dictionary with connection counts and stream details
        """
        streams = []
        
        for stream_type in StreamType:
            for stream_id, connections in self._connections[stream_type].items():
                streams.append({
                    "type": stream_type.value,
                    "id": stream_id,
                    "connections": len(connections)
                })
        
        return {
            "backtest": sum(
                len(conns) for conns in self._connections[StreamType.BACKTEST].values()
            ),
            "live_trading": sum(
                len(conns) for conns in self._connections[StreamType.LIVE_TRADING].values()
            ),
            "market_data": sum(
                len(conns) for conns in self._connections[StreamType.MARKET_DATA].values()
            ),
            "total": self._count_total_connections(),
            "streams": streams
        }
    
    def _count_total_connections(self) -> int:
        """Count total active connections across all streams."""
        total = 0
        for stream_type in StreamType:
            for connections in self._connections[stream_type].values():
                total += len(connections)
        return total
    
    def get_stream_connections(
        self,
        stream_type: StreamType,
        stream_id: str
    ) -> int:
        """
        Get number of active connections for a specific stream.
        
        Args:
            stream_type: Type of stream
            stream_id: Stream identifier
            
        Returns:
            Number of active connections
        """
        if stream_id in self._connections[stream_type]:
            return len(self._connections[stream_type][stream_id])
        return 0
    
    async def cleanup_stale_connections(self) -> int:
        """
        Check and clean up stale connections.
        
        Returns:
            Number of connections cleaned up
        """
        cleaned = 0
        
        for stream_type in StreamType:
            for stream_id in list(self._connections[stream_type].keys()):
                connections = self._connections[stream_type][stream_id].copy()
                
                for websocket in connections:
                    try:
                        # Send ping to check if connection is alive
                        await websocket.send_json({
                            "type": "ping",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    except Exception:
                        # Connection is dead, clean it up
                        await self.disconnect(websocket, stream_type, stream_id)
                        cleaned += 1
        
        if cleaned > 0:
            logger.info("Cleaned up stale connections", count=cleaned)
        
        return cleaned
