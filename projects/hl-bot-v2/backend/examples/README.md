# Position Monitor Examples

Examples demonstrating how to use the live position monitor.

## Quick Start

### 1. Simulation Mode (No API Key Required)

Run a simulation with fake fills to see how the position monitor works:

```bash
poetry run python examples/position_monitor_example.py simulate
```

This will:
- Create a position tracker
- Simulate order fills
- Show position updates
- Calculate P&L changes

**Output:**
```
Position Monitor Simulation Example
============================================================

1. Simulating order fills...

✅ Opened position: long 0.1 BTC @ $50000
📈 Price update: $50500 | P&L: $50.0
✅ Increased position: long 0.15 BTC @ $50166.67
📈 Price update: $51000 | P&L: $125.0
✅ Reduced position: long 0.05 BTC @ $50166.67
   Realized P&L: $83.33
```

### 2. Live Mode (Requires API Key)

Monitor real positions on Hyperliquid testnet:

```bash
# Set your API key
export HYPERLIQUID_PRIVATE_KEY=0x...

# Run live monitor
poetry run python examples/position_monitor_example.py
```

This will:
- Connect to Hyperliquid testnet
- Listen for order fills via WebSocket
- Update P&L every second
- Display position summary every 10 seconds

**Output:**
```
Live Position Monitor Example
============================================================

1. Initializing Hyperliquid client...
2. Initializing position tracker...
3. Initializing audit logger...
4. Creating position monitor...
5. Starting position monitor...

✅ Position monitor is running!
   - Listening for order fills via WebSocket
   - Updating prices every 1 second
   - Syncing with exchange every 60 seconds

Press Ctrl+C to stop...

============================================================
Position Summary
============================================================
Active Positions: 2
Total Exposure: $10500.0
Total P&L: $125.50
  Realized: $50.00
  Unrealized: $75.50

Positions:
  BTC-USD: long 0.1 @ $50000.0
    P&L: $50.0 ($50.0 unrealized)
  ETH-USD: short 2.0 @ $2500.0
    P&L: $75.5 ($75.5 unrealized)
```

## What to Expect

### On Fill Event

When an order fills, you'll see:

```
============================================================
Position Update: FILL
============================================================
Symbol: BTC-USD
Timestamp: 2025-02-11T17:30:00Z

Position:
  Side: long
  Quantity: 0.1
  Entry Price: $50000
  Current Price: $50000
  Unrealized P&L: $0
  Realized P&L: $0
  Total P&L: $0
  Notional Value: $5000

Fill:
  Side: buy
  Quantity: 0.1
  Price: $50000
  Fee: $5
```

### On Price Update

When market price changes:

```
============================================================
Position Update: PRICE_UPDATE
============================================================
Symbol: BTC-USD
Timestamp: 2025-02-11T17:30:05Z

Position:
  Side: long
  Quantity: 0.1
  Entry Price: $50000
  Current Price: $50500
  Unrealized P&L: $50.0
  Realized P&L: $0
  Total P&L: $50.0
  Notional Value: $5050
```

## Configuration

Set environment variables in `.env` or export them:

```bash
# Required for live mode
HYPERLIQUID_PRIVATE_KEY=0x...

# Optional
HYPERLIQUID_TESTNET=true  # Use testnet (default)
LOG_LEVEL=info            # Logging level
LOG_DIR=logs              # Log directory
```

## Troubleshooting

### "HYPERLIQUID_PRIVATE_KEY not set"

You need to set your Hyperliquid wallet private key:

```bash
export HYPERLIQUID_PRIVATE_KEY=0x1234567890abcdef...
```

Or add to `.env`:

```bash
echo "HYPERLIQUID_PRIVATE_KEY=0x..." >> .env
```

### "Position monitor not initialized"

Make sure `ENABLE_LIVE_TRADING=true` in your `.env`:

```bash
echo "ENABLE_LIVE_TRADING=true" >> .env
```

### "Connection refused"

If the WebSocket connection fails:
1. Check your internet connection
2. Verify Hyperliquid testnet is accessible
3. Check firewall settings

## Next Steps

- Read full documentation: `src/hl_bot/trading/POSITION_MONITOR_README.md`
- Integrate with frontend via WebSocket
- Add risk management with `RiskManager`
- Enable audit logging for compliance

## Safety Notes

⚠️ **Always test on testnet first!**

- Default configuration uses testnet
- Set `HYPERLIQUID_TESTNET=false` only when ready for production
- Monitor audit logs: `logs/trading/audit-*.jsonl`
- Start with small position sizes

## Support

For questions or issues:
1. Check the main README: `../README.md`
2. Read the position monitor docs: `../src/hl_bot/trading/POSITION_MONITOR_README.md`
3. Review test cases: `../tests/trading/test_position_monitor.py`
