-- Migration: Set up TimescaleDB hypertable with compression and retention policies
-- Created: 2024-02-11
--
-- IMPORTANT: Run this AFTER the base ohlcv_data table exists.
-- Requires TimescaleDB extension to be installed.
--
-- Retention Policy:
--   - 1m candles: 3 years
--   - All other timeframes: Forever
--
-- Compression:
--   - Automatic compression for chunks older than 7 days

-- ============================================================================
-- 1. Enable TimescaleDB Extension (if not already enabled)
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ============================================================================
-- 2. Convert ohlcv_data to a hypertable (if not already)
-- ============================================================================
-- NOTE: This will fail if the table is already a hypertable - that's OK
DO $$
BEGIN
    -- Check if ohlcv_data is already a hypertable
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables 
        WHERE hypertable_name = 'ohlcv_data'
    ) THEN
        -- Convert to hypertable with 1-day chunks
        -- chunk_time_interval is critical for efficient retention and compression
        PERFORM create_hypertable(
            'ohlcv_data', 
            'timestamp',
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
        RAISE NOTICE 'Created hypertable for ohlcv_data';
    ELSE
        RAISE NOTICE 'ohlcv_data is already a hypertable';
    END IF;
END $$;

-- ============================================================================
-- 3. Enable Compression
-- ============================================================================
-- Segment by symbol/timeframe/source for best compression and query performance
-- Order by timestamp DESC for efficient time-range queries
ALTER TABLE ohlcv_data SET (
    timescaledb.compress = true,
    timescaledb.compress_segmentby = 'symbol, timeframe, source',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- ============================================================================
-- 4. Add Automatic Compression Policy
-- ============================================================================
-- Compress chunks older than 7 days automatically
-- This runs in the background by TimescaleDB's job scheduler
SELECT add_compression_policy(
    'ohlcv_data', 
    INTERVAL '7 days',
    if_not_exists => true
);

-- ============================================================================
-- 5. Create Indexes for Retention Cleanup
-- ============================================================================
-- Index to speed up deletion of old 1m candles
CREATE INDEX IF NOT EXISTS idx_ohlcv_timeframe_timestamp 
    ON ohlcv_data (timeframe, timestamp DESC);

-- Index for efficient source-based queries
CREATE INDEX IF NOT EXISTS idx_ohlcv_source_symbol_timeframe
    ON ohlcv_data (source, symbol, timeframe, timestamp DESC);

-- ============================================================================
-- 6. Create Retention Helper Function
-- ============================================================================
-- Function to delete old 1m candles (called by Celery cleanup task)
CREATE OR REPLACE FUNCTION cleanup_old_1m_candles(retention_days INTEGER DEFAULT 1095)
RETURNS TABLE(deleted_count BIGINT, execution_time INTERVAL) AS $$
DECLARE
    cutoff_timestamp TIMESTAMPTZ;
    start_time TIMESTAMPTZ;
    rows_deleted BIGINT;
BEGIN
    start_time := clock_timestamp();
    cutoff_timestamp := NOW() - (retention_days || ' days')::INTERVAL;
    
    -- Delete old 1m candles
    DELETE FROM ohlcv_data 
    WHERE timeframe = '1m' 
    AND timestamp < cutoff_timestamp;
    
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    
    RETURN QUERY SELECT rows_deleted, clock_timestamp() - start_time;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 7. Create View for Data Summary
-- ============================================================================
CREATE OR REPLACE VIEW ohlcv_data_summary AS
SELECT 
    timeframe,
    source,
    COUNT(*) as candle_count,
    COUNT(DISTINCT symbol) as symbol_count,
    MIN(timestamp) as oldest_candle,
    MAX(timestamp) as newest_candle,
    pg_size_pretty(SUM(pg_column_size(ohlcv_data.*))) as approx_size
FROM ohlcv_data
GROUP BY timeframe, source
ORDER BY 
    CASE timeframe
        WHEN '1m' THEN 1
        WHEN '5m' THEN 2
        WHEN '15m' THEN 3
        WHEN '30m' THEN 4
        WHEN '1h' THEN 5
        WHEN '4h' THEN 6
        WHEN '1d' THEN 7
        WHEN '1w' THEN 8
        WHEN '1M' THEN 9
        ELSE 10
    END,
    source;

-- ============================================================================
-- 8. Add Comments for Documentation
-- ============================================================================
COMMENT ON TABLE ohlcv_data IS 
'OHLCV candlestick data stored as a TimescaleDB hypertable.
Retention: 1m candles kept for 3 years, all other timeframes kept forever.
Compression: Chunks older than 7 days are automatically compressed.';

COMMENT ON FUNCTION cleanup_old_1m_candles IS 
'Deletes 1m candles older than retention_days (default: 1095 = 3 years).
Called by Celery cleanup task daily.';

COMMENT ON VIEW ohlcv_data_summary IS 
'Summary view showing candle counts, date ranges, and approximate sizes per timeframe/source.';

-- ============================================================================
-- Verification Queries (for manual checking)
-- ============================================================================
-- Run these manually to verify setup:
--
-- Check hypertable status:
--   SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = 'ohlcv_data';
--
-- Check compression settings:
--   SELECT * FROM timescaledb_information.compression_settings WHERE hypertable_name = 'ohlcv_data';
--
-- Check scheduled jobs:
--   SELECT * FROM timescaledb_information.jobs WHERE hypertable_name = 'ohlcv_data';
--
-- Check chunks:
--   SELECT chunk_name, is_compressed, range_start, range_end 
--   FROM timescaledb_information.chunks 
--   WHERE hypertable_name = 'ohlcv_data' 
--   ORDER BY range_start DESC;
--
-- View data summary:
--   SELECT * FROM ohlcv_data_summary;
