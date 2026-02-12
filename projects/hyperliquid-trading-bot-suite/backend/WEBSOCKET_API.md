# WebSocket Streaming API

Real-time WebSocket streaming for backtest execution, live trading, and market data.

## Overview

The WebSocket API enables real-time streaming of trading data, allowing frontend applications to display live updates without polling. This provides a smooth, responsive user experience for monitoring backtests, live trading, and market data.

## Architecture

```
┌──────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Frontend   │◄───WS───│  WebSocketManager │◄────────│  Backtest   │
│   Client     │         │                   │         │  Engine     │
└──────────────┘         └──────────────────┘         └─────────────┘
                                  │
                                  ├── Backtest Streams
                                  ├── Live Trading Streams
                                  └── Market Data Streams
```

### Key Components

1. **WebSocketManager**: Central hub for managing connections and broadcasting messages
2. **StreamingBacktestEngine**: Wrapper around BacktestEngine that emits real-time events
3. **WebSocket Routes**: FastAPI endpoints for establishing WebSocket connections

## Endpoints

### 1. Backtest Stream

**Endpoint:** `ws://host/api/ws/stream/backtest/{backtest_id}`

Stream real-time backtest execution data.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/stream/backtest/backtest_20240211_123456');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log(message.type, message.data);
};
```

**Message Types:**

#### Connected
Sent immediately upon connection.
```json
{
  "type": "connected",
  "timestamp": "2024-02-11T12:34:56.789Z",
  "data": {
    "backtest_id": "backtest_20240211_123456",
    "message": "Connected to backtest stream"
  }
}
```

#### Progress
Periodic updates on backtest progress (configurable interval).
```json
{
  "type": "progress",
  "timestamp": "2024-02-11T12:35:00.123Z",
  "data": {
    "backtest_id": "backtest_20240211_123456",
    "progress": 45.2,
    "current_time": "2024-01-15T08:00:00Z",
    "metrics": {
      "balance": 11250.50,
      "open_positions": 3,
      "total_trades": 42,
      "winning_trades": 26,
      "win_rate": 0.619,
      "max_drawdown": -0.082
    }
  }
}
```

#### Trade Entry
Emitted when a position is opened.
```json
{
  "type": "trade",
  "timestamp": "2024-02-11T12:35:05.456Z",
  "data": {
    "event": "entry",
    "trade_id": "trade_123",
    "symbol": "BTC-USD",
    "direction": "long",
    "entry_price": 51234.50,
    "entry_time": "2024-01-15T08:15:00Z",
    "quantity": 0.1,
    "stop_loss": 50000.00,
    "take_profit_levels": [52000.00, 53000.00, 54000.00],
    "reasoning": {
      "decision": "enter_long",
      "confidence": 0.85,
      "rationale": "Strong confluence: HTF bullish bias + LTF LE candle at support"
    }
  }
}
```

#### Trade Exit
Emitted when a position is closed.
```json
{
  "type": "trade",
  "timestamp": "2024-02-11T12:35:30.789Z",
  "data": {
    "event": "exit",
    "trade_id": "trade_123",
    "symbol": "BTC-USD",
    "direction": "long",
    "entry_price": 51234.50,
    "entry_time": "2024-01-15T08:15:00Z",
    "exit_price": 52000.00,
    "exit_time": "2024-01-15T10:30:00Z",
    "exit_reason": "take_profit_1",
    "pnl": 76.55,
    "pnl_percent": 1.49,
    "mfe": 150.00,
    "mae": -25.00
  }
}
```

#### Equity Update
Periodic equity curve updates.
```json
{
  "type": "equity",
  "timestamp": "2024-02-11T12:36:00.123Z",
  "data": {
    "backtest_id": "backtest_20240211_123456",
    "time": "2024-01-15T12:00:00Z",
    "equity": 11327.05,
    "balance": 11250.50,
    "drawdown": -0.045
  }
}
```

#### Metrics
Performance metrics update (less frequent than progress).
```json
{
  "type": "metrics",
  "timestamp": "2024-02-11T12:37:00.456Z",
  "data": {
    "backtest_id": "backtest_20240211_123456",
    "total_trades": 50,
    "winning_trades": 31,
    "win_rate": 0.62,
    "profit_factor": 1.85,
    "sharpe_ratio": 1.32,
    "max_drawdown": -0.089
  }
}
```

#### Complete
Sent when backtest finishes.
```json
{
  "type": "complete",
  "timestamp": "2024-02-11T12:45:00.789Z",
  "data": {
    "backtest_id": "backtest_20240211_123456",
    "metrics": {
      "total_trades": 120,
      "winning_trades": 75,
      "losing_trades": 45,
      "win_rate": 0.625,
      "profit_factor": 1.88,
      "total_return": 23.5,
      "max_drawdown": -12.3,
      "sharpe_ratio": 1.42,
      "average_win": 2.1,
      "average_loss": -1.2,
      "largest_win": 5.8,
      "largest_loss": -2.3,
      "total_commissions": 45.67
    }
  }
}
```

#### Error
Sent when an error occurs.
```json
{
  "type": "error",
  "timestamp": "2024-02-11T12:40:00.123Z",
  "data": {
    "error": "Insufficient historical data",
    "details": {
      "symbol": "BTC-USD",
      "required_start": "2024-01-01",
      "available_start": "2024-01-15"
    }
  }
}
```

### 2. Live Trading Stream

**Endpoint:** `ws://host/api/ws/stream/live-trading?symbols=BTC-USD,ETH-USD`

