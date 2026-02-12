# Chart Components

This directory contains trading chart components for the Hyperliquid Trading Bot Suite frontend.

## MultiTimeframeChart.vue

A comprehensive trading chart component with multi-timeframe support, built with `lightweight-charts`.

### Features

- **Multi-Timeframe Support**: Switch between 1m, 5m, 15m, 30m, 1h, 4h, 1d, and 1w timeframes
- **Volume Display**: Toggle volume histogram overlay with color-coded buy/sell pressure
- **Interactive Controls**: Pan, zoom, crosshair, and fit content
- **Dark Mode**: Automatic theme detection and switching
- **Responsive**: Adapts to container size with automatic resize handling
- **Type-Safe**: Full TypeScript support with proper type definitions
- **Optimized**: Data caching and efficient re-rendering

### Usage

```vue
<template>
  <MultiTimeframeChart
    symbol="ETH/USD"
    :initial-timeframe="'15m'"
    :height="600"
    :show-volume="true"
  />
</template>

<script setup lang="ts">
// Component is auto-imported via Nuxt
const chartRef = ref<any>(null)

// Access chart methods programmatically
const handleRefresh = () => {
  chartRef.value?.refresh()
}

const handleFitContent = () => {
  chartRef.value?.fitContent()
}

const handleChangeTimeframe = (tf: Timeframe) => {
  chartRef.value?.changeTimeframe(tf)
}
</script>
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `symbol` | `string` | `undefined` | Trading pair symbol (e.g., "ETH/USD") |
| `initialTimeframe` | `Timeframe` | `'15m'` | Initial timeframe to display |
| `height` | `number` | `600` | Chart height in pixels |
| `showVolume` | `boolean` | `true` | Show volume histogram overlay |

### Exposed Methods

The component exposes the following methods via `defineExpose`:

- `refresh()`: Refresh chart data from API
- `fitContent()`: Fit all chart content in viewport
- `changeTimeframe(timeframe: Timeframe)`: Switch to a different timeframe
- `changeSymbol(symbol: string)`: Switch to a different trading pair
- `chart`: Access to underlying lightweight-charts instance
- `candlestickSeries`: Access to candlestick series
- `volumeSeries`: Access to volume series

### Architecture

The component is built using:

1. **Composition API** with `<script setup>` - Modern Vue 3 pattern
2. **useChartData Composable** - Manages data fetching, caching, and state
3. **TypeScript** - Full type safety with chart-specific types
4. **lightweight-charts** - High-performance charting library

### Data Flow

```
┌─────────────────────────────────────┐
│   MultiTimeframeChart Component     │
│                                     │
│  ┌───────────────────────────────┐ │
│  │   useChartData Composable     │ │
│  │                               │ │
│  │  - Data caching               │ │
│  │  - Timeframe management       │ │
│  │  - API communication          │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │   lightweight-charts          │ │
│  │                               │ │
│  │  - Rendering                  │ │
│  │  - Interactions               │ │
│  │  - Animations                 │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

## useChartData Composable

Located in `composables/useChartData.ts`, this composable manages chart data and state.

### Features

- **Data Caching**: Caches data per symbol/timeframe to minimize API calls
- **Reactive State**: All state is reactive and updates the chart automatically
- **Timeframe Management**: Handles timeframe switching and configuration
- **Error Handling**: Graceful error handling with error state

### Usage

```typescript
import { useChartData } from '~/composables/useChartData'

const {
  currentSymbol,
  currentTimeframe,
  loading,
  error,
  getCurrentData,
  availableTimeframes,
  loadData,
  changeTimeframe,
  changeSymbol,
} = useChartData()

// Load data
await loadData('ETH/USD', '15m')

// Change timeframe
await changeTimeframe('1h')

// Change symbol
await changeSymbol('BTC/USD')
```

### State

