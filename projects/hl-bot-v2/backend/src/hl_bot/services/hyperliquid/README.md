# Hyperliquid Client Wrapper

Safety-first exchange client following Trading Systems best practices.

## Features

✅ **Rate limiting** with configurable headroom (never hit the actual limit)  
✅ **Decimal precision** for all financial calculations (no floating-point errors)  
✅ **Automatic retries** with exponential backoff  
✅ **WebSocket reconnection** with exponential backoff  
✅ **Paper trading mode** for testing without real money  
✅ **Order validation** (size limits, precision checks)  
✅ **Comprehensive logging** for audit trails  

## Quick Start

### Live Trading

```python
from decimal import Decimal
from hl_bot.services.hyperliquid import HyperliquidClient, HyperliquidConfig
from hl_bot.types import OrderRequest, OrderSide, OrderType

# Initialize client
config = HyperliquidConfig(
    api_key="your-api-key",
    api_secret="your-api-secret",
    rate_limit_per_min=100,
    rate_limit_headroom=0.3,  # Use 70/min instead of 100/min
)

client = HyperliquidClient(config)

# Load symbol info (required before placing orders)
await client.load_symbol_info("BTC-USD")

# Place a market order
order_request = OrderRequest(
    symbol="BTC-USD",
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    quantity=0.1,
)

order = await client.place_order(order_request)
print(f"Order placed: {order.id} - Status: {order.status}")

# Get positions
positions = await client.get_positions()
for pos in positions:
    print(f"{pos.symbol}: {pos.quantity} @ {pos.entry_price}")
```

### Paper Trading

```python
from decimal import Decimal
from hl_bot.services.hyperliquid.paper_trading import PaperTradingEngine
from hl_bot.types import OrderRequest, OrderSide, OrderType

# Initialize paper trading engine
engine = PaperTradingEngine(
    initial_balance=Decimal("10000.0"),
    leverage=1.0,
)

# Place order (no real money!)
order_request = OrderRequest(
    symbol="BTC-USD",
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    quantity=0.1,
)

current_price = Decimal("50000")
order = await engine.place_order(order_request, current_price)

# Update price to simulate market movement
await engine.update_market_price("BTC-USD", Decimal("51000"))

# Check P&L
positions = engine.get_positions()
for pos in positions:
    print(f"{pos.symbol}: P&L = ${pos.unrealized_pnl:.2f}")
```

### WebSocket Market Data

```python
from hl_bot.services.hyperliquid import MarketDataFeed

# Define subscriptions
subscriptions = [
    {"type": "subscribe", "channel": "trades", "symbol": "BTC-USD"},
    {"type": "subscribe", "channel": "orderbook", "symbol": "BTC-USD"},
]

feed = MarketDataFeed(
    url="wss://api.hyperliquid.xyz/ws",
    subscriptions=subscriptions,
)

# Register message handler
async def handle_message(message: dict) -> None:
    if message.get("channel") == "trades":
        print(f"Trade: {message}")
    elif message.get("channel") == "orderbook":
        print(f"Orderbook update: {message}")

feed.on_message(handle_message)

# Start feed (reconnects automatically on disconnect)
await feed.start()
```

## Safety Features

### Rate Limiting

The client enforces rate limits with configurable headroom to prevent getting banned:

```python
# Exchange allows 100 requests/min
# With 30% headroom, client uses 70 requests/min
config = HyperliquidConfig(
    rate_limit_per_min=100,
    rate_limit_headroom=0.3,
)
```

### Decimal Precision

All prices and quantities use `Decimal` to avoid floating-point errors:

```python
# ❌ BAD: float arithmetic
price = 0.1 + 0.2  # = 0.30000000000000004

# ✅ GOOD: Decimal arithmetic
from decimal import Decimal
price = Decimal("0.1") + Decimal("0.2")  # = 0.3 (exact!)
```

The client automatically rounds prices and quantities to exchange precision:

