# Trade Markers and Overlays

Visual indicators and overlays for displaying trades, entry/exit points, and trade performance on charts.

## Overview

The trade markers system provides a comprehensive solution for visualizing trades on price charts. It includes:

- **Trade Markers**: Visual indicators for entry, exit, stop-loss, and take-profit points
- **Trade Overlays**: Contextual information and performance metrics for each trade
- **Trade Zones**: Shaded regions showing entry zones, stop-loss areas, and target zones
- **Price Lines**: Horizontal lines for active stop-loss and take-profit levels
- **Trade Statistics**: Aggregate performance metrics and analytics
- **Interactive Tooltips**: Rich tooltips with trade details on hover

## Components

### ChartWithTradeMarkers.vue

The main component that integrates trade markers with the MultiTimeframeChart.

#### Usage

```vue
<template>
  <ChartWithTradeMarkers
    symbol="ETH/USD"
    :initial-timeframe="'15m'"
    :height="600"
    :show-volume="true"
    :auto-load="true"
  />
</template>
```

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `symbol` | `string` | Required | Trading pair symbol |
| `initialTimeframe` | `Timeframe` | `'15m'` | Initial timeframe |
| `height` | `number` | `600` | Chart height in pixels |
| `showVolume` | `boolean` | `true` | Show volume overlay |
| `autoLoad` | `boolean` | `true` | Auto-load trades on mount |

#### Features

- Automatic marker placement based on trade data
- Color-coded markers for different trade types
- Toggle markers visibility
- Real-time trade statistics overlay
- Configurable marker display options

### TradeMarkerTooltip.vue

Interactive tooltip component that displays detailed information about a trade marker.

#### Features

- Entry/exit information with prices and quantities
- P&L display with percentage and R-multiple
- Entry/exit reasoning
- Trade actions (view details, close position)
- Smart positioning to avoid chart edges

## Composables

### useTradeMarkers

Centralized state management for trade markers and overlays.

#### Usage

```typescript
import { useTradeMarkers } from '~/composables/useTradeMarkers'

const {
  allMarkers,
  allOverlays,
  stats,
  loading,
  config,
  loadTrades,
  addMarker,
  selectTrade,
  updateConfig,
} = useTradeMarkers()

// Load trades from API
await loadTrades('ETHUSDT', '15m')

// Manually add a marker
addMarker({
  id: 'marker-1',
  time: Date.now() / 1000,
  type: 'entry',
  side: 'buy',
  price: 2500,
  quantity: 1.5,
  reason: 'LE candle at demand zone',
})

// Update configuration
updateConfig({
  showStopLoss: false,
  showTakeProfit: true,
})
```

#### State

- `markers` (Ref<Map>): All trade markers
- `overlays` (Ref<Map>): Trade overlay data
- `zones` (Ref<Map>): Trade zones (entry, stop, target)
- `priceLines` (Ref<Map>): Active price lines
- `config` (Ref<TradeMarkerConfig>): Display configuration
- `loading` (Ref<boolean>): Loading state
- `error` (Ref<string | null>): Error message

#### Computed

- `allMarkers`: Array of all markers
- `allOverlays`: Array of all overlays
- `activeOverlays`: Only active (open) trades
- `stats`: Aggregate trade statistics

#### Methods

**Marker Management**
- `addMarker(marker)`: Add a trade marker
- `removeMarker(markerId)`: Remove a marker
- `updateMarker(markerId, updates)`: Update marker properties
- `getMarkersByTrade(tradeId)`: Get all markers for a trade

**Overlay Management**
- `addOverlay(overlay)`: Add a trade overlay
- `removeOverlay(overlayId)`: Remove an overlay
- `updateOverlay(overlayId, updates)`: Update overlay properties
- `getOverlayByTrade(tradeId)`: Get overlay for a trade

**Zone Management**
- `addZone(zone)`: Add a trade zone
- `removeZone(zoneId)`: Remove a zone
- `getZonesByTrade(tradeId)`: Get all zones for a trade

**Price Line Management**
- `addPriceLine(line)`: Add a price line
- `removePriceLine(lineId)`: Remove a price line

**Selection and Interaction**
- `selectTrade(tradeId)`: Select and highlight a trade
- `hoverMarker(markerId)`: Set hovered marker for tooltip
- `clearAll()`: Clear all markers and overlays
- `clearByTrade(tradeId)`: Clear all markers for a specific trade

**Data Loading**
- `loadTrades(symbol, timeframe, startTime?, endTime?)`: Load trades from API
- `createTradeMarkers(trade)`: Create markers from trade data

**Configuration**
- `updateConfig(updates)`: Update display configuration

## Types

### TradeMarker

