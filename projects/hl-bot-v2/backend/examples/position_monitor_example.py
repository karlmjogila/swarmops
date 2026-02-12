"""Live Position Monitor Example

Demonstrates how to use the position monitor for real-time position tracking.

Run this example:
    poetry run python examples/position_monitor_example.py
"""

import asyncio
import os
from decimal import Decimal
from pathlib import Path

from hl_bot.trading.audit_logger import AuditLogger
from hl_bot.trading.hyperliquid import HyperliquidClient
from hl_bot.trading.position import Fill, PositionTracker
from hl_bot.trading.position_monitor import PositionMonitor, PositionUpdate


async def position_callback(update: PositionUpdate) -> None:
    """Handle position updates.

    Args:
        update: Position update event
    """
    print(f"\n{'='*60}")
    print(f"Position Update: {update.event_type.upper()}")
    print(f"{'='*60}")
    print(f"Symbol: {update.symbol}")
    print(f"Timestamp: {update.timestamp}")
    
    pos = update.position
    print(f"\nPosition:")
    print(f"  Side: {pos.side}")
    print(f"  Quantity: {pos.quantity}")
    print(f"  Entry Price: ${pos.entry_price}")
    print(f"  Current Price: ${pos.current_price}")
    print(f"  Unrealized P&L: ${pos.unrealized_pnl}")
    print(f"  Realized P&L: ${pos.realized_pnl}")
    print(f"  Total P&L: ${pos.total_pnl}")
    print(f"  Notional Value: ${pos.notional_value}")
    
    if update.fill:
        print(f"\nFill:")
        print(f"  Side: {update.fill.side}")
        print(f"  Quantity: {update.fill.quantity}")
        print(f"  Price: ${update.fill.price}")
        print(f"  Fee: ${update.fill.fee}")


async def main() -> None:
    """Main example function."""
    print("Live Position Monitor Example")
    print("=" * 60)
    
    # Check for API key
    private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
    if not private_key:
        print("\n❌ HYPERLIQUID_PRIVATE_KEY not set in environment")
        print("Set it in .env or export it:")
        print("  export HYPERLIQUID_PRIVATE_KEY=0x...")
        return
    
    # Initialize components
    print("\n1. Initializing Hyperliquid client...")
    hl_client = HyperliquidClient(
        private_key=private_key,
        testnet=True,  # Use testnet for safety
        audit_log_dir=Path("logs/trading"),
    )
    
    print("2. Initializing position tracker...")
    position_tracker = PositionTracker()
    
    print("3. Initializing audit logger...")
    audit_logger = AuditLogger(Path("logs/trading"))
    
    print("4. Creating position monitor...")
    monitor = PositionMonitor(
        hyperliquid_client=hl_client,
        position_tracker=position_tracker,
        audit_logger=audit_logger,
        update_interval=1.0,  # Update every second
    )
    
    # Register callback
    monitor.on_position_update(position_callback)
    
    # Start monitoring
    print("5. Starting position monitor...\n")
    await monitor.start()
    
    print("✅ Position monitor is running!")
    print("   - Listening for order fills via WebSocket")
    print("   - Updating prices every 1 second")
    print("   - Syncing with exchange every 60 seconds")
    print("\nPress Ctrl+C to stop...\n")
    
    try:
        # Display position summary every 10 seconds
        while True:
            await asyncio.sleep(10)
            
            summary = monitor.get_position_summary()
            print(f"\n{'='*60}")
            print("Position Summary")
            print(f"{'='*60}")
            print(f"Active Positions: {summary['active_positions']}")
            print(f"Total Exposure: ${summary['total_exposure']}")
            print(f"Total P&L: ${summary['total_pnl']}")
            print(f"  Realized: ${summary['realized_pnl']}")
            print(f"  Unrealized: ${summary['unrealized_pnl']}")
            
            if summary['positions']:
                print("\nPositions:")
                for symbol, pos in summary['positions'].items():
                    print(f"  {symbol}: {pos['side']} {pos['quantity']} @ ${pos['entry_price']}")
                    print(f"    P&L: ${pos['total_pnl']} (${pos['unrealized_pnl']} unrealized)")
            
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    
    finally:
        # Stop monitoring
        await monitor.stop()
        print("✅ Position monitor stopped")


async def simulation_example() -> None:
    """Example with simulated fills (no real trading).
    
    This demonstrates the position monitor without connecting to the exchange.
    Useful for testing and development.
    """
    print("Position Monitor Simulation Example")
    print("=" * 60)
    
    # Create position tracker
    position_tracker = PositionTracker()
    
    # Simulate some fills
    print("\n1. Simulating order fills...\n")
    
    # Buy 0.1 BTC at $50,000
    fill1 = Fill(
        symbol="BTC-USD",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
        timestamp=asyncio.get_event_loop().time(),
        order_id="order1",
        fill_id="fill1",
        fee=Decimal("5"),
    )
    
    pos1 = position_tracker.update_from_fill(fill1)
    print(f"✅ Opened position: {pos1.side} {pos1.quantity} BTC @ ${pos1.entry_price}")
    
    # Price moves to $50,500
    pos1.update_price(Decimal("50500"))
    print(f"📈 Price update: ${pos1.current_price} | P&L: ${pos1.unrealized_pnl}")
    
    # Buy 0.05 more BTC at $50,500 (increase position)
    fill2 = Fill(
        symbol="BTC-USD",
        side="buy",
        quantity=Decimal("0.05"),
        price=Decimal("50500"),
        timestamp=asyncio.get_event_loop().time(),
        order_id="order2",
        fill_id="fill2",
        fee=Decimal("2.5"),
    )
    
    pos2 = position_tracker.update_from_fill(fill2)
    print(f"✅ Increased position: {pos2.side} {pos2.quantity} BTC @ ${pos2.entry_price}")
    
    # Price moves to $51,000
    pos2.update_price(Decimal("51000"))
    print(f"📈 Price update: ${pos2.current_price} | P&L: ${pos2.unrealized_pnl}")
    
    # Sell 0.1 BTC at $51,000 (reduce position)
    fill3 = Fill(
        symbol="BTC-USD",
        side="sell",
        quantity=Decimal("0.1"),
        price=Decimal("51000"),
        timestamp=asyncio.get_event_loop().time(),
        order_id="order3",
        fill_id="fill3",
        fee=Decimal("5"),
    )
    
    pos3 = position_tracker.update_from_fill(fill3)
    print(f"✅ Reduced position: {pos3.side} {pos3.quantity} BTC @ ${pos3.entry_price}")
    print(f"   Realized P&L: ${pos3.realized_pnl}")
    
    # Display final summary
    print(f"\n{'='*60}")
    print("Final Position Summary")
    print(f"{'='*60}")
    print(f"Symbol: {pos3.symbol}")
    print(f"Side: {pos3.side}")
    print(f"Quantity: {pos3.quantity}")
    print(f"Entry Price: ${pos3.entry_price}")
    print(f"Current Price: ${pos3.current_price}")
    print(f"Realized P&L: ${pos3.realized_pnl}")
    print(f"Unrealized P&L: ${pos3.unrealized_pnl}")
    print(f"Total P&L: ${pos3.total_pnl}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "simulate":
        # Run simulation (no real trading)
        asyncio.run(simulation_example())
    else:
        # Run live monitor (requires API key)
        asyncio.run(main())
