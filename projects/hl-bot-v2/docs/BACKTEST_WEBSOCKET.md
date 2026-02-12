# Backtest WebSocket Streaming

Real-time backtest state streaming via WebSocket for live visualization and control.

## Architecture

```
Frontend (SvelteKit)
    ↓ HTTP API
Dashboard Backend (Nitro)
    ↓ spawn child process
Python Backtest Runner
    ↓ stdout (JSON lines)
Dashboard Backend
    ↓ WebSocket broadcast
Frontend (receives state updates)
```

## Components

### 1. Backend Session Manager

**File:** `/opt/swarmops/dashboard/server/utils/backtest-manager.ts`

Manages backtest sessions:
- Creates and tracks sessions
- Spawns Python backtest processes
- Handles process I/O and lifecycle
- Broadcasts state updates via WebSocket
- Implements pause/resume/stop control

### 2. API Endpoints

**Base:** `/api/backtest`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/create` | Create new session |
| GET | `/` | List all sessions |
| GET | `/:id` | Get session state |
| POST | `/:id/start` | Start backtest |
| POST | `/:id/pause` | Pause backtest |
| POST | `/:id/resume` | Resume backtest |
| POST | `/:id/stop` | Stop backtest |
| DELETE | `/:id` | Delete session |

### 3. Python Stream Runner

**File:** `/opt/swarmops/projects/hl-bot-v2/backend/scripts/run_backtest_stream.py`

Responsibilities:
- Loads historical candle data
- Runs `BacktestEngine` with state callbacks
- Emits state updates to stdout as JSON
- Listens for control commands on stdin
- Handles graceful shutdown

### 4. WebSocket Protocol

**Message Types:**

#### State Update (Backend → Frontend)
```json
{
  "type": "backtest_state_update",
  "sessionId": "backtest-1234567890-abc123",
  "state": {
    "status": "running",
    "currentTime": "2024-01-15T10:30:00Z",
    "currentCandleIndex": 120,
    "totalCandles": 1000,
    "progressPercent": 12.0,
    "currentCapital": 10250.50,
    "peakCapital": 10500.00,
    "drawdown": 249.50,
    "openTrades": [...],
    "recentSignals": [...],
    "recentTrades": [...],
    "metrics": {
      "totalTrades": 5,
      "winningTrades": 3,
      "losingTrades": 2,
      "winRate": 0.6,
      "totalPnl": 250.50,
      "equityCurve": [...]
    }
  }
}
```

#### Control Command (Frontend → Backend)
Sent via HTTP POST to control endpoints (not direct WebSocket).

## Usage

### Starting a Backtest

```typescript
// 1. Create session
const response = await fetch('/api/backtest/create', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    symbol: 'BTC-USD',
    startDate: '2024-01-01',
    endDate: '2024-01-31',
    initialCapital: 10000,
    positionSizePercent: 0.02,
    maxOpenTrades: 3,
    useStopOrders: true,
    useTakeProfits: true,
  }),
})

const { sessionId } = await response.json()

// 2. Start backtest
await fetch(`/api/backtest/${sessionId}/start`, { method: 'POST' })

// 3. Listen for state updates via WebSocket
// (Automatically broadcast to all connected clients)
```

### Frontend Integration

The frontend backtest store (`frontend/src/lib/stores/backtest.ts`) is already set up to receive these updates.

```typescript
// In your Svelte component
import { backtestState, updateBacktestState } from '$lib/stores/backtest'

// WebSocket listener (in app root or layout)
$: if (message.type === 'backtest_state_update') {
  updateBacktestState(message.state)
}
```

### Controlling Playback

```typescript
// Pause
await fetch(`/api/backtest/${sessionId}/pause`, { method: 'POST' })

// Resume
await fetch(`/api/backtest/${sessionId}/resume`, { method: 'POST' })

// Stop
await fetch(`/api/backtest/${sessionId}/stop`, { method: 'POST' })
```

## State Emission

State is emitted:
- Every N candles (default: 10, configurable via `--emit-interval`)
- On final completion
- On error or failure

This balances real-time visualization with performance.

## Process Management

### Lifecycle

1. **Create:** Session created, idle
2. **Start:** Python process spawned, backtest begins
3. **Running:** State updates stream via WebSocket
4. **Pause/Resume:** Process receives stdin commands
5. **Stop:** Graceful shutdown, final state emitted
6. **Complete:** Process exits, session remains for inspection

### Cleanup

- Sessions older than 1 hour (and not running) are automatically cleaned up every 30 minutes
- Can be manually deleted via `DELETE /api/backtest/:id`

### Error Handling

- Process crashes → status set to 'failed'
- Network errors → connection errors ignored (resilient broadcast)
- Invalid data → logged to stderr, backtest continues

## Performance

### Memory Efficiency
- Candles streamed from database, not loaded into memory all at once
- State updates throttled by emit interval
- Old sessions cleaned up automatically

### Concurrency
- Multiple backtest sessions can run in parallel
- Each session is an isolated Python process
- WebSocket broadcasts to all connected clients simultaneously

## Testing

### Manual Test

```bash
# Start backend
cd /opt/swarmops/dashboard
npm run dev

# Create and run backtest
curl -X POST http://localhost:3000/api/backtest/create \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC-USD",
    "startDate": "2024-01-01",
    "endDate": "2024-01-31",
    "initialCapital": 10000
  }'

# Use returned sessionId
curl -X POST http://localhost:3000/api/backtest/{sessionId}/start

# Monitor WebSocket messages in browser console
```

### Direct Script Test

```bash
cd /opt/swarmops/projects/hl-bot-v2/backend

python3 scripts/run_backtest_stream.py \
  --session-id test-123 \
  --symbol BTC-USD \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --initial-capital 10000 \
  --emit-interval 5
```

## Troubleshooting

### No state updates received

1. Check backend logs for process spawn errors
2. Verify Python environment has all dependencies
3. Check if candle data exists for the requested period
4. Verify WebSocket connection is established

### Process exits immediately

1. Check Python script stderr output
2. Verify database connection
3. Check for missing dependencies (`poetry install`)
4. Validate date range and symbol

### High CPU usage

- Reduce emit interval (emit less frequently)
- Limit date range for faster backtests
- Check for signal generator performance issues

## Future Enhancements

- [ ] Seek to specific timestamp
- [ ] Variable playback speed
- [ ] Multi-session comparison view
- [ ] Snapshot/restore session state
- [ ] Export backtest results to file
- [ ] Backtest replay from saved results (no re-run needed)

---

**Status:** ✅ Implemented  
**Task ID:** ws-stream  
**Dependencies:** backtest-runner, backend-init
