"""Risk management and pre-trade checks.

Every order must pass ALL risk checks before execution.
Safety first - a missed trade costs nothing, a bad trade costs everything.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Optional, Callable
import logging

from pydantic import BaseModel

from hl_bot.trading.position import Position, PositionTracker
from hl_bot.trading.risk_config import RiskConfig, TradingState


logger = logging.getLogger(__name__)


@dataclass
class RiskCheckResult:
    """Result of a risk check."""
    
    approved: bool
    reason: str = ""
    
    @classmethod
    def approved_result(cls) -> "RiskCheckResult":
        """Create an approved result."""
        return cls(approved=True)
    
    @classmethod
    def rejected_result(cls, reason: str) -> "RiskCheckResult":
        """Create a rejected result."""
        return cls(approved=False, reason=reason)


class OrderRequest(BaseModel):
    """Order request for risk checking."""
    
    id: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: Decimal
    price: Optional[Decimal] = None
    order_type: str = "limit"  # "market" or "limit"
    
    model_config = {"json_encoders": {Decimal: str}}
    
    @property
    def notional_value(self) -> Decimal:
        """Get notional value of order."""
        if self.price is None:
            return Decimal("0")
        return self.quantity * self.price


class RiskManager:
    """Pre-trade risk checks and circuit breaker.
    
    Every order passes through multiple risk checks before submission.
    Circuit breaker stops trading when consecutive errors occur.
    """
    
    def __init__(
        self,
        config: RiskConfig,
        position_tracker: PositionTracker,
        price_feed: Optional[Callable[[str], Optional[Decimal]]] = None,
        initial_balance: Optional[Decimal] = None,
        account_balance: Optional[Decimal] = None,  # Alias for compatibility
    ):
        """Initialize risk manager.
        
        Args:
            config: Risk configuration
            position_tracker: Position tracker instance
            price_feed: Callback to get current market price for a symbol
            initial_balance: Initial account balance
            account_balance: Alias for initial_balance (for compatibility)
        """
        self._config = config
        self._position_tracker = position_tracker
        self._price_feed = price_feed or (lambda symbol: None)
        
        # Trading state
        self._state = TradingState()
        balance = account_balance or initial_balance
        if balance is not None:
            self._state.account_balance = balance
            self._state.account_equity = balance
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def check_order(self, order: OrderRequest) -> RiskCheckResult:
        """Run all pre-trade risk checks on an order.
        
        Args:
            order: Order to check
            
        Returns:
            RiskCheckResult indicating approval or rejection
        """
        async with self._lock:
            # Reset daily metrics if new day
            self._reset_daily_if_needed()
            
            # Check circuit breaker first
            if self._state.circuit_breaker_tripped:
                return self._check_circuit_breaker()
            
            # Run all checks in sequence
            checks = [
                self._check_order_size(order),
                self._check_position_limit(order),
                self._check_position_count(),
                self._check_total_exposure(order),
                self._check_daily_loss_limit(),
                self._check_max_open_orders(),
                self._check_price_sanity(order),
            ]
            
            for result in checks:
                if not result.approved:
                    logger.warning(
                        f"Order rejected by risk check: order_id={order.id} symbol={order.symbol} reason={result.reason}"
                    )
                    return result
            
            return RiskCheckResult.approved_result()
    
    def _check_order_size(self, order: OrderRequest) -> RiskCheckResult:
        """Check if order size is within limits."""
        notional = order.notional_value
        
        if notional > self._config.max_order_notional:
            return RiskCheckResult.rejected_result(
                f"Order notional ${notional:.2f} exceeds limit ${self._config.max_order_notional:.2f}"
            )
        
        return RiskCheckResult.approved_result()
    
    def _check_position_limit(self, order: OrderRequest) -> RiskCheckResult:
        """Check if resulting position would exceed limits."""
        position = self._position_tracker.get_position(order.symbol)
        
        # Calculate new position size after order
        if position.side.value == "long":
            current_quantity = position.quantity
        elif position.side.value == "short":
            current_quantity = -position.quantity
        else:
            current_quantity = Decimal("0")
        
        order_quantity = order.quantity if order.side == "buy" else -order.quantity
        new_quantity = abs(current_quantity + order_quantity)
        
        # Check absolute position size (using USD limits)
        new_notional = new_quantity * (order.price or position.current_price or Decimal("0"))
        if new_notional > self._config.max_position_size_usd:
            return RiskCheckResult.rejected_result(
                f"Position size ${new_notional:.2f} would exceed limit ${self._config.max_position_size_usd:.2f}"
            )
        
        # Check position size as % of account
        if self._state.account_balance > 0:
            position_pct = new_notional / self._state.account_balance
            if position_pct > self._config.max_position_size_percent:
                return RiskCheckResult.rejected_result(
                    f"Position size {position_pct:.1%} would exceed limit {self._config.max_position_size_percent:.1%}"
                )
        
        return RiskCheckResult.approved_result()
    
    def _check_position_count(self) -> RiskCheckResult:
        """Check if max number of positions reached."""
        if self._state.open_positions >= self._config.max_positions:
            return RiskCheckResult.rejected_result(
                f"Max positions limit reached: {self._state.open_positions}"
            )
        return RiskCheckResult.approved_result()
    
    def _check_total_exposure(self, order: OrderRequest) -> RiskCheckResult:
        """Check if total exposure would exceed limit."""
        current_exposure = self._position_tracker.get_total_exposure()
        order_exposure = order.notional_value
        total_exposure = current_exposure + order_exposure
        
        # Check absolute exposure
        if total_exposure > self._config.max_total_exposure:
            return RiskCheckResult.rejected_result(
                f"Total exposure ${total_exposure:.2f} would exceed limit ${self._config.max_total_exposure:.2f}"
            )
        
        # Check exposure as % of account
        if self._state.account_balance > 0:
            exposure_pct = total_exposure / self._state.account_balance
            if exposure_pct > self._config.max_exposure_percent:
                return RiskCheckResult.rejected_result(
                    f"Total exposure {exposure_pct:.1%} would exceed limit {self._config.max_exposure_percent:.1%}"
                )
        
        return RiskCheckResult.approved_result()
    
    def _check_daily_loss_limit(self) -> RiskCheckResult:
        """Check if daily loss limit has been reached."""
        if self._state.daily_pnl < 0:
            daily_loss = abs(self._state.daily_pnl)
            
            # Check absolute loss
            if daily_loss >= self._config.max_daily_loss:
                return RiskCheckResult.rejected_result(
                    f"Daily loss limit reached: ${daily_loss:.2f}"
                )
            
            # Check loss as % of account
            if self._state.account_balance > 0:
                loss_pct = daily_loss / self._state.account_balance
                if loss_pct >= self._config.max_daily_loss_percent:
                    return RiskCheckResult.rejected_result(
                        f"Daily loss {loss_pct:.1%} exceeds limit {self._config.max_daily_loss_percent:.1%}"
                    )
        
        return RiskCheckResult.approved_result()
    
    def _check_max_open_orders(self) -> RiskCheckResult:
        """Check if max open orders limit reached."""
        if self._state.open_orders >= self._config.max_open_orders:
            return RiskCheckResult.rejected_result(
                f"Max open orders limit reached: {self._state.open_orders}"
            )
        
        return RiskCheckResult.approved_result()
    
    def _check_price_sanity(self, order: OrderRequest) -> RiskCheckResult:
        """Check if order price is reasonable compared to market.
        
        Prevents fat-finger errors and obvious bugs.
        """
        if order.price is None or order.order_type == "market":
            return RiskCheckResult.approved_result()
        
        market_price = self._price_feed(order.symbol)
        if market_price is None:
            return RiskCheckResult.rejected_result(
                "No market price available - cannot validate order price"
            )
        
        deviation = abs(order.price - market_price) / market_price
        if deviation > self._config.max_price_deviation:
            return RiskCheckResult.rejected_result(
                f"Price ${order.price:.2f} deviates {deviation:.1%} from market ${market_price:.2f}"
            )
        
        return RiskCheckResult.approved_result()
    
    def _check_circuit_breaker(self) -> RiskCheckResult:
        """Check if circuit breaker has cooled down."""
        if not self._state.circuit_breaker_tripped:
            return RiskCheckResult.approved_result()
        
        # Check if cooldown period has passed
        if self._state.can_reset_circuit_breaker(self._config.circuit_breaker_cooldown_minutes):
            logger.info("Circuit breaker cooldown complete - resetting")
            self._state.reset_circuit_breaker()
            return RiskCheckResult.approved_result()
        
        return RiskCheckResult.rejected_result(
            f"Circuit breaker tripped: {self._state.circuit_breaker_reason}"
        )
    
    def record_trade(self, pnl: Decimal) -> None:
        """Record a trade result.
        
        Args:
            pnl: Trade P&L (positive for win, negative for loss)
        """
        self._reset_daily_if_needed()
        self._state.record_trade(pnl)
        
        logger.info(
            f"Trade recorded: P&L ${float(pnl):.2f} - Daily P&L: ${float(self._state.daily_pnl):.2f} - Trades: {self._state.daily_trades}"
        )
        
        # Check consecutive losses for circuit breaker
        if self._state.consecutive_losses >= self._config.max_consecutive_losses:
            self.trip_circuit_breaker(
                f"Consecutive losses: {self._state.consecutive_losses}"
            )
    
    def record_loss(self, loss: Decimal) -> None:
        """Record a loss (convenience wrapper for record_trade with negative P&L).
        
        Args:
            loss: Loss amount (positive number)
        """
        self.record_trade(-loss)
    
    def record_order_opened(self) -> None:
        """Record that an order was opened."""
        self._state.open_orders += 1
    
    def record_order_closed(self) -> None:
        """Record that an order was closed/filled/cancelled."""
        self._state.open_orders = max(0, self._state.open_orders - 1)
    
    def record_position_opened(self) -> None:
        """Record that a position was opened."""
        self._state.open_positions += 1
    
    def record_position_closed(self) -> None:
        """Record that a position was closed."""
        self._state.open_positions = max(0, self._state.open_positions - 1)
    
    def record_error(self, error: Exception) -> None:
        """Record an error for circuit breaker tracking.
        
        Args:
            error: Exception that occurred
        """
        self._state.record_error()
        
        logger.warning(
            f"Error recorded: error={str(error)} consecutive_errors={self._state.consecutive_errors}"
        )
        
        if self._state.consecutive_errors >= self._config.max_consecutive_errors:
            self.trip_circuit_breaker(
                f"Consecutive errors: {self._state.consecutive_errors}"
            )
    
    def record_success(self) -> None:
        """Record a successful operation (resets error counter)."""
        self._state.record_success()
    
    def trip_circuit_breaker(self, reason: str) -> None:
        """Trip the circuit breaker to stop trading.
        
        Args:
            reason: Reason for tripping
        """
        self._state.trip_circuit_breaker(reason)
        
        logger.critical(
            f"🚨 CIRCUIT BREAKER TRIPPED 🚨 - reason={reason} time={datetime.now(timezone.utc).isoformat()}"
        )
    
    def reset_circuit_breaker(self) -> None:
        """Manually reset the circuit breaker."""
        self._state.reset_circuit_breaker()
        logger.info("Circuit breaker reset")
    
    def _reset_daily_if_needed(self) -> None:
        """Reset daily metrics if it's a new trading day."""
        # Simple date-based reset (can be enhanced with trading hours)
        today = datetime.now(timezone.utc).date()
        
        # Check if we've crossed into a new day since last trade
        if self._state.daily_trades > 0:
            # For now, assume we reset at UTC midnight
            # This is a simplified version - production should consider market hours
            pass  # TradingState.reset_daily() should be called externally at day start
    
    def update_account_state(self, balance: Decimal, equity: Decimal) -> None:
        """Update account state.
        
        Args:
            balance: Current account balance
            equity: Current account equity (balance + unrealized P&L)
        """
        self._state.account_balance = balance
        self._state.account_equity = equity
        
        # Update total exposure
        self._state.total_exposure_usd = self._position_tracker.get_total_exposure()
    
    @property
    def is_circuit_breaker_tripped(self) -> bool:
        """Check if circuit breaker is currently tripped."""
        return self._state.circuit_breaker_tripped
    
    @property
    def daily_pnl(self) -> Decimal:
        """Get current daily P&L."""
        return self._state.daily_pnl
    
    @property
    def daily_loss(self) -> Decimal:
        """Get current daily loss (absolute value if negative P&L)."""
        return abs(self._state.daily_pnl) if self._state.daily_pnl < 0 else Decimal("0")
    
    @property
    def daily_loss_remaining(self) -> Decimal:
        """Get remaining daily loss allowance."""
        return max(Decimal("0"), self._config.max_daily_loss - self.daily_loss)
    
    @property
    def state(self) -> TradingState:
        """Get current trading state."""
        return self._state
    
    @property
    def _open_orders(self) -> int:
        """Get open orders count (compatibility property for tests)."""
        return self._state.open_orders
    
    def get_risk_status(self) -> Dict:
        """Get current risk status summary.
        
        Returns:
            Dictionary with risk metrics
        """
        daily_loss_value = float(self.daily_loss)
        daily_loss_limit = float(self._config.max_daily_loss)
        
        return {
            "circuit_breaker_tripped": self._state.circuit_breaker_tripped,
            "circuit_breaker_reason": self._state.circuit_breaker_reason,
            "daily_pnl": float(self._state.daily_pnl),
            "daily_loss": daily_loss_value,
            "daily_loss_limit": daily_loss_limit,
            "daily_loss_remaining": max(0.0, daily_loss_limit - daily_loss_value),
            "daily_trades": self._state.daily_trades,
            "daily_wins": self._state.daily_wins,
            "daily_losses": self._state.daily_losses,
            "consecutive_wins": self._state.consecutive_wins,
            "consecutive_losses": self._state.consecutive_losses,
            "consecutive_errors": self._state.consecutive_errors,
            "open_positions": self._state.open_positions,
            "max_positions": self._config.max_positions,
            "open_orders": self._state.open_orders,
            "max_open_orders": self._config.max_open_orders,
            "total_exposure": float(self._state.total_exposure_usd),
            "max_total_exposure": float(self._config.max_total_exposure),
            "account_balance": float(self._state.account_balance),
            "account_equity": float(self._state.account_equity),
        }
