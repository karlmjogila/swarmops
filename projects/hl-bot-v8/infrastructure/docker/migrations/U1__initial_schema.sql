-- Undo: U1__initial_schema
-- Description: Drop all tables created in initial schema
-- WARNING: This will delete ALL data. Use with extreme caution.

-- Drop triggers first
DROP TRIGGER IF EXISTS learning_journal_updated_at ON learning_journal;
DROP TRIGGER IF EXISTS trades_updated_at ON trades;
DROP TRIGGER IF EXISTS signals_updated_at ON signals;
DROP TRIGGER IF EXISTS strategies_updated_at ON strategies;
DROP TRIGGER IF EXISTS content_updated_at ON content;
DROP TRIGGER IF EXISTS users_updated_at ON users;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at();

-- Drop tables in reverse order of creation (respecting foreign keys)
DROP TABLE IF EXISTS content_jobs CASCADE;
DROP TABLE IF EXISTS backtests CASCADE;
DROP TABLE IF EXISTS learning_journal CASCADE;
DROP TABLE IF EXISTS trade_audit_log CASCADE;
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS signals CASCADE;
DROP TABLE IF EXISTS strategies CASCADE;
DROP TABLE IF EXISTS content CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop extensions
DROP EXTENSION IF EXISTS "uuid-ossp";