- `currentSymbol` (Ref<string>): Currently selected trading pair
- `currentTimeframe` (Ref<Timeframe>): Currently selected timeframe
- `loading` (Ref<boolean>): Loading state
- `error` (Ref<string | null>): Error message if any
- `lastUpdate` (Ref<number>): Timestamp of last data update

### Computed

- `getCurrentData` (ComputedRef<CandleData[]>): Candle data for current symbol/timeframe
- `availableTimeframes` (ComputedRef<TimeframeConfig[]>): List of available timeframes

### Methods

- `loadData(symbol, timeframe)`: Load candle data for symbol/timeframe
- `changeTimeframe(timeframe)`: Switch to different timeframe
- `changeSymbol(symbol)`: Switch to different symbol
- `updateLatestCandle(candle)`: Update or append the latest candle (for real-time)
- `clearCache()`: Clear all cached data
- `getTimeframeConfig(timeframe)`: Get configuration for a timeframe

## Chart Types

Located in `types/chart.ts`, these types provide type safety for chart components.

### Key Types

```typescript
// Timeframe type
type Timeframe = '1m' | '5m' | '15m' | '30m' | '1h' | '4h' | '1d' | '1w'

// Candle data structure
interface CandleData {
  time: number        // Unix timestamp in seconds
  open: number        // Open price
  high: number        // High price
  low: number         // Low price
  close: number       // Close price
  volume?: number     // Volume (optional)
}

// Market data structure
interface MarketData {
  symbol: string
  timeframe: Timeframe
  candles: CandleData[]
  lastUpdate: number
}

// Timeframe configuration
interface TimeframeConfig {
  value: Timeframe
  label: string       // Display label (e.g., "15 Minutes")
  seconds: number     // Duration in seconds
  chartInterval: string // TradingView interval format
}
```

## Integration with API

To connect the chart component to your backend API:

1. **Update `useChartData.ts`** - Replace the sample data generation with actual API calls:

```typescript
const fetchCandleData = async (
  symbol: string,
  timeframe: Timeframe,
  limit: number = 500
): Promise<CandleData[]> => {
  const response = await $fetch<{ candles: CandleData[] }>(
    `${apiBaseUrl}/api/market/candles`,
    {
      query: {
        symbol: symbol.replace('/', ''),
        timeframe,
        limit,
      }
    }
  )
  return response.candles
}
```

2. **WebSocket Updates** (Optional) - Add real-time candle updates:

```typescript
// In your component or composable
const wsUrl = useRuntimeConfig().public.wsUrl
const ws = new WebSocket(`${wsUrl}/market/${symbol}/${timeframe}`)

ws.onmessage = (event) => {
  const candle = JSON.parse(event.data)
  updateLatestCandle(candle)
}
```

## Performance Considerations

- **Data Caching**: Data is cached per symbol/timeframe to avoid redundant API calls
- **Efficient Rendering**: lightweight-charts is optimized for rendering thousands of candles
- **Lazy Loading**: Only fetch data when switching timeframes/symbols
- **Resize Optimization**: Uses ResizeObserver for efficient resize handling
- **Theme Updates**: Only re-applies chart options on theme change

## Trade Markers and Overlays

✅ **NOW AVAILABLE** - See [TRADE_MARKERS.md](./TRADE_MARKERS.md) for complete documentation.

The trade markers system provides visual indicators for trades on price charts:

- **ChartWithTradeMarkers**: Enhanced chart component with trade marker support
- **TradeMarkerTooltip**: Interactive tooltips showing trade details
- **useTradeMarkers**: Composable for marker state management

Features:
- Entry/exit markers with color-coded outcomes
- Stop-loss and take-profit visualization
- Trade zones and price lines
- Real-time trade statistics
- Interactive tooltips with trade actions

See the [Trade Markers Documentation](./TRADE_MARKERS.md) for detailed usage and API reference.

## Future Enhancements

