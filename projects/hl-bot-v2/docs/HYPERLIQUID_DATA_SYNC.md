# Hyperliquid Historical Data Sync

This document describes the Hyperliquid historical data fetcher system that pulls OHLCV candle data from the Hyperliquid API and stores it in TimescaleDB.

## Overview

The data sync system provides:
- **Historical data fetching** from Hyperliquid's public API
- **Multiple timeframe support** (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d, 3d, 1w, 1M)
- **Incremental sync** to only fetch new data
- **Rate limiting** to respect API limits
- **Progress tracking** for long-running syncs
- **CLI tool** for manual operations
- **Celery tasks** for scheduled background syncing

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   CLI / API     │────▶│ DataSyncService  │────▶│  TimescaleDB    │
│   Endpoints     │     │                  │     │  (OHLCV Data)   │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                        ┌────────▼─────────┐
                        │ HyperliquidData  │
                        │    Fetcher       │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │  Hyperliquid     │
                        │  Public API      │
                        └──────────────────┘
```

## API Endpoints

### Trigger Sync

```bash
# Sync a single symbol/timeframe
POST /api/data/sync/hyperliquid
Content-Type: application/json

{
    "symbol": "BTC",
    "timeframe": "5m",
    "mode": "incremental"  # or "full"
}
```

### Bulk Sync

```bash
# Sync multiple symbols and timeframes
POST /api/data/sync/hyperliquid/bulk
Content-Type: application/json

{
    "symbols": ["BTC", "ETH", "SOL"],
    "timeframes": ["5m", "1h", "4h"],
    "mode": "incremental"
}
```

### Check Status

```bash
# Single pair status
GET /api/data/sync/status?symbol=BTC&timeframe=5m

# All sync statuses
GET /api/data/sync/status/all
```

### Available Data

```bash
# List what data is stored locally
GET /api/data/sync/available

# List Hyperliquid symbols
GET /api/data/sync/symbols
```

## CLI Tool

The CLI tool provides easy access to sync operations:

```bash
# Sync a single symbol/timeframe
python scripts/sync_data.py sync BTC 5m

# Full sync (all available history)
python scripts/sync_data.py sync BTC 5m --full

# Sync multiple symbols
python scripts/sync_data.py bulk BTC ETH SOL --timeframes 5m 1h 4h

# Sync all available Hyperliquid symbols
python scripts/sync_data.py all --timeframes 5m 15m 1h

# List available Hyperliquid symbols
python scripts/sync_data.py symbols

# Show sync status
python scripts/sync_data.py status

# Show local data summary
python scripts/sync_data.py available
```

## Celery Tasks

### Manual Task Invocation

```python
from app.workers.tasks import sync_hyperliquid_data, sync_hyperliquid_bulk

# Single sync
task = sync_hyperliquid_data.delay("BTC", "5m", "incremental")
result = task.get()

# Bulk sync
task = sync_hyperliquid_bulk.delay(
    symbols=["BTC", "ETH"],
    timeframes=["5m", "1h"],
    mode="incremental"
)
```

### Scheduled Sync

The Celery beat schedule includes automatic syncing. Configure in `celery_app.py`:

```python
beat_schedule={
    "sync-hyperliquid-incremental": {
        "task": "app.workers.tasks.sync_hyperliquid_bulk",
        "schedule": 300.0,  # Every 5 minutes
        "args": [["BTC", "ETH"], ["5m", "15m"]],
        "kwargs": {"mode": "incremental"},
    },
}
```

## Sync Modes

### Full Sync

Fetches all available historical data (up to ~5000 candles per timeframe, Hyperliquid limit):

```python
await service.sync("BTC", "5m", mode=SyncMode.FULL)
```

Use for:
- Initial data population
- Recovering from data loss
- Getting maximum historical depth

### Incremental Sync

Only fetches new data since the last sync:

```python
await service.sync("BTC", "5m", mode=SyncMode.INCREMENTAL)
```

Use for:
- Regular updates
- Keeping data current
- Lower API usage

## Rate Limiting

Hyperliquid allows ~100 requests per minute. The fetcher uses conservative limits:

- **Request delay**: 0.7 seconds between requests
- **Batch size**: 500 candles per request (API maximum)
- **Automatic backoff**: On rate limit errors

## Database Schema

### OHLCV Data Table

```sql
CREATE TABLE ohlcv_data (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (timestamp, symbol, timeframe)
);
```

### Sync State Table

```sql
CREATE TABLE data_sync_state (
    id UUID PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    source VARCHAR(50) DEFAULT 'hyperliquid',
    last_sync_timestamp TIMESTAMPTZ,
    last_sync_at TIMESTAMPTZ,
    oldest_timestamp TIMESTAMPTZ,
    newest_timestamp TIMESTAMPTZ,
    candle_count INTEGER DEFAULT 0,
    is_syncing BOOLEAN DEFAULT FALSE,
    sync_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Timeframe Support

### Default Timeframes (Synced Automatically)
These are the timeframes synced by default when running bulk or scheduled syncs:

| Timeframe | Description | Max History | Use Case |
|-----------|-------------|-------------|----------|
| **1m** | 1 minute | ~3.5 days | Scalping, precise entries |
| **5m** | 5 minutes | ~17.4 days | Intraday trading |
| **15m** | 15 minutes | ~52 days | Intraday setups |
| **30m** | 30 minutes | ~104 days | Intraday confirmation |
| **1h** | 1 hour | ~208 days | Swing trading |
| **4h** | 4 hours | ~833 days | Position entries |
| **1d** | 1 day | ~13.7 years | Trend analysis |
| **1w** | 1 week | ~96 years | Long-term bias |
| **1M** | 1 month | ~416 years | Macro trends |

### Additional Timeframes (Hyperliquid Also Supports)
These are available but not included in the default sync:

| Timeframe | Description |
|-----------|-------------|
| 3m | 3 minutes |
| 2h | 2 hours |
| 8h | 8 hours |
| 12h | 12 hours |
| 3d | 3 days |

*Note: Hyperliquid limits to ~5000 candles max per symbol/timeframe*

## Error Handling

### Retry Logic

- Automatic retries with exponential backoff
- Max 3 retries for API errors
- Rate limit errors trigger longer delays

### Error Tracking

Errors are tracked in the `data_sync_state` table:

```python
state = sync_repo.get_sync_state("BTC", "5m")
if state.sync_error:
    print(f"Last error: {state.sync_error}")
```

## Best Practices

1. **Start with incremental sync** for regular updates
2. **Use full sync sparingly** - only for initial setup or recovery
3. **Monitor sync status** to catch errors early
4. **Schedule syncs during low-activity periods** if possible
5. **Don't sync too many pairs simultaneously** - respect rate limits

## Example: Initial Setup

```bash
# 1. List available symbols
python scripts/sync_data.py symbols

# 2. Do a full sync of key pairs
python scripts/sync_data.py bulk BTC ETH SOL --timeframes 5m 15m 1h 4h --full

# 3. Check status
python scripts/sync_data.py status

# 4. Set up scheduled incremental sync (configure in celery_app.py)
```

## Troubleshooting

### "Sync already in progress"

Another sync is running for the same symbol/timeframe. Wait for it to complete or check for stale locks.

### Rate limit errors

Increase the delay between requests or reduce the number of concurrent syncs.

### Missing data

Use `--full` mode to fetch all available history again.

### Database connection errors

Check PostgreSQL/TimescaleDB is running and accessible.
