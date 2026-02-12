"""
Example usage of the Hyperliquid MCP Client.

This demonstrates how to use the client for both paper and live trading.
"""

import asyncio
import logging
from ..config import HyperliquidConfig
from ..types import OrderSide, OrderType, TradingMode
from .hyperliquid_client import HyperliquidClient


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def paper_trading_example():
    """Example of paper trading usage."""
    logger.info("=== Paper Trading Example ===")
    
    config = HyperliquidConfig.for_paper_trading()
    
    async with HyperliquidClient(config, TradingMode.PAPER) as client:
        logger.info(f"Connected in {client.trading_mode} mode")
        
        # Place a market buy order
        order = await client.place_order(
            asset="ETH-USD",
            size=1.0,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            metadata={"strategy": "test"}
        )
        
        logger.info(f"Order placed: {order}")
        
        # Check positions
        positions = await client.get_positions()
        logger.info(f"Positions: {positions}")
        
        # Place a limit sell order
        limit_order = await client.place_order(
            asset="ETH-USD",
            size=0.5,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=3600.0,
            metadata={"strategy": "test", "exit": "partial"}
        )
        
        logger.info(f"Limit order placed: {limit_order}")
        
        # Get all orders
        orders = await client.get_orders()
        logger.info(f"All orders: {len(orders)}")
        
        # Get balances
        balances = await client.get_balances()
        logger.info(f"Balances: {balances}")


async def live_trading_example():
    """Example of live trading usage (requires API keys)."""
    logger.info("=== Live Trading Example ===")
    
    config = HyperliquidConfig(
        private_key="your_private_key_here",
        wallet_address="your_wallet_address_here"
    )
    
    try:
        async with HyperliquidClient(config, TradingMode.LIVE) as client:
            logger.info(f"Connected in {client.trading_mode} mode")
            
            # Health check
            is_healthy = await client.health_check()
            logger.info(f"Health check: {is_healthy}")
            
            if not is_healthy:
                logger.error("Connection unhealthy, skipping trading")
                return
            
            # Place a small test order
            order = await client.place_order(
                asset="ETH-USD",
                size=0.01,  # Small size for testing
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=3000.0,  # Below market for safety
                metadata={"strategy": "test_live"}
            )
            
            logger.info(f"Live order placed: {order}")
            
            # Wait a bit then cancel if still pending
            await asyncio.sleep(5)
            
            order_status = await client.get_order(order.id)
            if order_status and order_status.status == "pending":
                cancelled = await client.cancel_order(order.id)
                logger.info(f"Order cancelled: {cancelled}")
                
    except Exception as e:
        logger.error(f"Live trading example failed: {e}")


async def callback_example():
    """Example of using callbacks for order and position updates."""
    logger.info("=== Callback Example ===")
    
    def on_order_update(order):
        logger.info(f"Order callback: {order.id} - {order.status}")
    
    def on_position_update(position):
        logger.info(f"Position callback: {position.asset} - {position.size}")
    
    config = HyperliquidConfig.for_paper_trading()
    
    async with HyperliquidClient(config, TradingMode.PAPER) as client:
        # Add callbacks
        client.add_order_callback(on_order_update)
        client.add_position_callback(on_position_update)
        
        # Place orders to trigger callbacks
        await client.place_order("BTC-USD", 0.1, OrderSide.BUY, OrderType.MARKET)
        await client.place_order("SOL-USD", 10.0, OrderSide.BUY, OrderType.MARKET)
        
        # Wait a bit for callbacks
        await asyncio.sleep(1)
        
        # Remove callbacks
        client.remove_order_callback(on_order_update)
        client.remove_position_callback(on_position_update)


async def main():
    """Run all examples."""
    logger.info("Starting Hyperliquid Client Examples...")
    
    try:
        await paper_trading_example()
        await asyncio.sleep(1)
        
        await callback_example()
        await asyncio.sleep(1)
        
        # Uncomment to test live trading (requires valid credentials)
        # await live_trading_example()
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())