-- Useful queries for Hyperliquid Trading Bot Suite database
-- These queries can help with monitoring, debugging, and analysis

-- ===============================
-- Database Information Queries
-- ===============================

-- Show all tables and their sizes
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation::NUMERIC(4,3) AS correlation,
    most_common_vals
FROM pg_stats 
WHERE schemaname = 'public'
ORDER BY tablename, attname;

-- Show table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::regclass)) AS size,
    pg_total_relation_size(tablename::regclass) AS bytes
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;

-- Show index usage
SELECT 
    indexname,
    tablename,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- ===============================
-- Trading Data Analysis Queries
-- ===============================

-- Strategy performance summary
SELECT 
    sr.name,
    sr.entry_type,
    sr.confidence,
    sr.trade_count,
    sr.win_rate,
    sr.avg_r_multiple,
    COUNT(tr.id) AS total_executions,
    AVG(tr.pnl_r) AS avg_pnl_r,
    SUM(CASE WHEN tr.outcome = 'win' THEN 1 ELSE 0 END)::FLOAT / 
        NULLIF(COUNT(tr.id), 0) AS actual_win_rate
FROM strategy_rules sr
LEFT JOIN trade_records tr ON sr.id = tr.strategy_rule_id
GROUP BY sr.id, sr.name, sr.entry_type, sr.confidence, sr.trade_count, sr.win_rate, sr.avg_r_multiple
ORDER BY sr.confidence DESC, sr.win_rate DESC;

-- Recent trade performance
SELECT 
    tr.asset,
    tr.direction,
    tr.entry_time,
    tr.exit_time,
    tr.outcome,
    tr.pnl_r,
    tr.pnl_usd,
    sr.name AS strategy_name,
    tr.confidence
FROM trade_records tr
JOIN strategy_rules sr ON tr.strategy_rule_id = sr.id
WHERE tr.entry_time >= NOW() - INTERVAL '30 days'
ORDER BY tr.entry_time DESC
LIMIT 100;

-- Asset performance breakdown
SELECT 
    asset,
    COUNT(*) AS trade_count,
    AVG(pnl_r) AS avg_pnl_r,
    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) AS win_rate,
    MAX(pnl_r) AS best_trade,
    MIN(pnl_r) AS worst_trade
FROM trade_records
WHERE pnl_r IS NOT NULL
GROUP BY asset
ORDER BY trade_count DESC;

-- Learning insights summary
SELECT 
    impact_type,
    COUNT(*) AS insight_count,
    AVG(confidence) AS avg_confidence,
    AVG(validation_count) AS avg_validations
FROM learning_entries
GROUP BY impact_type
ORDER BY insight_count DESC;

-- ===============================
-- Data Quality Checks
-- ===============================

-- Check for missing data
SELECT 
    'strategy_rules' AS table_name,
    COUNT(*) AS total_records,
    COUNT(CASE WHEN name IS NULL OR name = '' THEN 1 END) AS missing_names,
    COUNT(CASE WHEN win_rate IS NULL THEN 1 END) AS missing_win_rates
FROM strategy_rules

UNION ALL

SELECT 
    'trade_records' AS table_name,
    COUNT(*) AS total_records,
    COUNT(CASE WHEN exit_time IS NULL THEN 1 END) AS missing_exit_times,
    COUNT(CASE WHEN pnl_r IS NULL THEN 1 END) AS missing_pnl
FROM trade_records;

-- Check for data consistency
SELECT 
    'trade_records_consistency' AS check_name,
    COUNT(*) AS issues_found
FROM trade_records
WHERE (outcome = 'win' AND pnl_r <= 0) OR (outcome = 'loss' AND pnl_r > 0);

-- Check for orphaned records
SELECT 
    'orphaned_trades' AS check_name,
    COUNT(*) AS orphaned_count
FROM trade_records tr
LEFT JOIN strategy_rules sr ON tr.strategy_rule_id = sr.id
WHERE sr.id IS NULL;

-- ===============================
-- Performance Monitoring
-- ===============================

-- Most active strategies
SELECT 
    sr.name,
    sr.entry_type,
    COUNT(tr.id) AS trades_last_30_days,
    AVG(tr.confidence) AS avg_confidence,
    string_agg(DISTINCT tr.asset, ', ') AS traded_assets
FROM strategy_rules sr
JOIN trade_records tr ON sr.id = tr.strategy_rule_id
WHERE tr.entry_time >= NOW() - INTERVAL '30 days'
GROUP BY sr.id, sr.name, sr.entry_type
ORDER BY COUNT(tr.id) DESC
LIMIT 20;

-- Database activity summary
SELECT 
    'Total Strategies' AS metric,
    COUNT(*)::TEXT AS value
FROM strategy_rules

UNION ALL

SELECT 
    'Total Trades',
    COUNT(*)::TEXT
FROM trade_records

UNION ALL

SELECT 
    'Active Strategies (last 30 days)',
    COUNT(DISTINCT strategy_rule_id)::TEXT
FROM trade_records
WHERE entry_time >= NOW() - INTERVAL '30 days'

UNION ALL

SELECT 
    'Learning Insights',
    COUNT(*)::TEXT
FROM learning_entries

UNION ALL

SELECT 
    'Candle Data Points',
    COUNT(*)::TEXT
FROM candle_data;

-- ===============================
-- Maintenance Queries
-- ===============================

-- Update table statistics (run periodically)
-- ANALYZE strategy_rules;
-- ANALYZE trade_records;
-- ANALYZE learning_entries;
-- ANALYZE candle_data;

-- Vacuum tables (run less frequently)
-- VACUUM ANALYZE strategy_rules;
-- VACUUM ANALYZE trade_records;

-- Reindex tables if needed
-- REINDEX TABLE strategy_rules;
-- REINDEX TABLE trade_records;