- [x] Add trade markers to show entry/exit points ✅ COMPLETE
- [ ] Implement drawing tools (trendlines, rectangles, etc.)
- [ ] Add technical indicators (SMA, EMA, RSI, MACD)
- [ ] Support for multiple chart panes (price + indicator)
- [ ] Chart replay mode for backtesting
- [ ] Custom price alerts with visual markers
- [ ] Export chart as image
- [ ] Save/load chart templates
- [ ] Trade clustering and pattern recognition
- [ ] Performance analytics dashboard

## Troubleshooting

### Chart Not Rendering

- Ensure `lightweight-charts` is installed: `npm install lightweight-charts`
- Check that the chart container has a defined height
- Verify the component is mounted before initializing the chart

### Data Not Loading

- Check API endpoint configuration in `nuxt.config.ts`
- Verify the data format matches `CandleData` interface
- Check browser console for error messages

### Dark Mode Not Working

- Ensure Tailwind's dark mode is configured correctly
- Verify the `dark` class is applied to `document.documentElement`
- Check that theme observer is set up correctly

## Demo

A full demo is available at `/chart-demo` route. Run the development server and navigate to:

```
http://localhost:3000/chart-demo
```

## License

Part of the Hyperliquid Trading Bot Suite.

---

## ReplayControls.vue

A VCR-style control panel for historical data replay and backtesting visualization.

### Features

- **Playback Controls**: Play, pause, step forward/backward, reset
- **Variable Speed**: 0.25x to 16x playback speed
- **Timeline Scrubber**: Visual timeline with draggable seek control
- **Trade Markers**: Visual markers on timeline for buy/sell events
- **Status Bar**: Display current date, price, and volume
- **Loop Mode**: Automatic restart when reaching the end
- **Frame Counter**: Shows current position in dataset
- **Responsive**: Adapts to mobile and desktop layouts
- **Dark Mode**: Automatic theme switching

### Usage

