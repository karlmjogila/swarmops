# OHLCV Data Models and Repository

## Overview

This module implements the data access layer for OHLCV (Open, High, Low, Close, Volume) candlestick data. It follows the **repository pattern** to separate database logic from business logic, making the codebase more maintainable and testable.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Business Logic                      │
│          (Pattern Detection, Backtest, etc.)         │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│              OHLCVRepository                         │
│   (Clean data access interface - no SQLAlchemy)     │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│             SQLAlchemy Models                        │
│         (OHLCVData - TimescaleDB)                    │
└─────────────────────────────────────────────────────┘
```

## Components

### 1. Database Model (`app/db/models.py`)

**OHLCVData** - SQLAlchemy model for OHLCV candlestick data

- **Primary Key:** Composite of (timestamp, symbol, timeframe)
- **TimescaleDB Hypertable:** Optimized for time-series queries
- **Constraints:** Validates price relationships (high >= low, etc.)
- **Indexes:** Optimized for common query patterns

```python
from app.db.models import OHLCVData

# Model is already defined in app/db/models.py
# Managed via Alembic migrations
```

### 2. Repository (`app/db/repositories/ohlcv.py`)

**OHLCVRepository** - Data access layer with clean interface

#### Core Methods

##### Query Operations
```python
from app.db.repositories import OHLCVRepository
from datetime import datetime, timezone

repo = OHLCVRepository(db_session)

# Get candles in time range
candles = repo.get_candles(
    symbol="BTC-USD",
    timeframe="15m",
    start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
    end_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
    limit=1000,  # Optional
)

# Get latest candle
latest = repo.get_latest_candle("BTC-USD", "15m")

# Get last N candles (ordered chronologically)
last_100 = repo.get_last_n_candles("BTC-USD", "15m", 100)

# Get candles after a specific time (for incremental updates)
new_candles = repo.get_candles_since(
    "BTC-USD",
    "15m",
    since=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
)
```

##### Insert Operations
```python
# Insert single candle
candle = repo.insert_candle(
    symbol="BTC-USD",
    timeframe="5m",
    timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
    open_price=50000.0,
    high=50100.0,
    low=49900.0,
    close=50050.0,
    volume=100.0,
)

# Bulk insert (efficient for large datasets)
candles = [
    {
        "symbol": "BTC-USD",
        "timeframe": "5m",
        "timestamp": datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        "open": 50000.0,
        "high": 50100.0,
        "low": 49900.0,
        "close": 50050.0,
        "volume": 100.0,
    },
    # ... more candles
]
inserted_count = repo.bulk_insert_candles(candles)
```

##### Metadata Operations
```python
# Get available symbols
symbols = repo.get_available_symbols()  # ["BTC-USD", "ETH-USD", ...]

# Get available timeframes for a symbol
timeframes = repo.get_available_timeframes("BTC-USD")  # ["5m", "15m", "1h", ...]

# Get time range for data
earliest, latest = repo.get_time_range("BTC-USD", "15m")

# Count candles
count = repo.count_candles("BTC-USD", "15m")

# Get aggregate statistics
stats = repo.get_ohlc_aggregates(
    "BTC-USD", "15m",
    start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
    end_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
)
# Returns: {"min_low": 49000, "max_high": 51000, "total_volume": 10000, "candle_count": 96}
```

### 3. Data Utilities (`app/core/market/data.py`)

**Candle** - Lightweight dataclass for business logic

Decoupled from SQLAlchemy to avoid coupling business logic to database models.

```python
from app.core.market.data import Candle, validate_ohlcv, calculate_price_change

# Create candle from repository data
candle = Candle(
    timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
    open=50000.0,
    high=50200.0,
    low=49900.0,
    close=50150.0,
    volume=100.0,
    symbol="BTC-USD",
    timeframe="5m",
)

# Properties
candle.body_size          # 150.0
candle.wick_size_upper    # 50.0
candle.wick_size_lower    # 100.0
candle.total_range        # 300.0
candle.is_bullish         # True
candle.is_bearish         # False
candle.is_doji()          # False

# Utility functions
valid, error = validate_ohlcv(50000, 50100, 49900, 50050, 100)
change, percent = calculate_price_change(candle)  # (150.0, 0.3%)
```

#### Helper Functions

```python
from app.core.market.data import (
    find_highest_candle,
    find_lowest_candle,
    calculate_average_volume,
    is_volume_spike,
    align_timestamp_to_timeframe,
    get_timeframe_minutes,
)

# Find extremes
highest = find_highest_candle(candles)
lowest = find_lowest_candle(candles)

# Volume analysis
avg_vol = calculate_average_volume(candles)
spike = is_volume_spike(candle, avg_vol, threshold=2.0)

# Timeframe utilities
aligned = align_timestamp_to_timeframe(
    datetime(2024, 1, 1, 14, 27, 35),
    "5m"
)  # Returns: 2024-01-01 14:25:00

minutes = get_timeframe_minutes("1h")  # Returns: 60
```

## Usage Examples

### Example 1: Importing Data

```python
from app.db.session import get_db
from app.db.repositories import OHLCVRepository
from app.core.market.data import validate_ohlcv

def import_csv_data(file_path: str):
    """Import OHLCV data from CSV file."""
    db = next(get_db())
    repo = OHLCVRepository(db)
    
    candles = []
    with open(file_path) as f:
        for line in csv.DictReader(f):
            # Validate data
            valid, error = validate_ohlcv(
                float(line["open"]),
                float(line["high"]),
                float(line["low"]),
                float(line["close"]),
                float(line["volume"]),
            )
            
            if not valid:
                print(f"Skipping invalid candle: {error}")
                continue
            
            candles.append({
                "symbol": "BTC-USD",
                "timeframe": "5m",
                "timestamp": datetime.fromisoformat(line["timestamp"]),
                "open": float(line["open"]),
                "high": float(line["high"]),
                "low": float(line["low"]),
                "close": float(line["close"]),
                "volume": float(line["volume"]),
            })
    
    # Bulk insert
    count = repo.bulk_insert_candles(candles)
    db.commit()
    print(f"Imported {count} candles")
