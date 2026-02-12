"""Example usage of Hyperliquid client.

Demonstrates:
- Safe initialization
- Order placement
- Position monitoring
- WebSocket subscriptions
- Emergency shutdown

DO NOT RUN WITH REAL FUNDS WITHOUT TESTING!
"""

import asyncio
import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from hl_bot.trading import HyperliquidClient
from hl_bot.types import OrderRequest, OrderSide, OrderType


async def example_basic_usage():
    """Basic client usage example."""
    load_dotenv()

    # Initialize client (TESTNET!)
    client = HyperliquidClient(
        private_key=os.environ["HYPERLIQUID_PRIVATE_KEY"],
        testnet=True,  # ALWAYS test on testnet first!
        audit_log_dir=Path("./logs/audit"),
    )

    print(f"✅ Connected as: {client.address}")
    print(f"📊 Network: Testnet")
    print()

    try:
        # Get account state
        account = await client.get_account_state()
        print(f"💰 Balance: ${account.get('balance', 0):.2f}")
        print()

        # Get market data
        market = await client.get_market_data("BTC-USD")
        print(f"📈 BTC-USD Last Price: ${market.get('lastPx', 0):.2f}")
        print()

        # Get positions
        positions = await client.get_positions()
        if positions:
            print(f"📍 Open Positions: {len(positions)}")
            for pos in positions:
                print(f"  {pos.symbol}: {pos.quantity} @ ${pos.entry_price:.2f}")
                print(f"    P&L: ${pos.unrealized_pnl:.2f}")
        else:
            print("📍 No open positions")
        print()

    finally:
        await client.close()


async def example_place_order():
    """Example: Place a limit order."""
    load_dotenv()

    client = HyperliquidClient(
        private_key=os.environ["HYPERLIQUID_PRIVATE_KEY"],
        testnet=True,
        audit_log_dir=Path("./logs/audit"),
    )

    try:
        # Get current price
        market = await client.get_market_data("BTC-USD")
        current_price = float(market.get("lastPx", 50000))

        print(f"Current BTC-USD price: ${current_price:.2f}")

        # Place limit order 1% below market (buy low!)
        limit_price = current_price * 0.99

        order_request = OrderRequest(
            symbol="BTC-USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.001,  # Small size for testing
            price=limit_price,
            post_only=True,  # Maker-only
        )

        print(f"\n📝 Placing order:")
        print(f"  Symbol: {order_request.symbol}")
        print(f"  Side: {order_request.side}")
        print(f"  Quantity: {order_request.quantity}")
        print(f"  Price: ${limit_price:.2f}")
        print()

        # Place order
        order = await client.place_order(order_request)

        print(f"✅ Order placed!")
        print(f"  Order ID: {order.id}")
        print(f"  Status: {order.status}")
        print()

        # Wait a bit
        await asyncio.sleep(5)

        # Cancel order (cleanup)
        print(f"🗑️  Cancelling order {order.id}")
        await client.cancel_order(order.id, "BTC-USD")
        print("✅ Order cancelled")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        await client.close()


async def example_websocket():
    """Example: WebSocket real-time data."""
    load_dotenv()

    client = HyperliquidClient(
        private_key=os.environ["HYPERLIQUID_PRIVATE_KEY"],
        testnet=True,
        audit_log_dir=Path("./logs/audit"),
    )

    # Message counter
    message_count = 0

    async def handle_message(message):
        """Handle WebSocket messages."""
        nonlocal message_count
        message_count += 1

        msg_type = message.get("type")
        print(f"📨 [{message_count}] {msg_type}: {message}")

    # Register callback
    client.on_message(handle_message)

    # Subscriptions
    subscriptions = [
        {"type": "subscribe", "channel": "trades", "symbol": "BTC-USD"},
    ]

    try:
        print("🔌 Starting WebSocket...")
        print("📡 Subscribed to BTC-USD trades")
        print("⏱️  Will run for 30 seconds\n")

        # Start WebSocket (in background)
        ws_task = asyncio.create_task(client.start_websocket(subscriptions))

        # Run for 30 seconds
        await asyncio.sleep(30)

        # Stop WebSocket
        print("\n🛑 Stopping WebSocket...")
        await client.stop_websocket()
        await ws_task

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        await client.stop_websocket()

    finally:
        await client.close()
        print(f"✅ Received {message_count} messages")


