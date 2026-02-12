"""MCP server for Hyperliquid trading integration with Claude.

This server exposes Hyperliquid trading operations as MCP tools that Claude can use
for trade execution and market analysis.

Key Features:
- Safe tool exposure with validation
- Comprehensive error handling
- Audit trail of all Claude-initiated operations
- Paper trading mode support
- Position and risk monitoring

Following LLM Integration Excellence and Trading Systems Excellence principles.
"""

import os
from decimal import Decimal
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from hl_bot.trading.hyperliquid import HyperliquidClient, HyperliquidError
from hl_bot.types import OrderRequest, OrderSide, OrderType
from hl_bot.utils.logging import get_logger

logger = get_logger(__name__)


class HyperliquidMCPServer:
    """MCP server for Hyperliquid trading operations.
    
    Exposes trading operations as tools for Claude to use via MCP protocol.
    Includes safety checks, validation, and comprehensive audit logging.
    """
    
    def __init__(
        self,
        private_key: str | None = None,
        testnet: bool = True,
        paper_mode: bool = True,
    ):
        """Initialize MCP server.
        
        Args:
            private_key: Ethereum private key (from env if None)
            testnet: Use testnet if True
            paper_mode: Enable paper trading mode (no real orders)
        """
        self.paper_mode = paper_mode
        
        # Get private key from env if not provided
        if private_key is None:
            private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
            if not private_key:
                raise ValueError(
                    "HYPERLIQUID_PRIVATE_KEY environment variable required"
                )
        
        # Initialize Hyperliquid client
        self.client = HyperliquidClient(
            private_key=private_key,
            testnet=testnet,
        )
        
        # Initialize MCP server
        self.server = Server("hyperliquid-trading")
        
        # Register tools
        self._register_tools()
        
        logger.info(
            "MCP server initialized",
            paper_mode=paper_mode,
            network="testnet" if testnet else "mainnet",
            address=str(self.client.address),
        )
    
    def _register_tools(self) -> None:
        """Register all available trading tools."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools."""
            return [
                Tool(
                    name="get_market_data",
                    description="Get current market data for a trading symbol including price, volume, and orderbook depth",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading symbol (e.g., BTC, ETH)",
                            },
                        },
                        "required": ["symbol"],
                    },
                ),
                Tool(
                    name="get_positions",
                    description="Get all currently open positions with P&L and risk metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="get_account_state",
                    description="Get account state including balance, margin, and available capital",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="place_order",
                    description="Place a trading order. USE WITH EXTREME CAUTION. Always validate parameters and confirm intent before execution.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading symbol (e.g., BTC, ETH)",
                            },
                            "side": {
                                "type": "string",
                                "enum": ["buy", "sell"],
                                "description": "Order side: buy or sell",
                            },
                            "order_type": {
                                "type": "string",
                                "enum": ["market", "limit", "stop_loss", "take_profit"],
                                "description": "Order type",
                            },
                            "quantity": {
                                "type": "number",
                                "description": "Order quantity (positive number)",
                            },
                            "price": {
                                "type": "number",
                                "description": "Limit price (required for limit orders)",
                            },
                            "stop_price": {
                                "type": "number",
                                "description": "Stop trigger price (for stop_loss/take_profit orders)",
                            },
                            "reduce_only": {
                                "type": "boolean",
                                "description": "Only reduce existing position (safety feature)",
                                "default": False,
                            },
                            "post_only": {
                                "type": "boolean",
                                "description": "Only place order if it would be a maker (limit orders)",
                                "default": False,
                            },
                        },
                        "required": ["symbol", "side", "order_type", "quantity"],
                    },
                ),
                Tool(
                    name="cancel_order",
                    description="Cancel a specific open order",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Order ID to cancel",
                            },
                            "symbol": {
                                "type": "string",
                                "description": "Trading symbol",
                            },
                        },
                        "required": ["order_id", "symbol"],
                    },
                ),
                Tool(
                    name="cancel_all_orders",
                    description="Cancel all open orders. Use for emergency exits or risk management.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Optional: only cancel orders for this symbol",
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for cancellation (for audit trail)",
                                "default": "claude_requested",
                            },
                        },
                    },
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "get_market_data":
                    return await self._get_market_data(arguments)
                elif name == "get_positions":
                    return await self._get_positions()
                elif name == "get_account_state":
                    return await self._get_account_state()
                elif name == "place_order":
                    return await self._place_order(arguments)
                elif name == "cancel_order":
                    return await self._cancel_order(arguments)
                elif name == "cancel_all_orders":
                    return await self._cancel_all_orders(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            
            except Exception as e:
                logger.error("Tool call failed", tool=name, error=str(e))
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}",
                )]
    
    async def _get_market_data(self, args: dict[str, Any]) -> list[TextContent]:
        """Get market data for a symbol."""
        symbol = args["symbol"]
        
        try:
            data = await self.client.get_market_data(symbol)
            
            result = f"""Market Data for {symbol}:
- Current Price: {data.get('price', 'N/A')}
- 24h Volume: {data.get('volume', 'N/A')}
- 24h Change: {data.get('change', 'N/A')}
- Bid/Ask Spread: {data.get('spread', 'N/A')}
- Open Interest: {data.get('openInterest', 'N/A')}
"""
            
            return [TextContent(type="text", text=result)]
        
        except Exception as e:
            raise HyperliquidError(f"Failed to get market data: {e}")
    
    async def _get_positions(self) -> list[TextContent]:
        """Get all open positions."""
        try:
            positions = await self.client.get_positions()
            
            if not positions:
                return [TextContent(type="text", text="No open positions")]
            
            result = "Open Positions:\n\n"
            for pos in positions:
                result += f"""Symbol: {pos.symbol}
- Side: {pos.side.value.upper()}
- Quantity: {pos.quantity}
- Entry Price: {pos.entry_price}
- Mark Price: {pos.mark_price}
- Unrealized P&L: {pos.unrealized_pnl:.2f}
- Leverage: {pos.leverage}x
{f"- Liquidation Price: {pos.liquidation_price}" if pos.liquidation_price else ""}

"""
            
            return [TextContent(type="text", text=result)]
        
        except Exception as e:
            raise HyperliquidError(f"Failed to get positions: {e}")
    
    async def _get_account_state(self) -> list[TextContent]:
        """Get account state."""
        try:
            account = await self.client.get_account_state()
            
            result = f"""Account State:
- Total Balance: {account.get('balance', 'N/A')}
- Available Balance: {account.get('availableBalance', 'N/A')}
- Used Margin: {account.get('usedMargin', 'N/A')}
- Unrealized P&L: {account.get('unrealizedPnl', 'N/A')}
- Total P&L: {account.get('totalPnl', 'N/A')}
- Account Value: {account.get('accountValue', 'N/A')}
"""
            
            return [TextContent(type="text", text=result)]
        
        except Exception as e:
            raise HyperliquidError(f"Failed to get account state: {e}")
    
    async def _place_order(self, args: dict[str, Any]) -> list[TextContent]:
        """Place a trading order with safety checks."""
        
        # Validate inputs BEFORE paper mode check
        symbol = args["symbol"]
        side = OrderSide(args["side"].lower())
        order_type = OrderType(args["order_type"].lower())
        quantity = float(args["quantity"])
        
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # Validate limit orders have price BEFORE creating OrderRequest
        if order_type == OrderType.LIMIT and not args.get("price"):
            raise ValueError(f"{order_type.value} orders require a price")
        
        # Validate stop orders have stop_price BEFORE creating OrderRequest
        if order_type in (OrderType.STOP_LOSS, OrderType.TAKE_PROFIT) and not args.get("stop_price"):
            raise ValueError("Stop/take profit orders require a stop_price")
        
        # Build order request (Pydantic will do additional validation)
        order_request = OrderRequest(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=args.get("price"),
            stop_price=args.get("stop_price"),
            reduce_only=args.get("reduce_only", False),
            post_only=args.get("post_only", False),
        )
        
        # Paper mode check AFTER validation
        if self.paper_mode:
            logger.warning("Paper mode: simulating order placement", args=args)
            return [TextContent(
                type="text",
                text=f"[PAPER MODE] Order simulation:\n{args}\n\nNo real order placed.",
            )]
        
        try:
            # Place order (log dict representation, not Pydantic object)
            logger.info(
                "Claude placing order via MCP",
                symbol=symbol,
                side=side.value,
                order_type=order_type.value,
                quantity=quantity,
            )
            order = await self.client.place_order(order_request)
            
            result = f"""Order Placed Successfully:
- Order ID: {order.id}
- Symbol: {order.symbol}
- Side: {order.side.value.upper()}
- Type: {order.order_type.value.upper()}
- Quantity: {order.quantity}
- Price: {order.price or "MARKET"}
- Status: {order.status}
"""
            
            return [TextContent(type="text", text=result)]
        
        except Exception as e:
            raise HyperliquidError(f"Failed to place order: {e}")
    
    async def _cancel_order(self, args: dict[str, Any]) -> list[TextContent]:
        """Cancel a specific order."""
        order_id = args["order_id"]
        symbol = args["symbol"]
        
        if self.paper_mode:
            logger.warning("Paper mode: simulating order cancellation", args=args)
            return [TextContent(
                type="text",
                text=f"[PAPER MODE] Order cancellation simulation: {order_id}",
            )]
        
        try:
            await self.client.cancel_order(order_id, symbol)
            return [TextContent(
                type="text",
                text=f"Order {order_id} cancelled successfully",
            )]
        
        except Exception as e:
            raise HyperliquidError(f"Failed to cancel order: {e}")
    
    async def _cancel_all_orders(self, args: dict[str, Any]) -> list[TextContent]:
        """Cancel all open orders."""
        symbol = args.get("symbol")
        reason = args.get("reason", "claude_requested")
        
        if self.paper_mode:
            logger.warning("Paper mode: simulating cancel all", args=args)
            return [TextContent(
                type="text",
                text=f"[PAPER MODE] Cancel all simulation: symbol={symbol}, reason={reason}",
            )]
        
        try:
            count = await self.client.cancel_all_orders(symbol, reason)
            return [TextContent(
                type="text",
                text=f"Cancelled {count} orders{f' for {symbol}' if symbol else ''}",
            )]
        
        except Exception as e:
            raise HyperliquidError(f"Failed to cancel all orders: {e}")
    
    async def run(self) -> None:
        """Run the MCP server."""
        logger.info("Starting MCP server...")
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


async def main() -> None:
    """Main entry point for MCP server."""
    import sys
    
    # Configuration from environment
    testnet = os.getenv("HYPERLIQUID_TESTNET", "true").lower() == "true"
    paper_mode = os.getenv("HYPERLIQUID_PAPER_MODE", "true").lower() == "true"
    
    if not paper_mode:
        logger.warning("⚠️  LIVE TRADING MODE ENABLED - Real funds at risk!")
    
    try:
        server = HyperliquidMCPServer(
            testnet=testnet,
            paper_mode=paper_mode,
        )
        await server.run()
    
    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error("MCP server failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
