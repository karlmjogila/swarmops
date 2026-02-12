"""
Hyperliquid MCP Server Implementation

This module provides a Model Context Protocol (MCP) server that exposes
Hyperliquid trading functionality as callable tools for AI agents.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from ..types import OrderSide, OrderType, TradingMode
from ..config import HyperliquidConfig
from .hyperliquid_client import HyperliquidClient


logger = logging.getLogger(__name__)


class MCPTool:
    """Base class for MCP tools."""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any]):
        self.name = name
        self.description = description
        self.parameters = parameters
    
    async def execute(self, client: HyperliquidClient, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters."""
        raise NotImplementedError


class PlaceOrderTool(MCPTool):
    """Tool for placing trading orders."""
    
    def __init__(self):
        super().__init__(
            name="place_order",
            description="Place a trading order on Hyperliquid",
            parameters={
                "type": "object",
                "properties": {
                    "asset": {
                        "type": "string",
                        "description": "Trading symbol (e.g., 'ETH-USD')"
                    },
                    "size": {
                        "type": "number",
                        "description": "Order size"
                    },
                    "side": {
                        "type": "string",
                        "enum": ["buy", "sell"],
                        "description": "Order side"
                    },
                    "order_type": {
                        "type": "string",
                        "enum": ["market", "limit", "stop", "stop_limit"],
                        "description": "Order type",
                        "default": "market"
                    },
                    "price": {
                        "type": "number",
                        "description": "Limit price (required for limit orders)"
                    },
                    "stop_price": {
                        "type": "number",
                        "description": "Stop price (required for stop orders)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional order metadata"
                    }
                },
                "required": ["asset", "size", "side"]
            }
        )
    
    async def execute(self, client: HyperliquidClient, **kwargs) -> Dict[str, Any]:
        """Execute order placement."""
        try:
            # Convert string enums to proper enum types
            side = OrderSide(kwargs["side"])
            order_type = OrderType(kwargs.get("order_type", "market"))
            
            order = await client.place_order(
                asset=kwargs["asset"],
                size=float(kwargs["size"]),
                side=side,
                order_type=order_type,
                price=kwargs.get("price"),
                stop_price=kwargs.get("stop_price"),
                metadata=kwargs.get("metadata", {})
            )
            
            return {
                "success": True,
                "order": {
                    "id": order.id,
                    "asset": order.asset,
                    "size": order.size,
                    "side": order.side.value,
                    "order_type": order.order_type.value,
                    "status": order.status.value,
                    "price": order.price,
                    "filled_size": order.filled_size,
                    "avg_fill_price": order.avg_fill_price,
                    "created_at": order.created_at.isoformat() if order.created_at else None
                }
            }
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class CancelOrderTool(MCPTool):
    """Tool for cancelling orders."""
    
    def __init__(self):
        super().__init__(
            name="cancel_order",
            description="Cancel an existing order",
            parameters={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "ID of the order to cancel"
                    }
                },
                "required": ["order_id"]
            }
        )
    
    async def execute(self, client: HyperliquidClient, **kwargs) -> Dict[str, Any]:
        """Execute order cancellation."""
        try:
            success = await client.cancel_order(kwargs["order_id"])
            return {
                "success": success,
                "order_id": kwargs["order_id"],
                "cancelled": success
            }
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {
                "success": False,
                "error": str(e),
                "order_id": kwargs["order_id"]
            }


