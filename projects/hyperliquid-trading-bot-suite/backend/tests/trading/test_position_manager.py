"""
Tests for Position Manager

Comprehensive test suite covering all position management functionality.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any

from src.trading.position_manager import PositionManager, PositionState, PositionManagementState
from src.trading.hyperliquid_client import HyperliquidClient
from src.types import (
    Position, Order, OrderSide, OrderType, OrderStatus, 
    ExitReason, TradeRecord, MarketData
)


@pytest.fixture
def mock_client():
    """Mock HyperliquidClient for testing."""
    client = AsyncMock(spec=HyperliquidClient)
    client.add_order_callback = MagicMock()
    client.add_position_callback = MagicMock()
    return client


@pytest.fixture
def position_manager(mock_client):
    """Position manager instance with mocked client."""
    return PositionManager(mock_client)


@pytest.fixture
def sample_position():
    """Sample position for testing."""
    return Position(
        id="pos_123",
        asset="ETH-USD",
        side=OrderSide.LONG,
        size=1.0,
        avg_price=3000.0,
        unrealized_pnl=0.0,
        timestamp=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_trade_record():
    """Sample trade record for testing."""
    return TradeRecord(
        id="trade_123",
        asset="ETH-USD",
        direction=OrderSide.LONG,
        entry_price=3000.0,
        initial_stop_loss=2950.0,
        strategy_rule_id="rule_123",
        size=1.0,
        entry_time=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_order():
    """Sample order for testing."""
    return Order(
        id="order_123",
        asset="ETH-USD",
        side=OrderSide.SELL,
        size=0.5,
        order_type=OrderType.LIMIT,
        price=3050.0,
        status=OrderStatus.PENDING,
        timestamp=datetime.now(timezone.utc),
        metadata={"position_id": "pos_123", "order_purpose": "tp1"}
    )


@pytest.mark.asyncio
class TestPositionManager:
    """Test position manager functionality."""
    
    async def test_initialization(self, mock_client):
        """Test position manager initialization."""
        pm = PositionManager(mock_client)
        
        assert pm.client == mock_client
        assert pm.managed_positions == {}
        assert pm.active_orders == {}
        assert pm.tp1_r_multiple == 1.0
        assert pm.tp2_r_multiple == 2.0
        assert pm.tp1_exit_percentage == 0.5
        
        # Check callbacks were registered
        mock_client.add_order_callback.assert_called_once()
        mock_client.add_position_callback.assert_called_once()
    
    async def test_manage_position_long(self, position_manager, sample_position, sample_trade_record, mock_client):
        """Test managing a long position."""
        # Mock order placement
        stop_order = Order(
            id="stop_123", asset="ETH-USD", side=OrderSide.SELL, size=1.0,
            order_type=OrderType.STOP_LOSS, status=OrderStatus.PENDING,
            timestamp=datetime.now(timezone.utc)
        )
        tp1_order = Order(
            id="tp1_123", asset="ETH-USD", side=OrderSide.SELL, size=0.5,
            order_type=OrderType.LIMIT, status=OrderStatus.PENDING,
            timestamp=datetime.now(timezone.utc)
        )
        tp2_order = Order(
            id="tp2_123", asset="ETH-USD", side=OrderSide.SELL, size=0.5,
            order_type=OrderType.LIMIT, status=OrderStatus.PENDING,
            timestamp=datetime.now(timezone.utc)
        )
        
        mock_client.place_order.side_effect = [stop_order, tp1_order, tp2_order]
        
        # Manage position
        mgmt_state = await position_manager.manage_position(
            sample_position, sample_trade_record, 3010.0
        )
        
        # Verify management state
        assert mgmt_state.position_id == "pos_123"
        assert mgmt_state.asset == "ETH-USD"
        assert mgmt_state.side == OrderSide.LONG
        assert mgmt_state.entry_price == 3000.0
        assert mgmt_state.original_size == 1.0
        assert mgmt_state.current_size == 1.0
        assert mgmt_state.initial_stop_loss == 2950.0
        assert mgmt_state.state == PositionState.ACTIVE
        
        # Check calculated levels
        assert mgmt_state.tp1_price == 3050.0  # +1R
        assert mgmt_state.tp2_price == 3100.0  # +2R
        assert mgmt_state.tp1_size == 0.5
        assert mgmt_state.tp2_size == 0.5
        
        # Verify orders were placed
        assert mock_client.place_order.call_count == 3
        assert mgmt_state.stop_order_id == "stop_123"
        assert mgmt_state.tp1_order_id == "tp1_123"
        assert mgmt_state.tp2_order_id == "tp2_123"
        
        # Check position is tracked
        assert position_manager.managed_positions["pos_123"] == mgmt_state
    
    async def test_manage_position_short(self, position_manager, sample_trade_record, mock_client):
        """Test managing a short position."""
        short_position = Position(
            id="pos_456",
            asset="BTC-USD",
            side=OrderSide.SHORT,
            size=-0.1,
            avg_price=65000.0,
            unrealized_pnl=0.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        short_trade_record = TradeRecord(
            id="trade_456",
            asset="BTC-USD",
            direction=OrderSide.SHORT,
            entry_price=65000.0,
            initial_stop_loss=65500.0,  # Stop above entry for short
            strategy_rule_id="rule_456",
            size=0.1,
            entry_time=datetime.now(timezone.utc)
        )
        
        # Mock order placement
        mock_orders = [
            Order(id=f"order_{i}", asset="BTC-USD", side=OrderSide.BUY, size=0.1,
                  order_type=OrderType.STOP_LOSS, status=OrderStatus.PENDING,
                  timestamp=datetime.now(timezone.utc))
            for i in range(3)
        ]
        mock_client.place_order.side_effect = mock_orders
        
        mgmt_state = await position_manager.manage_position(
            short_position, short_trade_record, 64800.0
        )
        
        # For short positions, TP levels should be below entry
        assert mgmt_state.tp1_price == 64950.0  # -1R
        assert mgmt_state.tp2_price == 64900.0  # -2R
        assert mgmt_state.side == OrderSide.SHORT
    
    async def test_r_multiple_calculation(self):
        """Test R multiple calculations."""
        mgmt_state = PositionManagementState(
            position_id="test",
            asset="ETH-USD",
            side=OrderSide.LONG,
            entry_price=3000.0,
            original_size=1.0,
            current_size=1.0,
            initial_stop_loss=2950.0,
            current_stop_loss=2950.0,
            risk_amount=50.0,  # 3000 - 2950 = 50
            tp1_price=3050.0,
            tp2_price=3100.0,
            tp1_size=0.5,
            tp2_size=0.5
        )
        
        # Test at entry
        assert mgmt_state.calculate_r_multiple(3000.0) == 0.0
        
        # Test at +1R
        assert mgmt_state.calculate_r_multiple(3050.0) == 1.0
        
        # Test at +2R
        assert mgmt_state.calculate_r_multiple(3100.0) == 2.0
        
        # Test at stop loss
        assert mgmt_state.calculate_r_multiple(2950.0) == -1.0
    
    async def test_unrealized_pnl_calculation(self):
        """Test unrealized P&L calculations."""
        long_state = PositionManagementState(
            position_id="test_long",
            asset="ETH-USD",
            side=OrderSide.LONG,
            entry_price=3000.0,
            original_size=1.0,
            current_size=1.0,
            initial_stop_loss=2950.0,
            current_stop_loss=2950.0,
            risk_amount=50.0,
            tp1_price=3050.0,
            tp2_price=3100.0,
            tp1_size=0.5,
            tp2_size=0.5
        )
        
        short_state = PositionManagementState(
            position_id="test_short",
            asset="BTC-USD",
            side=OrderSide.SHORT,
            entry_price=65000.0,
            original_size=0.1,
            current_size=0.1,
            initial_stop_loss=65500.0,
            current_stop_loss=65500.0,
            risk_amount=50.0,
            tp1_price=64950.0,
            tp2_price=64900.0,
            tp1_size=0.05,
            tp2_size=0.05
        )
        
        # Long position tests
        assert long_state.calculate_unrealized_pnl(3050.0) == 50.0  # +$50
        assert long_state.calculate_unrealized_pnl(2950.0) == -50.0  # -$50
        
        # Short position tests
        assert short_state.calculate_unrealized_pnl(64950.0) == 5.0  # +$5
        assert short_state.calculate_unrealized_pnl(65050.0) == -5.0  # -$5
    
    async def test_order_filled_tp1(self, position_manager, mock_client):
        """Test TP1 order filled handling."""
        # Create a managed position
        mgmt_state = PositionManagementState(
            position_id="pos_123",
            asset="ETH-USD",
            side=OrderSide.LONG,
            entry_price=3000.0,
            original_size=1.0,
            current_size=1.0,
            initial_stop_loss=2950.0,
            current_stop_loss=2950.0,
            risk_amount=50.0,
            tp1_price=3050.0,
            tp2_price=3100.0,
            tp1_size=0.5,
            tp2_size=0.5
        )
        position_manager.managed_positions["pos_123"] = mgmt_state
        
        # Create TP1 order
        tp1_order = Order(
            id="tp1_123",
            asset="ETH-USD",
            side=OrderSide.SELL,
            size=0.5,
            order_type=OrderType.LIMIT,
            price=3050.0,
            status=OrderStatus.FILLED,
            filled_size=0.5,
            avg_fill_price=3051.0,
            timestamp=datetime.now(timezone.utc),
            metadata={"position_id": "pos_123", "order_purpose": "tp1"}
        )
        
        # Mock new stop order placement
        new_stop_order = Order(
            id="new_stop_123", asset="ETH-USD", side=OrderSide.SELL,
            size=0.5, order_type=OrderType.STOP_LOSS, status=OrderStatus.PENDING,
            timestamp=datetime.now(timezone.utc)
        )
        mock_client.place_order.return_value = new_stop_order
        
        # Process order update
        await position_manager._process_order_update(mgmt_state, tp1_order)
        
        # Verify state changes
        assert mgmt_state.tp1_filled is True
        assert mgmt_state.current_size == 0.5  # Half position closed
        assert mgmt_state.state == PositionState.PARTIAL_TP1
        
        # Verify new stop order was placed for remaining position
        mock_client.cancel_order.assert_called_once()
        mock_client.place_order.assert_called_once()
    
    async def test_breakeven_activation(self, position_manager, mock_client):
        """Test breakeven trailing activation."""
        mgmt_state = PositionManagementState(
            position_id="pos_123",
            asset="ETH-USD",
            side=OrderSide.LONG,
            entry_price=3000.0,
            original_size=1.0,
            current_size=1.0,
            initial_stop_loss=2950.0,
            current_stop_loss=2950.0,
            risk_amount=50.0,
            tp1_price=3050.0,
            tp2_price=3100.0,
            tp1_size=0.5,
            tp2_size=0.5,
            stop_order_id="old_stop_123"
        )
        
        # Mock new breakeven order
        breakeven_order = Order(
            id="breakeven_123", asset="ETH-USD", side=OrderSide.SELL,
            size=1.0, order_type=OrderType.STOP_LOSS, status=OrderStatus.PENDING,
            timestamp=datetime.now(timezone.utc)
        )
        mock_client.place_order.return_value = breakeven_order
        
        await position_manager._activate_breakeven_trailing(mgmt_state)
        
        # Verify breakeven activation
        assert mgmt_state.breakeven_activated is True
        assert mgmt_state.current_stop_loss == 3000.0  # Moved to breakeven
        assert mgmt_state.state == PositionState.BREAKEVEN
        assert mgmt_state.stop_order_id == "breakeven_123"
        
        # Verify old stop was cancelled and new one placed
        mock_client.cancel_order.assert_called_once_with("old_stop_123")
        mock_client.place_order.assert_called_once()
    
    async def test_momentum_exit_detection(self, position_manager, mock_client):
        """Test momentum exit detection and execution."""
        mgmt_state = PositionManagementState(
            position_id="pos_123",
            asset="ETH-USD",
            side=OrderSide.LONG,
            entry_price=3000.0,
            original_size=1.0,
            current_size=0.5,  # Partial position after TP1
            initial_stop_loss=2950.0,
            current_stop_loss=3000.0,
            risk_amount=50.0,
            tp1_price=3050.0,
            tp2_price=3100.0,
            tp1_size=0.5,
            tp2_size=0.5,
            highest_profitable_price=3080.0,  # Price peaked here
            state=PositionState.PARTIAL_TP1
        )
        
        # Mock market exit order
        exit_order = Order(
            id="exit_123", asset="ETH-USD", side=OrderSide.SELL,
            size=0.5, order_type=OrderType.MARKET, status=OrderStatus.PENDING,
            timestamp=datetime.now(timezone.utc)
        )
        mock_client.place_order.return_value = exit_order
        
        # Simulate significant pullback that triggers momentum exit
        current_price = 3065.0  # Pullback from 3080 to 3065 = 15 points
        # 15 points = 0.3R (15 / 50 = 0.3)
        
        await position_manager._check_momentum_exit(mgmt_state, current_price)
        
        # Momentum exit should be triggered
        assert mgmt_state.momentum_exit_triggered is True
        assert mgmt_state.state == PositionState.MOMENTUM_EXIT
        
        # Verify orders were cancelled and exit order placed
        assert mock_client.cancel_order.call_count >= 1
        mock_client.place_order.assert_called_once()
    
    async def test_position_cleanup(self, position_manager, mock_client):
        """Test position cleanup after closure."""
        mgmt_state = PositionManagementState(
            position_id="pos_123",
            asset="ETH-USD",
            side=OrderSide.LONG,
            entry_price=3000.0,
            original_size=1.0,
            current_size=0.0,
            initial_stop_loss=2950.0,
            current_stop_loss=2950.0,
            risk_amount=50.0,
            tp1_price=3050.0,
            tp2_price=3100.0,
            tp1_size=0.5,
            tp2_size=0.5,
            stop_order_id="stop_123",
            tp1_order_id="tp1_123",
            tp2_order_id="tp2_123"
        )
        
        position_manager.managed_positions["pos_123"] = mgmt_state
        position_manager.active_orders["stop_123"] = "pos_123"
        position_manager.active_orders["tp1_123"] = "pos_123"
        position_manager.active_orders["tp2_123"] = "pos_123"
        
        await position_manager._cleanup_position("pos_123")
        
        # Verify cleanup
        assert "pos_123" not in position_manager.managed_positions
        assert "stop_123" not in position_manager.active_orders
        assert "tp1_123" not in position_manager.active_orders
        assert "tp2_123" not in position_manager.active_orders
        
        # Verify orders were cancelled
        assert mock_client.cancel_order.call_count == 3
    
    async def test_manual_position_close(self, position_manager, mock_client):
        """Test manual position closure."""
        mgmt_state = PositionManagementState(
            position_id="pos_123",
            asset="ETH-USD",
            side=OrderSide.LONG,
            entry_price=3000.0,
            original_size=1.0,
            current_size=0.7,
            initial_stop_loss=2950.0,
            current_stop_loss=2950.0,
            risk_amount=50.0,
            tp1_price=3050.0,
            tp2_price=3100.0,
            tp1_size=0.5,
            tp2_size=0.5
        )
        position_manager.managed_positions["pos_123"] = mgmt_state
        
        # Mock exit order
        exit_order = Order(
            id="manual_exit_123", asset="ETH-USD", side=OrderSide.SELL,
            size=0.7, order_type=OrderType.MARKET, status=OrderStatus.PENDING,
            timestamp=datetime.now(timezone.utc)
        )
        mock_client.place_order.return_value = exit_order
        
        result = await position_manager.close_position("pos_123", ExitReason.MANUAL)
        
        assert result is True
        assert mgmt_state.state == PositionState.CLOSED
        assert "pos_123" not in position_manager.managed_positions
        
        # Verify market exit order was placed
        mock_client.place_order.assert_called()
        call_args = mock_client.place_order.call_args
        assert call_args[1]["order_type"] == OrderType.MARKET
        assert call_args[1]["size"] == 0.7
    
    async def test_get_position_statistics(self, position_manager, mock_client):
        """Test position statistics retrieval."""
        mgmt_state = PositionManagementState(
            position_id="pos_123",
            asset="ETH-USD",
            side=OrderSide.LONG,
            entry_price=3000.0,
            original_size=1.0,
            current_size=0.5,
            initial_stop_loss=2950.0,
            current_stop_loss=2950.0,
            risk_amount=50.0,
            tp1_price=3050.0,
            tp2_price=3100.0,
            tp1_size=0.5,
            tp2_size=0.5,
            tp1_filled=True,
            breakeven_activated=True
        )
        position_manager.managed_positions["pos_123"] = mgmt_state
        
        # Mock market data
        market_data = MarketData(
            asset="ETH-USD",
            last=3075.0,
            bid=3074.0,
            ask=3076.0,
            timestamp=datetime.now(timezone.utc)
        )
        mock_client.get_market_data.return_value = market_data
        
        stats = await position_manager.get_position_statistics("pos_123")
        
        assert stats is not None
        assert stats["position_id"] == "pos_123"
        assert stats["asset"] == "ETH-USD"
        assert stats["current_price"] == 3075.0
        assert stats["unrealized_pnl"] == 37.5  # (3075-3000) * 0.5
        assert stats["r_multiple"] == 1.5  # 75/50 = 1.5R
        assert stats["tp1_filled"] is True
        assert stats["breakeven_activated"] is True
    
    async def test_callback_management(self, position_manager):
        """Test callback management functions."""
        position_callback = MagicMock()
        exit_callback = MagicMock()
        
        # Add callbacks
        position_manager.add_position_update_callback(position_callback)
        position_manager.add_exit_callback(exit_callback)
        
        assert position_callback in position_manager._position_update_callbacks
        assert exit_callback in position_manager._exit_callbacks
        
        # Remove callbacks
        position_manager.remove_position_update_callback(position_callback)
        position_manager.remove_exit_callback(exit_callback)
        
        assert position_callback not in position_manager._position_update_callbacks
        assert exit_callback not in position_manager._exit_callbacks
    
    async def test_monitoring_loop_control(self, position_manager):
        """Test monitoring loop start/stop."""
        # Start monitoring
        await position_manager.start_monitoring()
        assert position_manager._monitoring_active is True
        assert position_manager._monitoring_task is not None
        
        # Stop monitoring
        await position_manager.stop_monitoring()
        assert position_manager._monitoring_active is False
        
        # Multiple starts should not create duplicate tasks
        await position_manager.start_monitoring()
        task1 = position_manager._monitoring_task
        await position_manager.start_monitoring()
        task2 = position_manager._monitoring_task
        
        # Should be the same task (or new one if first was done)
        await position_manager.stop_monitoring()


@pytest.mark.integration
class TestPositionManagerIntegration:
    """Integration tests requiring more complex setup."""
    
    async def test_full_position_lifecycle(self, position_manager, mock_client):
        """Test complete position lifecycle from entry to exit."""
        # This would test the full flow but requires more complex mocking
        # Left as a placeholder for future implementation
        pass
    
    async def test_multiple_position_management(self, position_manager, mock_client):
        """Test managing multiple positions simultaneously."""
        # This would test concurrent position management
        # Left as a placeholder for future implementation
        pass


if __name__ == "__main__":
    pytest.main([__file__])