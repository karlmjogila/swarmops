# Live Position Monitor

## Overview

The **Live Position Monitor** tracks open positions in real-time, calculates unrealized P&L, and streams updates to connected clients via WebSocket. Built following Trading Systems Excellence principles with paranoid-level safety and comprehensive audit logging.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Position Monitor                            │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │   Fill Monitor  │  │ Market Data    │  │ Position Sync  │    │
│  │   (WebSocket)   │  │ Monitor (Poll) │  │  (Periodic)    │    │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘    │
│           │                   │                   │             │
│           └───────────────────┴───────────────────┘             │
│                              │                                   │
│                    ┌─────────▼──────────┐                       │
│                    │  Position Tracker   │                       │
│                    │  (Single Source of  │                       │
│                    │      Truth)         │                       │
│                    └─────────┬──────────┘                       │
│                              │                                   │
│                    ┌─────────▼──────────┐                       │
│                    │   Update Broadcast  │                       │
│                    │   (WebSocket)       │                       │
│                    └─────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. **Real-Time Position Tracking**
- Tracks positions from **order fills** (not from polling)
- Updates unrealized P&L based on **live market data**
- Handles position increases, decreases, and flips

### 2. **WebSocket Streaming**
- Broadcasts position updates to all connected clients
- Efficient update throttling (only broadcasts significant P&L changes)
- Handles client disconnections gracefully

### 3. **Comprehensive Monitoring**
- **Fill events**: Position changes from order executions
- **Price updates**: Real-time P&L recalculation
- **Periodic sync**: Reconciles with exchange every 60 seconds

### 4. **Safety & Reliability**
- Automatic reconnection on WebSocket failures
- Comprehensive error handling
- Full audit trail of all position changes
- Decimal arithmetic (no floating point errors)

## Components

### PositionMonitor

Main service that orchestrates position monitoring.

```python
from hl_bot.trading.position_monitor import PositionMonitor
from hl_bot.trading.position import PositionTracker
from hl_bot.trading.hyperliquid import HyperliquidClient
from hl_bot.trading.audit_logger import AuditLogger

# Initialize components
hl_client = HyperliquidClient(
    private_key="0x...",
    testnet=True,
    audit_log_dir=Path("logs/trading"),
)

position_tracker = PositionTracker()
audit_logger = AuditLogger(Path("logs/trading"))

# Create monitor
monitor = PositionMonitor(
    hyperliquid_client=hl_client,
    position_tracker=position_tracker,
    audit_logger=audit_logger,
    update_interval=1.0,  # Update prices every second
)

# Register callback for position updates
def on_position_update(update):
    print(f"Position update: {update.symbol} {update.event_type}")

monitor.on_position_update(on_position_update)

# Start monitoring
await monitor.start()

# Get current summary
summary = monitor.get_position_summary()
print(summary)

# Stop monitoring
await monitor.stop()
```

### PositionUpdate

Position update event emitted by the monitor.

```python
class PositionUpdate:
    symbol: str              # Trading symbol
    position: Position       # Current position state
    event_type: str          # "fill", "price_update", "position_change"
    fill: Fill | None        # Fill that triggered update (if applicable)
    timestamp: datetime      # Update timestamp
```

**Event Types:**
- `"fill"`: Position changed due to order fill
- `"price_update"`: Unrealized P&L changed due to market price movement
- `"position_change"`: Position synced from exchange

### Position Summary

```json
{
  "timestamp": "2025-02-11T17:30:00Z",
  "active_positions": 2,
  "total_exposure": "10500.0",
  "total_pnl": "125.50",
  "realized_pnl": "50.00",
  "unrealized_pnl": "75.50",
  "positions": {
    "BTC-USD": {
      "symbol": "BTC-USD",
      "side": "long",
      "quantity": "0.1",
      "entry_price": "50000.0",
      "current_price": "50500.0",
      "unrealized_pnl": "50.0",
      "realized_pnl": "0.0",
      "notional_value": "5050.0",
      "total_pnl": "50.0",
      "leverage": "1.0",
      "last_updated": "2025-02-11T17:30:00Z"
    }
  }
}
```

