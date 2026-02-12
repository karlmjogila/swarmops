"""Live position monitor with real-time P&L tracking.

Monitors positions from Hyperliquid, tracks P&L in real-time, and streams updates
to connected clients. Handles market data updates, position changes, and fill events.

Following Trading Systems Excellence:
- Track positions from fills, not from polling
- Update prices from market data for accurate unrealized P&L
- Audit all position changes
- Handle WebSocket disconnections gracefully
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from hl_bot.trading.audit_logger import AuditLogger
from hl_bot.trading.hyperliquid import HyperliquidClient
from hl_bot.trading.position import Fill, Position, PositionTracker
from hl_bot.types import OrderSide
from hl_bot.utils.logging import get_logger

logger = get_logger(__name__)


class PositionUpdate:
    """Position update event."""

    def __init__(
        self,
        symbol: str,
        position: Position,
        event_type: str,  # "fill", "price_update", "position_change"
        fill: Fill | None = None,
    ):
        """Initialize position update.

        Args:
            symbol: Trading symbol
            position: Current position state
            event_type: Type of update event
            fill: Fill that triggered update (if applicable)
        """
        self.symbol = symbol
        self.position = position
        self.event_type = event_type
        self.fill = fill
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": "position_update",
            "event_type": self.event_type,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "position": {
                "symbol": self.position.symbol,
                "side": self.position.side.value,
                "quantity": str(self.position.quantity),
                "entry_price": str(self.position.entry_price),
                "current_price": str(self.position.current_price),
                "unrealized_pnl": str(self.position.unrealized_pnl),
                "realized_pnl": str(self.position.realized_pnl),
                "notional_value": str(self.position.notional_value),
                "total_pnl": str(self.position.total_pnl),
                "leverage": str(self.position.leverage),
                "last_updated": self.position.last_updated.isoformat(),
                "is_flat": self.position.is_flat,
            },
            "fill": (
                {
                    "symbol": self.fill.symbol,
                    "side": self.fill.side,
                    "quantity": str(self.fill.quantity),
                    "price": str(self.fill.price),
                    "timestamp": self.fill.timestamp.isoformat(),
                    "order_id": self.fill.order_id,
                    "fill_id": self.fill.fill_id,
                    "fee": str(self.fill.fee),
                }
                if self.fill
                else None
            ),
        }


class PositionMonitor:
    """Live position monitor with real-time tracking and streaming.

    Monitors positions from Hyperliquid exchange, tracks P&L in real-time,
    and streams updates to connected WebSocket clients.

    Key Features:
    - Real-time position tracking from fills
    - Live P&L updates from market data
    - WebSocket streaming to multiple clients
    - Comprehensive audit logging
    - Automatic reconnection handling
    """

    def __init__(
        self,
        hyperliquid_client: HyperliquidClient,
        position_tracker: PositionTracker,
        audit_logger: AuditLogger | None = None,
        update_interval: float = 1.0,
    ):
        """Initialize position monitor.

        Args:
            hyperliquid_client: Hyperliquid exchange client
            position_tracker: Position tracker instance
            audit_logger: Optional audit logger
            update_interval: Price update polling interval in seconds
        """
        self._client = hyperliquid_client
        self._tracker = position_tracker
        self._audit = audit_logger
        self._update_interval = update_interval

        # Callback registry for position updates
        self._callbacks: list[Callable[[PositionUpdate], None]] = []

        # Running state
        self._running = False
        self._tasks: list[asyncio.Task] = []

        # Latest market prices for P&L calculation
        self._market_prices: dict[str, Decimal] = {}

        # Symbols to monitor (auto-discovered from positions)
        self._monitored_symbols: set[str] = set()

        logger.info("PositionMonitor initialized")

    def on_position_update(self, callback: Callable[[PositionUpdate], None]) -> None:
        """Register callback for position updates.

        Args:
            callback: Function to call with position updates
        """
        self._callbacks.append(callback)
        logger.debug(f"Registered position update callback: {callback.__name__}")

    async def start(self) -> None:
        """Start the position monitor.

        Starts monitoring positions, fills, and market data.
        """
        if self._running:
            logger.warning("Position monitor already running")
            return

        self._running = True

        # Load initial positions from exchange
        await self._sync_positions()

        # Start monitoring tasks
        self._tasks = [
            asyncio.create_task(self._monitor_fills()),
            asyncio.create_task(self._monitor_market_data()),
            asyncio.create_task(self._periodic_position_sync()),
        ]

        logger.info("Position monitor started")

    async def stop(self) -> None:
        """Stop the position monitor gracefully."""
        logger.info("Stopping position monitor...")
        self._running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()
        logger.info("Position monitor stopped")

    async def _sync_positions(self) -> None:
        """Sync positions from exchange.

        Loads current positions from Hyperliquid and updates the tracker.
        This is used for initial sync and periodic reconciliation.
        """
        try:
            logger.info("Syncing positions from exchange...")
            positions = await self._client.get_positions()

            for pos in positions:
                # Update monitored symbols
                self._monitored_symbols.add(pos.symbol)

                # Get or create position in tracker
                tracked_pos = self._tracker.get_position(pos.symbol)

                # Update position state from exchange data
                tracked_pos.side = (
                    "long" if pos.side == OrderSide.BUY else "short"
                )
                tracked_pos.quantity = Decimal(str(pos.quantity))
                tracked_pos.entry_price = Decimal(str(pos.entry_price))
                tracked_pos.current_price = Decimal(str(pos.mark_price))
                tracked_pos.leverage = Decimal(str(pos.leverage))
                tracked_pos.realized_pnl = Decimal(str(pos.realized_pnl))
                tracked_pos.update_price(Decimal(str(pos.mark_price)))

                # Store current market price
                self._market_prices[pos.symbol] = Decimal(str(pos.mark_price))

                logger.info(
                    f"Synced position: {pos.symbol} {tracked_pos.side} "
                    f"{tracked_pos.quantity} @ {tracked_pos.entry_price}"
                )

                # Emit position update
                await self._emit_position_update(
                    PositionUpdate(
                        symbol=pos.symbol,
                        position=tracked_pos,
                        event_type="position_change",
                    )
                )

            logger.info(f"Position sync complete: {len(positions)} positions")

        except Exception as e:
            logger.error(f"Failed to sync positions: {e}", exc_info=True)

    async def _monitor_fills(self) -> None:
        """Monitor order fills via WebSocket.

        Listens for fill events and updates positions accordingly.
        """
        logger.info("Starting fill monitor...")

        while self._running:
            try:
                # Subscribe to user fills via Hyperliquid WebSocket
                async def handle_fill(message: dict[str, Any]) -> None:
                    """Handle fill message from WebSocket."""
                    if message.get("channel") != "fills":
                        return

                    fill_data = message.get("data", {})
                    
                    # Parse fill data
                    fill = Fill(
                        symbol=fill_data["coin"],
                        side="buy" if fill_data["side"] == "A" else "sell",
                        quantity=Decimal(str(fill_data["sz"])),
                        price=Decimal(str(fill_data["px"])),
                        timestamp=datetime.fromtimestamp(
                            fill_data["time"] / 1000, tz=timezone.utc
                        ),
                        order_id=fill_data.get("oid", ""),
                        fill_id=fill_data.get("tid", ""),
                        fee=Decimal(str(fill_data.get("fee", "0"))),
                    )

                    logger.info(
                        f"Fill received: {fill.symbol} {fill.side} "
                        f"{fill.quantity} @ {fill.price}"
                    )

                    # Update position from fill
                    position = self._tracker.update_from_fill(fill)

                    # Add to monitored symbols
                    self._monitored_symbols.add(fill.symbol)

                    # Log to audit trail
                    if self._audit:
                        await self._audit.log_event(
                            "fill",
                            {
                                "symbol": fill.symbol,
                                "side": fill.side,
                                "quantity": str(fill.quantity),
                                "price": str(fill.price),
                                "fee": str(fill.fee),
                            },
                        )

                    # Emit position update
                    await self._emit_position_update(
                        PositionUpdate(
                            symbol=fill.symbol,
                            position=position,
                            event_type="fill",
                            fill=fill,
                        )
                    )

                # Use Hyperliquid client's WebSocket connection
                await self._client.subscribe_user_events(handle_fill)

            except Exception as e:
                logger.error(f"Error in fill monitor: {e}", exc_info=True)
                if self._running:
                    await asyncio.sleep(5)  # Retry delay

    async def _monitor_market_data(self) -> None:
        """Monitor market data for price updates.

        Updates unrealized P&L based on current market prices.
        """
        logger.info("Starting market data monitor...")

        while self._running:
            try:
                # Poll market prices for monitored symbols
                for symbol in list(self._monitored_symbols):
                    try:
                        # Get current market price
                        price = await self._client.get_market_price(symbol)
                        self._market_prices[symbol] = price

                        # Update position price
                        if symbol in self._tracker._positions:
                            position = self._tracker.get_position(symbol)
                            old_pnl = position.unrealized_pnl
                            position.update_price(price)

                            # Only emit update if P&L changed significantly
                            pnl_change = abs(position.unrealized_pnl - old_pnl)
                            if pnl_change > Decimal("0.01"):  # $0.01 threshold
                                await self._emit_position_update(
                                    PositionUpdate(
                                        symbol=symbol,
                                        position=position,
                                        event_type="price_update",
                                    )
                                )

                    except Exception as e:
                        logger.warning(
                            f"Failed to update price for {symbol}: {e}"
                        )

                # Wait before next update
                await asyncio.sleep(self._update_interval)

            except Exception as e:
                logger.error(f"Error in market data monitor: {e}", exc_info=True)
                if self._running:
                    await asyncio.sleep(5)

    async def _periodic_position_sync(self) -> None:
        """Periodically sync positions from exchange.

        Reconciles local position state with exchange state every 60 seconds.
        This catches any missed events or discrepancies.
        """
        while self._running:
            try:
                await asyncio.sleep(60)  # Sync every minute
                await self._sync_positions()
            except Exception as e:
                logger.error(f"Error in periodic sync: {e}", exc_info=True)

    async def _emit_position_update(self, update: PositionUpdate) -> None:
        """Emit position update to all registered callbacks.

        Args:
            update: Position update event
        """
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(update)
                else:
                    callback(update)
            except Exception as e:
                logger.error(
                    f"Error in position update callback: {e}", exc_info=True
                )

    def get_position_summary(self) -> dict[str, Any]:
        """Get current position summary.

        Returns:
            Dictionary with position metrics and summary
        """
        positions = self._tracker.get_all_positions()

        # Filter out flat positions
        active_positions = {
            symbol: pos for symbol, pos in positions.items() if not pos.is_flat
        }

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_positions": len(active_positions),
            "total_exposure": str(self._tracker.get_total_exposure()),
            "total_pnl": str(self._tracker.get_total_pnl()),
            "realized_pnl": str(self._tracker.get_realized_pnl()),
            "unrealized_pnl": str(self._tracker.get_unrealized_pnl()),
            "positions": {
                symbol: {
                    "symbol": pos.symbol,
                    "side": pos.side.value,
                    "quantity": str(pos.quantity),
                    "entry_price": str(pos.entry_price),
                    "current_price": str(pos.current_price),
                    "unrealized_pnl": str(pos.unrealized_pnl),
                    "realized_pnl": str(pos.realized_pnl),
                    "notional_value": str(pos.notional_value),
                    "total_pnl": str(pos.total_pnl),
                    "leverage": str(pos.leverage),
                    "last_updated": pos.last_updated.isoformat(),
                }
                for symbol, pos in active_positions.items()
            },
        }

    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running
