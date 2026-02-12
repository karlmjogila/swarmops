# CSV Import Service for TradingView Data

Robust, production-ready CSV import pipeline for OHLCV market data from TradingView exports.

## Features

✅ **Schema Validation** - All data validated at ingestion boundary  
✅ **Dead Letter Queue** - Invalid records logged for inspection, never lost  
✅ **Idempotent** - Re-importing same data produces no duplicates  
✅ **Batch Processing** - Efficient bulk inserts for large datasets  
✅ **Multiple Formats** - Supports Unix timestamps, ISO format, TradingView format  
✅ **Comprehensive Stats** - Detailed import statistics and success rates  
✅ **Error Handling** - Graceful degradation, atomic transactions  

## Quick Start

### 1. Export CSV from TradingView

In TradingView:
1. Open your chart
2. Click the three dots menu (...)
3. Select "Export chart data"
4. Download CSV file

### 2. Import via API

```bash
# Upload CSV file
curl -X POST "http://localhost:8000/api/data/import?symbol=BTC-USD&timeframe=5m" \
  -F "file=@your_export.csv"

# Or send raw CSV content
curl -X POST "http://localhost:8000/api/data/import/raw" \
  -H "Content-Type: application/json" \
  -d '{
    "csv_content": "time,open,high,low,close,volume\n...",
    "symbol": "BTC-USD",
    "timeframe": "5m"
  }'
```

### 3. Verify Import

```bash
# Check available data
curl "http://localhost:8000/api/data/available"

# Get data range
curl "http://localhost:8000/api/data/range?symbol=BTC-USD&timeframe=5m"
```

## CSV Format

### Required Columns

- `time` - Timestamp (Unix, ISO, or TradingView format)
- `open` - Open price (positive number)
- `high` - High price (must be >= open, close, low)
- `low` - Low price (must be <= open, close, high)
- `close` - Close price (positive number)

### Optional Columns

- `volume` - Trade volume (non-negative, defaults to 0.0)

### Supported Timestamp Formats

```csv
# Unix timestamp (seconds)
time,open,high,low,close,volume
1704067200,50000.0,50100.0,49900.0,50050.0,100.5

# Unix timestamp (milliseconds)
time,open,high,low,close,volume
1704067200000,50000.0,50100.0,49900.0,50050.0,100.5

# ISO format
time,open,high,low,close,volume
2024-01-01T00:00:00Z,50000.0,50100.0,49900.0,50050.0,100.5

# TradingView format (space separator)
time,open,high,low,close,volume
2024-01-01 00:00:00,50000.0,50100.0,49900.0,50050.0,100.5
```

### Example CSV

```csv
time,open,high,low,close,volume
2024-01-01 00:00:00,50000.0,50100.0,49900.0,50050.0,100.5
2024-01-01 00:05:00,50050.0,50200.0,50000.0,50150.0,120.3
2024-01-01 00:10:00,50150.0,50250.0,50100.0,50200.0,95.7
```

See `examples/sample_tradingview.csv` for a complete example.

## API Endpoints

### POST /api/data/import

Upload CSV file for import.

**Parameters:**
- `file` (form-data) - CSV file
- `symbol` (query) - Trading symbol (e.g., "BTC-USD")
- `timeframe` (query) - Candle timeframe (e.g., "5m", "15m", "1h")

**Response:**
```json
{
  "success": true,
  "message": "Successfully imported 100 candles. 0 duplicates skipped.",
  "stats": {
    "run_id": "abc-123",
    "symbol": "BTC-USD",
    "timeframe": "5m",
    "extracted": 100,
    "valid": 100,
    "invalid": 0,
    "inserted": 100,
    "duplicates": 0,
    "success_rate": "100.00%"
  }
}
```

### POST /api/data/import/raw

Import from raw CSV content (JSON body).

**Request:**
```json
{
  "csv_content": "time,open,high,low,close\n...",
  "symbol": "BTC-USD",
  "timeframe": "5m"
}
```

### GET /api/data/range

Get time range of available data.

**Parameters:**
- `symbol` (query) - Trading symbol
- `timeframe` (query) - Candle timeframe

**Response:**
```json
{
  "symbol": "BTC-USD",
  "timeframe": "5m",
  "earliest": "2024-01-01T00:00:00+00:00",
  "latest": "2024-01-31T23:55:00+00:00",
  "candle_count": 8928
}
```

### GET /api/data/available

List all available symbols and timeframes.

**Response:**
```json
{
  "symbols": ["BTC-USD", "ETH-USD"],
  "timeframes": ["5m", "15m", "1h"]
}
```

### DELETE /api/data/clear

Delete candles for a symbol and timeframe.

**Parameters:**
- `symbol` (query) - Trading symbol
- `timeframe` (query) - Candle timeframe
- `start_time` (query, optional) - Start of time range (ISO format)
- `end_time` (query, optional) - End of time range (ISO format)

