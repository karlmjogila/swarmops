# Data Retention Policy

## Overview

This document describes the data retention policy for OHLCV candle data in HL-Bot V2.

## Retention Rules

| Timeframe | Retention Period | Reasoning |
|-----------|------------------|-----------|
| **1m** | 3 years | High volume, used for precise entries |
| **5m** | Forever | Essential for intraday analysis |
| **15m** | Forever | Key timeframe for setups |
| **30m** | Forever | Confluence confirmation |
| **1h** | Forever | Swing trading foundation |
| **4h** | Forever | Position trading timeframe |
| **1d** | Forever | Trend analysis |
| **1w** | Forever | Long-term bias |
| **1M** | Forever | Macro perspective |

### Why 3 Years for 1m Data?

- **Storage Efficiency**: 1m candles generate ~525,600 candles/year per symbol
- **Practical Utility**: Backtests rarely need 1m data beyond 2-3 years
- **Cost Management**: 3 years provides ample history while managing storage costs
- **Compression**: Old 1m data compresses well but still uses significant space

## Implementation

### TimescaleDB Hypertable

All OHLCV data is stored in a TimescaleDB hypertable with:

```sql
-- Hypertable with 1-day chunks
CREATE TABLE ohlcv_data (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    source VARCHAR(20) NOT NULL,  -- 'hyperliquid' or 'csv'
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume FLOAT DEFAULT 0,
    PRIMARY KEY (timestamp, symbol, timeframe, source)
);

-- Convert to hypertable
SELECT create_hypertable('ohlcv_data', 'timestamp', chunk_time_interval => INTERVAL '1 day');
```

### Compression Policy

Chunks older than 7 days are automatically compressed:

```sql
ALTER TABLE ohlcv_data SET (
    timescaledb.compress = true,
    timescaledb.compress_segmentby = 'symbol, timeframe, source',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('ohlcv_data', INTERVAL '7 days');
```

**Benefits:**
- 90%+ compression ratio for historical data
- Reduced storage costs
- Maintained query performance for compressed data

### Retention Cleanup

A daily Celery task deletes 1m candles older than 3 years:

```python
# Runs at 3:00 AM UTC daily
@celery_app.task
def cleanup_old_candles():
    """Delete 1m candles older than 3 years."""
    cutoff = datetime.utcnow() - timedelta(days=1095)
    
    DELETE FROM ohlcv_data 
    WHERE timeframe = '1m' 
    AND timestamp < cutoff
```

## Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `sync_hyperliquid_hourly` | Every hour | Fetch new candles for all timeframes |
| `cleanup_old_candles` | Daily at 3:00 AM UTC | Delete 1m candles > 3 years old |
| `run_timescaledb_maintenance` | Weekly (Sunday 4:00 AM UTC) | Compress chunks, update stats |

## Configuration

Set these in `.env` or environment variables:

```bash
# Retention: 1m candles kept for N days (1095 = 3 years)
HL_RETENTION_1M_DAYS=1095

# Compression: Compress chunks older than N days
HL_COMPRESSION_AFTER_DAYS=7

# Sync interval in seconds (3600 = 1 hour)
HL_SYNC_INTERVAL_SECONDS=3600

# Timeframes to sync (JSON array)
HL_SYNC_TIMEFRAMES='["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]'

# Symbols to sync (JSON array)
HL_SYNC_SYMBOLS='["BTC", "ETH", "SOL", "ARB", "DOGE", "WIF", "PEPE", "HYPE"]'
```

## Storage Estimates

### Per Symbol (Approximate)

| Timeframe | Candles/Year | Size/Year (uncompressed) | Size/Year (compressed) |
|-----------|--------------|--------------------------|------------------------|
| 1m | 525,600 | ~30 MB | ~3 MB |
| 5m | 105,120 | ~6 MB | ~600 KB |
| 15m | 35,040 | ~2 MB | ~200 KB |
| 30m | 17,520 | ~1 MB | ~100 KB |
| 1h | 8,760 | ~500 KB | ~50 KB |
| 4h | 2,190 | ~125 KB | ~12 KB |
| 1d | 365 | ~20 KB | ~2 KB |
| 1w | 52 | ~3 KB | ~300 B |
| 1M | 12 | ~700 B | ~70 B |

### 10 Symbols × 3 Years

- **1m data**: ~90 MB compressed
- **Other timeframes**: ~30 MB compressed
- **Total**: ~120 MB per 10 symbols

## Manual Operations

### Check Data Summary

```sql
SELECT * FROM ohlcv_data_summary;
```

### Run Cleanup Manually

```python
from app.workers.tasks import cleanup_old_candles
result = cleanup_old_candles.delay()
```

Or via SQL:
```sql
SELECT cleanup_old_1m_candles(1095);  -- 3 years
```

### Check Chunk Status

```sql
SELECT 
    chunk_name, 
    is_compressed, 
    range_start, 
    range_end
FROM timescaledb_information.chunks 
WHERE hypertable_name = 'ohlcv_data' 
ORDER BY range_start DESC
LIMIT 10;
```

### Force Compression

```sql
-- Compress all uncompressed chunks older than 7 days
SELECT compress_chunk(i) 
FROM show_chunks('ohlcv_data', older_than => INTERVAL '7 days') i
WHERE NOT is_compressed;
```

## Monitoring

### Alerts to Set Up

1. **Cleanup Failures**: Alert if `cleanup_old_candles` fails
2. **Sync Failures**: Alert if hourly sync fails 3+ times
3. **Storage Growth**: Alert if storage exceeds threshold
4. **Compression Lag**: Alert if uncompressed chunks > 7 days old

### Metrics to Track

- Total candle count by timeframe
- Storage usage (compressed vs uncompressed)
- Sync success rate
- Cleanup job execution time
- Oldest/newest candle timestamps

## Disaster Recovery

### Backup Strategy

1. **TimescaleDB Continuous Backup**: Use `pg_dump` with `--format=custom`
2. **Point-in-Time Recovery**: Configure WAL archiving
3. **Priority Data**: Back up non-1m data first (forever retention)

### Recovery Priorities

1. **High**: 1h, 4h, 1d data (most critical for analysis)
2. **Medium**: 5m, 15m, 30m data (intraday trading)
3. **Low**: 1m data (can be refetched from Hyperliquid, limited to 5000 candles)
4. **Low**: 1w, 1M data (few candles, easily refetched)
