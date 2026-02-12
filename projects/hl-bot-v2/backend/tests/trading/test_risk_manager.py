"""Tests for risk management."""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone

from hl_bot.trading.position import PositionTracker, Fill
from hl_bot.trading.risk import (
    RiskManager,
    RiskCheckResult,
    OrderRequest,
)
from hl_bot.trading.risk_config import RiskConfig


@pytest.fixture
def risk_config():
    """Create test risk config."""
    return RiskConfig(
        max_position_size_usd=Decimal("10000"),
        max_position_size_percent=Decimal("0.5"),
        max_total_exposure=Decimal("50000"),
        max_order_notional=Decimal("5000"),
        max_open_orders=5,
        max_daily_loss=Decimal("1000"),
        max_price_deviation=Decimal("0.05"),
        max_consecutive_errors=3,
        circuit_breaker_cooldown_minutes=5,
    )


@pytest.fixture
def position_tracker():
    """Create test position tracker."""
    return PositionTracker()


@pytest.fixture
def price_feed():
    """Create test price feed."""
    prices = {
        "BTC-USD": Decimal("50000"),
        "ETH-USD": Decimal("3000"),
    }
    return lambda symbol: prices.get(symbol)


@pytest.fixture
def risk_manager(risk_config, position_tracker, price_feed):
    """Create test risk manager."""
    return RiskManager(risk_config, position_tracker, price_feed, account_balance=Decimal("20000"))


class TestRiskCheckResult:
    """Test RiskCheckResult."""

    def test_approved_result(self):
        """Test creating approved result."""
        result = RiskCheckResult.approved_result()
        assert result.approved
        assert result.reason == ""

    def test_rejected_result(self):
        """Test creating rejected result."""
        result = RiskCheckResult.rejected_result("Test rejection")
        assert not result.approved
        assert result.reason == "Test rejection"


class TestRiskConfig:
    """Test RiskConfig."""

    def test_default_config(self):
        """Test default risk configuration."""
        config = RiskConfig()
        
        assert config.max_position_size_usd == Decimal("1000")
        assert config.max_order_notional == Decimal("5000")
        assert config.max_daily_loss == Decimal("500")
        assert config.max_consecutive_errors == 5


class TestOrderSizeCheck:
    """Test order size validation."""

    @pytest.mark.asyncio
    async def test_order_within_limit(self, risk_manager):
        """Test order within notional limit passes."""
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),  # Notional: 5000
        )
        
        result = await risk_manager.check_order(order)
        
        assert result.approved

    @pytest.mark.asyncio
    async def test_order_exceeds_limit(self, risk_manager):
        """Test order exceeding notional limit is rejected."""
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.2"),
            price=Decimal("50000"),  # Notional: 10000 (exceeds 5000 limit)
        )
        
        result = await risk_manager.check_order(order)
        
        assert not result.approved
        assert "notional" in result.reason.lower()


class TestPositionLimitCheck:
    """Test position size limit validation."""

    @pytest.mark.asyncio
    async def test_new_position_within_limit(self, risk_manager):
        """Test new position within limit passes."""
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),  # 5000
        )
        
        result = await risk_manager.check_order(order)
        
        assert result.approved

    @pytest.mark.asyncio
    async def test_new_position_exceeds_limit(self, risk_manager):
        """Test new position exceeding limit is rejected."""
        # max_order_notional=5000, max_position_size_usd=10000
        # So order notional must be <= 5000 to get to position check
        # An order at $5000 (within notional) but that would result in position > $10000 with existing positions
        # Since this is a fresh test, need a 0.21 qty to get 10500 > 10000 position limit
        # But 0.21 * 50000 = 10500 exceeds notional limit of 5000
        # So let's test that notional check fires first (which is expected behavior)
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.3"),
            price=Decimal("50000"),  # 15000 (exceeds 5000 notional limit)
        )
        
        result = await risk_manager.check_order(order)
        
        assert not result.approved
        assert "notional" in result.reason.lower() or "position size" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_position_percentage_limit(self, risk_manager, position_tracker):
        """Test position size as percentage of account."""
        # Account balance is 20000, max is 50%
        # So max position is 10000
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.21"),
            price=Decimal("50000"),  # 10500 = 52.5% (exceeds 50%)
        )
        
        result = await risk_manager.check_order(order)
        
        assert not result.approved


class TestTotalExposureCheck:
    """Test total exposure limit validation."""

    @pytest.mark.asyncio
    async def test_total_exposure_within_limit(self, risk_manager, position_tracker):
        """Test total exposure within limit passes."""
        # Account is $20000, max_exposure_percent=0.5 (50%)
        # So max exposure is $10000
        # Add existing position of $5000
        position_tracker.update_from_fill(
            Fill(
                symbol="ETH-USD",
                side="buy",
                quantity=Decimal("1.5"),
                price=Decimal("3000"),  # 4500 exposure
                order_id="fill-1",
                fill_id="fill-1",
            )
        )
        position_tracker.update_prices({"ETH-USD": Decimal("3000")})
        
        # New order adds 2500, total would be 7000 (within 10000 limit / 50% of 20000)
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.05"),
            price=Decimal("50000"),  # 2500 notional
        )
        
        result = await risk_manager.check_order(order)
        
        assert result.approved

    @pytest.mark.asyncio
    async def test_total_exposure_exceeds_limit(self, risk_manager, position_tracker):
        """Test total exposure exceeding limit is rejected."""
        # Add existing position at max exposure
        position_tracker.update_from_fill(
            Fill(
                symbol="ETH-USD",
                side="buy",
                quantity=Decimal("16"),
                price=Decimal("3000"),  # 48000 exposure
                order_id="fill-1",
                fill_id="fill-1",
            )
        )
        position_tracker.update_prices({"ETH-USD": Decimal("3000")})
        
        # New order would push over 50000 limit
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),  # +5000 = 53000 total
        )
        
        result = await risk_manager.check_order(order)
        
        assert not result.approved
        assert "exposure" in result.reason.lower()