## API Endpoints

### WebSocket: `/api/v1/positions/stream`

Real-time position updates via WebSocket.

**Client → Server Messages:**

```json
// Get current position summary
{"action": "get_summary"}

// Ping/pong keepalive
{"action": "ping"}
```

**Server → Client Messages:**

```json
// Initial state (sent on connect)
{
  "type": "initial_state",
  "active_positions": 2,
  "total_pnl": "125.50",
  ...
}

// Position update
{
  "type": "position_update",
  "event_type": "fill",
  "symbol": "BTC-USD",
  "timestamp": "2025-02-11T17:30:00Z",
  "position": {
    "symbol": "BTC-USD",
    "side": "long",
    "quantity": "0.1",
    ...
  },
  "fill": {
    "symbol": "BTC-USD",
    "side": "buy",
    "quantity": "0.1",
    "price": "50000.0",
    ...
  }
}

// Summary response
{
  "type": "summary",
  "active_positions": 2,
  "total_pnl": "125.50",
  ...
}

// Keepalive ping
{"type": "ping"}
```

### REST: `GET /api/v1/positions/summary`

Get current position summary.

**Response:**
```json
{
  "timestamp": "2025-02-11T17:30:00Z",
  "active_positions": 2,
  "total_exposure": "10500.0",
  "total_pnl": "125.50",
  "positions": {...}
}
```

### REST: `GET /api/v1/positions/health`

Check position monitor health.

**Response:**
```json
{
  "status": "healthy",
  "running": true
}
```

## Frontend Integration

### JavaScript/TypeScript Example

```typescript
// Connect to position stream
const ws = new WebSocket('ws://localhost:8000/api/v1/positions/stream');

ws.onopen = () => {
  console.log('Connected to position monitor');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'initial_state':
      // Initialize UI with current positions
      updatePositionTable(message.positions);
      break;
      
    case 'position_update':
      // Update specific position
      if (message.event_type === 'fill') {
        showFillNotification(message.fill);
      }
      updatePosition(message.symbol, message.position);
      break;
      
    case 'summary':
      // Update summary stats
      updateSummaryStats(message);
      break;
      
    case 'ping':
      // Respond to keepalive
      ws.send(JSON.stringify({action: 'ping'}));
      break;
  }
};

// Request position summary
function refreshPositions() {
  ws.send(JSON.stringify({action: 'get_summary'}));
}

// Auto-refresh every 5 seconds
setInterval(refreshPositions, 5000);
```

### React Example

```tsx
import { useEffect, useState } from 'react';

interface Position {
  symbol: string;
  side: 'long' | 'short' | 'flat';
  quantity: string;
  unrealized_pnl: string;
  // ... other fields
}

export function PositionMonitor() {
  const [positions, setPositions] = useState<Record<string, Position>>({});
  const [totalPnl, setTotalPnl] = useState('0');

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/api/v1/positions/stream');

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'initial_state' || message.type === 'summary') {
        setPositions(message.positions);
        setTotalPnl(message.total_pnl);
      } else if (message.type === 'position_update') {
        setPositions(prev => ({
          ...prev,
          [message.symbol]: message.position,
        }));
      }
    };

    return () => ws.close();
  }, []);

  return (
    <div>
      <h2>Total P&L: ${totalPnl}</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Side</th>
            <th>Quantity</th>
            <th>Unrealized P&L</th>
          </tr>
        </thead>
        <tbody>
          {Object.values(positions).map(pos => (
            <tr key={pos.symbol}>
              <td>{pos.symbol}</td>
              <td>{pos.side}</td>
              <td>{pos.quantity}</td>
              <td className={parseFloat(pos.unrealized_pnl) >= 0 ? 'green' : 'red'}>
                ${pos.unrealized_pnl}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

## Configuration

Add to `.env`:

```bash
# Enable live trading
ENABLE_LIVE_TRADING=true

