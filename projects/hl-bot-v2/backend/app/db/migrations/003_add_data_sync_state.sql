-- Migration: Add data_sync_state table for tracking Hyperliquid sync status
-- Created: 2024-02-11

-- Create data_sync_state table
CREATE TABLE IF NOT EXISTS data_sync_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'hyperliquid',
    
    -- Sync timestamps
    last_sync_timestamp TIMESTAMPTZ,  -- Last candle timestamp synced
    last_sync_at TIMESTAMPTZ,         -- When we last ran the sync
    oldest_timestamp TIMESTAMPTZ,     -- Oldest candle we have
    newest_timestamp TIMESTAMPTZ,     -- Newest candle we have
    candle_count INTEGER DEFAULT 0,
    
    -- Status
    is_syncing BOOLEAN DEFAULT FALSE,
    sync_error TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create unique index for symbol/timeframe/source combination
CREATE UNIQUE INDEX IF NOT EXISTS idx_sync_state_symbol_tf 
    ON data_sync_state (symbol, timeframe, source);

-- Create index for syncing status
CREATE INDEX IF NOT EXISTS idx_sync_state_syncing 
    ON data_sync_state (is_syncing);

-- Create index for last_sync_at for finding stale syncs
CREATE INDEX IF NOT EXISTS idx_sync_state_last_sync 
    ON data_sync_state (last_sync_at);

-- Add comment
COMMENT ON TABLE data_sync_state IS 'Tracks sync state for historical data fetching to support incremental syncs';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON data_sync_state TO hlbot;
