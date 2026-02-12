"""
Tests for the Hyperliquid MCP Server.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch

from backend.src.config import HyperliquidConfig
from backend.src.types import TradingMode, OrderSide, OrderType
from backend.src.trading.mcp_server import (
    HyperliquidMCPServer, 
    create_mcp_server,
    PlaceOrderTool,
    CancelOrderTool,
    GetPositionsTool
)


class TestMCPTools:
    """Test MCP tools individually."""
    
    @pytest.mark.asyncio
    async def test_place_order_tool(self):
        """Test place order tool execution."""
        tool = PlaceOrderTool()
        
        # Mock client
        mock_client = AsyncMock()
        mock_order = Mock()
        mock_order.id = "test_order_id"
        mock_order.asset = "ETH-USD"
        mock_order.size = 1.0
        mock_order.side = OrderSide.BUY
        mock_order.order_type = OrderType.MARKET
        mock_order.status = Mock()
        mock_order.status.value = "filled"
        mock_order.price = None
        mock_order.filled_size = 1.0
        mock_order.avg_fill_price = 3500.0
        mock_order.created_at = None
        
        mock_client.place_order.return_value = mock_order
        
        # Execute tool
        result = await tool.execute(
            mock_client,
            asset="ETH-USD",
            size=1.0,
            side="buy",
            order_type="market"
        )
        
        assert result["success"] is True
        assert result["order"]["id"] == "test_order_id"
        assert result["order"]["asset"] == "ETH-USD"
        assert result["order"]["side"] == "buy"
        
        # Verify client was called correctly
        mock_client.place_order.assert_called_once_with(
            asset="ETH-USD",
            size=1.0,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            price=None,
            stop_price=None,
            metadata={}
        )
    
    @pytest.mark.asyncio
    async def test_place_order_tool_error(self):
        """Test place order tool with error."""
        tool = PlaceOrderTool()
        
        # Mock client that raises exception
        mock_client = AsyncMock()
        mock_client.place_order.side_effect = Exception("Test error")
        
        # Execute tool
        result = await tool.execute(
            mock_client,
            asset="ETH-USD",
            size=1.0,
            side="buy"
        )
        
        assert result["success"] is False
        assert "Test error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_cancel_order_tool(self):
        """Test cancel order tool execution."""
        tool = CancelOrderTool()
        
        # Mock client
        mock_client = AsyncMock()
        mock_client.cancel_order.return_value = True
        
        # Execute tool
        result = await tool.execute(mock_client, order_id="test_order_id")
        
        assert result["success"] is True
        assert result["cancelled"] is True
        assert result["order_id"] == "test_order_id"
        
        mock_client.cancel_order.assert_called_once_with("test_order_id")
    
    @pytest.mark.asyncio
    async def test_get_positions_tool(self):
        """Test get positions tool execution."""
        tool = GetPositionsTool()
        
        # Mock client and position
        mock_client = AsyncMock()
        mock_position = Mock()
        mock_position.asset = "ETH-USD"
        mock_position.size = 1.0
        mock_position.avg_price = 3500.0
        mock_position.unrealized_pnl = 100.0
        mock_position.realized_pnl = 0.0
        mock_position.side = Mock()
        mock_position.side.value = "buy"
        mock_position.created_at.isoformat.return_value = "2024-01-01T00:00:00Z"
        mock_position.updated_at.isoformat.return_value = "2024-01-01T00:00:00Z"
        
        mock_client.get_positions.return_value = [mock_position]
        
        # Execute tool
        result = await tool.execute(mock_client)
        
        assert result["success"] is True
        assert len(result["positions"]) == 1
        assert result["positions"][0]["asset"] == "ETH-USD"
        assert result["positions"][0]["size"] == 1.0


class TestHyperliquidMCPServer:
    """Test MCP server functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return HyperliquidConfig.for_paper_trading()
    
    @pytest.fixture
    def server(self, config):
        """Create MCP server instance."""
        return HyperliquidMCPServer(config, TradingMode.PAPER)
    
    def test_server_initialization(self, server):
        """Test server initialization."""
        assert server.config is not None
        assert server.trading_mode == TradingMode.PAPER
        assert server.client is None
        assert not server._running
        assert len(server.tools) > 0  # Tools should be registered
    
    def test_get_available_tools(self, server):
        """Test getting available tools."""
        tools = server.get_available_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check tool structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
        
        # Check specific tools are available
        tool_names = [tool["name"] for tool in tools]
        assert "place_order" in tool_names
        assert "cancel_order" in tool_names
        assert "get_positions" in tool_names
        assert "get_orders" in tool_names
        assert "get_balances" in tool_names
        assert "get_market_data" in tool_names
    
    @pytest.mark.asyncio
    async def test_server_lifecycle(self, server):
        """Test server start/stop lifecycle."""
        assert not server._running
        
        with patch('backend.src.trading.mcp_server.HyperliquidClient') as MockClient:
            mock_client_instance = AsyncMock()
            MockClient.return_value = mock_client_instance
            
            await server.start()
            
            assert server._running
            assert server.client is not None
            mock_client_instance.connect.assert_called_once()
            
            await server.stop()
            
            assert not server._running
            mock_client_instance.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        """Test server as async context manager."""
        with patch('backend.src.trading.mcp_server.HyperliquidClient') as MockClient:
            mock_client_instance = AsyncMock()
            MockClient.return_value = mock_client_instance
            
            async with HyperliquidMCPServer(config, TradingMode.PAPER) as server:
                assert server._running
                assert server.client is not None
            
            # Should be stopped after exiting context
            assert not server._running
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_running(self, server):
        """Test executing tool when server not running."""
        result = await server.execute_tool("place_order", {"asset": "ETH-USD"})
        
        assert result["success"] is False
        assert "not running" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_execute_tool_unknown_tool(self, server):
        """Test executing unknown tool."""
        server._running = True
        server.client = AsyncMock()
        
        result = await server.execute_tool("unknown_tool", {})
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, server):
        """Test successful tool execution."""
        with patch('backend.src.trading.mcp_server.HyperliquidClient') as MockClient:
            mock_client_instance = AsyncMock()
            MockClient.return_value = mock_client_instance
            
            # Mock successful order placement
            mock_order = Mock()
            mock_order.id = "test_order"
            mock_order.asset = "ETH-USD"
            mock_order.size = 1.0
            mock_order.side = OrderSide.BUY
            mock_order.order_type = OrderType.MARKET
            mock_order.status = Mock()
            mock_order.status.value = "filled"
            mock_order.price = None
            mock_order.filled_size = 1.0
            mock_order.avg_fill_price = 3500.0
            mock_order.created_at = None
            
            mock_client_instance.place_order.return_value = mock_order
            
            async with server:
                result = await server.execute_tool("place_order", {
                    "asset": "ETH-USD",
                    "size": 1.0,
                    "side": "buy",
                    "order_type": "market"
                })
                
                assert result["success"] is True
                assert result["order"]["id"] == "test_order"
    
    @pytest.mark.asyncio
    async def test_health_check_not_running(self, server):
        """Test health check when server not running."""
        health = await server.health_check()
        
        assert health["healthy"] is False
        assert "not running" in health["error"].lower()
    
    @pytest.mark.asyncio
    async def test_health_check_running(self, server):
        """Test health check when server running."""
        with patch('backend.src.trading.mcp_server.HyperliquidClient') as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.health_check.return_value = True
            mock_client_instance.is_connected = True
            MockClient.return_value = mock_client_instance
            
            async with server:
                health = await server.health_check()
                
                assert health["healthy"] is True
                assert health["trading_mode"] == "paper"
                assert health["connected"] is True
                assert health["available_tools"] > 0


class TestMCPServerFactory:
    """Test MCP server factory functions."""
    
    @pytest.mark.asyncio
    async def test_create_mcp_server_default(self):
        """Test creating MCP server with defaults."""
        server = await create_mcp_server()
        
        assert isinstance(server, HyperliquidMCPServer)
        assert server.trading_mode == TradingMode.PAPER
        assert server.config is not None
    
    @pytest.mark.asyncio
    async def test_create_mcp_server_with_config(self):
        """Test creating MCP server with custom config."""
        config = HyperliquidConfig.for_paper_trading()
        server = await create_mcp_server(config, TradingMode.PAPER)
        
        assert isinstance(server, HyperliquidMCPServer)
        assert server.config == config
        assert server.trading_mode == TradingMode.PAPER
    
    @pytest.mark.asyncio
    async def test_create_mcp_server_live_mode(self):
        """Test creating MCP server for live trading."""
        server = await create_mcp_server(trading_mode=TradingMode.LIVE)
        
        assert isinstance(server, HyperliquidMCPServer)
        assert server.trading_mode == TradingMode.LIVE


if __name__ == "__main__":
    pytest.main([__file__])