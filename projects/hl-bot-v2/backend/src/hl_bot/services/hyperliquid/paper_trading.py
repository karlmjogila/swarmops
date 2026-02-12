"""Paper trading mode - simulated order execution.

Test strategies with zero risk. Every order is fake, but behavior matches the real thing.
Use this before touching real money. Always.
"""

import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from hl_bot.types import Order, OrderRequest, OrderSide, OrderType, Position

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """Simulated order execution engine for testing."""

    def __init__(
        self,
        initial_balance: Decimal = Decimal("10000.0"),
        leverage: float = 1.0,
    ) -> None:
        """Initialize paper trading engine.

        Args:
            initial_balance: Starting account balance
            leverage: Account leverage multiplier
        """
        self._balance = initial_balance
        self._leverage = leverage
        self._orders: dict[str, Order] = {}
        self._positions: dict[str, Position] = {}
        self._order_callbacks: list[Callable[[Order], None]] = []
        self._fill_callbacks: list[Callable[[Order], None]] = []

        logger.info(
            "Paper trading engine initialized",
            extra={"balance": float(initial_balance), "leverage": leverage},
        )

    def on_order_update(self, callback: Callable[[Order], None]) -> None:
        """Register callback for order updates.

        Args:
            callback: Function to call when orders update
        """
        self._order_callbacks.append(callback)

    def on_fill(self, callback: Callable[[Order], None]) -> None:
        """Register callback for order fills.

        Args:
            callback: Function to call when orders fill
        """
        self._fill_callbacks.append(callback)

    async def place_order(
        self,
        order_request: OrderRequest,
        current_price: Decimal,
    ) -> Order:
        """Simulate placing an order.

        Args:
            order_request: Order parameters
            current_price: Current market price for simulation

        Returns:
            Simulated order
        """
        order_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Market orders fill immediately at current price
        if order_request.order_type == OrderType.MARKET:
            status = "filled"
            filled_quantity = order_request.quantity
            average_fill_price = float(current_price)
        else:
            # Limit orders are pending
            status = "open"
            filled_quantity = 0.0
            average_fill_price = None

        order = Order(
            id=order_id,
            symbol=order_request.symbol,
            side=order_request.side,
            order_type=order_request.order_type,
            quantity=order_request.quantity,
            price=order_request.price,
            stop_price=order_request.stop_price,
            status=status,
            filled_quantity=filled_quantity,
            average_fill_price=average_fill_price,
            created_at=now,
            updated_at=now,
        )

        self._orders[order_id] = order

        logger.info(
            "Paper order placed",
            extra={
                "order_id": order_id,
                "symbol": order.symbol,
                "side": order.side,
                "type": order.order_type,
                "quantity": order.quantity,
                "status": status,
            },
        )

        # Trigger callbacks
        for callback in self._order_callbacks:
            callback(order)

        # If filled immediately, update position
        if status == "filled":
            await self._update_position(order, current_price)
            for callback in self._fill_callbacks:
                callback(order)

        return order

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel a simulated order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Cancellation confirmation
        """
        if order_id not in self._orders:
            raise ValueError(f"Order {order_id} not found")

        order = self._orders[order_id]
        if order.status in ("filled", "cancelled"):
            raise ValueError(f"Cannot cancel order with status {order.status}")

        order.status = "cancelled"
        order.updated_at = datetime.now(timezone.utc)

        logger.info("Paper order cancelled", extra={"order_id": order_id})

        for callback in self._order_callbacks:
            callback(order)

        return {"order_id": order_id, "status": "cancelled"}

    async def cancel_all_orders(self, symbol: str | None = None) -> list[str]:
        """Cancel all open orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of cancelled order IDs
        """
        cancelled = []
        for order_id, order in self._orders.items():
            if order.status in ("open", "partial"):
                if symbol is None or order.symbol == symbol:
                    await self.cancel_order(order_id)
                    cancelled.append(order_id)

        logger.info(
            "Paper orders cancelled",
            extra={"count": len(cancelled), "symbol": symbol},
        )
        return cancelled

    async def update_market_price(self, symbol: str, price: Decimal) -> None:
        """Update market price and check for limit order fills.

        Args:
            symbol: Trading symbol
            price: New market price
        """
        # Check if any limit orders should fill
        for order in self._orders.values():
            if order.symbol != symbol or order.status != "open":
                continue

            should_fill = False

            # Check if limit order price is hit
            if order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and price <= Decimal(str(order.price)):
                    should_fill = True
                elif order.side == OrderSide.SELL and price >= Decimal(str(order.price)):
                    should_fill = True

            # Check if stop order is triggered
            elif order.order_type == OrderType.STOP_LOSS:
                if order.side == OrderSide.BUY and price >= Decimal(str(order.stop_price)):
                    should_fill = True
                elif order.side == OrderSide.SELL and price <= Decimal(str(order.stop_price)):
                    should_fill = True

            if should_fill:
                order.status = "filled"
                order.filled_quantity = order.quantity
                order.average_fill_price = float(price)
                order.updated_at = datetime.now(timezone.utc)

                logger.info(
                    "Paper order filled",
                    extra={
                        "order_id": order.id,
                        "symbol": symbol,
                        "price": float(price),
                    },
                )

                await self._update_position(order, price)

                for callback in self._fill_callbacks:
                    callback(order)

    async def _update_position(self, order: Order, current_price: Decimal) -> None:
        """Update position after order fill.

        Args:
            order: Filled order
            current_price: Current market price
        """
        symbol = order.symbol
        quantity = Decimal(str(order.quantity))
        entry_price = Decimal(str(order.average_fill_price))

        if symbol in self._positions:
            pos = self._positions[symbol]
            existing_qty = Decimal(str(pos.quantity))
            existing_entry = Decimal(str(pos.entry_price))

            # Calculate new position
            if order.side == OrderSide.BUY:
                new_qty = existing_qty + quantity
                new_entry = (
                    (existing_qty * existing_entry) + (quantity * entry_price)
                ) / new_qty
            else:
                new_qty = existing_qty - quantity
                if new_qty < 0:
                    # Position flipped
                    new_qty = abs(new_qty)
                    new_entry = entry_price
                    pos.side = OrderSide.SELL
                else:
                    new_entry = existing_entry

            # Close position if quantity is zero
            if new_qty == 0:
                del self._positions[symbol]
                logger.info("Position closed", extra={"symbol": symbol})
                return

            pos.quantity = float(new_qty)
            pos.entry_price = float(new_entry)

        else:
            # New position
            self._positions[symbol] = Position(
                symbol=symbol,
                side=order.side,
                quantity=float(quantity),
                entry_price=float(entry_price),
                mark_price=float(current_price),
                liquidation_price=None,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                leverage=self._leverage,
            )

        # Update unrealized P&L
        pos = self._positions[symbol]
        pnl_multiplier = 1.0 if pos.side == OrderSide.BUY else -1.0
        pos.unrealized_pnl = (
            (float(current_price) - pos.entry_price) * pos.quantity * pnl_multiplier
        )
        pos.mark_price = float(current_price)

        logger.info(
            "Position updated",
            extra={
                "symbol": symbol,
                "side": pos.side,
                "quantity": pos.quantity,
                "entry": pos.entry_price,
                "pnl": pos.unrealized_pnl,
            },
        )

    def get_order(self, order_id: str) -> Order:
        """Get order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order object

        Raises:
            ValueError: If order not found
        """
        if order_id not in self._orders:
            raise ValueError(f"Order {order_id} not found")
        return self._orders[order_id]

    def get_open_orders(self, symbol: str | None = None) -> list[Order]:
        """Get all open orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of open orders
        """
        return [
            order
            for order in self._orders.values()
            if order.status in ("open", "partial")
            and (symbol is None or order.symbol == symbol)
        ]

    def get_positions(self) -> list[Position]:
        """Get all open positions.

        Returns:
            List of positions
        """
        return list(self._positions.values())

    def get_account_balance(self) -> dict[str, Any]:
        """Get account balance.

        Returns:
            Account balance details
        """
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self._positions.values())
        equity = float(self._balance) + total_unrealized_pnl

        return {
            "balance": float(self._balance),
            "equity": equity,
            "unrealized_pnl": total_unrealized_pnl,
            "margin_used": sum(
                pos.quantity * pos.entry_price / self._leverage
                for pos in self._positions.values()
            ),
            "available_margin": equity,
            "leverage": self._leverage,
        }

    def reset(self, initial_balance: Decimal | None = None) -> None:
        """Reset paper trading state.

        Args:
            initial_balance: New starting balance, uses current if None
        """
        if initial_balance is not None:
            self._balance = initial_balance

        self._orders.clear()
        self._positions.clear()

        logger.info(
            "Paper trading engine reset",
            extra={"balance": float(self._balance)},
        )
