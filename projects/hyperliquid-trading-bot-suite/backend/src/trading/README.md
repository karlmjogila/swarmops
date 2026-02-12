# Hyperliquid MCP Client

A comprehensive client for interacting with the Hyperliquid DEX through the MCP (Model Context Protocol) interface. Supports both paper trading (simulation) and live trading modes.

## Features

### Core Functionality
- **Paper Trading**: Full simulation mode with realistic order handling and position tracking
- **Live Trading**: Real order execution on Hyperliquid DEX
- **Order Management**: Market, limit, stop, and stop-limit orders
- **Position Tracking**: Real-time position updates and P&L calculation
- **Balance Management**: Account balance monitoring and updates
- **Market Data**: Real-time price and volume data
- **Error Handling**: Comprehensive error handling with retry logic

### Connection Management
- **WebSocket**: Real-time data streaming for live trading
- **HTTP API**: RESTful API for order placement and account queries
- **Auto-Reconnection**: Automatic reconnection on connection loss
- **Health Checks**: Connection health monitoring

### Safety Features
- **Risk Management**: Built-in position and order size limits
- **Authentication**: Secure API key and signature-based authentication
- **Validation**: Comprehensive order parameter validation
- **Logging**: Detailed logging for debugging and audit trails

## Quick Start

### Paper Trading (Recommended for Testing)

```python
import asyncio
from backend.src.config import HyperliquidConfig
from backend.src.types import OrderSide, OrderType, TradingMode
from backend.src.trading import HyperliquidClient

async def paper_trading_example():
    config = HyperliquidConfig()
    
    async with HyperliquidClient(config, TradingMode.PAPER) as client:
        # Place a market buy order
        order = await client.place_order(
            asset="ETH-USD",
            size=1.0,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            metadata={"strategy": "my_strategy"}
        )
        print(f"Order placed: {order.id}")
        
        # Check positions
        positions = await client.get_positions()
        print(f"Current positions: {len(positions)}")
        
        # Place a limit sell order
        limit_order = await client.place_order(
            asset="ETH-USD",
            size=0.5,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=3600.0
        )
        print(f"Limit order placed: {limit_order.id}")

asyncio.run(paper_trading_example())
```

### Live Trading (Requires API Keys)

```python
async def live_trading_example():
    config = HyperliquidConfig(
        private_key="your_private_key",
        wallet_address="your_wallet_address"
    )
    
    async with HyperliquidClient(config, TradingMode.LIVE) as client:
        # Health check
        if not await client.health_check():
            print("Connection unhealthy!")
            return
        
        # Place order
        order = await client.place_order(
            asset="ETH-USD",
            size=0.01,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=3000.0
        )
        
        # Cancel if still pending after 30 seconds
        await asyncio.sleep(30)
        if order.status == "pending":
            await client.cancel_order(order.id)
```

### Event-Driven Trading with Callbacks

```python
async def callback_example():
    def on_order_fill(order):
        print(f"Order filled: {order.id} at {order.avg_fill_price}")
    
    def on_position_change(position):
        print(f"Position updated: {position.asset} size={position.size}")
    
    config = HyperliquidConfig()
    
    async with HyperliquidClient(config, TradingMode.PAPER) as client:
        client.add_order_callback(on_order_fill)
        client.add_position_callback(on_position_change)
        
        # Your trading logic here
        await client.place_order("BTC-USD", 0.1, OrderSide.BUY, OrderType.MARKET)
```

## Configuration

### Environment Variables

```bash
# API Settings
HYPERLIQUID_BASE_URL=https://api.hyperliquid.xyz
HYPERLIQUID_WEBSOCKET_URL=wss://api.hyperliquid.xyz/ws

# Authentication (for live trading)
HYPERLIQUID_PRIVATE_KEY=your_private_key
HYPERLIQUID_WALLET_ADDRESS=your_wallet_address

# Trading Limits
HYPERLIQUID_MAX_POSITION_SIZE=1000.0
HYPERLIQUID_MAX_ORDER_VALUE=10000.0
HYPERLIQUID_MAX_DAILY_LOSS=1000.0
HYPERLIQUID_MAX_CONCURRENT_POSITIONS=10

# Connection Settings
HYPERLIQUID_CONNECTION_TIMEOUT=30
HYPERLIQUID_MAX_RETRIES=3
HYPERLIQUID_RETRY_DELAY=5
HYPERLIQUID_HEARTBEAT_INTERVAL=30
```

### Python Configuration

