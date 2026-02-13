-- Flyway Migration V1: Initial Schema
-- Description: Create core application tables
-- Created: 2024-02-13

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable TimescaleDB extension (required for hypertables in V2)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ============================================================================
-- Users and Authentication
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    name TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_users_email ON users(email);

-- ============================================================================
-- Content Sources
-- ============================================================================

CREATE TABLE content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('youtube', 'pdf', 'image', 'text', 'url')),
    source_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'downloading', 'processing', 'completed', 'failed')),
    artifacts JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    error TEXT,
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_content_user_id ON content(user_id);
CREATE INDEX idx_content_status ON content(status);
CREATE INDEX idx_content_type ON content(type);
CREATE INDEX idx_content_created_at ON content(created_at DESC);

-- ============================================================================
-- Extracted Strategies
-- ============================================================================

CREATE TABLE strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    content_id UUID REFERENCES content(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending_approval', 'approved', 'rejected', 'archived')),
    rules JSONB NOT NULL DEFAULT '[]',
    entry_conditions JSONB NOT NULL DEFAULT '[]',
    exit_conditions JSONB NOT NULL DEFAULT '[]',
    risk_parameters JSONB NOT NULL DEFAULT '{}',
    timeframes TEXT[] NOT NULL DEFAULT '{}',
    required_patterns TEXT[] DEFAULT '{}',
    confidence DECIMAL(5,4) DEFAULT 0 CHECK (confidence >= 0 AND confidence <= 1),
    reasoning TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    approved_at TIMESTAMPTZ,
    approved_by UUID REFERENCES users(id)
);

CREATE INDEX idx_strategies_user_id ON strategies(user_id);
CREATE INDEX idx_strategies_content_id ON strategies(content_id);
CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_strategies_created_at ON strategies(created_at DESC);

-- ============================================================================
-- Signals
-- ============================================================================

CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE NOT NULL,
    symbol TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('long', 'short')),
    entry_price DECIMAL(20,8) NOT NULL,
    stop_loss DECIMAL(20,8) NOT NULL,
    take_profits DECIMAL(20,8)[] DEFAULT '{}',
    confidence DECIMAL(5,4) DEFAULT 0 CHECK (confidence >= 0 AND confidence <= 1),
    reasoning TEXT DEFAULT '',
    patterns JSONB DEFAULT '[]',
    timeframe_confluence JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'triggered', 'expired', 'cancelled')),
    expires_at TIMESTAMPTZ,
    triggered_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_signals_strategy_id ON signals(strategy_id);
CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_direction ON signals(direction);
CREATE INDEX idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX idx_signals_created_at ON signals(created_at DESC);

-- ============================================================================
-- Trades
-- ============================================================================

CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id UUID REFERENCES signals(id) ON DELETE SET NULL,
    strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('long', 'short')),
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    size DECIMAL(20,8) NOT NULL CHECK (size > 0),
    entry_price DECIMAL(20,8),
    exit_price DECIMAL(20,8),
    stop_loss DECIMAL(20,8) NOT NULL,
    take_profits DECIMAL(20,8)[] DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'open', 'closed', 'cancelled')),
    mode TEXT NOT NULL DEFAULT 'paper' CHECK (mode IN ('paper', 'live')),
    pnl DECIMAL(20,8),
    pnl_percent DECIMAL(10,4),
    fees DECIMAL(20,8),
    timestamps JSONB NOT NULL DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_trades_signal_id ON trades(signal_id);
CREATE INDEX idx_trades_strategy_id ON trades(strategy_id);
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_mode ON trades(mode);
CREATE INDEX idx_trades_created_at ON trades(created_at DESC);

-- ============================================================================
-- Trade Audit Log
-- ============================================================================

CREATE TABLE trade_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trade_id UUID REFERENCES trades(id) ON DELETE CASCADE NOT NULL,
    action TEXT NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_trade_audit_log_trade_id ON trade_audit_log(trade_id);
CREATE INDEX idx_trade_audit_log_action ON trade_audit_log(action);
CREATE INDEX idx_trade_audit_log_created_at ON trade_audit_log(created_at DESC);

-- ============================================================================
-- Learning Journal
-- ============================================================================

CREATE TABLE learning_journal (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    trade_ids UUID[] DEFAULT '{}',
    analysis TEXT DEFAULT '',
    insights TEXT[] DEFAULT '{}',
    action_items TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_learning_journal_user_id ON learning_journal(user_id);
CREATE INDEX idx_learning_journal_created_at ON learning_journal(created_at DESC);

-- ============================================================================
-- Backtest Results
-- ============================================================================

CREATE TABLE backtests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    config JSONB NOT NULL,
    trades JSONB DEFAULT '[]',
    metrics JSONB DEFAULT '{}',
    equity_curve JSONB DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_backtests_strategy_id ON backtests(strategy_id);
CREATE INDEX idx_backtests_user_id ON backtests(user_id);
CREATE INDEX idx_backtests_status ON backtests(status);
CREATE INDEX idx_backtests_created_at ON backtests(created_at DESC);

-- ============================================================================
-- Content Processing Jobs (for BullMQ tracking)
-- ============================================================================

CREATE TABLE content_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID REFERENCES content(id) ON DELETE CASCADE NOT NULL,
    job_id TEXT NOT NULL UNIQUE,
    step TEXT NOT NULL CHECK (step IN ('download', 'transcribe', 'extract', 'upload')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_content_jobs_content_id ON content_jobs(content_id);
CREATE INDEX idx_content_jobs_job_id ON content_jobs(job_id);
CREATE INDEX idx_content_jobs_status ON content_jobs(status);

-- ============================================================================
-- Updated At Trigger Function
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER content_updated_at BEFORE UPDATE ON content FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER strategies_updated_at BEFORE UPDATE ON strategies FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER signals_updated_at BEFORE UPDATE ON signals FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trades_updated_at BEFORE UPDATE ON trades FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER learning_journal_updated_at BEFORE UPDATE ON learning_journal FOR EACH ROW EXECUTE FUNCTION update_updated_at();
