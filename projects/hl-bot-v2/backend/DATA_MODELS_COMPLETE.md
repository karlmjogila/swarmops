# OHLCV Data Models and Repository Implementation ✅

**Task ID:** data-models  
**Date:** 2025-02-11  
**Status:** COMPLETE

## What Was Implemented

### 1. Database Session Management
Created `src/hl_bot/db/session.py`:
- SQLAlchemy engine with connection pooling
- Session factory for dependency injection
- Health check with pre-ping enabled
- Proper session lifecycle management

### 2. OHLCV Repository
Implemented `src/hl_bot/repositories/ohlcv_repository.py` following Database Excellence principles:

#### Core Operations:
- **`insert_candle()`** - Insert single candle with validation
- **`insert_candles_batch()`** - Efficient batch insert with ON CONFLICT handling
- **`get_candles()`** - Query candles with time filters and limits
- **`get_latest_candle()`** - Get most recent candle for symbol/timeframe
- **`get_candle_at_time()`** - Get candle at exact timestamp
- **`count_candles()`** - Efficient count without loading data
- **`upsert_candle()`** - Insert or update candle (idempotent)
- **`delete_candles()`** - Delete candles by time range

#### Query Optimization:
- **Specific column selection** - No SELECT * in queries
- **Parameterized queries** - SQLAlchemy ORM prevents SQL injection
- **Composite index usage** - Leverages (symbol, timeframe, timestamp) indexes
- **Time-series optimization** - Works with TimescaleDB hypertable
- **Batch operations** - PostgreSQL INSERT ... ON CONFLICT for efficiency

#### Helper Methods:
- **`get_available_symbols()`** - List all symbols with data
- **`get_available_timeframes()`** - List timeframes for a symbol
- **`get_time_range()`** - Get earliest and latest timestamps

### 3. Type Integration
- Uses Pydantic `Candle` model from `types.py` for validation
- Converts between SQLAlchemy OHLCVData and Pydantic Candle models
- Full type safety with mypy-compatible annotations

### 4. Dependency Injection
Updated `src/hl_bot/dependencies.py`:
- **`get_db()`** - FastAPI dependency for database sessions
- **`get_ohlcv_repository()`** - Repository factory for route handlers

### 5. Test Coverage
Created comprehensive test suites:

#### Integration Tests (`tests/integration/test_ohlcv_repository.py`):
- Insert and retrieve operations
- Batch insertion and idempotency
- Time-based filtering
- Latest candle retrieval
- Upsert behavior
- Deletion operations
- Multiple timeframes handling
- Uses real PostgreSQL + TimescaleDB

#### Unit Tests (`tests/unit/test_ohlcv_repository.py`):
- Isolated testing of all repository methods
- Edge case coverage
- Validation testing
- Multiple symbols/timeframes isolation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Routes                         │
│                 (uses Depends(get_db))                     │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────────────────┐
│                   OHLCVRepository                           │
│  • Type-safe API (Pydantic Candle models)                  │
│  • Batch operations                                         │
│  • Time-series optimized queries                           │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────────────────┐
│                  SQLAlchemy ORM                             │
│  • OHLCVData model (app/db/models.py)                      │
│  • Session management                                       │
│  • Query builder                                            │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────────────────┐
│         PostgreSQL + TimescaleDB                            │
│  • ohlcv_data hypertable (7-day chunks)                    │
│  • Composite primary key: (timestamp, symbol, timeframe)   │
│  • CHECK constraints for data validation                   │
│  • Indexes for fast time-series queries                    │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

The repository works with the existing `ohlcv_data` TimescaleDB hypertable:

```sql
CREATE TABLE ohlcv_data (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume FLOAT NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (timestamp, symbol, timeframe),
    
    -- Validation constraints
    CONSTRAINT valid_high_low CHECK (high >= low),
    CONSTRAINT valid_high_open CHECK (high >= open),
    CONSTRAINT valid_high_close CHECK (high >= close),
    CONSTRAINT valid_low_open CHECK (low <= open),
    CONSTRAINT valid_low_close CHECK (low <= close),
    CONSTRAINT valid_volume CHECK (volume >= 0)
);

-- Indexes for fast queries
CREATE INDEX idx_ohlcv_symbol_timeframe ON ohlcv_data (symbol, timeframe, timestamp);
CREATE INDEX idx_ohlcv_timestamp ON ohlcv_data (timestamp);

-- TimescaleDB hypertable (7-day chunks)
SELECT create_hypertable('ohlcv_data', 'timestamp', chunk_time_interval => INTERVAL '7 days');
```

## Usage Examples

### FastAPI Route Handler

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from hl_bot.dependencies import get_db
from hl_bot.repositories import OHLCVRepository
from hl_bot.types import Candle, Timeframe

router = APIRouter()

