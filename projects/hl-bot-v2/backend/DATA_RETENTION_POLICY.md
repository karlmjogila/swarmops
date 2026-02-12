# Data Retention & Sync Policy

This document describes the Hyperliquid data synchronization and retention policies for the HL-Bot trading system.

## Overview

The system continuously fetches OHLCV (Open, High, Low, Close, Volume) candle data from Hyperliquid and stores it in TimescaleDB for analysis and backtesting.

## Data Retention Policy

| Timeframe | Retention Period | Rationale |
|-----------|-----------------|-----------|
| **1m** | 3 years | Granular data useful for short-term analysis but very large |
| **5m** | Forever | Essential for scalping strategies |
| **15m** | Forever | Key timeframe for day trading |
| **30m** | Forever | Important for swing analysis |
| **1h** | Forever | Core timeframe for trend analysis |
| **4h** | Forever | Higher timeframe structure |
| **1d** | Forever | Daily candles critical for long-term analysis |
| **1w** | Forever | Weekly structure for macro view |
| **1M** | Forever | Monthly data for historical context |

### Why 3 Years for 1m Data?

1-minute candles generate approximately:
- **525,600 candles/year per symbol** (60 × 24 × 365)
- For 50 symbols: **~26 million rows/year**
- After 3 years: **~78 million rows** just for 1m data

After 3 years, 1-minute data becomes less relevant for most trading strategies while still maintaining significant storage costs. The 3-year window provides enough historical data for:
- Seasonal pattern analysis
- Volatility studies
- Strategy backtesting

## Sync Schedule

### Hourly Sync (Celery Beat)

The `sync_hyperliquid_hourly` task runs every hour and fetches incremental updates for:
- All configured symbols (default: BTC, ETH, SOL, ARB, DOGE, WIF, PEPE, HYPE)
- All timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M

```python
# Celery beat schedule
"sync-hyperliquid-hourly": {
    "task": "app.workers.tasks.sync_hyperliquid_hourly",
    "schedule": 3600.0,  # Every hour
}
```

### Configuration

All sync parameters are configurable via environment variables:

```bash
# Timeframes to sync
HL_SYNC_TIMEFRAMES='["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]'

# Symbols to sync
HL_SYNC_SYMBOLS='["BTC", "ETH", "SOL", "ARB", "DOGE", "WIF", "PEPE", "HYPE"]'

# Sync interval (seconds)
HL_SYNC_INTERVAL_SECONDS=3600
```

## Cleanup Schedule

### Daily Cleanup (3:00 AM UTC)

The `cleanup_old_candles` task runs daily and:
1. Identifies 1m candles older than the retention period
2. Deletes them using efficient batch queries
3. Logs the number of candles deleted

```python
"cleanup-old-candles-daily": {
    "task": "app.workers.tasks.cleanup_old_candles",
    "schedule": crontab(hour=3, minute=0),  # 3:00 AM UTC
}
```

### Weekly Maintenance (Sunday 4:00 AM UTC)

The `run_timescaledb_maintenance` task runs weekly and:
1. Compresses chunks older than the compression threshold
2. Updates table statistics (ANALYZE)
3. Reports compression stats

```python
"timescaledb-maintenance-weekly": {
    "task": "app.workers.tasks.run_timescaledb_maintenance",
    "schedule": crontab(hour=4, minute=0, day_of_week=0),  # Sunday
}
```

## TimescaleDB Optimization

### Hypertable Configuration

The `ohlcv_data` table is a TimescaleDB hypertable with:
- **Chunk interval**: 7 days (default)
- **Compression**: Enabled with segmentation by `symbol, timeframe, source`

### Compression Policy

Chunks older than 7 days are automatically compressed:

```sql
SELECT add_compression_policy(
    'ohlcv_data', 
    INTERVAL '7 days',
    if_not_exists => true
);
```

**Compression settings:**
```sql
ALTER TABLE ohlcv_data SET (
    timescaledb.compress = true,
    timescaledb.compress_segmentby = 'symbol, timeframe, source',
    timescaledb.compress_orderby = 'timestamp DESC'
);
```

### Why Segmentation Matters

Segmenting by `symbol, timeframe, source` allows:
1. Efficient queries filtered by symbol/timeframe
2. Parallel decompression of relevant segments only
3. Better compression ratios within homogeneous data

