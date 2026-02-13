-- Undo: U4__performance_indexes
-- Description: Remove performance-optimized indexes
-- Direction: DOWN

-- Signals indexes
DROP INDEX IF EXISTS idx_signals_strategy_status_timestamp;
DROP INDEX IF EXISTS idx_signals_pending_active;
DROP INDEX IF EXISTS idx_signals_confidence;
DROP INDEX IF EXISTS idx_signals_pending_only;
DROP INDEX IF EXISTS idx_signals_patterns_gin;
DROP INDEX IF EXISTS idx_signals_symbol_upper;

-- Strategies indexes
DROP INDEX IF EXISTS idx_strategies_user_status_created;
DROP INDEX IF EXISTS idx_strategies_approved;
DROP INDEX IF EXISTS idx_strategies_entry_conditions_gin;
DROP INDEX IF EXISTS idx_strategies_exit_conditions_gin;
DROP INDEX IF EXISTS idx_strategies_draft;

-- Trades indexes
DROP INDEX IF EXISTS idx_trades_user_status_created;
DROP INDEX IF EXISTS idx_trades_user_symbol;
DROP INDEX IF EXISTS idx_trades_user_mode_status;
DROP INDEX IF EXISTS idx_trades_open;
DROP INDEX IF EXISTS idx_trades_symbol_upper;

-- Backtests indexes
DROP INDEX IF EXISTS idx_backtests_user_status_created;
DROP INDEX IF EXISTS idx_backtests_user_running;
DROP INDEX IF EXISTS idx_backtests_config_gin;

-- Content indexes
DROP INDEX IF EXISTS idx_content_user_status_created;
DROP INDEX IF EXISTS idx_content_processing;

-- Audit log indexes
DROP INDEX IF EXISTS idx_audit_trade_time;
