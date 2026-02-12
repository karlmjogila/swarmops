"""
Hyperliquid MCP Client Implementation

This module provides a client for interacting with Hyperliquid DEX through the MCP protocol.
Supports both paper trading (simulated) and live trading modes.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from decimal import Decimal
import websockets
import aiohttp

from ..types import (
    Order, OrderSide, OrderType, OrderStatus, Position, 
    Trade, Balance, MarketData, TradingMode
)
from ..config import HyperliquidConfig


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    
    Implements a simple token bucket algorithm to enforce rate limits
    and prevent getting banned by the exchange.
    """
    
    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_size: int = 20,
        retry_after_rate_limit: float = 60.0
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_second: Steady-state request rate
            burst_size: Maximum burst of requests allowed
            retry_after_rate_limit: Seconds to wait after hitting rate limit
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.retry_after_rate_limit = retry_after_rate_limit
        
        # Token bucket state
        self._tokens = float(burst_size)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()
        
        # Rate limit tracking
        self._rate_limited_until: Optional[float] = None
        self._consecutive_rate_limits = 0
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from the bucket. Blocks if necessary.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens acquired, False if rate limited
        """
        async with self._lock:
            # Check if we're in a rate-limit cooldown
            if self._rate_limited_until:
                if time.monotonic() < self._rate_limited_until:
                    wait_time = self._rate_limited_until - time.monotonic()
                    logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                self._rate_limited_until = None
            
            # Refill tokens based on elapsed time
            now = time.monotonic()
            elapsed = now - self._last_update
            self._tokens = min(
                self.burst_size,
                self._tokens + elapsed * self.requests_per_second
            )
            self._last_update = now
            
            # Check if we have enough tokens
            if self._tokens >= tokens:
                self._tokens -= tokens
                self._consecutive_rate_limits = 0
                return True
            
            # Wait for tokens to become available
            wait_time = (tokens - self._tokens) / self.requests_per_second
            logger.debug(f"Rate limiter waiting {wait_time:.2f}s for tokens")
            await asyncio.sleep(wait_time)
            
            # Recalculate after wait
            now = time.monotonic()
            elapsed = now - self._last_update
            self._tokens = min(
                self.burst_size,
                self._tokens + elapsed * self.requests_per_second
            )
            self._last_update = now
            self._tokens -= tokens
            
            return True
    
    def record_rate_limit(self):
        """Record that we hit a rate limit from the server."""
        self._consecutive_rate_limits += 1
        # Exponential backoff: 60s, 120s, 240s, etc.
        backoff = self.retry_after_rate_limit * (2 ** (self._consecutive_rate_limits - 1))
        backoff = min(backoff, 600)  # Cap at 10 minutes
        self._rate_limited_until = time.monotonic() + backoff
        logger.warning(f"Rate limit recorded. Backing off for {backoff:.0f}s")
    
    def reset(self):
        """Reset rate limiter state."""
        self._tokens = float(self.burst_size)
        self._last_update = time.monotonic()
        self._rate_limited_until = None
        self._consecutive_rate_limits = 0


class CircuitBreaker:
    """
    Circuit breaker for connection management.
    
    Prevents hammering the exchange during outages with exponential backoff.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            half_open_max_calls: Test calls in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        # State: closed, open, half_open
        self._state = "closed"
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
    
    async def can_proceed(self) -> bool:
        """Check if a call can proceed."""
        async with self._lock:
            if self._state == "closed":
                return True
            
            if self._state == "open":
                # Check if recovery timeout has passed
                if self._last_failure_time:
                    elapsed = time.monotonic() - self._last_failure_time
                    if elapsed >= self.recovery_timeout:
                        self._state = "half_open"
                        self._half_open_calls = 0
                        logger.info("Circuit breaker entering half-open state")
                        return True
                return False
            
            # Half-open state
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False
    
    async def record_success(self):
        """Record a successful call."""
        async with self._lock:
            if self._state == "half_open":
                self._state = "closed"
                logger.info("Circuit breaker closed after successful recovery")
            self._failure_count = 0
    
    async def record_failure(self):
        """Record a failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            
            if self._state == "half_open":
                self._state = "open"
                logger.warning("Circuit breaker reopened after failure in half-open state")
            elif self._failure_count >= self.failure_threshold:
                self._state = "open"
                logger.warning(f"Circuit breaker opened after {self._failure_count} failures")
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking calls)."""
        return self._state == "open"
    
    def reset(self):
        """Reset circuit breaker to closed state."""
        self._state = "closed"
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0


