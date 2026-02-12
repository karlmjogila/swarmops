# Hyperliquid MCP Server

## Overview

This MCP (Model Context Protocol) server exposes Hyperliquid trading operations as tools that Claude can use for trade execution and market analysis.

## Features

- **Safe Tool Exposure**: All trading operations with validation and safety checks
- **Paper Trading Mode**: Test without real funds (default: enabled)
- **Comprehensive Audit Trail**: All Claude-initiated operations are logged
- **Error Handling**: Robust error handling with detailed error messages
- **Position Monitoring**: Real-time position and account state queries

## Architecture

```
Claude Desktop <-> MCP Protocol <-> MCP Server <-> Hyperliquid Client <-> Hyperliquid API
```

## Available Tools

### 1. `get_market_data`
Get current market data for a trading symbol.

**Parameters:**
- `symbol` (string, required): Trading symbol (e.g., "BTC", "ETH")

**Returns:** Price, volume, spread, and open interest

### 2. `get_positions`
Get all currently open positions with P&L and risk metrics.

**Returns:** List of positions with entry price, mark price, unrealized P&L, leverage, etc.

### 3. `get_account_state`
Get account state including balance, margin, and available capital.

**Returns:** Account balance, available balance, used margin, unrealized P&L

### 4. `place_order`
Place a trading order. **USE WITH EXTREME CAUTION.**

**Parameters:**
- `symbol` (string, required): Trading symbol
- `side` (string, required): "buy" or "sell"
- `order_type` (string, required): "market", "limit", or "stop"
- `quantity` (number, required): Order quantity (positive number)
- `price` (number, optional): Limit price (required for limit/stop orders)
- `stop_price` (number, optional): Stop trigger price (for stop orders)
- `reduce_only` (boolean, optional): Only reduce existing position
- `post_only` (boolean, optional): Only place if it would be a maker

**Returns:** Order confirmation with order ID and status

### 5. `cancel_order`
Cancel a specific open order.

**Parameters:**
- `order_id` (string, required): Order ID to cancel
- `symbol` (string, required): Trading symbol

**Returns:** Cancellation confirmation

### 6. `cancel_all_orders`
Cancel all open orders (emergency exit/risk management).

**Parameters:**
- `symbol` (string, optional): Only cancel orders for this symbol
- `reason` (string, optional): Reason for cancellation (audit trail)

**Returns:** Number of orders cancelled

## Setup

### 1. Environment Variables

Create a `.env` file:

```bash
# Required
HYPERLIQUID_PRIVATE_KEY=your_ethereum_private_key_here

# Optional (defaults shown)
HYPERLIQUID_TESTNET=true          # Use testnet (true) or mainnet (false)
HYPERLIQUID_PAPER_MODE=true       # Paper trading mode (no real orders)
```

### 2. Install Dependencies

```bash
cd backend
poetry install
```

### 3. Run the Server

```bash
# Paper mode (safe, no real trades)
poetry run python -m hl_bot.trading.mcp_server

# Live mode (DANGER: real funds at risk)
HYPERLIQUID_PAPER_MODE=false poetry run python -m hl_bot.trading.mcp_server
```

## Claude Desktop Integration

Add to Claude Desktop's MCP configuration file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "hyperliquid-trading": {
      "command": "poetry",
      "args": [
        "run",
        "python",
        "-m",
        "hl_bot.trading.mcp_server"
      ],
      "cwd": "/path/to/hl-bot-v2/backend",
      "env": {
        "HYPERLIQUID_PRIVATE_KEY": "your_private_key",
        "HYPERLIQUID_TESTNET": "true",
        "HYPERLIQUID_PAPER_MODE": "true"
      }
    }
  }
}
```

## Safety Features

### Paper Mode (Default)
- All order operations are simulated
- No real funds at risk
- Full logging and validation still active

### Validation
- Positive quantity checks
- Required price validation for limit/stop orders
- Symbol and side validation

### Audit Trail
- All operations logged with timestamps
- Claude-initiated trades marked clearly
- Full parameter logging for review

### Rate Limiting
- Respects Hyperliquid's 100 req/min limit
- 30% headroom built in (70 req/min)
- Automatic backoff on rate limit errors

## Usage Examples

### Query Market Data

```
User: "What's the current price of BTC?"

Claude uses get_market_data:
{
  "symbol": "BTC"
}
```

### Check Positions

```
User: "Show me my open positions"

