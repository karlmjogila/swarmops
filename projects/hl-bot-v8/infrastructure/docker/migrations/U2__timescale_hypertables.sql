-- Undo: U2__timescale_hypertables
-- Description: Drop TimescaleDB hypertables and related objects
-- WARNING: This will delete ALL time-series data. Use with extreme caution.

-- Remove continuous aggregate policies first
SELECT remove_continuous_aggregate_policy('candles_hourly_stats', if_exists => TRUE);

-- Drop continuous aggregates
DROP MATERIALIZED VIEW IF EXISTS candles_hourly_stats CASCADE;

-- Drop helper functions
DROP FUNCTION IF EXISTS upsert_candle(TIMESTAMPTZ, TEXT, TEXT, DECIMAL, DECIMAL, DECIMAL, DECIMAL, DECIMAL);
DROP FUNCTION IF EXISTS get_candles_range(TEXT, TEXT, TIMESTAMPTZ, TIMESTAMPTZ);
DROP FUNCTION IF EXISTS get_latest_candle(TEXT, TEXT);

-- Remove retention policies (must do before dropping tables)
SELECT remove_retention_policy('candles', if_exists => TRUE);
SELECT remove_retention_policy('ticks', if_exists => TRUE);

-- Remove compression policies
SELECT remove_compression_policy('candles', if_exists => TRUE);
SELECT remove_compression_policy('detected_patterns', if_exists => TRUE);
SELECT remove_compression_policy('market_structure', if_exists => TRUE);
SELECT remove_compression_policy('ticks', if_exists => TRUE);

-- Drop hypertables (this also drops the underlying tables)
DROP TABLE IF EXISTS ticks CASCADE;
DROP TABLE IF EXISTS sr_zones CASCADE;
DROP TABLE IF EXISTS market_structure CASCADE;
DROP TABLE IF EXISTS detected_patterns CASCADE;
DROP TABLE IF EXISTS candles CASCADE;
