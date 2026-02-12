#!/usr/bin/env python3
"""
Simple test to verify position manager implementation is working correctly.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from typing import Optional
from datetime import datetime, timezone
from src.types import (
    Position, Order, OrderSide, OrderType, OrderStatus, 
    ExitReason, TradeRecord, CandleData, MarketData, TradingMode
)
from src.trading.position_manager import PositionManager, PositionState
from src.config import HyperliquidConfig


# Mock Hyperliquid client for testing
class MockHyperliquidClient:
    def __init__(self):
        self.orders = {}
        self.positions = {}
        self.market_data = {}
        self._order_callbacks = []
        self._position_callbacks = []
        
    def add_order_callback(self, callback):
        self._order_callbacks.append(callback)
        
    def add_position_callback(self, callback):
        self._position_callbacks.append(callback)
        
    async def place_order(self, asset: str, size: float, side: OrderSide, 
                         order_type: OrderType, price: Optional[float] = None, 
                         stop_price: Optional[float] = None, metadata: dict = None) -> Order:
        order = Order(
            id=f"order_{len(self.orders)}",
            asset=asset,
            size=size,
            side=side,
            order_type=order_type,
            price=price,
            status=OrderStatus.PENDING,
            metadata=metadata or {}
        )
        self.orders[order.id] = order
        return order
        
    async def cancel_order(self, order_id: str):
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            for callback in self._order_callbacks:
                callback(self.orders[order_id])
                
    async def get_market_data(self, asset: str) -> Optional[MarketData]:
        return MarketData(
            asset=asset,
            bid=50000.0,
            ask=50001.0,
            last=50000.5,
            volume_24h=1000.0,
            timestamp=datetime.now(timezone.utc)
        )


async def test_position_manager():
    """Test position manager functionality."""
    print("🧪 Testing Position Manager Implementation...")
    
    # Create mock client
    mock_client = MockHyperliquidClient()
    
    # Create position manager
    position_manager = PositionManager(mock_client)
    
    # Test 1: Create position management state
    print("\n📍 Test 1: Creating position management...")
    
    position = Position(
        id="pos_001",
        asset="BTC-USD",
        size=0.1,
        avg_price=50000.0,
        side=OrderSide.LONG
    )
    
    trade_record = TradeRecord(
        id="trade_001",
        asset="BTC-USD",
        direction=OrderSide.LONG,
        entry_price=50000.0,
        initial_stop_loss=49000.0,
        quantity=0.1
    )
    
    mgmt_state = await position_manager.manage_position(
        position=position,
        trade_record=trade_record,
        current_price=50000.5
    )
    
    assert mgmt_state.position_id == "pos_001"
    assert mgmt_state.asset == "BTC-USD"
    assert mgmt_state.side == OrderSide.LONG
    assert mgmt_state.entry_price == 50000.0
    assert mgmt_state.current_size == 0.1
    assert mgmt_state.state == PositionState.ACTIVE
    
    print(f"✅ Position management created: {mgmt_state.asset}")
    print(f"   TP1: ${mgmt_state.tp1_price:.2f}")
    print(f"   TP2: ${mgmt_state.tp2_price:.2f}")
    print(f"   Stop Loss: ${mgmt_state.current_stop_loss:.2f}")
    
    # Test 2: Check risk calculation
    print("\n💰 Test 2: Risk calculations...")
    
    current_price = 50500.0  # +$500 profit
    unrealized_pnl = mgmt_state.calculate_unrealized_pnl(current_price)
    r_multiple = mgmt_state.calculate_r_multiple(current_price)
    
    print(f"   Current price: ${current_price:.2f}")
    print(f"   Unrealized P&L: ${unrealized_pnl:.2f}")
    print(f"   R-multiple: {r_multiple:.2f}R")
    
    assert unrealized_pnl > 0  # Should be profitable
    assert r_multiple > 0  # Should be positive R
    
    # Test 3: Check order placement
    print("\n📋 Test 3: Order management...")
    
    # Should have placed 3 initial orders (SL, TP1, TP2)
    assert len(mock_client.orders) == 3
    print(f"   Orders placed: {len(mock_client.orders)}")
    
    for order_id, order in mock_client.orders.items():
        purpose = order.metadata.get('order_purpose', 'unknown')
        print(f"   - {purpose}: {order.order_type.value} @ ${order.price or order.stop_price or 'market'}")
    
    # Test 4: Position statistics
    print("\n📊 Test 4: Position statistics...")
    
    stats = await position_manager.get_position_statistics("pos_001")
    assert stats is not None
    assert stats['asset'] == 'BTC-USD'
    assert stats['state'] == 'active'
    
    print(f"   Asset: {stats['asset']}")
    print(f"   State: {stats['state']}")
    print(f"   Entry: ${stats['entry_price']:.2f}")
    print(f"   Size: {stats['current_size']}")
    
    # Test 5: Manual position close
    print("\n🔐 Test 5: Manual position close...")
    
    success = await position_manager.close_position("pos_001", ExitReason.MANUAL)
    assert success == True
    
    # Should have placed exit order
    exit_orders = [o for o in mock_client.orders.values() if o.metadata.get('order_purpose') == 'manual_close']
    assert len(exit_orders) > 0
    
    print(f"   Position closed successfully")
    print(f"   Exit orders placed: {len(exit_orders)}")
    
    print("\n🎉 All tests passed! Position Manager is working correctly.")
    return True


async def main():
    """Run the tests."""
    try:
        await test_position_manager()
        print("\n✅ Position Manager implementation verified!")
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))