-- Flyway Migration V3: Seed Data
-- Description: Initial seed data for development
-- Created: 2024-02-13

-- ============================================================================
-- Development User
-- ============================================================================

INSERT INTO users (id, email, name, settings)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'dev@hlbot.local',
    'Development User',
    '{"theme": "dark", "defaultTimeframe": "15m", "defaultMode": "paper"}'::jsonb
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- Sample Strategy (for testing)
-- ============================================================================

INSERT INTO strategies (id, user_id, name, description, status, rules, entry_conditions, exit_conditions, risk_parameters, timeframes, confidence, reasoning)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',
    'Sample ICT Strategy',
    'A sample strategy based on ICT concepts for testing purposes',
    'draft',
    '[
        {
            "type": "entry",
            "conditions": [
                {"indicator": "pattern", "operator": "equals", "value": "bullish_engulfing"},
                {"indicator": "market_structure", "operator": "equals", "value": "bullish"}
            ],
            "logic": "AND",
            "description": "Enter on bullish engulfing in bullish market structure"
        }
    ]'::jsonb,
    '[
        {"indicator": "pattern", "operator": "equals", "value": "bullish_engulfing"},
        {"indicator": "sr_zone", "operator": "equals", "value": "support"}
    ]'::jsonb,
    '[
        {"indicator": "pnl_percent", "operator": "greater_or_equal", "value": 3},
        {"indicator": "pattern", "operator": "equals", "value": "bearish_engulfing"}
    ]'::jsonb,
    '{
        "maxPositionSizePct": 5,
        "defaultStopLossPct": 2,
        "defaultTakeProfitPct": 6,
        "maxDailyLossPct": 5,
        "maxOpenPositions": 3,
        "riskRewardRatio": 3
    }'::jsonb,
    ARRAY['15m', '1h', '4h'],
    0.75,
    'Sample strategy for development and testing of the pattern engine and signal generation.'
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- Sample Candle Data (BTC-USD, 15m timeframe)
-- ============================================================================

-- Insert some sample candle data for testing
INSERT INTO candles (time, symbol, timeframe, open, high, low, close, volume)
VALUES
    (NOW() - INTERVAL '4 hours', 'BTC-USD', '15m', 42000.00, 42150.00, 41950.00, 42100.00, 150.5),
    (NOW() - INTERVAL '3 hours 45 minutes', 'BTC-USD', '15m', 42100.00, 42200.00, 42050.00, 42180.00, 175.2),
    (NOW() - INTERVAL '3 hours 30 minutes', 'BTC-USD', '15m', 42180.00, 42300.00, 42100.00, 42250.00, 200.8),
    (NOW() - INTERVAL '3 hours 15 minutes', 'BTC-USD', '15m', 42250.00, 42280.00, 42000.00, 42050.00, 180.3),
    (NOW() - INTERVAL '3 hours', 'BTC-USD', '15m', 42050.00, 42150.00, 41900.00, 42000.00, 220.5),
    (NOW() - INTERVAL '2 hours 45 minutes', 'BTC-USD', '15m', 42000.00, 42400.00, 41980.00, 42350.00, 350.0),
    (NOW() - INTERVAL '2 hours 30 minutes', 'BTC-USD', '15m', 42350.00, 42500.00, 42300.00, 42450.00, 280.5),
    (NOW() - INTERVAL '2 hours 15 minutes', 'BTC-USD', '15m', 42450.00, 42550.00, 42400.00, 42520.00, 190.2),
    (NOW() - INTERVAL '2 hours', 'BTC-USD', '15m', 42520.00, 42600.00, 42480.00, 42580.00, 165.8),
    (NOW() - INTERVAL '1 hour 45 minutes', 'BTC-USD', '15m', 42580.00, 42620.00, 42400.00, 42450.00, 210.3),
    (NOW() - INTERVAL '1 hour 30 minutes', 'BTC-USD', '15m', 42450.00, 42500.00, 42350.00, 42480.00, 145.6),
    (NOW() - INTERVAL '1 hour 15 minutes', 'BTC-USD', '15m', 42480.00, 42700.00, 42460.00, 42680.00, 320.0),
    (NOW() - INTERVAL '1 hour', 'BTC-USD', '15m', 42680.00, 42750.00, 42650.00, 42720.00, 185.4),
    (NOW() - INTERVAL '45 minutes', 'BTC-USD', '15m', 42720.00, 42800.00, 42700.00, 42780.00, 175.9),
    (NOW() - INTERVAL '30 minutes', 'BTC-USD', '15m', 42780.00, 42850.00, 42750.00, 42820.00, 155.2),
    (NOW() - INTERVAL '15 minutes', 'BTC-USD', '15m', 42820.00, 42900.00, 42800.00, 42880.00, 200.0)
ON CONFLICT (time, symbol, timeframe) DO NOTHING;

-- Also insert 1h candles for multi-timeframe testing
INSERT INTO candles (time, symbol, timeframe, open, high, low, close, volume)
VALUES
    (NOW() - INTERVAL '4 hours', 'BTC-USD', '1h', 42000.00, 42300.00, 41900.00, 42250.00, 700.0),
    (NOW() - INTERVAL '3 hours', 'BTC-USD', '1h', 42250.00, 42550.00, 41980.00, 42520.00, 1000.0),
    (NOW() - INTERVAL '2 hours', 'BTC-USD', '1h', 42520.00, 42620.00, 42350.00, 42480.00, 720.0),
    (NOW() - INTERVAL '1 hour', 'BTC-USD', '1h', 42480.00, 42900.00, 42460.00, 42880.00, 880.0)
ON CONFLICT (time, symbol, timeframe) DO NOTHING;

-- ============================================================================
-- Verify Data
-- ============================================================================

-- Verify the seed data was inserted
DO $$
DECLARE
    user_count INTEGER;
    strategy_count INTEGER;
    candle_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO strategy_count FROM strategies;
    SELECT COUNT(*) INTO candle_count FROM candles;
    
    RAISE NOTICE 'Seed data summary: % users, % strategies, % candles', 
        user_count, strategy_count, candle_count;
END $$;
