"""
Comprehensive example of Hyperliquid MCP server usage.

This demonstrates how AI agents can interact with the Hyperliquid MCP server
to perform trading operations through a structured interface.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List

from ..config import HyperliquidConfig
from ..types import TradingMode
from .mcp_server import create_mcp_server


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AITradingAgent:
    """
    Example AI trading agent that uses the MCP server to execute trading strategies.
    
    This demonstrates how an AI agent would interact with the Hyperliquid MCP server
    to implement trading logic.
    """
    
    def __init__(self, mcp_server):
        self.mcp_server = mcp_server
        self.active_orders = []
        self.trade_history = []
    
    async def analyze_market(self, asset: str) -> Dict[str, Any]:
        """Analyze market conditions for an asset."""
        logger.info(f"Analyzing market for {asset}...")
        
        # Get current market data
        market_data_result = await self.mcp_server.execute_tool("get_market_data", {
            "asset": asset
        })
        
        # Get current positions
        positions_result = await self.mcp_server.execute_tool("get_positions", {
            "asset": asset
        })
        
        # Get pending orders
        orders_result = await self.mcp_server.execute_tool("get_orders", {
            "asset": asset,
            "status": "pending"
        })
        
        return {
            "asset": asset,
            "market_data": market_data_result.get("market_data"),
            "position": positions_result.get("positions", [])[0] if positions_result.get("positions") else None,
            "pending_orders": orders_result.get("orders", [])
        }
    
    async def execute_simple_strategy(self, asset: str, target_size: float) -> Dict[str, Any]:
        """
        Execute a simple trading strategy.
        
        Strategy: Buy if we don't have a position, sell if we do.
        This is just an example - real strategies would be much more sophisticated.
        """
        logger.info(f"Executing simple strategy for {asset} (target size: {target_size})...")
        
        # Analyze current market situation
        analysis = await self.analyze_market(asset)
        current_position = analysis["position"]
        current_size = current_position["size"] if current_position else 0.0
        
        logger.info(f"Current position size: {current_size}, Target: {target_size}")
        
        # Calculate the trade needed
        size_diff = target_size - current_size
        
        if abs(size_diff) < 0.001:  # Already at target
            logger.info("Already at target position size")
            return {"action": "none", "reason": "already_at_target"}
        
        # Determine trade direction and size
        if size_diff > 0:
            side = "buy"
            trade_size = abs(size_diff)
        else:
            side = "sell"
            trade_size = abs(size_diff)
        
        # Place the order
        logger.info(f"Placing {side} order for {trade_size} {asset}")
        
        order_result = await self.mcp_server.execute_tool("place_order", {
            "asset": asset,
            "size": trade_size,
            "side": side,
            "order_type": "market",
            "metadata": {
                "strategy": "simple_example",
                "target_size": target_size,
                "agent": "AITradingAgent"
            }
        })
        
        if order_result["success"]:
            self.active_orders.append(order_result["order"])
            logger.info(f"Order placed successfully: {order_result['order']['id']}")
        else:
            logger.error(f"Order placement failed: {order_result['error']}")
        
        return order_result
    
    async def manage_risk(self, max_position_value: float = 10000.0) -> List[Dict[str, Any]]:
        """
        Simple risk management - check if positions are too large and reduce them.
        
        In a real system, this would be much more sophisticated with stop losses,
        position sizing based on volatility, etc.
        """
        logger.info("Running risk management checks...")
        
        # Get current positions
        positions_result = await self.mcp_server.execute_tool("get_positions", {})
        
        if not positions_result["success"]:
            logger.error("Failed to get positions for risk check")
            return []
        
        actions_taken = []
        
        for position in positions_result["positions"]:
            position_value = abs(position["size"] * position["avg_price"])
            
            if position_value > max_position_value:
                logger.warning(f"Position {position['asset']} too large: ${position_value:.2f}")
                
                # Reduce position size by 50%
                reduce_size = abs(position["size"]) * 0.5
                reduce_side = "sell" if position["size"] > 0 else "buy"
                
                order_result = await self.mcp_server.execute_tool("place_order", {
                    "asset": position["asset"],
                    "size": reduce_size,
                    "side": reduce_side,
                    "order_type": "market",
                    "metadata": {
                        "strategy": "risk_management",
                        "reason": "position_too_large"
                    }
                })
                
                actions_taken.append({
                    "action": "reduce_position",
                    "asset": position["asset"],
                    "original_size": position["size"],
                    "reduce_size": reduce_size,
                    "order_result": order_result
                })
        
        return actions_taken
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get a comprehensive portfolio summary."""
        logger.info("Generating portfolio summary...")
        
        # Get balances
        balances_result = await self.mcp_server.execute_tool("get_balances", {})
        
        # Get all positions
        positions_result = await self.mcp_server.execute_tool("get_positions", {})
        
        # Get all orders
        orders_result = await self.mcp_server.execute_tool("get_orders", {})
        
        # Calculate totals
        total_balance = sum(balance["total"] for balance in balances_result.get("balances", []))
        
        total_position_value = 0.0
        total_pnl = 0.0
        
        for position in positions_result.get("positions", []):
            position_value = abs(position["size"]) * position["avg_price"]
            total_position_value += position_value
            total_pnl += position["unrealized_pnl"] + position["realized_pnl"]
        
        # Count orders by status
        orders_by_status = {}
        for order in orders_result.get("orders", []):
            status = order["status"]
            orders_by_status[status] = orders_by_status.get(status, 0) + 1
        
        return {
            "total_balance": total_balance,
            "total_position_value": total_position_value,
            "total_pnl": total_pnl,
            "num_positions": len(positions_result.get("positions", [])),
            "orders_by_status": orders_by_status,
            "balances": balances_result.get("balances", []),
            "positions": positions_result.get("positions", [])
        }


