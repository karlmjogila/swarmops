# Hyperliquid Historical Data Fetcher - Implementation Complete

## Summary

Implemented a comprehensive Hyperliquid historical data fetcher for hl-bot-v2 that pulls OHLCV data directly from the Hyperliquid API and stores it in TimescaleDB.

## Files Created

### Core Services
- `backend/app/services/hyperliquid_data.py` - Data fetcher service
  - `HyperliquidDataFetcher` class for API interactions
  - `Candle` dataclass for OHLCV data
  - `SyncProgress` for tracking progress
  - Rate limiting and pagination support
  - Supports all 14 Hyperliquid timeframes

- `backend/app/services/data_sync.py` - Sync orchestration service
  - `DataSyncService` for managing syncs
  - Full and incremental sync modes
  - Progress callbacks for UI updates
  - Error handling and state tracking

- `backend/app/services/__init__.py` - Package exports

### Database
- `backend/app/db/models.py` - Added `DataSyncState` model
- `backend/app/db/repositories/sync_state.py` - Sync state repository
- `backend/app/db/migrations/003_add_data_sync_state.sql` - Migration

### API Endpoints
- `backend/app/api/routes/sync.py` - REST API for sync operations
  - `POST /api/data/sync/hyperliquid` - Trigger single sync
  - `POST /api/data/sync/hyperliquid/bulk` - Bulk sync
  - `GET /api/data/sync/status` - Check sync status
  - `GET /api/data/sync/status/all` - All statuses
  - `GET /api/data/sync/available` - List local data
  - `GET /api/data/sync/symbols` - List Hyperliquid symbols
  - `GET /api/data/sync/task/{id}` - Background task status

### Celery Tasks
- `backend/app/workers/tasks.py` - Added sync tasks
  - `sync_hyperliquid_data` - Single symbol/timeframe sync
  - `sync_hyperliquid_bulk` - Multiple symbols sync
  - `sync_all_hyperliquid_data` - All available symbols
  - Scheduled sync in beat_schedule

### CLI Tool
- `backend/scripts/sync_data.py` - Command-line interface
  - `sync` - Single symbol/timeframe
  - `bulk` - Multiple symbols
  - `all` - All available symbols
  - `symbols` - List Hyperliquid symbols
  - `status` - Show sync status
  - `available` - Show local data

### Tests
- `backend/tests/unit/test_hyperliquid_data.py` - Unit tests
- `backend/tests/integration/test_data_sync.py` - Integration tests

### Documentation
- `docs/HYPERLIQUID_DATA_SYNC.md` - Usage documentation

## Key Features

### 1. Data Fetcher Service
- Queries Hyperliquid API for historical candle data
- Supports all timeframes: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d, 3d, 1w, 1M
- Automatic pagination (500 candles per request limit)
- Rate limiting (~100 req/min with 0.7s delay)
- Retry logic with exponential backoff

### 2. Database Integration
- Stores data in existing OHLCV tables (TimescaleDB)
- Upsert logic to avoid duplicates
- Tracks sync state per symbol/timeframe
- Uses `DataSyncState` table for tracking

### 3. Sync Modes
- **Full sync**: Fetch all available history (~5000 candles max)
- **Incremental sync**: Only new data since last sync
- **Scheduled sync**: Via Celery beat (configurable)

### 4. API Endpoints
- REST API for triggering and monitoring syncs
- Background task support
- Bulk operations
- Status and availability queries

### 5. CLI Tool
- Easy command-line access
- Progress indicators
- Status formatting
- All sync modes supported

## Usage Examples

### API
```bash
# Sync BTC 5-minute candles
curl -X POST "http://localhost:8000/api/data/sync/hyperliquid" \
     -H "Content-Type: application/json" \
     -d '{"symbol": "BTC", "timeframe": "5m", "mode": "incremental"}'

# Check status
curl "http://localhost:8000/api/data/sync/status?symbol=BTC&timeframe=5m"
```

### CLI
```bash
# Sync single pair
python scripts/sync_data.py sync BTC 5m

# Full history sync
python scripts/sync_data.py sync ETH 1h --full

# Bulk sync
python scripts/sync_data.py bulk BTC ETH SOL --timeframes 5m 1h 4h

# Show status
python scripts/sync_data.py status
```

### Celery
```python
from app.workers.tasks import sync_hyperliquid_data

# Async task
task = sync_hyperliquid_data.delay("BTC", "5m", "incremental")
```

## Configuration

### Environment Variables
No new environment variables required. Uses existing database and Redis config.

### Celery Beat Schedule
Configure in `backend/app/celery_app.py`:
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

## Database Migration

Run the migration to add the sync state table:
```bash
psql -U hlbot -d hlbot -f backend/app/db/migrations/003_add_data_sync_state.sql
```

## Testing

```bash
# Unit tests
pytest backend/tests/unit/test_hyperliquid_data.py -v

# Integration tests
pytest backend/tests/integration/test_data_sync.py -v
```

## Notes

1. Hyperliquid limits historical data to ~5000 candles per symbol/timeframe
2. Rate limiting is conservative (0.7s delay) to avoid API issues
3. The fetcher doesn't require authentication (public API)
4. Testnet support available via `--testnet` flag