class HyperliquidError(Exception):
    """Base exception for Hyperliquid client errors."""
    pass


class ConnectionError(HyperliquidError):
    """Raised when connection to Hyperliquid fails."""
    pass


class OrderError(HyperliquidError):
    """Raised when order operations fail."""
    pass


class HyperliquidClient:
    """
    Hyperliquid MCP client for trading operations.
    
    Supports both paper trading (simulated) and live trading modes.
    Handles connection management, order placement, position tracking, and market data.
    """
    
    def __init__(self, config: HyperliquidConfig, mode: TradingMode = TradingMode.PAPER):
        self.config = config
        self.mode = mode
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[websockets.WebSocketServerProtocol] = None
        self._connected = False
        self._orders: Dict[str, Order] = {}
        self._positions: Dict[str, Position] = {}
        self._balances: Dict[str, Balance] = {}
        self._market_data: Dict[str, MarketData] = {}
        self._order_callbacks: List[Callable[[Order], None]] = []
        self._position_callbacks: List[Callable[[Position], None]] = []
        
        # Rate limiter - enforce API rate limits
        self._rate_limiter = RateLimiter(
            requests_per_second=10.0,  # Hyperliquid typical limit
            burst_size=20,
            retry_after_rate_limit=60.0
        )
        
        # Circuit breaker for connection management
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            half_open_max_calls=3
        )
        
        # WebSocket reconnection state
        self._ws_reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._ws_listen_task: Optional[asyncio.Task] = None
        
        # Paper trading simulation
        self._paper_balance = 100000.0  # $100k starting balance
        self._paper_positions: Dict[str, Position] = {}
        self._paper_orders: Dict[str, Order] = {}
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Establish connection to Hyperliquid."""
        try:
            logger.info(f"Connecting to Hyperliquid in {self.mode} mode...")
            
            # Create HTTP session
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.connection_timeout)
            )
            
            if self.mode == TradingMode.LIVE:
                # Establish WebSocket connection for live trading
                await self._connect_websocket()
                await self._authenticate()
            else:
                logger.info("Paper trading mode - no real connection established")
            
            self._connected = True
            logger.info("Successfully connected to Hyperliquid")
            
        except Exception as e:
            logger.error(f"Failed to connect to Hyperliquid: {e}")
            await self.disconnect()
            raise ConnectionError(f"Connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Close connection to Hyperliquid."""
        logger.info("Disconnecting from Hyperliquid...")
        self._connected = False
        
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        if self._session:
            await self._session.close()
            self._session = None
            
        logger.info("Disconnected from Hyperliquid")
    
    async def _connect_websocket(self) -> None:
        """Connect to Hyperliquid WebSocket for real-time data."""
        try:
            self._ws = await websockets.connect(
                self.config.websocket_url,
                ping_interval=self.config.heartbeat_interval,
                ping_timeout=10
            )
            # Start listening for messages
            asyncio.create_task(self._listen_websocket())
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise ConnectionError(f"WebSocket connection failed: {e}")
    
    async def _authenticate(self) -> None:
        """Authenticate with Hyperliquid API."""
        if not self.config.private_key or not self.config.wallet_address:
            raise ConnectionError("Private key and wallet address required for live trading")
        
        # Implementation would include proper authentication
        # This is a placeholder for the actual authentication logic
        auth_message = {
            "method": "authenticate",
            "params": {
                "wallet": self.config.wallet_address,
                "timestamp": int(time.time() * 1000)
            }
        }
        
        if self._ws:
            await self._ws.send(json.dumps(auth_message))
    
    async def _listen_websocket(self) -> None:
        """Listen for WebSocket messages with automatic reconnection and circuit breaker."""
        while self._connected:
            try:
                # Check circuit breaker before attempting connection
                if not await self._circuit_breaker.can_proceed():
                    logger.warning("Circuit breaker is open, waiting before reconnect attempt")
                    await asyncio.sleep(self._circuit_breaker.recovery_timeout)
                    continue
                
                if not self._ws:
                    # Attempt reconnection with exponential backoff
                    if self._ws_reconnect_attempts >= self._max_reconnect_attempts:
                        logger.error(f"Max reconnect attempts ({self._max_reconnect_attempts}) reached")
                        await self._circuit_breaker.record_failure()
                        break
                    
                    # Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s, 64s, 128s, 256s, 512s
                    backoff = min(2 ** self._ws_reconnect_attempts, 512)
                    logger.info(f"Reconnecting WebSocket in {backoff}s (attempt {self._ws_reconnect_attempts + 1})")
                    await asyncio.sleep(backoff)
                    
                    try:
                        await self._connect_websocket()
                        self._ws_reconnect_attempts = 0  # Reset on success
                        await self._circuit_breaker.record_success()
                    except Exception as e:
                        self._ws_reconnect_attempts += 1
                        await self._circuit_breaker.record_failure()
                        logger.error(f"WebSocket reconnection failed: {e}")
                        continue
                
                async for message in self._ws:
                    data = json.loads(message)
                    await self._handle_websocket_message(data)
                    # Reset reconnect attempts on successful message
                    self._ws_reconnect_attempts = 0
                    
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                self._ws = None
                await self._circuit_breaker.record_failure()
                # Continue loop to attempt reconnection
                
            except asyncio.CancelledError:
                logger.info("WebSocket listener cancelled")
                break
                
            except Exception as e:
                logger.error(f"Error in WebSocket listener: {e}")
                self._ws = None
                await self._circuit_breaker.record_failure()
                # Continue loop to attempt reconnection
    
    async def _handle_websocket_message(self, data: Dict[str, Any]) -> None:
        """Handle incoming WebSocket messages."""
        message_type = data.get("type")
        
        if message_type == "order_update":
            await self._handle_order_update(data)
        elif message_type == "position_update":
            await self._handle_position_update(data)
        elif message_type == "market_data":
            await self._handle_market_data_update(data)
        elif message_type == "balance_update":
            await self._handle_balance_update(data)
    
    async def _handle_order_update(self, data: Dict[str, Any]) -> None:
        """Handle order status updates."""
        order_id = data.get("order_id")
        if not order_id or order_id not in self._orders:
            return
        
        order = self._orders[order_id]
        order.status = OrderStatus(data.get("status", order.status))
        order.filled_size = float(data.get("filled_size", order.filled_size))
        order.avg_fill_price = data.get("avg_fill_price")
        order.updated_at = datetime.now(timezone.utc)
        
        # Notify callbacks
        for callback in self._order_callbacks:
            try:
                callback(order)
            except Exception as e:
                logger.error(f"Error in order callback: {e}")
    
    async def _handle_position_update(self, data: Dict[str, Any]) -> None:
        """Handle position updates."""
        asset = data.get("asset")
        if not asset:
            return
        
        position = Position(
            asset=asset,
            size=float(data.get("size", 0)),
            avg_price=float(data.get("avg_price", 0)),
            unrealized_pnl=float(data.get("unrealized_pnl", 0)),
            realized_pnl=float(data.get("realized_pnl", 0)),
            side=OrderSide.BUY if float(data.get("size", 0)) > 0 else OrderSide.SELL,
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.now(timezone.utc)
        )
        
        self._positions[asset] = position
        
        # Notify callbacks
        for callback in self._position_callbacks:
            try:
                callback(position)
            except Exception as e:
                logger.error(f"Error in position callback: {e}")
    
    async def _handle_market_data_update(self, data: Dict[str, Any]) -> None:
        """Handle market data updates."""
        asset = data.get("asset")
        if not asset:
            return
        
        market_data = MarketData(
            asset=asset,
            bid=float(data.get("bid", 0)),
            ask=float(data.get("ask", 0)),
            last=float(data.get("last", 0)),
            volume_24h=float(data.get("volume_24h", 0)),
            timestamp=datetime.now(timezone.utc)
        )
        
        self._market_data[asset] = market_data
    
    async def _handle_balance_update(self, data: Dict[str, Any]) -> None:
        """Handle balance updates."""
        asset = data.get("asset")
        if not asset:
            return
        
        balance = Balance(
            asset=asset,
            total=float(data.get("total", 0)),
            available=float(data.get("available", 0)),
            locked=float(data.get("locked", 0))
        )
        
        self._balances[asset] = balance
    
    async def place_order(
        self,
        asset: str,
        size: float,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Order:
        """
        Place a trading order.
        
        Args:
            asset: Trading symbol (e.g., 'ETH-USD')
            size: Order size
            side: Buy or sell
            order_type: Market, limit, stop, etc.
            price: Limit price (required for limit orders)
            stop_price: Stop price (required for stop orders)
            metadata: Additional order metadata
            
        Returns:
            Order object with order details
        """
        if not self._connected and self.mode == TradingMode.LIVE:
            raise OrderError("Not connected to Hyperliquid")
        
        # Validate order parameters
        if order_type == OrderType.LIMIT and price is None:
            raise OrderError("Price required for limit orders")
        
        if order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and stop_price is None:
            raise OrderError("Stop price required for stop orders")
        
        # Create order object
        order = Order(
            id=str(uuid.uuid4()),
            asset=asset,
            size=size,
            price=price,
            side=side,
            order_type=order_type,
            status=OrderStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {}
        )
        
        if self.mode == TradingMode.PAPER:
            # Simulate paper trading
            await self._simulate_paper_order(order)
        else:
            # Place real order
            await self._place_live_order(order)
        
        self._orders[order.id] = order
        logger.info(f"Order placed: {order.id} - {side} {size} {asset} @ {price}")
        
        return order
    
    async def _simulate_paper_order(self, order: Order) -> None:
        """Simulate order execution for paper trading."""
        # Get current market price (simulated)
        current_price = await self._get_simulated_price(order.asset)
        
        if order.order_type == OrderType.MARKET:
            # Market orders fill immediately at current price
            order.status = OrderStatus.FILLED
            order.filled_size = order.size
            order.avg_fill_price = current_price
            
            # Update paper position
            await self._update_paper_position(order)
            
        else:
            # For limit/stop orders, we'd need price monitoring
            # This is simplified for the MVP
            order.status = OrderStatus.PENDING
        
        order.updated_at = datetime.now(timezone.utc)
    
    async def _place_live_order(self, order: Order) -> None:
        """Place a live order on Hyperliquid."""
        if not self._session:
            raise OrderError("No HTTP session available")
        
        # Enforce rate limit before making API call
        await self._rate_limiter.acquire()
        
        # Check circuit breaker
        if not await self._circuit_breaker.can_proceed():
            raise OrderError("Circuit breaker is open - too many recent failures")
        
        order_data = {
            "asset": order.asset,
            "size": str(order.size),
            "side": order.side.value,
            "orderType": order.order_type.value,
            "price": str(order.price) if order.price else None,
            "clientOrderId": order.id
        }
        
        try:
            async with self._session.post(
                f"{self.config.base_url}/order",
                json=order_data,
                headers=await self._get_auth_headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    order.status = OrderStatus.PENDING
                    await self._circuit_breaker.record_success()
                    logger.info(f"Live order submitted: {result}")
                elif response.status == 429:
                    # Rate limited by server
                    self._rate_limiter.record_rate_limit()
                    await self._circuit_breaker.record_failure()
                    order.status = OrderStatus.REJECTED
                    raise OrderError("Rate limited by exchange")
                else:
                    error_msg = await response.text()
                    logger.error(f"Order placement failed: {error_msg}")
                    await self._circuit_breaker.record_failure()
                    order.status = OrderStatus.REJECTED
                    raise OrderError(f"Order placement failed: {error_msg}")
                    
        except OrderError:
            raise
        except Exception as e:
            logger.error(f"Error placing live order: {e}")
            await self._circuit_breaker.record_failure()
            order.status = OrderStatus.REJECTED
            raise OrderError(f"Error placing live order: {e}")
    
    async def _get_simulated_price(self, asset: str) -> float:
        """Get simulated market price for paper trading."""
        # This would typically fetch from a data source
        # For now, return a placeholder price
        base_prices = {
            "ETH-USD": 3500.0,
            "BTC-USD": 65000.0,
            "SOL-USD": 180.0
        }
        return base_prices.get(asset, 100.0)
    
    async def _update_paper_position(self, order: Order) -> None:
        """Update paper trading position after order fill."""
        current_pos = self._paper_positions.get(order.asset)
        
        if current_pos is None:
            # New position
            self._paper_positions[order.asset] = Position(
                asset=order.asset,
                size=order.filled_size if order.side == OrderSide.BUY else -order.filled_size,
                avg_price=order.avg_fill_price,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                side=order.side,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        else:
            # Update existing position
            if order.side == OrderSide.BUY:
                current_pos.size += order.filled_size
            else:
                current_pos.size -= order.filled_size
            
            current_pos.updated_at = datetime.now(timezone.utc)
    
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        # This would include proper signature generation
        # Placeholder implementation
        return {
            "Authorization": f"Bearer {self.config.private_key}",
            "Content-Type": "application/json"
        }
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        if order_id not in self._orders:
            raise OrderError(f"Order {order_id} not found")
        
        order = self._orders[order_id]
        
        if self.mode == TradingMode.PAPER:
            # Simulate cancellation
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                order.updated_at = datetime.now(timezone.utc)
                logger.info(f"Paper order cancelled: {order_id}")
                return True
            else:
                logger.warning(f"Cannot cancel order {order_id} in status {order.status}")
                return False
        else:
            # Enforce rate limit before making API call
            await self._rate_limiter.acquire()
            
            # Check circuit breaker
            if not await self._circuit_breaker.can_proceed():
                logger.error("Circuit breaker is open - cannot cancel order")
                return False
            
            # Cancel live order
            try:
                async with self._session.delete(
                    f"{self.config.base_url}/order/{order_id}",
                    headers=await self._get_auth_headers()
                ) as response:
                    if response.status == 200:
                        order.status = OrderStatus.CANCELLED
                        order.updated_at = datetime.now(timezone.utc)
                        await self._circuit_breaker.record_success()
                        logger.info(f"Live order cancelled: {order_id}")
                        return True
                    elif response.status == 429:
                        self._rate_limiter.record_rate_limit()
                        await self._circuit_breaker.record_failure()
                        logger.error("Rate limited while cancelling order")
                        return False
                    else:
                        await self._circuit_breaker.record_failure()
                        logger.error(f"Failed to cancel order: {await response.text()}")
                        return False
            except Exception as e:
                await self._circuit_breaker.record_failure()
                logger.error(f"Error cancelling order: {e}")
                return False
    
    async def get_positions(self) -> List[Position]:
        """Get current positions."""
        if self.mode == TradingMode.PAPER:
            return list(self._paper_positions.values())
        else:
            return list(self._positions.values())
    
    async def get_position(self, asset: str) -> Optional[Position]:
        """Get position for specific asset."""
        if self.mode == TradingMode.PAPER:
            return self._paper_positions.get(asset)
        else:
            return self._positions.get(asset)
    
    async def get_orders(self, asset: Optional[str] = None) -> List[Order]:
        """Get orders, optionally filtered by asset."""
        orders = list(self._orders.values())
        if asset:
            orders = [order for order in orders if order.asset == asset]
        return orders
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get specific order by ID."""
        return self._orders.get(order_id)
    
    async def get_balances(self) -> List[Balance]:
        """Get account balances."""
        if self.mode == TradingMode.PAPER:
            # Return simulated balance
            return [Balance(asset="USD", total=self._paper_balance, available=self._paper_balance, locked=0.0)]
        else:
            return list(self._balances.values())
    
    async def get_market_data(self, asset: str) -> Optional[MarketData]:
        """Get market data for asset."""
        return self._market_data.get(asset)
    
    def add_order_callback(self, callback: Callable[[Order], None]) -> None:
        """Add callback for order updates."""
        self._order_callbacks.append(callback)
    
    def add_position_callback(self, callback: Callable[[Position], None]) -> None:
        """Add callback for position updates."""
        self._position_callbacks.append(callback)
    
    def remove_order_callback(self, callback: Callable[[Order], None]) -> None:
        """Remove order callback."""
        if callback in self._order_callbacks:
            self._order_callbacks.remove(callback)
    
    def remove_position_callback(self, callback: Callable[[Position], None]) -> None:
        """Remove position callback."""
        if callback in self._position_callbacks:
            self._position_callbacks.remove(callback)
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected
    
    @property
    def trading_mode(self) -> TradingMode:
        """Get current trading mode."""
        return self.mode
    
    async def health_check(self) -> bool:
        """Check connection health."""
        if self.mode == TradingMode.PAPER:
            return True
        
        if not self._session:
            return False
        
        try:
            async with self._session.get(
                f"{self.config.base_url}/health",
                headers=await self._get_auth_headers()
            ) as response:
                return response.status == 200
        except Exception:
            return False