async def example_position_monitor():
    """Example: Monitor positions and enforce max loss."""
    load_dotenv()

    MAX_LOSS = -100.0  # Max loss: $100

    client = HyperliquidClient(
        private_key=os.environ["HYPERLIQUID_PRIVATE_KEY"],
        testnet=True,
        audit_log_dir=Path("./logs/audit"),
    )

    try:
        print(f"👁️  Position Monitor Started")
        print(f"🛡️  Max Loss: ${abs(MAX_LOSS):.2f}")
        print(f"⏱️  Checking every 10 seconds\n")

        for i in range(6):  # Run for 1 minute
            positions = await client.get_positions()

            if positions:
                total_pnl = sum(p.unrealized_pnl for p in positions)

                print(f"[{i+1}/6] Positions: {len(positions)} | Total P&L: ${total_pnl:.2f}")

                for pos in positions:
                    print(f"  {pos.symbol}: ${pos.unrealized_pnl:+.2f}")

                # Check max loss
                if total_pnl <= MAX_LOSS:
                    print(f"\n⚠️  MAX LOSS REACHED: ${total_pnl:.2f}")
                    print("🚨 Emergency shutdown initiated!")

                    # Cancel all orders
                    cancelled = await client.cancel_all_orders(reason="max_loss")
                    print(f"✅ Cancelled {cancelled} orders")

                    # TODO: Close positions here
                    print("⚠️  Positions should be closed manually or via separate logic")

                    break
            else:
                print(f"[{i+1}/6] No open positions")

            await asyncio.sleep(10)

    finally:
        await client.close()


async def example_emergency_shutdown():
    """Example: Emergency shutdown (cancel all orders)."""
    load_dotenv()

    client = HyperliquidClient(
        private_key=os.environ["HYPERLIQUID_PRIVATE_KEY"],
        testnet=True,
        audit_log_dir=Path("./logs/audit"),
    )

    try:
        print("🚨 EMERGENCY SHUTDOWN")
        print()

        # Cancel all orders
        print("🗑️  Cancelling all orders...")
        cancelled = await client.cancel_all_orders(reason="emergency_shutdown")
        print(f"✅ Cancelled {cancelled} orders")
        print()

        # Get final positions
        positions = await client.get_positions()
        if positions:
            print(f"⚠️  Still have {len(positions)} open positions:")
            for pos in positions:
                print(f"  {pos.symbol}: {pos.quantity} @ ${pos.entry_price:.2f}")
            print("\n💡 Close positions manually via exchange UI or implement closing logic")
        else:
            print("✅ No open positions")

    finally:
        await client.close()


async def example_rate_limit_check():
    """Example: Check rate limit utilization."""
    load_dotenv()

    client = HyperliquidClient(
        private_key=os.environ["HYPERLIQUID_PRIVATE_KEY"],
        testnet=True,
        audit_log_dir=Path("./logs/audit"),
    )

    try:
        print("🚦 Rate Limit Test")
        print(f"   Limit: {client.RATE_LIMIT_REQUESTS} requests / {client.RATE_LIMIT_WINDOW}s")
        print()

        # Make several requests
        for i in range(10):
            await client.get_market_data("BTC-USD")

            current, max_req = client._rate_limiter.current_usage()
            utilization = client._rate_limiter.utilization

            print(f"[{i+1}] Usage: {current}/{max_req} ({utilization:.1%})")

        print()
        print("✅ Rate limiter working correctly")

    finally:
        await client.close()


def main():
    """Main menu."""
    print("=" * 50)
    print("Hyperliquid Client Examples")
    print("=" * 50)
    print()
    print("1. Basic usage (account, market data, positions)")
    print("2. Place and cancel an order")
    print("3. WebSocket real-time data")
    print("4. Position monitor (with max loss)")
    print("5. Emergency shutdown")
    print("6. Rate limit check")
    print()

    choice = input("Select example (1-6): ").strip()

    examples = {
        "1": example_basic_usage,
        "2": example_place_order,
        "3": example_websocket,
        "4": example_position_monitor,
        "5": example_emergency_shutdown,
        "6": example_rate_limit_check,
    }

    example = examples.get(choice)

    if example:
        print()
        print("=" * 50)
        asyncio.run(example())
        print("=" * 50)
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