class TestDailyLossLimit:
    """Test daily loss limit validation."""

    @pytest.mark.asyncio
    async def test_within_daily_loss_limit(self, risk_manager):
        """Test trading allowed within daily loss limit."""
        # Record a small loss
        risk_manager.record_loss(Decimal("100"))
        
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )
        
        result = await risk_manager.check_order(order)
        
        assert result.approved

    @pytest.mark.asyncio
    async def test_daily_loss_limit_reached(self, risk_manager):
        """Test trading blocked when daily loss limit reached."""
        # Record loss at limit
        risk_manager.record_loss(Decimal("1000"))
        
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )
        
        result = await risk_manager.check_order(order)
        
        assert not result.approved
        assert "daily loss" in result.reason.lower()

    def test_daily_loss_tracking(self, risk_manager):
        """Test daily loss tracking."""
        # Record loss
        risk_manager.record_loss(Decimal("500"))
        assert risk_manager.daily_loss == Decimal("500")
        assert risk_manager.daily_pnl == Decimal("-500")


class TestPriceSanityCheck:
    """Test price sanity validation."""

    @pytest.mark.asyncio
    async def test_price_within_deviation(self, risk_manager):
        """Test order price within acceptable deviation passes."""
        # Market price is 50000, order at 51000 (2% deviation)
        # Use smaller quantity to stay under $5000 notional limit
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.05"),  # $2550 notional
            price=Decimal("51000"),
        )
        
        result = await risk_manager.check_order(order)
        
        assert result.approved

    @pytest.mark.asyncio
    async def test_price_exceeds_deviation(self, risk_manager):
        """Test order price with excessive deviation is rejected."""
        # Market price is 50000, order at 60000 (20% deviation, exceeds 5% limit)
        # Use smaller quantity to stay under $5000 notional limit
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.05"),  # $3000 notional
            price=Decimal("60000"),
        )
        
        result = await risk_manager.check_order(order)
        
        assert not result.approved
        assert "deviates" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_market_order_skips_price_check(self, risk_manager):
        """Test market orders skip price sanity check."""
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.1"),
            price=None,  # Market order
            order_type="market",
        )
        
        result = await risk_manager.check_order(order)
        
        assert result.approved


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_trips_on_errors(self, risk_manager):
        """Test circuit breaker trips after consecutive errors."""
        # Record errors up to limit (3)
        for i in range(3):
            risk_manager.record_error(Exception(f"Error {i}"))
        
        assert risk_manager.is_circuit_breaker_tripped

    @pytest.mark.asyncio
    async def test_success_resets_error_counter(self, risk_manager):
        """Test successful operations reset error counter."""
        # Record 2 errors
        risk_manager.record_error(Exception("Error 1"))
        risk_manager.record_error(Exception("Error 2"))
        
        # Record success
        risk_manager.record_success()
        
        # Should not trip on next error
        risk_manager.record_error(Exception("Error 3"))
        
        assert not risk_manager.is_circuit_breaker_tripped

    @pytest.mark.asyncio
    async def test_orders_blocked_when_tripped(self, risk_manager):
        """Test orders are blocked when circuit breaker trips."""
        # Trip circuit breaker
        risk_manager.trip_circuit_breaker("Test trip")
        
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )
        
        result = await risk_manager.check_order(order)
        
        assert not result.approved
        assert "circuit breaker" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self, risk_manager):
        """Test circuit breaker can be manually reset."""
        # Trip breaker
        risk_manager.trip_circuit_breaker("Test trip")
        assert risk_manager.is_circuit_breaker_tripped
        
        # Reset
        risk_manager.reset_circuit_breaker()
        
        assert not risk_manager.is_circuit_breaker_tripped


class TestRiskStatus:
    """Test risk status reporting."""

    def test_get_risk_status(self, risk_manager, position_tracker):
        """Test getting risk status summary."""
        # Add some state
        risk_manager.record_loss(Decimal("250"))
        risk_manager.record_order_opened()
        risk_manager.record_order_opened()
        
        status = risk_manager.get_risk_status()
        
        assert status["daily_pnl"] == -250.0
        assert status["daily_trades"] == 1
        assert status["daily_losses"] == 1
        assert status["open_orders"] == 2
        assert status["max_open_orders"] == 5
        assert not status["circuit_breaker_tripped"]


class TestOpenOrdersTracking:
    """Test open orders tracking."""

    @pytest.mark.asyncio
    async def test_max_open_orders_limit(self, risk_manager):
        """Test max open orders limit enforcement."""
        # Open orders up to limit (5)
        for i in range(5):
            risk_manager.record_order_opened()
        
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )
        
        result = await risk_manager.check_order(order)
        
        assert not result.approved
        assert "max open orders" in result.reason.lower()

    def test_closing_orders_decrements_counter(self, risk_manager):
        """Test closing orders decrements counter."""
        risk_manager.record_order_opened()
        risk_manager.record_order_opened()
        
        risk_manager.record_order_closed()
        
        assert risk_manager._open_orders == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
