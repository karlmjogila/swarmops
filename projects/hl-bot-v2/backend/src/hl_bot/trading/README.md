# Hyperliquid Trading Client

Production-ready Hyperliquid DEX client with comprehensive safety features.

## Features

### 🛡️ Safety First

- **Rate Limiting**: 70 requests/min (30% headroom below 100/min limit)
- **Decimal Precision**: All prices and quantities use `Decimal` (never `float`)
- **Audit Logging**: Every order, fill, and error is logged to append-only JSONL files
- **Automatic Retries**: Exponential backoff on timeouts and 5xx errors
- **Error Handling**: Comprehensive error types and logging

### 🔌 Connectivity

- **REST API**: Authenticated requests with signature verification
- **WebSocket**: Auto-reconnecting WebSocket for real-time data
- **Testnet/Mainnet**: Easy switching between environments

### 📊 Order Management

- **Order Types**: Market, Limit, Stop Loss, Take Profit
- **Position Management**: Query positions, calculate P&L
- **Bulk Operations**: Cancel all orders (emergency shutdown)

## Installation

Add dependencies to `pyproject.toml`:

```toml
httpx = "^0.27.0"
websockets = "^14.1"
eth-account = "^0.13.0"
aiofiles = "^24.1.0"
```

## Usage

### Basic Setup

```python
from hl_bot.trading import HyperliquidClient
from hl_bot.types import OrderRequest, OrderSide, OrderType

# Initialize client (testnet)
client = HyperliquidClient(
    private_key="0x...",  # Your Ethereum private key
    testnet=True,
    audit_log_dir="./logs/audit",
)

print(f"Connected as: {client.address}")
```

### Place an Order

```python
from decimal import Decimal

# Create order request
order_request = OrderRequest(
    symbol="BTC-USD",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    quantity=0.1,
    price=50000.0,
    post_only=True,  # Maker-only
)

# Place order (automatically rounded to exchange precision)
order = await client.place_order(order_request)
print(f"Order placed: {order.id}")
```

### Get Positions

```python
# Get all open positions
positions = await client.get_positions()

for pos in positions:
    print(f"{pos.symbol}: {pos.quantity} @ {pos.entry_price}")
    print(f"  Unrealized P&L: ${pos.unrealized_pnl:.2f}")
```

### Cancel Orders

```python
# Cancel specific order
await client.cancel_order(order_id="abc123", symbol="BTC-USD")

# Emergency: cancel ALL orders
await client.cancel_all_orders(reason="emergency_shutdown")
```

### WebSocket (Real-time Data)

```python
async def handle_message(message):
    if message["type"] == "trade":
        print(f"Trade: {message['data']}")

# Register callback
client.on_message(handle_message)

# Start WebSocket
subscriptions = [
    {"type": "subscribe", "channel": "trades", "symbol": "BTC-USD"},
    {"type": "subscribe", "channel": "positions"},
]

await client.start_websocket(subscriptions)
```

### Decimal Precision

**NEVER use `float` for financial calculations!**

```python
from decimal import Decimal

# ❌ WRONG - Float has precision errors
price = 0.1 + 0.2  # = 0.30000000000000004

# ✅ CORRECT - Decimal is exact
price = Decimal("0.1") + Decimal("0.2")  # = 0.3

# Client handles rounding automatically
rounded_price = client.round_price("BTC-USD", Decimal("123.456789"))
# Result: Decimal("123.45")  (tick size = 0.01)

rounded_qty = client.round_quantity("BTC-USD", Decimal("0.123456"))
# Result: Decimal("0.123")  (lot size = 0.001)
```

### Account State

```python
account = await client.get_account_state()
print(f"Balance: ${account['balance']:.2f}")
print(f"Margin Used: ${account['marginUsed']:.2f}")
```

### Market Data

```python
market = await client.get_market_data("BTC-USD")
print(f"Last Price: ${market['lastPx']:.2f}")
print(f"24h Volume: {market['volume24h']}")
```

## Safety Features

### Rate Limiting

The client enforces 70 requests/minute (30% below the exchange limit of 100/min):

```python
# Automatically rate-limited
for i in range(100):
    await client.get_market_data("BTC-USD")  # Will slow down automatically

# Check current utilization
print(f"Rate limit usage: {client._rate_limiter.utilization:.1%}")
```

### Audit Trail

Every operation is logged to `./logs/audit/audit-YYYY-MM-DD.jsonl`:

```json
{"timestamp": "2024-01-01T12:00:00Z", "type": "order_submitted", "symbol": "BTC-USD", ...}
{"timestamp": "2024-01-01T12:00:01Z", "type": "order_filled", "order": {...}, "fill": {...}}
{"timestamp": "2024-01-01T12:05:00Z", "type": "risk_rejection", "reason": "Daily loss limit"}
```

This allows you to reconstruct **exactly** what happened and when.

### Error Handling

