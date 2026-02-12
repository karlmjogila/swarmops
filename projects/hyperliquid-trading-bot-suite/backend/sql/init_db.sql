-- Initialize database for Hyperliquid Trading Bot Suite
-- This script sets up the database with proper extensions and settings

-- Create database if it doesn't exist (this needs to be run as superuser)
-- CREATE DATABASE trading_bot OWNER postgres;

-- Connect to the trading_bot database
-- \c trading_bot;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- For similarity searches
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- For GIN indexes on multiple columns

-- Set up timezone
SET timezone = 'UTC';

-- Create schema for the application (optional, using public for now)
-- CREATE SCHEMA IF NOT EXISTS trading_bot;
-- GRANT ALL ON SCHEMA trading_bot TO postgres;

-- Configure some PostgreSQL settings for better performance
-- These can be set in postgresql.conf or here for the session

-- Increase work_mem for better sort performance
SET work_mem = '256MB';

-- Increase shared_buffers (this needs to be set in postgresql.conf)
-- shared_buffers = 256MB

-- Enable query planning optimizations
SET enable_hashjoin = on;
SET enable_mergejoin = on;
SET enable_nestloop = on;

-- Configure logging for development
SET log_statement = 'all';
SET log_min_duration_statement = 1000;  -- Log queries taking longer than 1s

-- Show current configuration
SELECT name, setting, unit, context 
FROM pg_settings 
WHERE name IN (
    'shared_buffers',
    'work_mem', 
    'maintenance_work_mem',
    'effective_cache_size',
    'random_page_cost',
    'timezone'
)
ORDER BY name;