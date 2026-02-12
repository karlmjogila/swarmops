# TradingView Lightweight Charts Integration

This document explains the TradingView lightweight-charts integration in the HL-Bot-V2 frontend.

## Overview

The chart system provides professional-grade financial charting with:
- Multi-timeframe candlestick charts
- Trade entry/exit markers
- Support/resistance zones
- Market structure annotations
- Real-time WebSocket updates (Phase 4)

## Components

### `TradingChart.svelte`

Base chart component wrapping TradingView lightweight-charts.

**Props:**
- `candles: Candle[]` - OHLCV data to display
- `markers?: ChartMarker[]` - Entry/exit/signal markers
- `annotations?: ChartAnnotation[]` - Lines, rectangles, text
- `zones?: Zone[]` - Support/resistance zones
- `structures?: MarketStructure[]` - BOS, CHoCH, FVG, etc.
- `height?: number` - Chart height in pixels (default: 500)
- `width?: number | string` - Chart width (default: '100%')
- `onCrosshairMove?: (price, time) => void` - Crosshair callback

**Example:**
```svelte
<script>
  import { TradingChart } from '$lib/components';
  
  const candles = [
    {
      timestamp: '2024-01-01T00:00:00Z',
      open: 50000,
      high: 51000,
      low: 49500,
      close: 50500,
      volume: 1000,
      timeframe: '15m',
      symbol: 'BTCUSD',
    },
    // ... more candles
  ];
</script>

<TradingChart {candles} height={600} />
```

### `MultiTimeframeChart.svelte`

Full-featured chart with timeframe selector, price info, and legend.

**Props:**
- `candleData: Record<Timeframe, Candle[]>` - Data for all timeframes
- `trades?: Trade[]` - Trades to display as markers
- `signals?: Signal[]` - Signals to display as markers
- `zones?: Zone[]` - Support/resistance zones
- `structures?: MarketStructure[]` - Market structure elements
- `activeTimeframe?: Timeframe` - Selected timeframe (bindable)
- `onTimeframeChange?: (tf) => void` - Timeframe change callback

**Example:**
```svelte
<script>
  import { MultiTimeframeChart } from '$lib/components';
  
  const candleData = {
    '5m': [...],
    '15m': [...],
    '30m': [...],
    '1h': [...],
    '4h': [...],
    '1d': [...],
  };
  
  const trades = [...];
  
  let activeTimeframe = '15m';
</script>

<MultiTimeframeChart
  {candleData}
  {trades}
  bind:activeTimeframe
  onTimeframeChange={(tf) => console.log('Switched to', tf)}
/>
```

## Utilities (`chartHelpers.ts`)

### Time Conversion

```typescript
import { isoToChartTime, unixToChartTime } from '$lib/utils/chartHelpers';

const time1 = isoToChartTime('2024-01-01T00:00:00Z');
const time2 = unixToChartTime(1704067200);
```

### Marker Generation

```typescript
import { 
  createEntryMarker, 
  createExitMarker,
  createTradeMarkers,
  createSignalMarkers 
} from '$lib/utils/chartHelpers';

// Single entry marker
const marker = createEntryMarker(
  '2024-01-01T00:00:00Z',
  'long',
  'LONG Entry'
);

// All markers from trades
const markers = createTradeMarkers(trades);

// All markers from signals
const signalMarkers = createSignalMarkers(signals);
```

### Data Validation

```typescript
import { validateCandle, validateCandles, sortCandles } from '$lib/utils/chartHelpers';

// Validate single candle
if (validateCandle(candle)) {
  // Safe to use
}

// Validate and filter array
const validCandles = validateCandles(candles);

// Sort by timestamp
const sortedCandles = sortCandles(candles);
```

### Performance Metrics

```typescript
import { 
  calculateWinRate,
  calculateTotalPnL,
  calculateProfitFactor 
} from '$lib/utils/chartHelpers';

const winRate = calculateWinRate(trades);        // 0-1
const totalPnl = calculateTotalPnL(trades);      // number
const profitFactor = calculateProfitFactor(trades); // number
```

### Formatting

```typescript
import { formatPrice, formatPercent, formatPnL } from '$lib/utils/chartHelpers';

formatPrice(50123.45);              // "50123.45"
formatPercent(0.0234);              // "2.34%"
formatPnL(123.45);                  // { text: "+123.45", color: "#4caf50" }
```

## Color Scheme

The chart uses a professional dark theme with semantic colors:

| Element | Color | Hex |
|---------|-------|-----|
| Bull Candle | Green | `#26a69a` |
| Bear Candle | Red | `#ef5350` |
| Long Entry | Green | `#26a69a` |
| Short Entry | Red | `#ef5350` |
| Take Profit | Green | `#4caf50` |
| Stop Loss | Red | `#f44336` |
| Breakeven | Orange | `#ff9800` |
| Support/Demand | Green (15% opacity) | `rgba(38, 166, 154, 0.15)` |
| Resistance/Supply | Red (15% opacity) | `rgba(239, 83, 80, 0.15)` |
| BOS | Blue | `#2196f3` |
| CHoCH | Purple | `#9c27b0` |

## Data Validation

Following the **Trading Systems Excellence** principles, all data is validated before rendering:

1. **Timestamp validation** - Ensures valid ISO 8601 dates
2. **OHLC relationships** - Validates high ≥ open/close and low ≤ open/close
3. **Price sanity** - Rejects negative prices
4. **Type safety** - TypeScript enforces correct types at compile time

All validation errors are logged to console but don't crash the chart.

## TypeScript Types

All chart types are defined in `$lib/types/index.ts`:

- `Candle` - OHLCV data
- `ChartMarker` - Entry/exit markers
- `ChartAnnotation` - Lines and shapes
- `Zone` - Support/resistance zones
- `MarketStructure` - BOS, CHoCH, FVG, etc.
- `Trade` - Trade record with P&L
- `Signal` - Trading signal

All types use:
- **Readonly properties** - Immutable by default
- **Branded types** - IDs are type-safe (`TradeId`, `SignalId`)
- **Discriminated unions** - Type-safe state handling
- **Zero `any`** - Full type safety

## WebSocket Integration (Phase 4)

The chart will integrate with WebSocket streams for real-time updates:

```typescript
// WebSocket message handling (coming in Phase 4)
import { isWSCandleMessage } from '$lib/types';

websocket.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (isWSCandleMessage(message)) {
    // Update chart with new candle
    candlestickSeries.update(convertCandleData(message.data));
  }
};
```

## Performance Considerations

1. **Data chunking** - Only render visible candles for large datasets
2. **Marker limits** - Limit markers to visible range to prevent slowdown
3. **Update batching** - Batch multiple updates into single render
4. **Lazy loading** - Load historical data on-demand when scrolling

## Testing

The `/backtest` page includes demo data for testing the chart:

```bash
npm run dev
# Navigate to http://localhost:5173/backtest
```

## Dependencies

- `lightweight-charts` - TradingView's official charting library
- `svelte` - Component framework
- `typescript` - Type safety

## Future Enhancements (Post-Phase 7)

- [ ] Custom drawing tools (trendlines, Fibonacci)
- [ ] Volume profile display
- [ ] Order book visualization
- [ ] Heatmap overlays
- [ ] Chart snapshots/export
- [ ] Mobile touch controls
- [ ] Multi-chart layouts (2x2, 3x1, etc.)

---

**Created:** 2025-02-11  
**Phase:** 7 - Frontend Charts  
**Status:** ✅ Complete