```python
from hl_bot.trading.hyperliquid import (
    HyperliquidError,
    HyperliquidOrderError,
    HyperliquidRateLimitError,
    HyperliquidConnectionError,
)

try:
    order = await client.place_order(order_request)
except HyperliquidOrderError as e:
    print(f"Order rejected: {e}")
except HyperliquidRateLimitError as e:
    print(f"Rate limited: {e}")
except HyperliquidConnectionError as e:
    print(f"Connection failed: {e}")
except HyperliquidError as e:
    print(f"General error: {e}")
```

### Automatic Retries

The client retries failed requests with exponential backoff:

- **Timeouts**: Retry 3 times with 1s, 2s, 4s delays
- **5xx Errors**: Retry 3 times with backoff
- **429 Rate Limit**: Wait for `Retry-After` header and retry

### WebSocket Reconnection

WebSocket automatically reconnects on disconnect:

```python
# Start WebSocket (runs forever, auto-reconnects)
await client.start_websocket(subscriptions)

# Stop when done
await client.stop_websocket()
```

## Production Checklist

Before going live:

- [ ] **Never hardcode private keys** — use environment variables
- [ ] **Test on testnet first** — verify all functionality
- [ ] **Set up monitoring** — watch audit logs for errors
- [ ] **Configure rate limits** — ensure headroom for your trading frequency
- [ ] **Implement circuit breaker** — stop trading on consecutive errors
- [ ] **Daily loss limit** — enforce max loss per day
- [ ] **Position size limits** — prevent fat-finger orders
- [ ] **Review audit logs daily** — check for anomalies

## Environment Variables

```bash
# .env file
HYPERLIQUID_PRIVATE_KEY=0x...
HYPERLIQUID_TESTNET=true
AUDIT_LOG_DIR=./logs/audit
```

```python
import os
from pathlib import Path

client = HyperliquidClient(
    private_key=os.environ["HYPERLIQUID_PRIVATE_KEY"],
    testnet=os.environ.get("HYPERLIQUID_TESTNET", "true").lower() == "true",
    audit_log_dir=Path(os.environ.get("AUDIT_LOG_DIR", "./logs/audit")),
)
```

## Testing

Run tests:

```bash
cd backend
poetry run pytest tests/unit/test_hyperliquid_client.py -v
```

Key tests:
- Rate limiting enforcement
- Decimal precision (no float errors)
- Audit logging
- Retry logic
- WebSocket callbacks

## Architecture

```
HyperliquidClient
├── RateLimiter (70 req/min with headroom)
├── AuditLogger (append-only JSONL logs)
├── REST API (signed requests, retries, timeouts)
└── WebSocket (auto-reconnect, callbacks)
```

## Hyperliquid API Reference

- **Docs**: https://hyperliquid.gitbook.io/hyperliquid-docs/
- **Mainnet**: https://api.hyperliquid.xyz
- **Testnet**: https://api.hyperliquid-testnet.xyz

## Common Patterns

### Emergency Shutdown

```python
async def emergency_shutdown(client: HyperliquidClient):
    """Cancel all orders and close WebSocket."""
    try:
        # Cancel all orders
        cancelled = await client.cancel_all_orders(reason="emergency")
        print(f"Cancelled {cancelled} orders")
        
        # Stop WebSocket
        await client.stop_websocket()
        
        # Close client
        await client.close()
        
        print("Emergency shutdown complete")
    except Exception as e:
        print(f"Emergency shutdown failed: {e}")
        # Log and alert
```

### Position Monitor

```python
async def monitor_positions(client: HyperliquidClient):
    """Monitor positions and enforce max loss."""
    while True:
        positions = await client.get_positions()
        
        total_pnl = sum(p.unrealized_pnl for p in positions)
        
        if total_pnl < -1000:  # Max loss: $1000
            print("Max loss reached, closing all positions")
            await client.cancel_all_orders(reason="max_loss")
            # Close positions...
            break
        
        await asyncio.sleep(10)
```

### Real-time Trade Monitor

```python
async def trade_monitor(client: HyperliquidClient):
    """Monitor trades via WebSocket."""
    async def on_trade(message):
        if message.get("type") == "trade":
            trade = message["data"]
            print(f"Trade: {trade['symbol']} {trade['side']} {trade['quantity']} @ {trade['price']}")
    
    client.on_message(on_trade)
    
    await client.start_websocket([
        {"type": "subscribe", "channel": "trades"},
    ])
```

## Troubleshooting

### "Rate limit exceeded"

- Check `client._rate_limiter.utilization`
- Reduce request frequency
- Increase `RATE_LIMIT_REQUESTS` (max 80-90 for safety)

### "Signature verification failed"

- Verify private key is correct
- Check system clock is synchronized
- Ensure proper message formatting

### "Order rejected"

- Check audit logs for reason
- Verify price/quantity are within limits
- Check account balance and margin

### WebSocket keeps disconnecting

- Check network stability
- Review audit logs for error patterns
- Ensure subscriptions are valid

## License

MIT