class GetPositionsTool(MCPTool):
    """Tool for getting current positions."""
    
    def __init__(self):
        super().__init__(
            name="get_positions",
            description="Get current trading positions",
            parameters={
                "type": "object",
                "properties": {
                    "asset": {
                        "type": "string",
                        "description": "Filter by specific asset (optional)"
                    }
                },
                "required": []
            }
        )
    
    async def execute(self, client: HyperliquidClient, **kwargs) -> Dict[str, Any]:
        """Execute position retrieval."""
        try:
            asset = kwargs.get("asset")
            
            if asset:
                position = await client.get_position(asset)
                positions = [position] if position else []
            else:
                positions = await client.get_positions()
            
            return {
                "success": True,
                "positions": [
                    {
                        "asset": pos.asset,
                        "size": pos.size,
                        "avg_price": pos.avg_price,
                        "unrealized_pnl": pos.unrealized_pnl,
                        "realized_pnl": pos.realized_pnl,
                        "side": pos.side.value,
                        "created_at": pos.created_at.isoformat(),
                        "updated_at": pos.updated_at.isoformat()
                    }
                    for pos in positions
                ]
            }
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class GetOrdersTool(MCPTool):
    """Tool for getting orders."""
    
    def __init__(self):
        super().__init__(
            name="get_orders",
            description="Get trading orders",
            parameters={
                "type": "object",
                "properties": {
                    "asset": {
                        "type": "string",
                        "description": "Filter by specific asset (optional)"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "filled", "partial", "cancelled", "rejected"],
                        "description": "Filter by order status (optional)"
                    }
                },
                "required": []
            }
        )
    
    async def execute(self, client: HyperliquidClient, **kwargs) -> Dict[str, Any]:
        """Execute order retrieval."""
        try:
            asset = kwargs.get("asset")
            status_filter = kwargs.get("status")
            
            orders = await client.get_orders(asset)
            
            # Filter by status if specified
            if status_filter:
                orders = [order for order in orders if order.status.value == status_filter]
            
            return {
                "success": True,
                "orders": [
                    {
                        "id": order.id,
                        "asset": order.asset,
                        "size": order.size,
                        "side": order.side.value,
                        "order_type": order.order_type.value,
                        "status": order.status.value,
                        "price": order.price,
                        "filled_size": order.filled_size,
                        "avg_fill_price": order.avg_fill_price,
                        "created_at": order.created_at.isoformat() if order.created_at else None,
                        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                        "metadata": order.metadata
                    }
                    for order in orders
                ]
            }
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class GetBalancesTool(MCPTool):
    """Tool for getting account balances."""
    
    def __init__(self):
        super().__init__(
            name="get_balances",
            description="Get account balances",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    
    async def execute(self, client: HyperliquidClient, **kwargs) -> Dict[str, Any]:
        """Execute balance retrieval."""
        try:
            balances = await client.get_balances()
            
            return {
                "success": True,
                "balances": [
                    {
                        "asset": balance.asset,
                        "total": balance.total,
                        "available": balance.available,
                        "locked": balance.locked
                    }
                    for balance in balances
                ]
            }
        except Exception as e:
            logger.error(f"Error getting balances: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class GetMarketDataTool(MCPTool):
    """Tool for getting market data."""
    
    def __init__(self):
        super().__init__(
            name="get_market_data",
            description="Get market data for an asset",
            parameters={
                "type": "object",
                "properties": {
                    "asset": {
                        "type": "string",
                        "description": "Trading symbol (e.g., 'ETH-USD')"
                    }
                },
                "required": ["asset"]
            }
        )
    
    async def execute(self, client: HyperliquidClient, **kwargs) -> Dict[str, Any]:
        """Execute market data retrieval."""
        try:
            market_data = await client.get_market_data(kwargs["asset"])
            
            if market_data is None:
                return {
                    "success": False,
                    "error": f"No market data available for {kwargs['asset']}"
                }
            
            return {
                "success": True,
                "market_data": {
                    "asset": market_data.asset,
                    "bid": market_data.bid,
                    "ask": market_data.ask,
                    "last": market_data.last,
                    "volume_24h": market_data.volume_24h,
                    "timestamp": market_data.timestamp.isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class HyperliquidMCPServer:
    """MCP server for Hyperliquid trading functionality."""
    
    def __init__(self, config: HyperliquidConfig, trading_mode: TradingMode = TradingMode.PAPER):
        self.config = config
        self.trading_mode = trading_mode
        self.client: Optional[HyperliquidClient] = None
        self.tools: Dict[str, MCPTool] = {}
        self._running = False
        
        # Register available tools
        self._register_tools()
    
    def _register_tools(self):
        """Register available MCP tools."""
        tools = [
            PlaceOrderTool(),
            CancelOrderTool(),
            GetPositionsTool(),
            GetOrdersTool(),
            GetBalancesTool(),
            GetMarketDataTool()
        ]
        
        for tool in tools:
            self.tools[tool.name] = tool
            logger.info(f"Registered MCP tool: {tool.name}")
    
    async def start(self):
        """Start the MCP server."""
        logger.info(f"Starting Hyperliquid MCP server in {self.trading_mode} mode...")
        
        self.client = HyperliquidClient(self.config, self.trading_mode)
        await self.client.connect()
        self._running = True
        
        logger.info("Hyperliquid MCP server started successfully")
    
    async def stop(self):
        """Stop the MCP server."""
        logger.info("Stopping Hyperliquid MCP server...")
        
        self._running = False
        
        if self.client:
            await self.client.disconnect()
            self.client = None
        
        logger.info("Hyperliquid MCP server stopped")
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools and their schemas."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.parameters
            }
            for tool in self.tools.values()
        ]
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given parameters."""
        if not self._running or not self.client:
            return {
                "success": False,
                "error": "MCP server not running or client not connected"
            }
        
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}"
            }
        
        tool = self.tools[tool_name]
        logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
        
        try:
            result = await tool.execute(self.client, **parameters)
            logger.info(f"Tool {tool_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}"
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check server and client health."""
        if not self._running:
            return {
                "healthy": False,
                "error": "Server not running"
            }
        
        if not self.client:
            return {
                "healthy": False,
                "error": "Client not connected"
            }
        
        client_healthy = await self.client.health_check()
        
        return {
            "healthy": client_healthy,
            "trading_mode": self.trading_mode.value,
            "connected": self.client.is_connected,
            "available_tools": len(self.tools)
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


async def create_mcp_server(
    config: Optional[HyperliquidConfig] = None,
    trading_mode: TradingMode = TradingMode.PAPER
) -> HyperliquidMCPServer:
    """Create and return an MCP server instance."""
    if config is None:
        if trading_mode == TradingMode.PAPER:
            config = HyperliquidConfig.for_paper_trading()
        else:
            config = HyperliquidConfig.from_settings()
    
    return HyperliquidMCPServer(config, trading_mode)


# Example usage and testing
async def example_mcp_usage():
    """Example of how to use the MCP server."""
    logger.info("Starting MCP server example...")
    
    # Create server for paper trading
    async with await create_mcp_server() as server:
        # Check health
        health = await server.health_check()
        logger.info(f"Server health: {health}")
        
        # Get available tools
        tools = server.get_available_tools()
        logger.info(f"Available tools: {[tool['name'] for tool in tools]}")
        
        # Execute a tool - place order
        result = await server.execute_tool("place_order", {
            "asset": "ETH-USD",
            "size": 1.0,
            "side": "buy",
            "order_type": "market",
            "metadata": {"strategy": "example"}
        })
        logger.info(f"Place order result: {result}")
        
        # Get positions
        positions = await server.execute_tool("get_positions", {})
        logger.info(f"Positions: {positions}")
        
        # Get balances
        balances = await server.execute_tool("get_balances", {})
        logger.info(f"Balances: {balances}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_mcp_usage())