Claude uses get_positions (no parameters)
```

### Place Order (Paper Mode)

```
User: "Buy 0.1 BTC at market"

Claude uses place_order:
{
  "symbol": "BTC",
  "side": "buy",
  "order_type": "market",
  "quantity": 0.1
}

Result: [PAPER MODE] Order simulation (no real order placed)
```

## Security Considerations

### Private Key Storage
- **NEVER** commit private keys to git
- Use environment variables or secure key management
- Separate keys for testnet and mainnet

### Paper Mode
- Always test with paper mode first
- Understand all tool operations before going live
- Set `HYPERLIQUID_PAPER_MODE=true` in production config

### Access Control
- MCP server runs locally only
- Claude Desktop is the only client
- No network exposure

### Audit Review
- Regularly review audit logs in `./logs/audit/`
- Monitor for unexpected operations
- Set up alerts for large trades

## Testing

### Unit Tests

```bash
poetry run pytest tests/unit/test_mcp_server.py -v
```

### Integration Tests

```bash
# With testnet
HYPERLIQUID_TESTNET=true poetry run pytest tests/integration/test_mcp_integration.py -v
```

### Manual Testing

1. Start the server:
   ```bash
   poetry run python -m hl_bot.trading.mcp_server
   ```

2. Open Claude Desktop

3. Test with safe operations first:
   - Get market data
   - Check positions
   - Check account state

4. Test order operations in paper mode:
   - Place market order
   - Place limit order
   - Cancel orders

## Troubleshooting

### "HYPERLIQUID_PRIVATE_KEY environment variable required"
- Set the environment variable in your shell or `.env` file

### "Rate limited by exchange"
- Wait for rate limit window to reset
- Check `utilization` metric in logs
- Reduce request frequency

### "Order rejected"
- Check symbol is valid
- Verify account has sufficient balance
- Ensure price is within exchange limits

### "WebSocket disconnected"
- Normal behavior, auto-reconnection enabled
- Check network connectivity
- Verify API endpoint is accessible

## Production Deployment

### Best Practices

1. **Start with Paper Mode**
   - Test all workflows thoroughly
   - Verify Claude understands your strategies
   - Review all generated orders

2. **Use Testnet First**
   - Test with testnet funds
   - Validate order execution
   - Confirm audit logging

3. **Enable Live Trading Gradually**
   - Start with small position sizes
   - Monitor closely for first trades
   - Scale up confidence level

4. **Set Risk Limits**
   - Max position size
   - Max daily loss
   - Max concurrent positions

5. **Monitor Continuously**
   - Watch audit logs in real-time
   - Set up alerts for large trades
   - Review Claude's reasoning

### Environment Setup

```bash
# Production .env
HYPERLIQUID_PRIVATE_KEY=<mainnet_key>
HYPERLIQUID_TESTNET=false
HYPERLIQUID_PAPER_MODE=false  # Only after thorough testing!

# Logging
LOG_LEVEL=info
AUDIT_LOG_DIR=./logs/audit
```

## Architecture Notes

### Why MCP?
- **Tool-based paradigm**: Claude sees trading as discrete tool calls
- **Safety**: All operations go through validation layer
- **Auditability**: Complete trace of AI decisions
- **Separation of concerns**: Trading logic separate from LLM integration

### Design Decisions

1. **Paper Mode Default**: Safety first - must explicitly enable live trading
2. **Decimal Precision**: All prices use Decimal type to avoid floating point errors
3. **Rate Limiting**: Built into client, not MCP layer
4. **Synchronous Tools**: MCP tools are async but appear synchronous to Claude
5. **Error Wrapping**: All exchange errors wrapped with context

## Future Enhancements

- [ ] Add resource subscriptions for real-time market data
- [ ] Implement position size calculator tool
- [ ] Add risk assessment tool
- [ ] Strategy backtesting tool integration
- [ ] Multi-account support
- [ ] Advanced order types (OCO, trailing stop)

## References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Anthropic MCP Documentation](https://docs.anthropic.com/mcp)
- [Hyperliquid API Docs](https://hyperliquid.xyz/docs)
- [Trading Systems Excellence](../README.md)

---

**⚠️ WARNING:** Trading cryptocurrencies involves substantial risk. Never trade with funds you cannot afford to lose. Always thoroughly test in paper mode before live trading.