## Running Tasks Manually

### Trigger Hourly Sync

```bash
# Via Celery
celery -A app.celery_app call app.workers.tasks.sync_hyperliquid_hourly

# Or via Python
from app.workers.tasks import sync_hyperliquid_hourly
sync_hyperliquid_hourly.delay()
```

### Trigger Cleanup

```bash
celery -A app.celery_app call app.workers.tasks.cleanup_old_candles
```

### Trigger Maintenance

```bash
celery -A app.celery_app call app.workers.tasks.run_timescaledb_maintenance
```

### Full Historical Sync

For initial setup or to backfill data:

```bash
# Sync all available symbols with full history
celery -A app.celery_app call app.workers.tasks.sync_all_hyperliquid_data \
    --kwargs='{"mode": "full"}'
```

## Monitoring

### Check Sync Status

```python
from app.services.data_sync import DataSyncService
from app.db.session import SessionLocal

db = SessionLocal()
service = DataSyncService(db)
statuses = service.get_all_sync_statuses()

for status in statuses:
    print(f"{status.symbol}/{status.timeframe}: {status.candle_count} candles")
```

### Check Compression Stats

```sql
SELECT 
    COUNT(*) FILTER (WHERE is_compressed) as compressed_chunks,
    COUNT(*) FILTER (WHERE NOT is_compressed) as uncompressed_chunks,
    pg_size_pretty(SUM(total_bytes)) as total_size
FROM timescaledb_information.chunks 
WHERE hypertable_name = 'ohlcv_data';
```

### Check Data Distribution

```sql
SELECT 
    timeframe,
    COUNT(*) as candle_count,
    MIN(timestamp) as oldest,
    MAX(timestamp) as newest
FROM ohlcv_data
GROUP BY timeframe
ORDER BY candle_count DESC;
```

## Storage Estimates

Rough storage estimates per symbol:

| Timeframe | Candles/Year | Size/Year (uncompressed) | Size/Year (compressed) |
|-----------|--------------|--------------------------|------------------------|
| 1m | 525,600 | ~50 MB | ~5-10 MB |
| 5m | 105,120 | ~10 MB | ~1-2 MB |
| 15m | 35,040 | ~3.5 MB | ~500 KB |
| 1h | 8,760 | ~1 MB | ~100 KB |
| 4h | 2,190 | ~250 KB | ~25 KB |
| 1d | 365 | ~40 KB | ~5 KB |

**For 50 symbols with all timeframes:**
- Uncompressed: ~3 GB/year
- Compressed: ~300-600 MB/year

## Troubleshooting

### Sync Fails with Rate Limit

Hyperliquid has rate limits. If you see 429 errors:
1. Reduce the number of symbols synced in parallel
2. Increase delay between requests in `HyperliquidDataFetcher`

### Cleanup Takes Too Long

If the daily cleanup is slow:
1. Ensure the `idx_ohlcv_timeframe_timestamp` index exists
2. Consider running cleanup more frequently (e.g., twice daily)
3. Use `drop_chunks()` if you can restructure to have 1m data in separate chunks

### Compression Not Working

Check if compression is enabled:
```sql
SELECT * FROM timescaledb_information.compression_settings 
WHERE hypertable_name = 'ohlcv_data';
```

Manually compress old chunks:
```sql
SELECT compress_chunk(c.chunk_name::regclass)
FROM (
    SELECT chunk_name 
    FROM timescaledb_information.chunks 
    WHERE hypertable_name = 'ohlcv_data'
    AND NOT is_compressed
    AND range_end < NOW() - INTERVAL '7 days'
) c;
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `HL_SYNC_TIMEFRAMES` | `["1m"..."1M"]` | Timeframes to sync |
| `HL_SYNC_SYMBOLS` | `["BTC", "ETH"...]` | Symbols to sync |
| `HL_SYNC_INTERVAL_SECONDS` | `3600` | Sync interval (1 hour) |
| `HL_RETENTION_1M_DAYS` | `1095` | 1m retention (3 years) |
| `HL_COMPRESSION_AFTER_DAYS` | `7` | Compress chunks after N days |
| `HL_CLEANUP_INTERVAL_SECONDS` | `86400` | Cleanup interval (1 day) |