async def demonstrate_mcp_functionality():
    """Demonstrate various MCP server capabilities."""
    logger.info("=== MCP Server Functionality Demo ===")
    
    # Create MCP server for paper trading
    async with await create_mcp_server() as server:
        
        # 1. Server health check
        logger.info("\n1. Checking server health...")
        health = await server.health_check()
        logger.info(f"Health check result: {json.dumps(health, indent=2)}")
        
        # 2. List available tools
        logger.info("\n2. Available tools:")
        tools = server.get_available_tools()
        for tool in tools:
            logger.info(f"  - {tool['name']}: {tool['description']}")
        
        # 3. Check initial balances
        logger.info("\n3. Initial account state:")
        balances = await server.execute_tool("get_balances", {})
        logger.info(f"Balances: {json.dumps(balances, indent=2)}")
        
        positions = await server.execute_tool("get_positions", {})
        logger.info(f"Positions: {json.dumps(positions, indent=2)}")
        
        # 4. Place some orders
        logger.info("\n4. Placing test orders...")
        
        # Market buy order
        order1 = await server.execute_tool("place_order", {
            "asset": "ETH-USD",
            "size": 1.0,
            "side": "buy",
            "order_type": "market",
            "metadata": {"demo": "market_buy"}
        })
        logger.info(f"Market buy order: {json.dumps(order1, indent=2)}")
        
        # Limit sell order
        order2 = await server.execute_tool("place_order", {
            "asset": "ETH-USD",
            "size": 0.5,
            "side": "sell",
            "order_type": "limit",
            "price": 4000.0,
            "metadata": {"demo": "limit_sell"}
        })
        logger.info(f"Limit sell order: {json.dumps(order2, indent=2)}")
        
        # 5. Check updated state
        logger.info("\n5. Updated account state after orders:")
        positions = await server.execute_tool("get_positions", {})
        logger.info(f"Positions: {json.dumps(positions, indent=2)}")
        
        orders = await server.execute_tool("get_orders", {})
        logger.info(f"All orders: {len(orders.get('orders', []))} orders")
        
        # 6. Cancel pending orders
        logger.info("\n6. Managing orders...")
        pending_orders = await server.execute_tool("get_orders", {"status": "pending"})
        
        for order in pending_orders.get("orders", []):
            logger.info(f"Cancelling pending order: {order['id']}")
            cancel_result = await server.execute_tool("cancel_order", {
                "order_id": order["id"]
            })
            logger.info(f"Cancel result: {cancel_result}")


async def demonstrate_ai_agent():
    """Demonstrate AI agent using MCP server."""
    logger.info("\n=== AI Trading Agent Demo ===")
    
    async with await create_mcp_server() as server:
        # Create AI trading agent
        agent = AITradingAgent(server)
        
        # 1. Initial portfolio analysis
        logger.info("\n1. Initial portfolio analysis:")
        summary = await agent.get_portfolio_summary()
        logger.info(f"Portfolio: {json.dumps(summary, indent=2)}")
        
        # 2. Market analysis
        logger.info("\n2. Market analysis:")
        analysis = await agent.analyze_market("ETH-USD")
        logger.info(f"ETH-USD analysis: {json.dumps(analysis, indent=2)}")
        
        # 3. Execute trading strategy
        logger.info("\n3. Executing trading strategy:")
        strategy_result = await agent.execute_simple_strategy("ETH-USD", 2.0)
        logger.info(f"Strategy result: {json.dumps(strategy_result, indent=2)}")
        
        # 4. Risk management
        logger.info("\n4. Risk management:")
        risk_actions = await agent.manage_risk(max_position_value=5000.0)
        logger.info(f"Risk actions: {json.dumps(risk_actions, indent=2)}")
        
        # 5. Final portfolio state
        logger.info("\n5. Final portfolio state:")
        final_summary = await agent.get_portfolio_summary()
        logger.info(f"Final portfolio: {json.dumps(final_summary, indent=2)}")


async def demonstrate_tool_schemas():
    """Demonstrate tool schemas for AI integration."""
    logger.info("\n=== Tool Schemas for AI Integration ===")
    
    server = await create_mcp_server()
    tools = server.get_available_tools()
    
    logger.info("Tool schemas that can be provided to AI models:\n")
    
    for tool in tools:
        logger.info(f"Tool: {tool['name']}")
        logger.info(f"Description: {tool['description']}")
        logger.info(f"Schema: {json.dumps(tool['inputSchema'], indent=2)}")
        logger.info("-" * 50)


async def main():
    """Run all demonstrations."""
    logger.info("Starting Hyperliquid MCP Server Demonstrations...")
    
    try:
        # Demonstrate basic MCP functionality
        await demonstrate_mcp_functionality()
        await asyncio.sleep(1)
        
        # Demonstrate AI agent usage
        await demonstrate_ai_agent()
        await asyncio.sleep(1)
        
        # Show tool schemas
        await demonstrate_tool_schemas()
        
        logger.info("\n=== All demonstrations completed successfully! ===")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())