```python
await client.load_symbol_info("BTC-USD")

# Rounds to valid tick size (e.g., 0.1 for BTC-USD)
rounded_price = client.round_price("BTC-USD", Decimal("50123.456"))
# => Decimal("50123.4")

# Rounds to valid lot size (e.g., 0.001 for BTC-USD)
rounded_qty = client.round_quantity("BTC-USD", Decimal("0.12345"))
# => Decimal("0.123")
```

### Order Validation

Orders are validated before submission:

- Minimum order size check
- Maximum order size check
- Price precision rounding
- Quantity precision rounding

```python
# Raises ValueError if quantity < min_order_size
await client.place_order(order_request)
```

### Error Handling

The client retries transient errors with exponential backoff:

```python
# Retries on:
# - Network timeouts (up to max_retries)
# - 5xx server errors (up to max_retries)
# - 429 rate limit (waits for Retry-After header)

# Fails immediately on:
# - 4xx client errors (bad request, unauthorized, etc.)
```

### Automatic Reconnection

WebSocket connections reconnect automatically with exponential backoff:

```python
feed = MarketDataFeed(
    url="wss://api.hyperliquid.xyz/ws",
    subscriptions=[...],
    reconnect_delay=1.0,        # Initial delay
    max_reconnect_delay=60.0,   # Cap on exponential backoff
)

# Reconnects automatically on:
# - ConnectionClosed
# - WebSocketException
# - Network errors
```

## Best Practices

### 1. Always Test with Paper Trading First

```python
# ✅ Test strategy with paper trading
engine = PaperTradingEngine(initial_balance=Decimal("10000"))
# ... run strategy ...
# ... verify P&L makes sense ...

# ✅ Only then use live trading
client = HyperliquidClient(config)
```

### 2. Load Symbol Info Before Trading

```python
# ✅ Load symbol info once at startup
await client.load_symbol_info("BTC-USD")
await client.load_symbol_info("ETH-USD")

# Now orders will use correct precision
await client.place_order(order_request)
```

### 3. Handle Errors Gracefully

```python
try:
    order = await client.place_order(order_request)
except ValueError as e:
    logger.error(f"Order validation failed: {e}")
except httpx.HTTPStatusError as e:
    logger.error(f"Exchange rejected order: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Trigger circuit breaker, cancel orders, etc.
```

### 4. Use Callbacks for Paper Trading Events

```python
engine = PaperTradingEngine(initial_balance=Decimal("10000"))

# Track fills
async def on_fill(order: Order) -> None:
    logger.info(f"Order filled: {order.id} @ {order.average_fill_price}")

engine.on_fill(on_fill)
```

### 5. Monitor Rate Limit Usage

```python
# Check current usage (for metrics/monitoring)
usage = client._rate_limiter.current_usage
capacity = client._rate_limiter.capacity
print(f"Rate limit: {usage}/{capacity}")
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  HyperliquidClient                       │
├─────────────────────────────────────────────────────────┤
│  - Rate limiter (70/min with 30% headroom)              │
│  - Decimal precision (round_price, round_quantity)      │
│  - Order validation (min/max size checks)               │
│  - Auto-retry with exponential backoff                  │
│  - HMAC-SHA256 request signing                          │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ REST API     │   │  WebSocket   │   │    Paper     │
│ (httpx)      │   │   Feed       │   │   Trading    │
│              │   │              │   │              │
│ - place_order│   │ - subscribe  │   │ - simulate   │
│ - cancel     │   │ - reconnect  │   │ - track P&L  │
│ - positions  │   │ - callbacks  │   │ - no risk    │
└──────────────┘   └──────────────┘   └──────────────┘
```

## Testing

Run the test suite:

```bash
cd backend
poetry install
poetry run pytest tests/unit/test_hyperliquid_client.py -v
```

Tests cover:
- Rate limiting behavior
- Decimal precision (no float errors)
- Paper trading simulation
- Order validation
- Position tracking
- P&L calculation

## Changelog

### v0.1.0 (2025-02-11)

Initial implementation:
- REST API client with rate limiting
- WebSocket market data feed
- Paper trading engine
- Decimal precision for prices/quantities
- Order validation
- Comprehensive test coverage

## License

Part of hl-bot-v2 project.
