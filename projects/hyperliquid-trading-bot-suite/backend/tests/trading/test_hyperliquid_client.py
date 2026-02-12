"""
Tests for the Hyperliquid MCP Client.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from backend.src.config import HyperliquidConfig
from backend.src.types import OrderSide, OrderType, OrderStatus, TradingMode
from backend.src.trading.hyperliquid_client import HyperliquidClient, OrderError, ConnectionError


class TestHyperliquidClient:
    """Test cases for HyperliquidClient."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return HyperliquidConfig(
            base_url="https://test.hyperliquid.xyz",
            websocket_url="wss://test.hyperliquid.xyz/ws",
            private_key="test_private_key",
            wallet_address="test_wallet_address",
            testnet=True
        )
    
    @pytest.fixture
    def paper_client(self, config):
        """Create paper trading client."""
        return HyperliquidClient(config, TradingMode.PAPER)
    
    @pytest.fixture
    def live_client(self, config):
        """Create live trading client."""
        return HyperliquidClient(config, TradingMode.LIVE)
    
    def test_client_initialization(self, config):
        """Test client initialization."""
        client = HyperliquidClient(config, TradingMode.PAPER)
        
        assert client.config == config
        assert client.mode == TradingMode.PAPER
        assert not client.is_connected
        assert client._orders == {}
        assert client._positions == {}
        assert client._paper_balance == 100000.0
    
    @pytest.mark.asyncio
    async def test_paper_trading_connection(self, paper_client):
        """Test paper trading connection."""
        await paper_client.connect()
        
        assert paper_client.is_connected
        assert paper_client.trading_mode == TradingMode.PAPER
        
        await paper_client.disconnect()
        assert not paper_client.is_connected
    
    @pytest.mark.asyncio
    async def test_context_manager(self, paper_client):
        """Test async context manager."""
        async with paper_client as client:
            assert client.is_connected
        
        assert not paper_client.is_connected
    
    @pytest.mark.asyncio
    async def test_paper_market_order(self, paper_client):
        """Test paper trading market order."""
        async with paper_client:
            order = await paper_client.place_order(
                asset="ETH-USD",
                size=1.0,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET
            )
            
            assert order.asset == "ETH-USD"
            assert order.size == 1.0
            assert order.side == OrderSide.BUY
            assert order.order_type == OrderType.MARKET
            assert order.status == OrderStatus.FILLED
            assert order.filled_size == 1.0
            assert order.avg_fill_price == 3500.0  # Simulated ETH price
            
            # Check that order is stored
            stored_order = await paper_client.get_order(order.id)
            assert stored_order == order
    
    @pytest.mark.asyncio
    async def test_paper_limit_order(self, paper_client):
        """Test paper trading limit order."""
        async with paper_client:
            order = await paper_client.place_order(
                asset="BTC-USD",
                size=0.1,
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                price=70000.0
            )
            
            assert order.price == 70000.0
            assert order.status == OrderStatus.PENDING  # Limit orders start pending in simulation
    
    @pytest.mark.asyncio
    async def test_position_tracking(self, paper_client):
        """Test position tracking in paper trading."""
        async with paper_client:
            # Place buy order
            await paper_client.place_order(
                asset="SOL-USD",
                size=10.0,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET
            )
            
            # Check position
            position = await paper_client.get_position("SOL-USD")
            assert position is not None
            assert position.asset == "SOL-USD"
            assert position.size == 10.0
            assert position.side == OrderSide.BUY
            
            # Place sell order
            await paper_client.place_order(
                asset="SOL-USD",
                size=5.0,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET
            )
            
            # Check updated position
            position = await paper_client.get_position("SOL-USD")
            assert position.size == 5.0  # 10 - 5
    
    @pytest.mark.asyncio
    async def test_order_cancellation(self, paper_client):
        """Test order cancellation in paper trading."""
        async with paper_client:
            order = await paper_client.place_order(
                asset="ETH-USD",
                size=1.0,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=3000.0
            )
            
            assert order.status == OrderStatus.PENDING
            
            # Cancel the order
            cancelled = await paper_client.cancel_order(order.id)
            assert cancelled
            
            # Check order status
            updated_order = await paper_client.get_order(order.id)
            assert updated_order.status == OrderStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_get_orders_filtering(self, paper_client):
        """Test getting orders with asset filtering."""
        async with paper_client:
            # Place orders for different assets
            eth_order = await paper_client.place_order("ETH-USD", 1.0, OrderSide.BUY, OrderType.MARKET)
            btc_order = await paper_client.place_order("BTC-USD", 0.1, OrderSide.BUY, OrderType.MARKET)
            
            # Get all orders
            all_orders = await paper_client.get_orders()
            assert len(all_orders) == 2
            
            # Get ETH orders only
            eth_orders = await paper_client.get_orders("ETH-USD")
            assert len(eth_orders) == 1
            assert eth_orders[0].asset == "ETH-USD"
    
    @pytest.mark.asyncio
    async def test_get_balances(self, paper_client):
        """Test getting account balances."""
        async with paper_client:
            balances = await paper_client.get_balances()
            
            assert len(balances) == 1
            assert balances[0].asset == "USD"
            assert balances[0].total == 100000.0
            assert balances[0].available == 100000.0
    
    @pytest.mark.asyncio
    async def test_order_validation(self, paper_client):
        """Test order parameter validation."""
        async with paper_client:
            # Test limit order without price
            with pytest.raises(OrderError, match="Price required for limit orders"):
                await paper_client.place_order(
                    asset="ETH-USD",
                    size=1.0,
                    side=OrderSide.BUY,
                    order_type=OrderType.LIMIT
                )
            
            # Test stop order without stop price
            with pytest.raises(OrderError, match="Stop price required for stop orders"):
                await paper_client.place_order(
                    asset="ETH-USD",
                    size=1.0,
                    side=OrderSide.BUY,
                    order_type=OrderType.STOP
                )
    
    @pytest.mark.asyncio
    async def test_callbacks(self, paper_client):
        """Test order and position callbacks."""
        order_updates = []
        position_updates = []
        
        def order_callback(order):
            order_updates.append(order)
        
        def position_callback(position):
            position_updates.append(position)
        
        paper_client.add_order_callback(order_callback)
        paper_client.add_position_callback(position_callback)
        
        async with paper_client:
            # Place order (should trigger callbacks)
            await paper_client.place_order("ETH-USD", 1.0, OrderSide.BUY, OrderType.MARKET)
            
            # In paper trading, callbacks aren't automatically triggered
            # This would be tested differently in live mode
            
        # Remove callbacks
        paper_client.remove_order_callback(order_callback)
        paper_client.remove_position_callback(position_callback)
    
    def test_health_check_paper_trading(self, paper_client):
        """Test health check in paper trading mode."""
        # Paper trading should always be healthy
        health = asyncio.run(paper_client.health_check())
        assert health is True
    
    @pytest.mark.asyncio
    async def test_disconnected_order_placement(self, paper_client):
        """Test placing order when not connected in live mode."""
        live_client = HyperliquidClient(paper_client.config, TradingMode.LIVE)
        
        # Try to place order without connecting
        with pytest.raises(OrderError, match="Not connected to Hyperliquid"):
            await live_client.place_order("ETH-USD", 1.0, OrderSide.BUY, OrderType.MARKET)
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_order(self, paper_client):
        """Test cancelling a non-existent order."""
        async with paper_client:
            with pytest.raises(OrderError, match="Order .* not found"):
                await paper_client.cancel_order("nonexistent_order_id")
    
    @pytest.mark.asyncio
    async def test_cancel_filled_order(self, paper_client):
        """Test cancelling an already filled order."""
        async with paper_client:
            order = await paper_client.place_order(
                asset="ETH-USD",
                size=1.0,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET
            )
            
            assert order.status == OrderStatus.FILLED
            
            # Try to cancel filled order
            cancelled = await paper_client.cancel_order(order.id)
            assert not cancelled  # Should not be able to cancel filled order


if __name__ == "__main__":
    pytest.main([__file__])