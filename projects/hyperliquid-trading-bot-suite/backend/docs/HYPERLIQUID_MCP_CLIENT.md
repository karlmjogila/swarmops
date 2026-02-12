# Hyperliquid MCP Client

The Hyperliquid MCP (Model Context Protocol) client provides a structured interface for AI agents to interact with the Hyperliquid DEX for trading operations.

## Overview

The MCP client consists of two main components:

1. **HyperliquidClient** - Low-level client for direct trading operations
2. **HyperliquidMCPServer** - MCP server that exposes trading functionality as structured tools

## Architecture

```
AI Agent/LLM
    ↓
MCP Protocol
    ↓
HyperliquidMCPServer
    ↓
HyperliquidClient
    ↓
Hyperliquid DEX
```

## Features

### Trading Modes

- **Paper Trading**: Simulated trading for testing and development
- **Live Trading**: Real trading on Hyperliquid testnet/mainnet

### Supported Operations

- Place orders (market, limit, stop)
- Cancel orders
- Get positions
- Get account balances
- Get market data
- Real-time updates via WebSocket

### MCP Tools

The server exposes the following tools for AI agents:

1. `place_order` - Place trading orders
2. `cancel_order` - Cancel existing orders  
3. `get_positions` - Retrieve current positions
4. `get_orders` - Get order history and status
5. `get_balances` - Get account balances
6. `get_market_data` - Get real-time market data

## Quick Start

### Paper Trading

```python
from backend.src.trading import create_mcp_server
from backend.src.types import TradingMode

# Create MCP server for paper trading
async with await create_mcp_server() as server:
    # Place a market order
    result = await server.execute_tool("place_order", {
        "asset": "ETH-USD",
        "size": 1.0,
        "side": "buy",
        "order_type": "market"
    })
    
    print(f"Order result: {result}")
    
    # Get positions
    positions = await server.execute_tool("get_positions", {})
    print(f"Positions: {positions}")
```

### Live Trading

```python
from backend.src.config import HyperliquidConfig
from backend.src.trading import create_mcp_server
from backend.src.types import TradingMode

# Configure for live trading
config = HyperliquidConfig(
    private_key="your_private_key_hex",
    wallet_address="your_wallet_address",
    testnet=True  # Use testnet for testing
)

async with await create_mcp_server(config, TradingMode.LIVE) as server:
    # Check health before trading
    health = await server.health_check()
    if health["healthy"]:
        # Place order...
        pass
```

## Configuration

### Environment Variables

```bash
# Hyperliquid Configuration
HYPERLIQUID_API_URL=https://api.hyperliquid.xyz
HYPERLIQUID_PRIVATE_KEY=your_private_key_in_hex
HYPERLIQUID_WALLET_ADDRESS=your_wallet_address
HYPERLIQUID_TESTNET=true
```

### Configuration Classes

```python
from backend.src.config import HyperliquidConfig

# Paper trading (no credentials needed)
config = HyperliquidConfig.for_paper_trading()

# Live trading with credentials
config = HyperliquidConfig(
    private_key="0x...",
    wallet_address="0x...",
    testnet=True
)

# From application settings
config = HyperliquidConfig.from_settings()
```

## Tool Schemas

### place_order

```json
{
  "name": "place_order",
  "description": "Place a trading order on Hyperliquid",
  "inputSchema": {
    "type": "object",
    "properties": {
      "asset": {"type": "string", "description": "Trading symbol (e.g., 'ETH-USD')"},
      "size": {"type": "number", "description": "Order size"},
      "side": {"type": "string", "enum": ["buy", "sell"]},
      "order_type": {"type": "string", "enum": ["market", "limit", "stop", "stop_limit"]},
      "price": {"type": "number", "description": "Limit price (for limit orders)"},
      "stop_price": {"type": "number", "description": "Stop price (for stop orders)"},
      "metadata": {"type": "object", "description": "Additional metadata"}
    },
    "required": ["asset", "size", "side"]
  }
}
```

### get_positions

```json
{
  "name": "get_positions",
  "description": "Get current trading positions",
  "inputSchema": {
    "type": "object",
    "properties": {
      "asset": {"type": "string", "description": "Filter by asset (optional)"}
    }
  }
}
```

### cancel_order

