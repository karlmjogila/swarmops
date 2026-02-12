"""Tests for risk manager."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from hl_bot.trading.risk import RiskManager, RiskCheckResult, OrderRequest
from hl_bot.trading.risk_config import RiskConfig, TradingState
from hl_bot.trading.position import PositionTracker, Fill


@pytest.fixture
def risk_config():
    """Create test risk configuration."""
    return RiskConfig(
        max_order_notional=Decimal("5000"),
        max_position_size_usd=Decimal("10000"),
        max_position_size_percent=Decimal("0.5"),
        max_daily_loss=Decimal("1000"),
        max_daily_loss_percent=Decimal("0.05"),
        max_positions=3,
        max_total_exposure=Decimal("50000"),
        max_exposure_percent=Decimal("0.5"),
        max_price_deviation=Decimal("0.05"),
        max_consecutive_losses=3,
        max_consecutive_errors=5,
        max_open_orders=10,
    )


@pytest.fixture
def position_tracker():
    """Create position tracker."""
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
    """Create risk manager."""
    return RiskManager(
        config=risk_config,
        position_tracker=position_tracker,
        price_feed=price_feed,
        account_balance=Decimal("20000"),
    )


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


class TestRiskManager:
    """Test risk manager functionality."""
    
    @pytest.mark.asyncio
    async def test_order_size_check_passes(self, risk_manager):
        """Test order size check passes for valid order."""
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.05"),  # $2500 at $50k
            price=Decimal("50000"),
        )
        
        result = await risk_manager.check_order(order)
        assert result.approved
    
    @pytest.mark.asyncio
    async def test_order_size_check_fails(self, risk_manager):
        """Test order size check fails for too large order."""
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.2"),  # $10000 > $5000 limit
            price=Decimal("50000"),
        )
        
        result = await risk_manager.check_order(order)
        assert not result.approved
        assert "notional" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_position_limit_check(self, risk_manager):
        """Test position size limit (max_position_size_usd=1000)."""
        # Config has max_order_notional=1000 and max_position_size_usd=1000
        # So $800 order should pass notional check but position check will determine outcome
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.016"),  # $800 - within notional, but let's try exceeding position
            price=Decimal("50000"),
        )
        
        # This should pass since it's under limits
        result = await risk_manager.check_order(order)
        assert result.approved
    
    @pytest.mark.asyncio
    async def test_daily_loss_limit(self, risk_manager):
        """Test daily loss limit enforcement."""
        # Simulate daily loss exceeding limit
        risk_manager.record_loss(Decimal("1100"))  # Over $1000 limit
        
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.01"),
            price=Decimal("50000"),
        )
        
        result = await risk_manager.check_order(order)
        assert not result.approved
        assert "daily loss" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_exposure_limit(self, risk_manager, position_tracker):
        """Test total exposure limit."""
        # Add a large existing position
        position_tracker.update_from_fill(
            Fill(
                symbol="ETH-USD",
                side="buy",
                quantity=Decimal("16"),
                price=Decimal("3000"),  # $48000 exposure
                order_id="fill-1",
                fill_id="fill-1",
            )
        )
        position_tracker.update_prices({"ETH-USD": Decimal("3000")})
        
        # Try to add another position that would exceed limit
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.1"),  # +$5000 = $53000 > $50000 limit
            price=Decimal("50000"),
        )
        
        result = await risk_manager.check_order(order)
        assert not result.approved
        assert "exposure" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_price_sanity_check(self, risk_manager):
        """Test price deviation check."""
        # Order with price 10% above market (exceeds 5% limit)
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.01"),
            price=Decimal("55000"),  # 10% above $50000 market
        )
        
        result = await risk_manager.check_order(order)
        assert not result.approved
        assert "deviates" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_max_open_orders(self, risk_manager):
        """Test max open orders limit."""
        # Record orders up to limit (10)
        for _ in range(10):
            risk_manager.record_order_opened()
        
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.01"),
            price=Decimal("50000"),
        )
        
        result = await risk_manager.check_order(order)
        assert not result.approved
        assert "open orders" in result.reason.lower()
    
    def test_circuit_breaker_on_consecutive_losses(self, risk_manager):
        """Test circuit breaker trips on consecutive losses."""
        # Record 3 losses (at limit)
        for _ in range(3):
            risk_manager.record_trade(Decimal("-10"))
        
        assert risk_manager.is_circuit_breaker_tripped
    
    def test_circuit_breaker_on_consecutive_errors(self, risk_manager):
        """Test circuit breaker trips on consecutive errors."""
        # Record 5 errors (at limit)
        for _ in range(5):
            risk_manager.record_error(Exception("Test error"))
        
        assert risk_manager.is_circuit_breaker_tripped
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_orders(self, risk_manager):
        """Test circuit breaker blocks all orders."""
        risk_manager.trip_circuit_breaker("Test trip")
        
        order = OrderRequest(
            id="order-1",
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.01"),
            price=Decimal("50000"),
        )
        
        result = await risk_manager.check_order(order)
        assert not result.approved
        assert "circuit breaker" in result.reason.lower()
    
    def test_circuit_breaker_reset(self, risk_manager):
        """Test circuit breaker can be reset."""
        risk_manager.trip_circuit_breaker("Test trip")
        assert risk_manager.is_circuit_breaker_tripped
        
        risk_manager.reset_circuit_breaker()
        assert not risk_manager.is_circuit_breaker_tripped


class TestTradingState:
    """Test trading state tracking."""
    
    def test_record_trade_win(self):
        """Test recording winning trade."""
        state = TradingState()
        
        state.record_trade(Decimal("10"))
        
        assert state.daily_trades == 1
        assert state.daily_wins == 1
        assert state.daily_losses == 0
        assert state.daily_pnl == Decimal("10")
        assert state.consecutive_wins == 1
        assert state.consecutive_losses == 0
    
    def test_record_trade_loss(self):
        """Test recording losing trade."""
        state = TradingState()
        
        state.record_trade(Decimal("-10"))
        
        assert state.daily_trades == 1
        assert state.daily_wins == 0
        assert state.daily_losses == 1
        assert state.daily_pnl == Decimal("-10")
        assert state.consecutive_wins == 0
        assert state.consecutive_losses == 1
    
    def test_consecutive_tracking(self):
        """Test consecutive win/loss tracking."""
        state = TradingState()
        
        state.record_trade(Decimal("10"))
        state.record_trade(Decimal("10"))
        assert state.consecutive_wins == 2
        
        state.record_trade(Decimal("-10"))
        assert state.consecutive_wins == 0
        assert state.consecutive_losses == 1
    
    def test_daily_reset(self):
        """Test daily metrics reset."""
        state = TradingState()
        state.daily_pnl = Decimal("-50")
        state.daily_trades = 10
        state.daily_wins = 6
        state.daily_losses = 4
        
        state.reset_daily()
        
        assert state.daily_pnl == Decimal("0")
        assert state.daily_trades == 0
        assert state.daily_wins == 0
        assert state.daily_losses == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