# Hyperliquid configuration
HYPERLIQUID_PRIVATE_KEY=0x...
HYPERLIQUID_TESTNET=true

# Logging
LOG_DIR=logs
LOG_LEVEL=info
```

## Safety Features

### 1. **Update Throttling**
Only broadcasts position updates when P&L changes by > $0.01. Prevents spam from tiny price fluctuations.

### 2. **Periodic Reconciliation**
Syncs with exchange every 60 seconds to catch any missed events or discrepancies.

### 3. **Decimal Precision**
All financial calculations use `Decimal` to avoid floating-point errors.

### 4. **Audit Trail**
Every position change is logged with full context for post-mortem analysis.

### 5. **Graceful Degradation**
- WebSocket disconnections trigger automatic reconnection
- Failed callbacks don't kill the monitor
- Client errors don't affect other clients

## Monitoring & Debugging

### Check Monitor Status

```bash
curl http://localhost:8000/api/v1/positions/health
```

### View Position Summary

```bash
curl http://localhost:8000/api/v1/positions/summary
```

### Audit Logs

All position changes are logged to `logs/trading/audit-YYYY-MM-DD.jsonl`:

```json
{"timestamp": "2025-02-11T17:30:00Z", "type": "fill", "symbol": "BTC-USD", "side": "buy", "quantity": "0.1", "price": "50000.0"}
{"timestamp": "2025-02-11T17:30:05Z", "type": "position_change", "symbol": "BTC-USD", "event": "price_update"}
```

## Testing

Run tests:

```bash
# All position monitor tests
pytest tests/trading/test_position_monitor.py -v

# Specific test
pytest tests/trading/test_position_monitor.py::test_position_update_callback -v

# With coverage
pytest tests/trading/test_position_monitor.py --cov=hl_bot.trading.position_monitor
```

## Performance

- **Update Latency**: < 50ms from fill to client broadcast
- **Price Update Frequency**: Configurable (default: 1 second)
- **WebSocket Overhead**: ~100 bytes per update
- **Memory**: ~1MB per 100 positions

## Troubleshooting

### Position Monitor Not Starting

Check logs for initialization errors:

```bash
tail -f logs/hl_bot.log | grep "position monitor"
```

Common issues:
- `ENABLE_LIVE_TRADING` not set to `true`
- Invalid `HYPERLIQUID_PRIVATE_KEY`
- Missing dependencies

### WebSocket Connection Fails

1. Check position monitor is running:
   ```bash
   curl http://localhost:8000/api/v1/positions/health
   ```

2. Check CORS settings in `main.py`

3. Verify WebSocket URL format:
   - Development: `ws://localhost:8000/api/v1/positions/stream`
   - Production: `wss://your-domain.com/api/v1/positions/stream`

### Position Discrepancies

1. Check audit logs for missed fills:
   ```bash
   grep "fill" logs/trading/audit-*.jsonl | tail -20
   ```

2. Force reconciliation:
   ```python
   await monitor._sync_positions()
   ```

3. Compare with exchange:
   ```python
   exchange_positions = await hl_client.get_positions()
   tracker_positions = monitor._tracker.get_all_positions()
   ```

## Production Checklist

- [ ] Set `ENABLE_LIVE_TRADING=true`
- [ ] Configure mainnet credentials (`HYPERLIQUID_TESTNET=false`)
- [ ] Set up log rotation
- [ ] Enable HTTPS/WSS for WebSocket
- [ ] Set up monitoring alerts for position discrepancies
- [ ] Test WebSocket reconnection logic
- [ ] Verify audit logs are being written
- [ ] Load test with multiple concurrent WebSocket clients
- [ ] Set up backup position reconciliation

## Related Components

- **PositionTracker**: Core position tracking logic (`position.py`)
- **HyperliquidClient**: Exchange API client (`hyperliquid.py`)
- **AuditLogger**: Audit trail logging (`audit_logger.py`)
- **RiskManager**: Pre-trade risk checks (`risk.py`)