```vue
<template>
  <ReplayControls
    :total-points="candleData.length"
    :current-time="currentCandle.time"
    :start-time="startTime"
    :end-time="endTime"
    :markers="tradeMarkers"
    :current-price="currentPrice"
    :current-volume="currentVolume"
    :show-status-bar="true"
    :show-stats="true"
    @play="onPlay"
    @pause="onPause"
    @seek="onSeek"
    @step="onStep"
    @reset="onReset"
    @speed-change="onSpeedChange"
    @settings="onSettings"
  />
</template>

<script setup lang="ts">
import type { TradeMarker } from '~/types/chart'

const candleData = ref<CandleData[]>([])
const currentIndex = ref(0)
const playbackSpeed = ref(1)

const currentCandle = computed(() => candleData.value[currentIndex.value])
const currentPrice = computed(() => currentCandle.value?.close)
const currentVolume = computed(() => currentCandle.value?.volume)

const startTime = computed(() => candleData.value[0]?.time || 0)
const endTime = computed(() => candleData.value[candleData.value.length - 1]?.time || 0)

const tradeMarkers = ref<TradeMarker[]>([
  { id: '1', time: 1707667200, type: 'buy', price: 3200, quantity: 1.5 },
  { id: '2', time: 1707670800, type: 'sell', price: 3285, quantity: 1.5, pnl: 127.5 },
])

function onPlay() {
  console.log('Playback started')
  // Start advancing currentIndex
}

function onPause() {
  console.log('Playback paused')
}

function onSeek(index: number) {
  currentIndex.value = index
  // Update chart to show this candle
}

function onStep(direction: 'forward' | 'backward') {
  console.log(`Step ${direction}`)
}

function onReset() {
  currentIndex.value = 0
}

function onSpeedChange(speed: number) {
  playbackSpeed.value = speed
  console.log(`Speed changed to ${speed}x`)
}

function onSettings() {
  // Open settings modal
}
</script>
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `totalPoints` | `number` | `0` | Total number of data points (candles) |
| `currentTime` | `number` | `0` | Current timestamp (Unix seconds) |
| `startTime` | `number` | `0` | Start timestamp of replay range |
| `endTime` | `number` | `0` | End timestamp of replay range |
| `markers` | `TradeMarker[]` | `[]` | Trade markers to display on timeline |
| `showStatusBar` | `boolean` | `false` | Show status bar with price/volume |
| `showStats` | `boolean` | `true` | Show frame counter |
| `disabled` | `boolean` | `false` | Disable all controls |
| `currentPrice` | `number \| null` | `null` | Current price to display |
| `currentVolume` | `number \| null` | `null` | Current volume to display |

### Events

| Event | Payload | Description |
|-------|---------|-------------|
| `play` | `void` | Emitted when playback starts |
| `pause` | `void` | Emitted when playback pauses |
| `seek` | `number` | Emitted when seeking (index) |
| `step` | `'forward' \| 'backward'` | Emitted when stepping |
| `reset` | `void` | Emitted when reset to start |
| `speed-change` | `number` | Emitted when speed changes |
| `settings` | `void` | Emitted when settings clicked |

### TradeMarker Type

```typescript
interface TradeMarker {
  id: string              // Unique identifier
  time: number            // Unix timestamp
  type: 'buy' | 'sell'    // Trade type
  price: number           // Execution price
  quantity: number        // Trade quantity
  reason?: string         // Entry reason (optional)
  pnl?: number           // Profit/loss (optional)
}
```

### Internal State Management

The component manages its own playback state:
- **Play/Pause State**: Controlled internally with interval timers
- **Current Index**: Syncs with `currentTime` prop but can be controlled manually
- **Speed Control**: Adjusts interval timing based on selected speed
- **Loop Mode**: Automatically restarts playback when enabled

### Integration with Charts

Typical integration pattern:

```vue
<template>
  <div class="backtest-container">
    <!-- Chart displays current candle -->
    <MultiTimeframeChart
      ref="chartRef"
      :symbol="symbol"
      :timeframe="timeframe"
      :height="600"
    />

    <!-- Replay controls drive the chart -->
    <ReplayControls
      :total-points="historicalData.length"
      :current-time="currentCandle.time"
      :start-time="startTime"
      :end-time="endTime"
      :markers="executedTrades"
      :current-price="currentCandle.close"
      :show-status-bar="true"
      @seek="updateChart"
      @step="updateChart"
    />
  </div>
</template>

<script setup lang="ts">
const chartRef = ref()
const historicalData = ref<CandleData[]>([])
const currentIndex = ref(0)

const currentCandle = computed(() => 
  historicalData.value[currentIndex.value]
)

function updateChart(index: number) {
  currentIndex.value = index
  
  // Update chart to show only data up to current index
  const visibleData = historicalData.value.slice(0, index + 1)
  chartRef.value?.updateData(visibleData)
}
</script>
```

### Keyboard Shortcuts (Future Enhancement)

Consider adding keyboard shortcuts for better UX:
- `Space`: Play/pause
- `→`: Step forward
- `←`: Step backward
- `Home`: Reset to start
- `End`: Jump to end
- `+/-`: Increase/decrease speed

### Styling Customization

The component uses scoped CSS with CSS variables for easy theming:

```vue
<style>
.replay-controls-container {
  /* Override default styles */
  --control-bg: #ffffff;
  --control-border: #e5e7eb;
  --control-text: #374151;
  --primary-color: #3b82f6;
  --timeline-height: 4px;
}
</style>
```

### Performance Considerations

- **Playback Interval**: Uses `setInterval` with speed-based timing
- **Timeline Updates**: Throttled to avoid excessive re-renders
- **Marker Rendering**: Only renders visible markers for large datasets
- **Memory Management**: Cleans up intervals on component unmount

### Accessibility

- All buttons have `title` attributes for tooltips
- Disabled states properly indicated
- Keyboard navigation support (via standard button focus)
- ARIA labels can be added for screen readers

### Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- CSS Grid and Flexbox for layout
- Native range input with custom styling
- No IE11 support (uses modern JavaScript features)

