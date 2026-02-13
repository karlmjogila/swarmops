-- Migration: V4__performance_indexes
-- Description: Add performance-optimized indexes for common query patterns
-- Created: 2024-02-13

-- ============================================================================
-- Composite Indexes for Signals
-- ============================================================================

-- Signals: userId lookup through strategy join is expensive
-- Add composite index for common filtered queries
CREATE INDEX IF NOT EXISTS idx_signals_strategy_status_timestamp 
  ON signals (strategy_id, status, timestamp DESC);

-- For active signals query (status=pending, not expired)
CREATE INDEX IF NOT EXISTS idx_signals_pending_active 
  ON signals (strategy_id, status, expires_at) 
  WHERE status = 'pending';

-- Confidence-based filtering (common in signal search)
CREATE INDEX IF NOT EXISTS idx_signals_confidence 
  ON signals (confidence DESC) 
  WHERE status = 'pending';

-- ============================================================================
-- Composite Indexes for Strategies
-- ============================================================================

-- User's strategies by status (common query pattern)
CREATE INDEX IF NOT EXISTS idx_strategies_user_status_created 
  ON strategies (user_id, status, created_at DESC);

-- Approved strategies for signal generation
CREATE INDEX IF NOT EXISTS idx_strategies_approved 
  ON strategies (user_id, created_at DESC) 
  WHERE status = 'approved';

-- ============================================================================
-- Composite Indexes for Trades
-- ============================================================================

-- User trades with status filter (dashboard view)
CREATE INDEX IF NOT EXISTS idx_trades_user_status_created 
  ON trades (user_id, status, created_at DESC);

-- Symbol-based trade lookup
CREATE INDEX IF NOT EXISTS idx_trades_user_symbol 
  ON trades (user_id, symbol, created_at DESC);

-- Mode-based filtering (paper vs live)
CREATE INDEX IF NOT EXISTS idx_trades_user_mode_status 
  ON trades (user_id, mode, status);

-- ============================================================================
-- Composite Indexes for Backtests
-- ============================================================================

-- User backtests with status (common dashboard query)
CREATE INDEX IF NOT EXISTS idx_backtests_user_status_created 
  ON backtests (user_id, status, created_at DESC);

-- Running backtests count (rate limiting)
CREATE INDEX IF NOT EXISTS idx_backtests_user_running 
  ON backtests (user_id) 
  WHERE status IN ('pending', 'running');

-- ============================================================================
-- Composite Indexes for Content
-- ============================================================================

-- User content with status filter
CREATE INDEX IF NOT EXISTS idx_content_user_status_created 
  ON content (user_id, status, created_at DESC);

-- Processing content (job queue)
CREATE INDEX IF NOT EXISTS idx_content_processing 
  ON content (status, created_at ASC) 
  WHERE status IN ('pending', 'downloading', 'processing');

-- ============================================================================
-- Composite Indexes for Audit Log
-- ============================================================================

-- Audit log by trade with time ordering
CREATE INDEX IF NOT EXISTS idx_audit_trade_time 
  ON trade_audit_log (trade_id, created_at DESC);

-- ============================================================================
-- JSONB GIN Indexes for Fast JSON Queries
-- ============================================================================

-- Strategy entry/exit conditions search
CREATE INDEX IF NOT EXISTS idx_strategies_entry_conditions_gin 
  ON strategies USING GIN (entry_conditions);

CREATE INDEX IF NOT EXISTS idx_strategies_exit_conditions_gin 
  ON strategies USING GIN (exit_conditions);

-- Signal patterns search
CREATE INDEX IF NOT EXISTS idx_signals_patterns_gin 
  ON signals USING GIN (patterns);

-- Backtest config search (for symbol filtering)
CREATE INDEX IF NOT EXISTS idx_backtests_config_gin 
  ON backtests USING GIN (config);

-- ============================================================================
-- Partial Indexes for Common Filters
-- ============================================================================

-- Only pending signals (most commonly queried status)
CREATE INDEX IF NOT EXISTS idx_signals_pending_only 
  ON signals (strategy_id, timestamp DESC) 
  WHERE status = 'pending';

-- Open trades only
CREATE INDEX IF NOT EXISTS idx_trades_open 
  ON trades (user_id, symbol, created_at DESC) 
  WHERE status = 'open';

-- Draft strategies (for editing)
CREATE INDEX IF NOT EXISTS idx_strategies_draft 
  ON strategies (user_id, updated_at DESC) 
  WHERE status = 'draft';

-- ============================================================================
-- Expression Indexes
-- ============================================================================

-- Case-insensitive symbol search
CREATE INDEX IF NOT EXISTS idx_signals_symbol_upper 
  ON signals (UPPER(symbol));

CREATE INDEX IF NOT EXISTS idx_trades_symbol_upper 
  ON trades (UPPER(symbol));
