-- Flyway Migration V2: TimescaleDB Hypertables
-- Description: Create TimescaleDB hypertables for time-series data
-- Created: 2024-02-13
-- Requires: TimescaleDB extension (created in V1)

-- ============================================================================
-- OHLCV Candle Data
-- ============================================================================

CREATE TABLE candles (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL DEFAULT 0,
    trades_count INTEGER DEFAULT 0,
    PRIMARY KEY (time, symbol, timeframe)
);

-- Convert to hypertable with 1 day chunks (adjust based on expected data volume)
SELECT create_hypertable('candles', 'time', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create indexes for efficient queries
CREATE INDEX idx_candles_symbol_tf_time ON candles (symbol, timeframe, time DESC);
CREATE INDEX idx_candles_symbol ON candles (symbol);
CREATE INDEX idx_candles_timeframe ON candles (timeframe);

-- Compression policy: compress chunks older than 30 days
ALTER TABLE candles SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, timeframe'
);

SELECT add_compression_policy('candles', INTERVAL '30 days', if_not_exists => TRUE);

-- Retention policy: delete data older than 2 years (adjust as needed)
SELECT add_retention_policy('candles', INTERVAL '2 years', if_not_exists => TRUE);

-- ============================================================================
-- Detected Patterns (for historical analysis)
-- ============================================================================

CREATE TABLE detected_patterns (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    direction TEXT CHECK (direction IN ('bullish', 'bearish', 'neutral')),
    confidence DECIMAL(5,4) CHECK (confidence >= 0 AND confidence <= 1),
    start_index INTEGER,
    end_index INTEGER,
    candle_indices INTEGER[],
    metadata JSONB DEFAULT '{}'
);

-- Convert to hypertable
SELECT create_hypertable('detected_patterns', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create indexes
CREATE INDEX idx_patterns_symbol_tf_time ON detected_patterns (symbol, timeframe, time DESC);
CREATE INDEX idx_patterns_type ON detected_patterns (pattern_type);
CREATE INDEX idx_patterns_direction ON detected_patterns (direction);

-- Compression policy
ALTER TABLE detected_patterns SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, timeframe'
);

SELECT add_compression_policy('detected_patterns', INTERVAL '30 days', if_not_exists => TRUE);

-- ============================================================================
-- Market Structure Points
-- ============================================================================

CREATE TABLE market_structure (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    structure_type TEXT NOT NULL CHECK (structure_type IN ('BOS', 'CHoCH', 'swing_high', 'swing_low', 'higher_high', 'higher_low', 'lower_high', 'lower_low')),
    price DECIMAL(20,8) NOT NULL,
    candle_index INTEGER,
    trend TEXT CHECK (trend IN ('bullish', 'bearish', 'neutral')),
    metadata JSONB DEFAULT '{}'
);

-- Convert to hypertable
SELECT create_hypertable('market_structure', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create indexes
CREATE INDEX idx_mkt_structure_symbol_tf_time ON market_structure (symbol, timeframe, time DESC);
CREATE INDEX idx_mkt_structure_type ON market_structure (structure_type);

-- Compression policy
ALTER TABLE market_structure SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, timeframe'
);

SELECT add_compression_policy('market_structure', INTERVAL '30 days', if_not_exists => TRUE);

-- ============================================================================
-- Support/Resistance Zones
-- ============================================================================

CREATE TABLE sr_zones (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    zone_type TEXT NOT NULL CHECK (zone_type IN ('support', 'resistance')),
    top_price DECIMAL(20,8) NOT NULL,
    bottom_price DECIMAL(20,8) NOT NULL,
    strength DECIMAL(5,4) CHECK (strength >= 0 AND strength <= 1),
    touches INTEGER DEFAULT 1,
    first_touch TIMESTAMPTZ NOT NULL,
    last_touch TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'
);

-- Convert to hypertable
SELECT create_hypertable('sr_zones', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Create indexes
CREATE INDEX idx_sr_zones_symbol_tf ON sr_zones (symbol, timeframe, time DESC);
CREATE INDEX idx_sr_zones_type ON sr_zones (zone_type);
CREATE INDEX idx_sr_zones_active ON sr_zones (is_active) WHERE is_active = TRUE;

-- ============================================================================
-- Tick Data (for high-frequency analysis if needed)
-- ============================================================================

CREATE TABLE ticks (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    side TEXT CHECK (side IN ('buy', 'sell'))
);

-- Convert to hypertable with smaller chunks for tick data
SELECT create_hypertable('ticks', 'time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

CREATE INDEX idx_ticks_symbol_time ON ticks (symbol, time DESC);

-- Aggressive compression for tick data
ALTER TABLE ticks SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy('ticks', INTERVAL '1 day', if_not_exists => TRUE);

-- Shorter retention for tick data (30 days)
SELECT add_retention_policy('ticks', INTERVAL '30 days', if_not_exists => TRUE);

-- ============================================================================
-- Continuous Aggregates for Common Queries
-- ============================================================================

-- Hourly candle stats (example)
CREATE MATERIALIZED VIEW candles_hourly_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    symbol,
    timeframe,
    COUNT(*) as candle_count,
    AVG(volume) as avg_volume,
    MAX(high) as period_high,
    MIN(low) as period_low
FROM candles
GROUP BY bucket, symbol, timeframe
WITH NO DATA;

-- Add refresh policy for the continuous aggregate
SELECT add_continuous_aggregate_policy('candles_hourly_stats',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to get latest candle for a symbol/timeframe
CREATE OR REPLACE FUNCTION get_latest_candle(p_symbol TEXT, p_timeframe TEXT)
RETURNS TABLE (
    "time" TIMESTAMPTZ,
    open DECIMAL(20,8),
    high DECIMAL(20,8),
    low DECIMAL(20,8),
    close DECIMAL(20,8),
    volume DECIMAL(20,8)
) AS $$
BEGIN
    RETURN QUERY
    SELECT c.time, c.open, c.high, c.low, c.close, c.volume
    FROM candles c
    WHERE c.symbol = p_symbol AND c.timeframe = p_timeframe
    ORDER BY c.time DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to get candles in a time range
CREATE OR REPLACE FUNCTION get_candles_range(
    p_symbol TEXT,
    p_timeframe TEXT,
    p_start TIMESTAMPTZ,
    p_end TIMESTAMPTZ
)
RETURNS SETOF candles AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM candles
    WHERE symbol = p_symbol
      AND timeframe = p_timeframe
      AND time >= p_start
      AND time <= p_end
    ORDER BY time ASC;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to insert/update candle (upsert)
CREATE OR REPLACE FUNCTION upsert_candle(
    p_time TIMESTAMPTZ,
    p_symbol TEXT,
    p_timeframe TEXT,
    p_open DECIMAL(20,8),
    p_high DECIMAL(20,8),
    p_low DECIMAL(20,8),
    p_close DECIMAL(20,8),
    p_volume DECIMAL(20,8)
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO candles (time, symbol, timeframe, open, high, low, close, volume)
    VALUES (p_time, p_symbol, p_timeframe, p_open, p_high, p_low, p_close, p_volume)
    ON CONFLICT (time, symbol, timeframe)
    DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume;
END;
$$ LANGUAGE plpgsql;