```json
{
  "name": "cancel_order",
  "description": "Cancel an existing order",
  "inputSchema": {
    "type": "object",
    "properties": {
      "order_id": {"type": "string", "description": "Order ID to cancel"}
    },
    "required": ["order_id"]
  }
}
```

## AI Agent Integration

### Example AI Trading Agent

```python
class AITradingAgent:
    def __init__(self, mcp_server):
        self.mcp_server = mcp_server
    
    async def execute_strategy(self, asset: str):
        # Analyze market
        market_data = await self.mcp_server.execute_tool(
            "get_market_data", {"asset": asset}
        )
        
        # Check current position
        positions = await self.mcp_server.execute_tool(
            "get_positions", {"asset": asset}
        )
        
        # Make trading decision based on analysis
        if self.should_buy(market_data, positions):
            await self.mcp_server.execute_tool("place_order", {
                "asset": asset,
                "size": 1.0,
                "side": "buy",
                "order_type": "market"
            })
    
    def should_buy(self, market_data, positions):
        # Implement your trading logic here
        return True
```

### Integration with LLM

The MCP server can be integrated with Large Language Models by providing the tool schemas:

```python
# Get available tools for LLM
tools = server.get_available_tools()

# Each tool contains:
# - name: Tool identifier
# - description: Human-readable description
# - inputSchema: JSON schema for parameters

# These can be provided to LLMs like Claude or GPT-4 for function calling
```

## Error Handling

All MCP tools return structured responses:

```python
# Success response
{
    "success": True,
    "order": {...},  # Tool-specific data
    # ... other fields
}

# Error response
{
    "success": False,
    "error": "Error description"
}
```

## Security Considerations

### Paper Trading
- No real funds at risk
- Perfect for testing and development
- Simulated market conditions

### Live Trading
- Requires proper private key management
- Always start with testnet
- Implement proper risk management
- Monitor position sizes and exposure

### Best Practices

1. **Always validate credentials** before live trading
2. **Use testnet first** for any new strategy
3. **Implement position limits** and risk controls
4. **Monitor API rate limits** 
5. **Log all trading operations** for audit trails
6. **Use secure key storage** (environment variables, key vaults)

## Testing

### Unit Tests

```bash
# Run client tests
python -m pytest tests/trading/test_hyperliquid_client.py -v

# Run MCP server tests  
python -m pytest tests/trading/test_mcp_server.py -v
```

### Integration Tests

```python
# Test with paper trading
async def test_integration():
    async with await create_mcp_server() as server:
        # Test complete trading flow
        result = await server.execute_tool("place_order", {
            "asset": "ETH-USD", "size": 1.0, "side": "buy"
        })
        assert result["success"]
```

## Examples

See the following files for comprehensive examples:

- `backend/src/trading/example_usage.py` - Basic client usage
- `backend/src/trading/mcp_example.py` - MCP server and AI agent examples

## API Reference

### HyperliquidClient

The low-level trading client with full async support.

#### Methods

- `connect()` - Establish connection to Hyperliquid
- `disconnect()` - Close connection
- `place_order()` - Place a trading order
- `cancel_order()` - Cancel an order
- `get_positions()` - Get current positions
- `get_orders()` - Get order history
- `get_balances()` - Get account balances
- `health_check()` - Check connection health

### HyperliquidMCPServer

MCP server that wraps the client for AI agent integration.

#### Methods

- `start()` - Start the server
- `stop()` - Stop the server  
- `execute_tool()` - Execute an MCP tool
- `get_available_tools()` - Get tool schemas
- `health_check()` - Check server health

## Troubleshooting

### Common Issues

1. **Connection failed**
   - Check internet connection
   - Verify API endpoints
   - Check credentials for live trading

2. **Order placement failed**
   - Verify account has sufficient balance
   - Check order parameters (price, size)
   - Ensure asset symbol is correct

3. **Authentication failed**
   - Verify private key format (hex)
   - Check wallet address format
   - Ensure credentials match the trading account

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show detailed API calls and responses
```

## Contributing

When contributing to the MCP client:

1. Add comprehensive tests for new features
2. Update documentation
3. Follow the existing code style
4. Test with both paper and testnet modes
5. Ensure backwards compatibility

## Support

For issues specific to this MCP client implementation, create an issue in the repository.

For Hyperliquid platform issues, refer to their official documentation and support channels.