```

### Example 2: Pattern Detection

```python
from app.db.repositories import OHLCVRepository
from app.core.market.data import from_db_model

def detect_patterns(symbol: str, timeframe: str):
    """Detect patterns in recent candles."""
    db = next(get_db())
    repo = OHLCVRepository(db)
    
    # Get last 100 candles
    db_candles = repo.get_last_n_candles(symbol, timeframe, 100)
    
    # Convert to business logic objects
    candles = [from_db_model(c) for c in db_candles]
    
    # Analyze patterns
    for candle in candles:
        if candle.is_doji():
            print(f"Doji at {candle.timestamp}")
        
        if is_volume_spike(candle, avg_volume, threshold=2.0):
            print(f"Volume spike at {candle.timestamp}")
```

### Example 3: Multi-Timeframe Analysis

```python
def get_multi_tf_context(symbol: str, timestamp: datetime):
    """Get candles from multiple timeframes at a specific time."""
    db = next(get_db())
    repo = OHLCVRepository(db)
    
    timeframes = ["5m", "15m", "1h", "4h"]
    context = {}
    
    for tf in timeframes:
        # Get candles around the timestamp
        candles = repo.get_candles(
            symbol,
            tf,
            start_time=timestamp - timedelta(hours=4),
            end_time=timestamp,
        )
        context[tf] = [from_db_model(c) for c in candles]
    
    return context
```

## Database Schema

### Table: `ohlcv_data`

```sql
CREATE TABLE ohlcv_data (
    timestamp    TIMESTAMPTZ NOT NULL,
    symbol       VARCHAR(20) NOT NULL,
    timeframe    VARCHAR(10) NOT NULL,
    open         FLOAT NOT NULL,
    high         FLOAT NOT NULL,
    low          FLOAT NOT NULL,
    close        FLOAT NOT NULL,
    volume       FLOAT NOT NULL DEFAULT 0.0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (timestamp, symbol, timeframe),
    
    CONSTRAINT valid_high_low CHECK (high >= low),
    CONSTRAINT valid_high_open CHECK (high >= open),
    CONSTRAINT valid_high_close CHECK (high >= close),
    CONSTRAINT valid_low_open CHECK (low <= open),
    CONSTRAINT valid_low_close CHECK (low <= close),
    CONSTRAINT valid_volume CHECK (volume >= 0)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('ohlcv_data', 'timestamp');

-- Indexes for performance
CREATE INDEX idx_ohlcv_symbol_timeframe ON ohlcv_data (symbol, timeframe, timestamp);
CREATE INDEX idx_ohlcv_timestamp ON ohlcv_data (timestamp);
```

### Composite Primary Key

Using `(timestamp, symbol, timeframe)` as primary key ensures:
- No duplicate candles for same time/symbol/timeframe
- Natural time-series partitioning for TimescaleDB
- Efficient queries by time range

## Testing

Comprehensive test coverage in `tests/unit/`:

- `test_ohlcv_repository.py` - Repository CRUD operations
- `test_ohlcv_data.py` - Data utilities and calculations

Run tests:
```bash
cd backend
poetry run pytest tests/unit/test_ohlcv_*.py -v
```

## Performance Considerations

### 1. Bulk Inserts
- Use `bulk_insert_candles()` for importing large datasets
- Processes in batches of 1000 to avoid memory issues
- Silently skips duplicates

### 2. Query Optimization
- Indexes on `(symbol, timeframe, timestamp)` for fast range queries
- TimescaleDB hypertable for time-series optimization
- Use `limit` parameter to prevent loading massive datasets

### 3. Avoid N+1 Queries
```python
# BAD - N+1 query
for symbol in symbols:
    candles = repo.get_last_n_candles(symbol, "5m", 100)

# GOOD - Batch query
symbols = repo.get_available_symbols()
all_candles = {}
for symbol in symbols:
    all_candles[symbol] = repo.get_last_n_candles(symbol, "5m", 100)
```

## Best Practices

### 1. Always Use UTC Timezone
```python
from datetime import datetime, timezone

# GOOD
timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)

# BAD - no timezone
timestamp = datetime(2024, 1, 1, 0, 0)
```

### 2. Validate Data Before Insert
```python
valid, error = validate_ohlcv(open, high, low, close, volume)
if not valid:
    print(f"Invalid data: {error}")
    return
```

### 3. Use Transactions for Multi-Step Operations
```python
try:
    repo.bulk_insert_candles(candles)
    db.commit()
except Exception as e:
    db.rollback()
    print(f"Import failed: {e}")
```

### 4. Separate Business Logic from Database Models
```python
# Convert DB models to business objects at repository boundary
db_candles = repo.get_last_n_candles("BTC-USD", "5m", 100)
candles = [from_db_model(c) for c in db_candles]

# Now work with clean Candle dataclass, not SQLAlchemy models
```

## Future Enhancements

Potential additions (not in current scope):

- [ ] Data resampling (5m → 15m, 1h, etc.)
- [ ] Gap detection and filling
- [ ] Data quality monitoring
- [ ] Retention policies (auto-delete old data)
- [ ] Compression (TimescaleDB native compression)

---

**Status:** ✅ Implemented  
**Phase:** 2. Data Layer  
**Dependencies:** backend-init, db-setup, types  
**Test Coverage:** ~90% (repository + utilities)