@router.get("/candles/{symbol}")
async def get_candles(
    symbol: str,
    timeframe: Timeframe,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    repo = OHLCVRepository(db)
    candles = repo.get_candles(symbol, timeframe, limit=limit)
    return {"candles": candles}
```

### Batch Data Import

```python
from datetime import datetime, timedelta
from hl_bot.repositories import OHLCVRepository
from hl_bot.types import Candle, Timeframe
from hl_bot.db import get_db_session

# Create repository
db = get_db_session()
repo = OHLCVRepository(db)

# Prepare batch data
base_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
candles = [
    Candle(
        timestamp=base_time + timedelta(hours=i),
        symbol="BTC-USD",
        timeframe=Timeframe.H1,
        open=50000.0,
        high=51000.0,
        low=49500.0,
        close=50500.0,
        volume=1000.0,
    )
    for i in range(1000)
]

# Insert batch (idempotent - duplicates ignored)
inserted = repo.insert_candles_batch(candles)
print(f"Inserted {inserted} new candles")

db.close()
```

### Query with Time Range

```python
from datetime import datetime, timezone
from hl_bot.repositories import OHLCVRepository
from hl_bot.types import Timeframe
from hl_bot.db import get_db_session

db = get_db_session()
repo = OHLCVRepository(db)

# Get candles for specific date range
start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
end = datetime(2024, 1, 31, 23, 59, tzinfo=timezone.utc)

candles = repo.get_candles(
    symbol="BTC-USD",
    timeframe=Timeframe.D1,
    start_time=start,
    end_time=end,
)

print(f"Found {len(candles)} daily candles for January 2024")

db.close()
```

### Data Exploration

```python
from hl_bot.repositories import OHLCVRepository
from hl_bot.db import get_db_session

db = get_db_session()
repo = OHLCVRepository(db)

# What symbols do we have?
symbols = repo.get_available_symbols()
print(f"Available symbols: {symbols}")

# What timeframes for BTC?
timeframes = repo.get_available_timeframes("BTC-USD")
print(f"BTC timeframes: {timeframes}")

# When does our data start/end?
time_range = repo.get_time_range("BTC-USD", Timeframe.H1)
if time_range:
    earliest, latest = time_range
    print(f"Data range: {earliest} to {latest}")

db.close()
```

## Quality Checklist

- [x] Repository pattern for clean separation of concerns
- [x] Specific column selection (no SELECT *)
- [x] Parameterized queries (SQLAlchemy ORM)
- [x] Batch operations for efficiency
- [x] Idempotent inserts (ON CONFLICT DO NOTHING)
- [x] Time-series optimized queries
- [x] Proper index usage
- [x] Type-safe with Pydantic models
- [x] Comprehensive test coverage
- [x] Database constraints enforced
- [x] Connection pooling configured
- [x] Session lifecycle managed
- [x] Documentation and examples

## Database Excellence Principles Applied

✅ **Model the domain, not the UI**
- Schema represents candlestick data accurately
- Composite primary key reflects natural uniqueness

✅ **Data integrity is non-negotiable**
- CHECK constraints validate OHLCV relationships
- Foreign key behavior defined
- NOT NULL on critical fields

✅ **Optimize for reads you actually make**
- Indexes on (symbol, timeframe, timestamp)
- TimescaleDB hypertable for time-series performance
- Efficient count queries without loading data

✅ **Repository pattern**
- Clean abstraction over database access
- No SQL in route handlers
- Easy to test and mock

✅ **Batch operations**
- `insert_candles_batch()` for efficient bulk inserts
- ON CONFLICT handling for idempotency

✅ **Type safety**
- Pydantic models at API boundary
- SQLAlchemy models at database layer
- Conversion layer in repository

## Performance Characteristics

### TimescaleDB Optimization
- Data partitioned into 7-day chunks
- Fast time-range queries
- Automatic data retention policies possible
- Parallel query execution

### Query Performance
- **Single candle lookup**: O(1) with primary key
- **Time range query**: O(log n) with B-tree index
- **Latest candle**: O(log n) with index on timestamp DESC
- **Batch insert**: O(n) with single round-trip

### Connection Pool
- Pool size: 10 connections
- Max overflow: 20 connections
- Pre-ping enabled for connection health
- Auto-reconnect on failure

## Next Steps

The following tasks are now unblocked:

1. **csv-import** (Task ID: csv-import)
   - Use `OHLCVRepository.insert_candles_batch()` for bulk imports
   - Parse TradingView CSV exports
   - Validate and import into database

2. **tf-alignment** (Task ID: tf-alignment)
   - Use `OHLCVRepository.get_candles()` to fetch multiple timeframes
   - Align timestamps across timeframes
   - Build multi-timeframe data structures

3. **Pattern detection** (Task IDs: candle-patterns, market-structure, zones)
   - Query candles using repository
   - Process OHLCV data for pattern detection
   - Store results in respective tables

## Files Created

### Core Implementation:
- `src/hl_bot/db/__init__.py` - Database module exports
- `src/hl_bot/db/session.py` - Session management (1.7KB)
- `src/hl_bot/repositories/ohlcv_repository.py` - Repository implementation (12KB)
- `src/hl_bot/repositories/__init__.py` - Updated exports

### Dependencies:
- `src/hl_bot/dependencies.py` - Updated with DB and repo factories

### Tests:
- `tests/integration/test_ohlcv_repository.py` - Integration tests (7.7KB)
- `tests/unit/test_ohlcv_repository.py` - Unit tests (13KB)

### Documentation:
- `DATA_MODELS_COMPLETE.md` - This file

## Running Tests

```bash
# Integration tests (requires PostgreSQL running)
cd /opt/swarmops/projects/hl-bot-v2/backend
poetry run pytest tests/integration/test_ohlcv_repository.py -v

# All tests
poetry run pytest tests/unit/test_ohlcv_repository.py tests/integration/test_ohlcv_repository.py -v
```

---

**Task Status:** COMPLETE  
**Ready for:** CSV import, multi-timeframe alignment, pattern detection  
**Updated:** progress.md will be marked as [x] for data-models task
