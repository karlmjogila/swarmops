# Data Source Selection in Backtest UI

## Status: ✅ Fully Implemented

The data source selection feature for backtests is fully implemented across the entire stack.

## Overview

When starting a backtest, users can choose where the OHLCV data comes from:

| Option | Description |
|--------|-------------|
| **Auto** (default) | Prefers Hyperliquid data, automatically falls back to CSV if not available |
| **Hyperliquid** | Use only data fetched from Hyperliquid API |
| **CSV** | Use only data imported from CSV files |

## Implementation Details

### Backend API

**`app/api/routes/backtest.py`**

```python
# Request model with data_source field
class BacktestStartRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 10000.0
    data_source: Literal['hyperliquid', 'csv', 'auto'] = 'auto'
    # ... other fields

# Data availability endpoint
@router.get("/data-availability")
async def get_data_availability(
    symbol: str,
    timeframe: str = "1h",
    db: Session = Depends(get_db),
) -> DataAvailabilityResponse:
    """Returns data availability for each source (hyperliquid, csv)."""
```

### OHLCV Repository

**`app/db/repositories/ohlcv.py`**

```python
def get_candles(
    self,
    symbol: str,
    timeframe: str,
    start_time: datetime,
    end_time: datetime,
    source: Optional[DataSource] = None,  # 'hyperliquid', 'csv', 'auto'
) -> List[OHLCVData]:
    """
    For 'auto' mode:
    1. Try hyperliquid first
    2. Fall back to csv if no hyperliquid data
    """
```

### Database Model

**`app/db/models.py`**

```python
class OHLCVData(Base):
    __tablename__ = "ohlcv_data"
    
    # Primary key includes source
    timestamp = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(20), primary_key=True)
    timeframe = Column(String(10), primary_key=True)
    source = Column(String(20), primary_key=True, default='csv')  # 'hyperliquid' or 'csv'
```

### Backtest Runner

**`scripts/run_backtest_stream.py`**

```bash
python run_backtest_stream.py \
    --session-id abc123 \
    --symbol BTC \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --data-source auto  # hyperliquid, csv, or auto
```

### Frontend Components

**`src/routes/backtest/+page.svelte`**

- Backtest setup panel with DataSourceSelector
- Passes `data_source` parameter when starting backtest

**`src/lib/components/DataSourceSelector.svelte`**

- Shows three options: Auto, Hyperliquid, CSV
- Fetches data availability from `/api/backtest/data-availability`
- Displays date ranges and candle counts for each source
- Disables unavailable sources
- Shows which source 'auto' will use

**`src/lib/types/index.ts`**

```typescript
export const DataSource = {
  HYPERLIQUID: 'hyperliquid',
  CSV: 'csv',
  AUTO: 'auto',
} as const

export type DataSource = typeof DataSource[keyof typeof DataSource]

export interface DataSourceAvailability {
  readonly available: boolean
  readonly earliest: string | null
  readonly latest: string | null
  readonly candle_count: number
}
```

## User Interface

The DataSourceSelector component displays:

```
┌─────────────────────────────────────────────────────────────────┐
│  Symbol: [BTC▼]              Timeframe: [1h▼]                   │
├─────────────────────────────────────────────────────────────────┤
│  Data Source                                                     │
│                                                                  │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐                 │
│  │   Auto   │  │  Hyperliquid │  │    CSV     │                 │
│  │    ✓     │  │              │  │            │                 │
│  │ Prefer   │  │ Live API     │  │ Imported   │                 │
│  │ HL,      │  │ data         │  │ historical │                 │
│  │ fallback │  │              │  │ data       │                 │
│  │ to CSV   │  │ ✓ 1/1-12/31  │  │ No data    │                 │
│  │          │  │ (5,000)      │  │ available  │                 │
│  └──────────┘  └──────────────┘  └────────────┘                 │
│                                                                  │
│  📊 Data Availability                                            │
│  hyperliquid: 5,000    csv: —                                   │
└─────────────────────────────────────────────────────────────────┘
```

## API Example

```bash
# Start backtest with specific data source
curl -X POST "http://localhost:8000/api/backtest/start" \
     -H "Content-Type: application/json" \
     -d '{
       "symbol": "BTC",
       "start_date": "2024-01-01",
       "end_date": "2024-12-31",
       "initial_capital": 10000,
       "data_source": "hyperliquid"
     }'

# Check data availability
curl "http://localhost:8000/api/backtest/data-availability?symbol=BTC&timeframe=1h"

# Response:
{
  "symbol": "BTC",
  "timeframe": "1h",
  "sources": {
    "hyperliquid": {
      "available": true,
      "earliest": "2024-01-01T00:00:00Z",
      "latest": "2024-12-31T23:00:00Z",
      "candle_count": 5000
    },
    "csv": {
      "available": false,
      "earliest": null,
      "latest": null,
      "candle_count": 0
    }
  }
}
```

## How Auto Mode Works

1. Query OHLCV data with `source='auto'`
2. Repository first tries `source='hyperliquid'`
3. If no hyperliquid data found, falls back to `source='csv'`
4. If neither has data, raises error
5. Frontend shows which source 'auto' will actually use

## Files Involved

| File | Description |
|------|-------------|
| `backend/app/api/routes/backtest.py` | API endpoint with data_source param |
| `backend/app/db/models.py` | OHLCVData model with source column |
| `backend/app/db/repositories/ohlcv.py` | Repository with source filtering |
| `backend/scripts/run_backtest_stream.py` | Backtest runner script |
| `frontend/src/routes/backtest/+page.svelte` | Backtest page with selector |
| `frontend/src/lib/components/DataSourceSelector.svelte` | UI component |
| `frontend/src/lib/types/index.ts` | TypeScript types |