```typescript
interface TradeMarker {
  id: string
  time: number                    // Unix timestamp (seconds)
  type: 'entry' | 'exit' | 'partial-exit' | 'stop-loss' | 'take-profit'
  side: 'buy' | 'sell'
  price: number
  quantity: number
  
  // Optional metadata
  reason?: string
  pnl?: number
  pnlPercent?: number
  rMultiple?: number
  fees?: number
  
  // Associated trade
  tradeId?: string
  strategyId?: string
  
  // Visual customization
  color?: string
  label?: string
  showTooltip?: boolean
}
```

### TradeOverlay

```typescript
interface TradeOverlay {
  id: string
  tradeId: string
  
  entryTime: number
  entryPrice: number
  exitTime?: number
  exitPrice?: number
  
  side: 'buy' | 'sell'
  quantity: number
  outcome: 'win' | 'loss' | 'breakeven' | 'pending'
  
  pnl: number
  pnlPercent: number
  rMultiple: number
  fees: number
  
  stopLoss?: number
  takeProfitLevels?: number[]
  
  reasoning?: string
  entryPattern?: string
  exitReason?: string
  
  isActive: boolean
  isHighlighted: boolean
}
```

### TradeZone

```typescript
interface TradeZone {
  id: string
  tradeId: string
  type: 'entry-zone' | 'target-zone' | 'stop-zone'
  
  topPrice: number
  bottomPrice: number
  startTime: number
  endTime?: number
  
  color: string
  opacity: number
  borderColor?: string
  label?: string
}
```

### TradeStats

```typescript
interface TradeStats {
  totalTrades: number
  winningTrades: number
  losingTrades: number
  breakevenTrades: number
  pendingTrades: number
  
  winRate: number
  averageWin: number
  averageLoss: number
  profitFactor: number
  averageRMultiple: number
  
  totalPnl: number
  totalFees: number
  netPnl: number
}
```

## Configuration

### TradeMarkerConfig

```typescript
interface TradeMarkerConfig {
  // Visibility toggles
  showEntryMarkers: boolean
  showExitMarkers: boolean
  showStopLoss: boolean
  showTakeProfit: boolean
  showPartialExits: boolean
  showTradeZones: boolean
  showPriceLines: boolean
  showTooltips: boolean
  showLabels: boolean
  
  // Display options
  highlightActiveTrades: boolean
  groupByTrade: boolean
  
  // Color scheme
  colors: {
    buyEntry: string
    sellEntry: string
    profitExit: string
    lossExit: string
    breakevenExit: string
    stopLoss: string
    takeProfit: string
    activeZone: string
  }
}
```

### Default Configuration

```typescript
const defaultMarkerConfig: TradeMarkerConfig = {
  showEntryMarkers: true,
  showExitMarkers: true,
  showStopLoss: true,
  showTakeProfit: true,
  showPartialExits: true,
  showTradeZones: true,
  showPriceLines: true,
  showTooltips: true,
  showLabels: true,
  highlightActiveTrades: true,
  groupByTrade: true,
  
  colors: {
    buyEntry: '#10b981',      // green-500
    sellEntry: '#ef4444',     // red-500
    profitExit: '#059669',    // green-600
    lossExit: '#dc2626',      // red-600
    breakevenExit: '#6b7280', // gray-500
    stopLoss: '#f59e0b',      // amber-500
    takeProfit: '#3b82f6',    // blue-500
    activeZone: '#8b5cf6',    // purple-500
  }
}
```

## Marker Shapes

The library uses different shapes to represent different trade actions:

- **Entry (Long)**: Upward arrow (▲) in green
- **Entry (Short)**: Downward arrow (▼) in red
- **Exit**: Opposite arrow from entry
- **Partial Exit**: Circle (●)
- **Stop Loss Hit**: Square (■) in amber
- **Take Profit Hit**: Square (■) in blue

## Color Coding

Markers are color-coded based on outcome:

