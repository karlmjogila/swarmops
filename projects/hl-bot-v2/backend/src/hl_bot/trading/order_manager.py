"""Order management - lifecycle tracking and execution.

Manages order lifecycle from creation to final state.
Integrates risk checks, position tracking, and audit logging.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

from hl_bot.trading.audit_logger import AuditLogger
from hl_bot.trading.position_tracker import Fill, PositionTracker
from hl_bot.trading.risk_manager import RiskManager
from hl_bot.types import Order, OrderRequest, OrderSide, OrderType

logger = structlog.get_logger()


class OrderStatus(StrEnum):
    """Order lifecycle states."""

    PENDING = "pending"  # Created locally, not yet sent
    RISK_REJECTED = "risk_rejected"  # Rejected by risk checks
    SUBMITTED = "submitted"  # Sent to exchange
    OPEN = "open"  # Confirmed on exchange order book
    PARTIALLY_FILLED = "partial"  # Some quantity filled
    FILLED = "filled"  # Fully filled
    CANCELLED = "cancelled"  # Cancelled (by us or exchange)
    REJECTED = "rejected"  # Rejected by exchange
    EXPIRED = "expired"  # Time-in-force expired
    FAILED = "failed"  # Failed to submit


class ManagedOrder(BaseModel):
    """Internal order state with full lifecycle tracking."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    exchange_id: str | None = None
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    filled_quantity: Decimal = Decimal("0")
    price: Decimal | None = None
    avg_fill_price: Decimal | None = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    risk_check_reason: str | None = None

    @property
    def remaining_quantity(self) -> Decimal:
        """Calculate remaining unfilled quantity."""
        return self.quantity - self.filled_quantity

    @property
    def is_active(self) -> bool:
        """Check if order is still active."""
        return self.status in (
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
        )

    @property
    def is_terminal(self) -> bool:
        """Check if order is in terminal state."""
        return self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
            OrderStatus.FAILED,
            OrderStatus.RISK_REJECTED,
        )

    def to_order(self) -> Order:
        """Convert to API Order model."""
        return Order(
            id=self.exchange_id or self.id,
            symbol=self.symbol,
            side=self.side,
            order_type=self.order_type,
            quantity=float(self.quantity),
            price=float(self.price) if self.price else None,
            stop_price=None,
            status=self.status.value,
            filled_quantity=float(self.filled_quantity),
            average_fill_price=float(self.avg_fill_price) if self.avg_fill_price else None,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class OrderManager:
    """Track all orders, handle fills, manage cancellations.

    Integrates:
    - Risk management (pre-trade checks)
    - Position tracking (from fills)
    - Audit logging (all events)
    - Order lifecycle management
    """

    def __init__(
        self,
        risk_manager: RiskManager,
        position_tracker: PositionTracker,
        audit_logger: AuditLogger,
    ):
        """Initialize order manager.

        Args:
            risk_manager: Risk manager for pre-trade checks
            position_tracker: Position tracker for fill processing
            audit_logger: Audit logger for event logging
        """
        self._risk = risk_manager
        self._positions = position_tracker
        self._audit = audit_logger
        self._orders: dict[str, ManagedOrder] = {}

    async def submit_order(
        self,
        order_request: OrderRequest,
        current_price: Decimal,
        exchange_submit_fn: Any = None,
    ) -> ManagedOrder:
        """Submit order with risk checks.

        Args:
            order_request: Order request
            current_price: Current market price for risk checks
            exchange_submit_fn: Optional exchange submission function

        Returns:
            Managed order with status
        """
        # Create managed order
        order = ManagedOrder(
            symbol=order_request.symbol,
            side=order_request.side,
            order_type=order_request.order_type,
            quantity=Decimal(str(order_request.quantity)),
            price=Decimal(str(order_request.price)) if order_request.price else None,
        )

        # Risk check BEFORE sending to exchange
        risk_check = self._risk.check_order(order_request, current_price)

        if not risk_check.approved:
            order.status = OrderStatus.RISK_REJECTED
            order.risk_check_reason = risk_check.reason

            await self._audit.log_risk_rejection(
                order_data=self._order_to_dict(order),
                reason=risk_check.reason,
            )

            logger.warning(
                "Order rejected by risk",
                order_id=order.id,
                symbol=order.symbol,
                reason=risk_check.reason,
            )

            self._orders[order.id] = order
            return order

        # Submit to exchange (if function provided)
        if exchange_submit_fn:
            try:
                result = await exchange_submit_fn(order_request)
                order.exchange_id = result.get("id") or result.get("order_id")
                order.status = OrderStatus.SUBMITTED

                await self._audit.log_order_submitted(self._order_to_dict(order))

                logger.info(
                    "Order submitted to exchange",
                    order_id=order.id,
                    exchange_id=order.exchange_id,
                    symbol=order.symbol,
                    side=order.side.value,
                    quantity=str(order.quantity),
                )

                self._risk.record_success()

            except Exception as e:
                order.status = OrderStatus.FAILED
                order.error = str(e)

                await self._audit.log_error(
                    error_type="order_submission_failed",
                    error_message=str(e),
                    context={"order": self._order_to_dict(order)},
                )

                logger.error(
                    "Order submission failed",
                    order_id=order.id,
                    error=str(e),
                )

                self._risk.record_error(e)
        else:
            # Simulated submission (for testing/backtesting)
            order.status = OrderStatus.SUBMITTED
            await self._audit.log_order_submitted(self._order_to_dict(order))

        self._orders[order.id] = order
        return order

    async def update_order_status(
        self,
        order_id: str,
        status: OrderStatus,
        exchange_id: str | None = None,
    ) -> ManagedOrder | None:
        """Update order status.

        Args:
            order_id: Internal order ID
            status: New order status
            exchange_id: Optional exchange order ID

        Returns:
            Updated order or None if not found
        """
        order = self._orders.get(order_id)
        if not order:
            logger.warning("Order not found for status update", order_id=order_id)
            return None

        old_status = order.status
        order.status = status
        order.updated_at = datetime.now(timezone.utc)

        if exchange_id:
            order.exchange_id = exchange_id

        logger.info(
            "Order status updated",
            order_id=order.id,
            old_status=old_status.value,
            new_status=status.value,
        )

        return order

    async def process_fill(
        self,
        order_id: str,
        fill_quantity: Decimal,
        fill_price: Decimal,
        timestamp: datetime | None = None,
    ) -> ManagedOrder | None:
        """Process order fill and update positions.

        Args:
            order_id: Internal order ID
            fill_quantity: Quantity filled
            fill_price: Fill price
            timestamp: Optional fill timestamp

        Returns:
            Updated order or None if not found
        """
        order = self._orders.get(order_id)
        if not order:
            logger.warning("Order not found for fill", order_id=order_id)
            return None

        # Update order fill quantities
        order.filled_quantity += fill_quantity
        order.updated_at = datetime.now(timezone.utc)

        # Calculate average fill price
        if order.avg_fill_price is None:
            order.avg_fill_price = fill_price
        else:
            total_filled = order.filled_quantity
            previous_filled = total_filled - fill_quantity
            order.avg_fill_price = (
                (order.avg_fill_price * previous_filled) + (fill_price * fill_quantity)
            ) / total_filled

        # Update status
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
        elif order.filled_quantity > 0:
            order.status = OrderStatus.PARTIALLY_FILLED

        # Create fill event
        fill = Fill(
            symbol=order.symbol,
            side=order.side,
            quantity=fill_quantity,
            price=fill_price,
            timestamp=timestamp or datetime.now(timezone.utc),
            order_id=order.id,
        )

        # Update positions
        self._positions.update_from_fill(fill)

        # Log fill
        await self._audit.log_order_filled(
            order_data=self._order_to_dict(order),
            fill_data={
                "quantity": str(fill_quantity),
                "price": str(fill_price),
                "timestamp": fill.timestamp.isoformat(),
            },
        )

        logger.info(
            "Order filled",
            order_id=order.id,
            fill_quantity=str(fill_quantity),
            fill_price=str(fill_price),
            total_filled=str(order.filled_quantity),
            status=order.status.value,
        )

        return order

    async def cancel_order(
        self,
        order_id: str,
        reason: str,
        exchange_cancel_fn: Any = None,
    ) -> ManagedOrder | None:
        """Cancel an order.

        Args:
            order_id: Internal order ID
            reason: Cancellation reason
            exchange_cancel_fn: Optional exchange cancellation function

        Returns:
            Cancelled order or None if not found
        """
        order = self._orders.get(order_id)
        if not order:
            logger.warning("Order not found for cancellation", order_id=order_id)
            return None

        if not order.is_active:
            logger.warning(
                "Cannot cancel inactive order",
                order_id=order.id,
                status=order.status.value,
            )
            return order

        # Cancel on exchange if function provided
        if exchange_cancel_fn and order.exchange_id:
            try:
                await exchange_cancel_fn(order.exchange_id)
                logger.info(
                    "Order cancelled on exchange",
                    order_id=order.id,
                    exchange_id=order.exchange_id,
                )
            except Exception as e:
                logger.error(
                    "Exchange cancellation failed",
                    order_id=order.id,
                    error=str(e),
                )

        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now(timezone.utc)

        await self._audit.log_order_cancelled(order.id, reason)

        logger.info(
            "Order cancelled",
            order_id=order.id,
            reason=reason,
        )

        return order

    async def cancel_all_orders(self, reason: str) -> list[ManagedOrder]:
        """Emergency: cancel all active orders.

        Args:
            reason: Cancellation reason

        Returns:
            List of cancelled orders
        """
        logger.warning("Cancelling all orders", reason=reason)

        active_orders = [o for o in self._orders.values() if o.is_active]

        cancelled = []
        for order in active_orders:
            result = await self.cancel_order(order.id, reason)
            if result:
                cancelled.append(result)

        logger.warning(
            "All orders cancelled",
            count=len(cancelled),
            reason=reason,
        )

        return cancelled

    def get_order(self, order_id: str) -> ManagedOrder | None:
        """Get order by ID.

        Args:
            order_id: Internal order ID

        Returns:
            Order or None if not found
        """
        return self._orders.get(order_id)

    def get_active_orders(self) -> list[ManagedOrder]:
        """Get all active orders.

        Returns:
            List of active orders
        """
        return [o for o in self._orders.values() if o.is_active]

    def get_orders_by_symbol(self, symbol: str) -> list[ManagedOrder]:
        """Get all orders for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of orders
        """
        return [o for o in self._orders.values() if o.symbol == symbol]

    def get_all_orders(self) -> list[ManagedOrder]:
        """Get all orders.

        Returns:
            List of all orders
        """
        return list(self._orders.values())

    def _order_to_dict(self, order: ManagedOrder) -> dict[str, Any]:
        """Convert order to dictionary for logging.

        Args:
            order: Managed order

        Returns:
            Order dictionary
        """
        return {
            "id": order.id,
            "exchange_id": order.exchange_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "quantity": str(order.quantity),
            "filled_quantity": str(order.filled_quantity),
            "price": str(order.price) if order.price else None,
            "avg_fill_price": str(order.avg_fill_price) if order.avg_fill_price else None,
            "status": order.status.value,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "error": order.error,
            "risk_check_reason": order.risk_check_reason,
        }