Stream live trading data for active positions and orders.

**Query Parameters:**
- `symbols` (optional): Comma-separated list of symbols to watch

**Message Types:**
- `position`: Position updates (open, modify, close)
- `order`: Order execution updates
- `risk`: Risk metrics updates
- `pnl`: P&L updates

### 3. Market Data Stream

**Endpoint:** `ws://host/api/ws/stream/market-data/{symbol}`

Stream real-time market data and pattern detection results.

**Message Types:**
- `candle`: New candle data (multiple timeframes)
- `pattern`: Pattern detection results
- `structure`: Market structure updates
- `confluence`: Confluence score updates

## Client-Side Implementation

### JavaScript/TypeScript

```typescript
class BacktestStreamClient {
  private ws: WebSocket;
  private handlers: Map<string, Function[]> = new Map();

  constructor(backtestId: string) {
    this.ws = new WebSocket(
      `ws://localhost:8000/api/ws/stream/backtest/${backtestId}`
    );
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.emit(message.type, message.data);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket closed');
    };
  }

  on(eventType: string, handler: Function) {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, []);
    }
    this.handlers.get(eventType)!.push(handler);
  }

  private emit(eventType: string, data: any) {
    const handlers = this.handlers.get(eventType) || [];
    handlers.forEach(handler => handler(data));
  }

  close() {
    this.ws.close();
  }
}

// Usage
const client = new BacktestStreamClient('backtest_20240211_123456');

client.on('connected', (data) => {
  console.log('Connected:', data.message);
});

client.on('progress', (data) => {
  updateProgressBar(data.progress);
  updateMetrics(data.metrics);
});

client.on('trade', (data) => {
  if (data.event === 'entry') {
    addTradeMarker(data);
  } else if (data.event === 'exit') {
    updateTradeMarker(data);
  }
});

client.on('equity', (data) => {
  updateEquityCurve(data);
});

client.on('complete', (data) => {
  showFinalResults(data.metrics);
});
```

### Python

```python
import asyncio
import json
import websockets

async def stream_backtest(backtest_id: str):
    uri = f"ws://localhost:8000/api/ws/stream/backtest/{backtest_id}"
    
    async with websockets.connect(uri) as ws:
        async for message in ws:
            data = json.loads(message)
            
            if data['type'] == 'progress':
                print(f"Progress: {data['data']['progress']:.1f}%")
            elif data['type'] == 'trade':
                print(f"Trade {data['data']['event']}: {data['data']['trade_id']}")
            elif data['type'] == 'complete':
                print("Backtest complete!")
                print(json.dumps(data['data']['metrics'], indent=2))
                break