⚠️ **Warning:** This operation is irreversible.

## Programmatic Usage

### Python Example

```python
from pathlib import Path
from app.db.session import SessionLocal
from app.db.repositories.ohlcv import OHLCVRepository
from app.core.market.importer import CSVImporter

# Create session and repository
db = SessionLocal()
repo = OHLCVRepository(db)
importer = CSVImporter(dlq_dir=Path("./data/dlq"))

try:
    # Import from file
    stats = importer.import_from_file(
        Path("btc_5m.csv"),
        symbol="BTC-USD",
        timeframe="5m",
        repository=repo
    )
    
    # Commit transaction
    db.commit()
    
    print(f"Imported {stats.inserted} candles")
    print(f"Success rate: {stats.success_rate:.2f}%")
    
finally:
    db.close()
```

See `examples/csv_import_example.py` for more examples.

## Data Validation

### Price Validation Rules

1. All prices must be positive (> 0)
2. `high` must be >= `open`, `close`, and `low`
3. `low` must be <= `open`, `close`, and `high`
4. Volume must be non-negative (>= 0)
5. Timestamps must not be in the future

### What Happens to Invalid Records?

Invalid records are:
1. **Logged** to dead letter queue (`data/dlq/dlq-{run_id}.jsonl`)
2. **Counted** in import statistics
3. **Not inserted** into database

Good records continue processing - one bad record doesn't kill the entire import.

### Dead Letter Queue (DLQ)

Invalid records are stored in JSONL format:

```json
{"line_number": 42, "raw_data": {...}, "error": "High (49900.0) must be >= close (50050.0)", "timestamp": "2024-01-01T12:00:00Z"}
```

You can:
- Inspect invalid records
- Fix source data
- Re-import corrected data

## Idempotency

Re-importing the same data **does not create duplicates**.

```bash
# First import
$ curl -X POST ".../import?symbol=BTC-USD&timeframe=5m" -F "file=@data.csv"
{"inserted": 100, "duplicates": 0}

# Second import (same data)
$ curl -X POST ".../import?symbol=BTC-USD&timeframe=5m" -F "file=@data.csv"
{"inserted": 0, "duplicates": 100}
```

Duplicates are detected by composite key: `(symbol, timeframe, timestamp)`

## Performance

- **Batch Processing:** Processes records in batches of 1000
- **Bulk Inserts:** Uses SQLAlchemy bulk operations
- **Typical Speed:** ~10,000 candles/second on modern hardware

## Error Handling

### Graceful Degradation

- Invalid records → DLQ, valid records continue
- Database constraints → rollback batch, retry individual inserts
- Timestamp parsing errors → record logged to DLQ

### Transaction Safety

- All inserts wrapped in database transactions
- Rollback on error
- No partial data corruption

## Testing

Run unit tests:

```bash
cd backend
pytest tests/test_csv_importer.py -v
```

Run examples:

```bash
cd backend
python examples/csv_import_example.py
```

## Common Issues

### Issue: "CSV missing required columns"

**Solution:** Ensure CSV has headers: `time,open,high,low,close`

### Issue: "High must be >= close"

**Solution:** Check data quality - prices may be corrupted in export

### Issue: "Unable to parse timestamp"

**Solution:** Supported formats are Unix (seconds/ms), ISO, and TradingView format

### Issue: No data inserted (0 inserted)

**Solution:** Check DLQ file for validation errors:
```bash
cat data/dlq/dlq-*.jsonl | jq .
```

## Architecture

```
┌─────────────┐
│  CSV File   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│    Extract      │ ─── Read raw CSV rows
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│    Validate     │ ─── Schema validation (Pydantic)
└──────┬──────────┘
       │
       ├─── Invalid ──▶ Dead Letter Queue
       │
       ▼ Valid
┌─────────────────┐
│   Transform     │ ─── Normalize timestamps, align to timeframe
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│     Load        │ ─── Bulk insert to TimescaleDB
└──────┬──────────┘
       │
       ▼
   Statistics
```

## Data Engineering Best Practices

✅ **Idempotent by design** - Safe to re-run  
✅ **Schema is a contract** - Validate early, fail fast  
✅ **Fail gracefully** - Bad records isolated, good records flow  
✅ **Atomic operations** - All-or-nothing transactions  
✅ **Observable** - Comprehensive stats and logging  
✅ **Recoverable** - DLQ enables data recovery  

## Next Steps

- [ ] Add multi-file batch import
- [ ] Support compressed CSV (gzip)
- [ ] Add data quality reports
- [ ] Implement automatic backfill detection
- [ ] Add webhook notifications on import complete

## Support

For issues or questions:
1. Check DLQ files for validation errors
2. Run examples to verify setup
3. Check logs for detailed error messages

---

**Last Updated:** 2025-02-11  
**Version:** 1.0.0