```python
from backend.src.config import HyperliquidConfig

config = HyperliquidConfig(
    private_key="your_key",
    wallet_address="your_address",
    max_position_size=500.0,
    max_concurrent_positions=5,
    default_trading_mode="paper"  # or "live"
)
```

## API Reference

### HyperliquidClient

#### Constructor
```python
HyperliquidClient(config: HyperliquidConfig, mode: TradingMode = TradingMode.PAPER)
```

#### Connection Methods
- `connect()` - Establish connection to Hyperliquid
- `disconnect()` - Close connection
- `is_connected` - Check connection status
- `health_check()` - Verify connection health

#### Trading Methods
- `place_order(asset, size, side, order_type, price=None, stop_price=None, metadata=None)` - Place order
- `cancel_order(order_id)` - Cancel existing order
- `get_order(order_id)` - Get order by ID
- `get_orders(asset=None)` - Get all orders, optionally filtered by asset

#### Position Methods
- `get_positions()` - Get all positions
- `get_position(asset)` - Get position for specific asset

#### Account Methods
- `get_balances()` - Get account balances
- `get_market_data(asset)` - Get market data for asset

#### Callback Methods
- `add_order_callback(callback)` - Add order update callback
- `add_position_callback(callback)` - Add position update callback
- `remove_order_callback(callback)` - Remove order callback
- `remove_position_callback(callback)` - Remove position callback

### Data Types

#### Order
```python
@dataclass
class Order:
    id: str
    asset: str
    size: float
    price: Optional[float]
    side: OrderSide  # BUY or SELL
    order_type: OrderType  # MARKET, LIMIT, STOP, STOP_LIMIT
    status: OrderStatus  # PENDING, FILLED, PARTIAL, CANCELLED, REJECTED
    filled_size: float
    avg_fill_price: Optional[float]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    metadata: Dict[str, Any]
```

#### Position
```python
@dataclass
class Position:
    asset: str
    size: float
    avg_price: float
    unrealized_pnl: float
    realized_pnl: float
    side: OrderSide
    created_at: datetime
    updated_at: datetime
```

## Error Handling

The client provides specific exception types for different error conditions:

```python
from backend.src.trading.hyperliquid_client import HyperliquidError, ConnectionError, OrderError

try:
    async with HyperliquidClient(config, TradingMode.LIVE) as client:
        order = await client.place_order("ETH-USD", 1.0, OrderSide.BUY, OrderType.MARKET)
        
except ConnectionError as e:
    print(f"Connection failed: {e}")
except OrderError as e:
    print(f"Order failed: {e}")
except HyperliquidError as e:
    print(f"Hyperliquid error: {e}")
```

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
pytest backend/tests/trading/test_hyperliquid_client.py -v

# Run with coverage
pytest backend/tests/trading/test_hyperliquid_client.py --cov=backend.src.trading --cov-report=html
```

## Security Considerations

### For Live Trading
1. **Never commit API keys** to version control
2. **Use environment variables** for sensitive configuration
3. **Start with paper trading** to test strategies
4. **Use small position sizes** when testing live
5. **Monitor logs** for unusual activity
6. **Set strict risk limits** in configuration

### Best Practices
1. **Always use the context manager** (`async with`) for automatic cleanup
2. **Implement proper error handling** for all trading operations
3. **Log all trading activity** for audit purposes
4. **Test thoroughly in paper mode** before live trading
5. **Monitor connection health** and implement reconnection logic
6. **Use callbacks** for event-driven trading logic

## Contributing

When contributing to the Hyperliquid client:

1. **Add tests** for new functionality
2. **Update documentation** for API changes
3. **Follow the existing code style** (black, isort, flake8)
4. **Test both paper and live modes** (where applicable)
5. **Handle edge cases** and error conditions
6. **Add appropriate logging** for debugging

## Roadmap

Future enhancements planned:

- [ ] Advanced order types (OCO, trailing stops)
- [ ] Portfolio-level risk management
- [ ] Multiple exchange support
- [ ] Performance optimizations for high-frequency trading
- [ ] Enhanced market data feeds
- [ ] Strategy backtesting integration
- [ ] Web dashboard for monitoring

## Support

For issues or questions:

1. Check the test suite for usage examples
2. Review the implementation plan in `specs/IMPLEMENTATION_PLAN.md`
3. Check logs for error details
4. Create an issue with reproduction steps

---

*This client is part of the Hyperliquid Trading Bot Suite - an AI-powered trading system that learns strategies from educational content and executes trades via pattern detection.*