# Run
asyncio.run(stream_backtest('backtest_20240211_123456'))
```

## Testing

### 1. Start the API Server

```bash
cd backend
uvicorn src.api.main:app --reload
```

### 2. Start a Backtest

```bash
curl -X POST http://localhost:8000/api/backtesting/start \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Backtest",
    "symbol": "BTC-USD",
    "timeframes": ["4H", "1H", "15M"],
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "initial_capital": 10000,
    "strategy_ids": ["strategy1"],
    "risk_per_trade": 0.02
  }'
```

Response:
```json
{
  "backtest_id": "backtest_20240211_143022",
  "status": "pending",
  "streaming": true,
  "stream_url": "ws://localhost:8000/api/ws/stream/backtest/backtest_20240211_143022",
  "message": "Backtest 'Test Backtest' queued. Connect to WebSocket for real-time updates."
}
```

### 3. Connect to WebSocket Stream

Using the test client:
```bash
python test_websocket_client.py backtest_20240211_143022
```

Or using `websocat`:
```bash
websocat ws://localhost:8000/api/ws/stream/backtest/backtest_20240211_143022
```

## Best Practices

### Connection Management

1. **Reconnection Logic**: Implement exponential backoff for reconnection attempts
```typescript
class ReconnectingWebSocket {
  private maxRetries = 5;
  private retryDelay = 1000;
  
  async connect() {
    for (let i = 0; i < this.maxRetries; i++) {
      try {
        await this.connectOnce();
        return;
      } catch (error) {
        const delay = this.retryDelay * Math.pow(2, i);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
    throw new Error('Max reconnection attempts reached');
  }
}
```

2. **Heartbeat/Ping**: Send periodic pings to keep connection alive
```typescript
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }));
  }
}, 30000); // Every 30 seconds
```

### Error Handling

Always handle errors gracefully:
```typescript
ws.onerror = (error) => {
  logger.error('WebSocket error', error);
  showErrorNotification('Connection error');
};

ws.onclose = (event) => {
  if (!event.wasClean) {
    logger.error('Connection closed unexpectedly', event.code);
    attemptReconnect();
  }
};
```

### Resource Management

Close connections when no longer needed:
```typescript
// React example
useEffect(() => {
  const client = new BacktestStreamClient(backtestId);
  
  return () => {
    client.close(); // Cleanup on unmount
  };
}, [backtestId]);
```

## Performance Considerations

1. **Message Rate**: Progress updates are throttled (default: every 100 candles)
2. **Batch Updates**: Equity updates are batched to reduce message frequency
3. **Connection Limits**: Server limits connections per stream (default: unlimited, but monitor)
4. **Message Size**: Large messages (e.g., with reasoning) may be split or compressed

## Security

1. **Authentication**: Add JWT token authentication for production
2. **Rate Limiting**: Implement connection rate limiting
3. **Message Validation**: All incoming messages are validated
4. **CORS**: Configure allowed origins in production

## Monitoring

Check active streams:
```bash
curl http://localhost:8000/api/ws/stream/status
```

Response:
```json
{
  "timestamp": "2024-02-11T12:45:00.789Z",
  "active_connections": {
    "backtest": 5,
    "live_trading": 2,
    "market_data": 8,
    "total": 15
  },
  "streams": [
    {
      "type": "backtest",
      "id": "backtest_20240211_143022",
      "connections": 3
    },
    {
      "type": "market_data",
      "id": "BTC-USD",
      "connections": 2
    }
  ]
}
```

## Future Enhancements

1. **Pause/Resume**: Support pausing and resuming backtest execution
2. **Replay Mode**: Replay historical backtests with adjustable speed
3. **Filtering**: Client-side filtering of message types
4. **Compression**: Message compression for large payloads
5. **Authentication**: JWT-based authentication for production use

## Troubleshooting

### Connection Refused
- Check if API server is running
- Verify port and host
- Check firewall rules

### No Messages Received
- Verify backtest is actually running
- Check server logs for errors
- Ensure backtest_id is correct

### Connection Drops
- Check network stability
- Implement reconnection logic
- Monitor server resources

## Support

For issues or questions:
- Check server logs: `tail -f logs/api.log`
- Enable debug mode: Set `DEBUG=true` in `.env`
- Review FastAPI logs for WebSocket errors
