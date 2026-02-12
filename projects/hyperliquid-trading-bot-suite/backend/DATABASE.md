# Database Schema and Migrations

This document describes the database setup, schema, and migration management for the Hyperliquid Trading Bot Suite.

## Overview

The system uses **PostgreSQL** with the following key features:
- **Async SQLAlchemy** for database operations
- **Alembic** for schema migrations
- **pgvector** extension for future vector similarity search
- **Redis** for caching and real-time data

## Database Schema

### Core Tables

#### `strategy_rules`
Stores AI-extracted trading strategy rules from educational content.

```sql
- id (String, PK)              - Unique identifier  
- name (String)                - Human-readable strategy name
- source_type (String)         - Type: pdf, youtube, manual
- source_ref (String)          - File path or YouTube URL
- entry_type (String)          - Entry pattern type
- conditions (JSON)            - Pattern conditions array
- confluence_required (JSON)   - Timeframe alignments needed
- risk_params (JSON)           - Risk management parameters
- confidence (Float)           - AI confidence score (0-1)
- trade_count (Integer)        - Number of times executed
- win_rate (Float)             - Historical success rate
- avg_r_multiple (Float)       - Average risk/reward ratio
```

#### `trade_records`
Stores all trade executions (live and backtest).

```sql
- id (String, PK)              - Unique identifier
- strategy_rule_id (String, FK) - Links to strategy_rules
- asset (String)               - Trading pair (e.g., ETH-USD)
- direction (String)           - long/short
- entry_price (Float)          - Entry price
- exit_price (Float)           - Exit price (null if open)
- entry_time (DateTime)        - When trade was opened
- exit_time (DateTime)         - When trade was closed
- outcome (String)             - win/loss/pending
- pnl_r (Float)                - P&L in R multiples
- pnl_usd (Float)              - P&L in USD
- reasoning (Text)             - AI reasoning for the trade
- confidence (Float)           - Confidence at execution time
- is_backtest (Boolean)        - Live trade vs backtest
```

#### `learning_entries`
Stores AI-generated insights and learning from trade outcomes.

```sql
- id (String, PK)              - Unique identifier
- strategy_rule_id (String, FK) - Optional link to strategy
- insight (Text)               - The learning insight
- supporting_trades (Array)    - Trade IDs that support this
- confidence (Float)           - How confident in this insight
- impact_type (String)         - Type of impact/learning
- market_conditions (JSON)     - Context when learned
- validation_count (Integer)   - How many times validated
```

#### `candle_data`
Stores OHLCV price data for analysis.

```sql
- id (Integer, PK)             - Auto-increment ID
- asset (String)               - Trading pair
- timeframe (String)           - 1m, 5m, 15m, 1h, 4h, 1d
- timestamp (DateTime)         - Candle start time
- open, high, low, close (Float) - OHLC prices
- volume (Float)               - Volume
```

### Backtest Tables

#### `backtest_configs`
Configuration for backtest runs.

#### `backtest_results` 
Results and performance metrics from backtests.

### Utility Tables

#### `ingestion_tasks`
Tracks PDF/video processing jobs.

## Setup Instructions

### 1. Environment Setup

Ensure PostgreSQL is running and create the database:

```bash
# Create database (as postgres user)
createdb trading_bot

# Or using psql
psql -c "CREATE DATABASE trading_bot;"
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update database settings:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/trading_bot
```

### 3. Install Dependencies

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Initialize Database

**Option A: Using the setup script (Recommended)**
```bash
# Create tables directly using SQLAlchemy
python scripts/setup_database.py

# Initialize Alembic (marks as up-to-date)
python scripts/manage_migrations.py init
```

**Option B: Using Alembic migrations**
```bash
# Run migrations
python scripts/manage_migrations.py upgrade head
```

**Option C: Reset everything**
```bash
# Drop and recreate all tables
python scripts/setup_database.py --reset
```

## Migration Management

The project includes helpful scripts for managing database migrations:

### `scripts/manage_migrations.py`

```bash
# Show current revision
python scripts/manage_migrations.py current

# Show migration history
python scripts/manage_migrations.py history

# Upgrade to latest
python scripts/manage_migrations.py upgrade

# Upgrade by one revision
python scripts/manage_migrations.py upgrade +1

# Downgrade by one revision  
python scripts/manage_migrations.py downgrade -1

# Generate new migration
python scripts/manage_migrations.py generate "Add new feature"

# Initialize fresh database
python scripts/manage_migrations.py init
```

### `scripts/setup_database.py`

```bash
# Create tables (safe, won't drop existing)
python scripts/setup_database.py

# Reset database (drops everything!)
python scripts/setup_database.py --reset
```

## Manual Alembic Commands

If you need to use Alembic directly:

```bash
# From backend directory with activated venv
cd backend
source venv/bin/activate

# Set Python path
export PYTHONPATH=/path/to/backend:$PYTHONPATH

# Run alembic commands
alembic current
alembic upgrade head
alembic revision --autogenerate -m "Description"
```

## Performance Considerations

### Indexes

The schema includes several performance indexes:

- **Strategy performance**: `(confidence DESC, win_rate DESC, trade_count DESC)`
- **Trade timeseries**: `(entry_time DESC, asset, is_backtest)`  
- **Candle timeseries**: `(asset, timeframe, timestamp DESC)`
- **Learning validation**: `(validation_count DESC, confidence DESC)`

### Query Optimization

- Use appropriate WHERE clauses on indexed columns
- Limit result sets with LIMIT when possible
- Use EXPLAIN ANALYZE to check query performance
- Consider partitioning for large time-series data

## Useful Queries

See `sql/useful_queries.sql` for common queries including:

- Strategy performance analysis
- Trade performance by asset
- Data quality checks
- Database monitoring queries

## Docker Setup

For containerized deployment:

```yaml
# docker-compose.yml includes:
postgres:
  image: pgvector/pgvector:pg15
  environment:
    POSTGRES_DB: trading_bot
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: password
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./backend/sql/init:/docker-entrypoint-initdb.d
```

## Troubleshooting

### Common Issues

**Migration fails with "asyncpg not found"**
```bash
pip install asyncpg
```

**"Cannot connect to database"**
- Check PostgreSQL is running
- Verify DATABASE_URL in environment
- Test connection: `psql $DATABASE_URL`

**"Permission denied"** 
- Ensure database user has CREATE privileges
- Check PostgreSQL authentication in pg_hba.conf

**"Alembic InterpolationSyntaxError"**
- Fixed in current alembic.ini (was version_num_format issue)

### Development Database Reset

```bash
# Quick reset for development
python scripts/setup_database.py --reset
```

### Production Migration

```bash
# Always backup first!
pg_dump trading_bot > backup_$(date +%Y%m%d_%H%M%S).sql

# Run migration
python scripts/manage_migrations.py upgrade head

# Verify
python scripts/manage_migrations.py current
```

## Schema Evolution

When adding new features:

1. Update models in `src/database/models.py`
2. Generate migration: `python scripts/manage_migrations.py generate "Description"`
3. Review generated migration in `alembic/versions/`
4. Test migration: `python scripts/manage_migrations.py upgrade`
5. Update this documentation

## Monitoring

Key metrics to monitor:

- Table sizes: `sql/useful_queries.sql` has size queries
- Index usage: Monitor `pg_stat_user_indexes`
- Query performance: Enable `log_min_duration_statement`
- Connection usage: Monitor active connections

For production, consider:
- Regular VACUUM ANALYZE
- Index maintenance
- Connection pooling (PgBouncer)
- Monitoring with pg_stat_statements