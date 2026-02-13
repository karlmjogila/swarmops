-- Undo: U3__seed_data
-- Description: Remove seed data
-- Safe to run in development

-- Delete sample candle data
DELETE FROM candles WHERE symbol = 'BTC-USD' AND timeframe IN ('15m', '1h');

-- Delete sample strategy
DELETE FROM strategies WHERE id = '00000000-0000-0000-0000-000000000002';

-- Delete development user (cascade will delete related data)
DELETE FROM users WHERE id = '00000000-0000-0000-0000-000000000001';

-- Verify deletion
DO $$
DECLARE
    user_count INTEGER;
    strategy_count INTEGER;
    candle_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO strategy_count FROM strategies;
    SELECT COUNT(*) INTO candle_count FROM candles;
    
    RAISE NOTICE 'After seed rollback: % users, % strategies, % candles', 
        user_count, strategy_count, candle_count;
END $$;