- **Long Entry**: Green (#10b981)
- **Short Entry**: Red (#ef4444)
- **Winning Exit**: Dark green (#059669)
- **Losing Exit**: Dark red (#dc2626)
- **Breakeven Exit**: Gray (#6b7280)
- **Stop Loss**: Amber (#f59e0b)
- **Take Profit**: Blue (#3b82f6)

## API Integration

### Loading Trades

Trades are loaded from the backend API endpoint `/api/trades`:

```typescript
GET /api/trades?symbol=ETHUSDT&timeframe=15m&start_time=1234567890&end_time=1234567999
```

#### Response Format

```json
{
  "trades": [
    {
      "id": "trade-uuid",
      "strategy_rule_id": "strategy-uuid",
      "asset": "ETHUSDT",
      "direction": "buy",
      "entry_price": 2500.00,
      "entry_time": "2024-01-01T12:00:00Z",
      "quantity": 1.5,
      "exit_price": 2550.00,
      "exit_time": "2024-01-01T14:00:00Z",
      "exit_reason": "take_profit",
      "outcome": "win",
      "pnl_absolute": 75.00,
      "pnl_r_multiple": 2.0,
      "fees_paid": 5.00,
      "reasoning": "LE candle at demand zone with HTF bullish bias",
      "initial_stop_loss": 2480.00,
      "current_stop_loss": 2500.00,
      "take_profit_levels": [2520.00, 2550.00],
      "partial_exits": [],
      "trading_mode": "paper"
    }
  ]
}
```

### Converting API Trades to Markers

The `createTradeMarkers` function automatically converts API trade data to markers:

```typescript
const trade = { /* API trade data */ }
createTradeMarkers(trade)
// Creates:
// - Entry marker
// - Exit marker (if closed)
// - Partial exit markers
// - Trade overlay
// - Trade zones (entry, stop, targets)
// - Price lines (for active trades)
```

## Best Practices

### Performance

1. **Limit Visible Markers**: Don't load too many markers at once
   - Use time-based filtering
   - Implement pagination for historical trades
   
2. **Debounce Updates**: Avoid updating markers on every tick
   - Batch marker updates
   - Use computed properties for filtering

3. **Lazy Loading**: Load trades only when needed
   - Load on timeframe/symbol change
   - Clear old markers before loading new ones

### User Experience

1. **Clear Visual Hierarchy**: 
   - Entry markers should be most prominent
   - Exit markers should show outcome clearly
   - Use consistent colors and shapes

2. **Tooltips**:
   - Show on hover, not by default
   - Include actionable information
   - Position tooltips to avoid overlapping chart

3. **Statistics**:
   - Make stats collapsible
   - Update in real-time
   - Show only relevant metrics

### Trading Safety

1. **Trade Validation**:
   - Validate all trade data before creating markers
   - Handle missing or malformed data gracefully
   - Show errors clearly

2. **State Management**:
   - Keep marker state in sync with actual trades
   - Clear stale markers on refresh
   - Update markers when trades change

## Future Enhancements

- [ ] Drawing tools integration (connect entry to exit with line)
- [ ] Risk/reward ratio visualization
- [ ] Heatmap of entry/exit zones
- [ ] Trade replay animation
- [ ] Export trade history with markers
- [ ] Custom marker styles per strategy
- [ ] Multi-symbol trade comparison
- [ ] Trade clustering and pattern recognition
- [ ] Performance analytics dashboard
- [ ] Notification markers for important events

## Examples

### Basic Usage

```vue
<template>
  <ChartWithTradeMarkers
    symbol="BTC/USD"
    :initial-timeframe="'1h'"
    :height="800"
  />
</template>
```

### Custom Configuration

```vue
<script setup>
import { useTradeMarkers } from '~/composables/useTradeMarkers'

const { updateConfig } = useTradeMarkers()

// Hide zones, show only entry/exit markers
updateConfig({
  showTradeZones: false,
  showPriceLines: false,
  showLabels: true,
  colors: {
    buyEntry: '#00ff00',
    sellEntry: '#ff0000',
  }
})
</script>
```

### Manual Marker Creation

```vue
<script setup>
import { useTradeMarkers } from '~/composables/useTradeMarkers'

const { addMarker, addOverlay } = useTradeMarkers()

// Add a custom entry marker
addMarker({
  id: 'custom-entry-1',
  time: Date.now() / 1000,
  type: 'entry',
  side: 'buy',
  price: 45000,
  quantity: 0.1,
  reason: 'Manual entry at support',
  tradeId: 'manual-trade-1',
})

// Add corresponding overlay
addOverlay({
  id: 'overlay-1',
  tradeId: 'manual-trade-1',
  entryTime: Date.now() / 1000,
  entryPrice: 45000,
  side: 'buy',
  quantity: 0.1,
  outcome: 'pending',
  pnl: 0,
  pnlPercent: 0,
  rMultiple: 0,
  fees: 0,
  stopLoss: 44500,
  takeProfitLevels: [45500, 46000],
  isActive: true,
  isHighlighted: false,
})
</script>
```

## Troubleshooting

### Markers Not Showing

1. Check `markersVisible` is `true`
2. Verify markers are within chart time range
3. Check marker configuration filters
4. Inspect browser console for errors

### Tooltips Not Appearing

1. Verify `showTooltips` in config is `true`
2. Check marker has `showTooltip: true`
3. Ensure tooltip component is rendered
4. Check z-index and positioning

### Performance Issues

1. Limit number of visible markers
2. Use time-based filtering
3. Disable zones for large datasets
4. Batch marker updates

## License

Part of the Hyperliquid Trading Bot Suite.
