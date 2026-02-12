"""Tests for MCP server implementation.

Following Node Backend Excellence principles for async testing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime, timezone

from hl_bot.trading.mcp_server import HyperliquidMCPServer
from hl_bot.types import Order, OrderSide, OrderType, Position


@pytest.fixture
def mock_client():
    """Create a mock Hyperliquid client."""
    client = MagicMock()
    client.address = "0x1234567890abcdef"
    client._symbol_info = {}
    
    # Create proper async mocks
    client.get_market_data = AsyncMock(return_value={
        "price": "42500.50",
        "volume": "1000.5",
        "change": "+2.5%",
        "spread": "0.05",
        "openInterest": "500.0",
    })
    client.get_positions = AsyncMock(return_value=[])
    client.get_account_state = AsyncMock(return_value={
        "balance": "10000.00",
        "availableBalance": "8000.00",
        "usedMargin": "2000.00",
        "unrealizedPnl": "500.00",
        "totalPnl": "1500.00",
        "accountValue": "10500.00",
    })
    client.place_order = AsyncMock()
    client.cancel_order = AsyncMock(return_value=True)
    client.cancel_all_orders = AsyncMock(return_value=2)
    
    return client


@pytest.fixture
def mcp_server(mock_client):
    """Create MCP server with mock client."""
    test_key = "0x" + "a" * 64
    with patch("hl_bot.trading.mcp_server.HyperliquidClient", return_value=mock_client):
        server = HyperliquidMCPServer(
            private_key=test_key,
            testnet=True,
            paper_mode=True,
        )
        return server


@pytest.mark.asyncio
async def test_get_market_data(mcp_server, mock_client):
    """Test get_market_data tool."""
    # Execute tool
    result = await mcp_server._get_market_data({"symbol": "BTC"})

    # Verify - result is list[TextContent]
    assert len(result) == 1
    assert "BTC" in result[0].text
    mock_client.get_market_data.assert_called_once_with("BTC")


@pytest.mark.asyncio
async def test_get_positions_empty(mcp_server, mock_client):
    """Test getting positions when none exist."""
    mock_client.get_positions = AsyncMock(return_value=[])
    
    result = await mcp_server._get_positions()
    
    assert len(result) == 1
    assert "No open positions" in result[0].text


@pytest.mark.asyncio
async def test_get_positions_with_data(mcp_server, mock_client):
    """Test getting positions with open positions."""
    mock_client.get_positions = AsyncMock(return_value=[
        Position(
            symbol="BTC",
            side=OrderSide.BUY,
            quantity=0.5,
            entry_price=48000.0,
            mark_price=50000.0,
            liquidation_price=40000.0,
            unrealized_pnl=1000.0,
            realized_pnl=0.0,
            leverage=10.0,
        ),
    ])
    
    result = await mcp_server._get_positions()
    
    assert len(result) == 1
    assert "BTC" in result[0].text


@pytest.mark.asyncio
async def test_get_account_state(mcp_server, mock_client):
    """Test getting account state."""
    result = await mcp_server._get_account_state()
    
    assert len(result) == 1
    assert "Account State" in result[0].text
    mock_client.get_account_state.assert_called_once()


@pytest.mark.asyncio
async def test_place_order_paper_mode(mcp_server, mock_client):
    """Test placing order in paper mode."""
    mcp_server.paper_mode = True
    
    result = await mcp_server._place_order({
        "symbol": "BTC",
        "side": "buy",
        "order_type": "market",
        "quantity": 0.1,
    })
    
    assert len(result) == 1
    assert "PAPER MODE" in result[0].text
    mock_client.place_order.assert_not_called()


@pytest.mark.asyncio
async def test_place_order_live_mode(mcp_server, mock_client):
    """Test placing order in live mode."""
    mcp_server.paper_mode = False
    
    mock_client.place_order.return_value = Order(
        id="order_123",
        symbol="BTC",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1,
        price=None,
        stop_price=None,
        status="submitted",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    result = await mcp_server._place_order({
        "symbol": "BTC",
        "side": "buy",
        "order_type": "market",
        "quantity": 0.1,
    })
    
    assert len(result) == 1
    mock_client.place_order.assert_called_once()


@pytest.mark.asyncio
async def test_place_order_validation_negative_quantity(mcp_server):
    """Test order validation rejects negative quantity."""
    mcp_server.paper_mode = False
    with pytest.raises(ValueError, match="[Qq]uantity"):
        await mcp_server._place_order({
            "symbol": "BTC",
            "side": "buy",
            "order_type": "market",
            "quantity": -0.1,
        })


@pytest.mark.asyncio
async def test_place_order_validation_limit_requires_price(mcp_server):
    """Test limit order validation requires price."""
    mcp_server.paper_mode = False
    with pytest.raises(ValueError, match="[Pp]rice"):
        await mcp_server._place_order({
            "symbol": "BTC",
            "side": "buy",
            "order_type": "limit",
            "quantity": 0.1,
        })


@pytest.mark.asyncio
async def test_cancel_order_paper_mode(mcp_server, mock_client):
    """Test cancelling order in paper mode."""
    mcp_server.paper_mode = True
    
    result = await mcp_server._cancel_order({
        "order_id": "order_123",
        "symbol": "BTC",
    })
    
    assert len(result) == 1
    assert "PAPER MODE" in result[0].text
    mock_client.cancel_order.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_order_live_mode(mcp_server, mock_client):
    """Test cancelling order in live mode."""
    mcp_server.paper_mode = False
    mock_client.cancel_order.return_value = True
    
    result = await mcp_server._cancel_order({
        "order_id": "order_123",
        "symbol": "BTC",
    })
    
    assert len(result) == 1
    mock_client.cancel_order.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_all_orders_paper_mode(mcp_server, mock_client):
    """Test cancelling all orders in paper mode."""
    mcp_server.paper_mode = True
    
    result = await mcp_server._cancel_all_orders({
        "symbol": "BTC",
        "reason": "test_cancel",
    })
    
    assert len(result) == 1
    assert "PAPER MODE" in result[0].text
    mock_client.cancel_all_orders.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_all_orders_live_mode(mcp_server, mock_client):
    """Test cancelling all orders in live mode."""
    mcp_server.paper_mode = False
    mock_client.cancel_all_orders.return_value = 5
    
    result = await mcp_server._cancel_all_orders({
        "symbol": "BTC",
        "reason": "test_cancel",
    })
    
    assert len(result) == 1
    assert "5" in result[0].text  # Should mention number cancelled
    mock_client.cancel_all_orders.assert_called_once()


@pytest.mark.asyncio
async def test_server_initialization_requires_private_key():
    """Test server initialization requires private key."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="HYPERLIQUID_PRIVATE_KEY"):
            HyperliquidMCPServer()


@pytest.mark.asyncio
async def test_server_initialization_from_env():
    """Test server initialization from environment variable."""
    test_key = "0x" + "a" * 64
    with patch.dict("os.environ", {"HYPERLIQUID_PRIVATE_KEY": test_key}):
        with patch("hl_bot.trading.mcp_server.HyperliquidClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_instance.address = "0x1234567890abcdef"
            mock_client_class.return_value = mock_instance
            server = HyperliquidMCPServer()
            assert server is not None


def test_mcp_server_has_tools(mcp_server):
    """Test MCP server has expected tools registered."""
    assert mcp_server.server is not None
    assert mcp_server.server.name == "hyperliquid-trading"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
