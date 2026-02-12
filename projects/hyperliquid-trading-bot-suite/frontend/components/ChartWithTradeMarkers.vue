<template>
  <div class="chart-with-markers">
    <!-- Multi-Timeframe Chart -->
    <MultiTimeframeChart
      ref="chartRef"
      :symbol="symbol"
      :initial-timeframe="initialTimeframe"
      :height="height"
      :show-volume="showVolume"
      @mounted="handleChartMounted"
    />
    
    <!-- Trade Marker Tooltips -->
    <TradeMarkerTooltip
      :marker="hoveredMarker"
      :visible="tooltipVisible"
      :position="tooltipPosition"
      :show-trade-id="true"
      :show-actions="true"
      @view-trade="handleViewTrade"
      @close-position="handleClosePosition"
    />
    
    <!-- Trade Stats Overlay (optional) -->
    <div
      v-if="showStats && stats"
      class="trade-stats-overlay"
    >
      <div class="stats-header">
        <h4 class="text-sm font-semibold text-gray-900 dark:text-white">
          Trade Statistics
        </h4>
        <button
          @click="toggleStats"
          class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
      
      <div class="stats-grid">
        <div class="stat-item">
          <span class="stat-label">Win Rate</span>
          <span class="stat-value" :class="stats.winRate >= 50 ? 'text-green-600' : 'text-red-600'">
            {{ stats.winRate.toFixed(1) }}%
          </span>
        </div>
        
        <div class="stat-item">
          <span class="stat-label">Total Trades</span>
          <span class="stat-value">{{ stats.totalTrades }}</span>
        </div>
        
        <div class="stat-item">
          <span class="stat-label">Net P&L</span>
          <span class="stat-value" :class="stats.netPnl >= 0 ? 'text-green-600' : 'text-red-600'">
            {{ formatCurrency(stats.netPnl) }}
          </span>
        </div>
        
        <div class="stat-item">
          <span class="stat-label">Avg R-Multiple</span>
          <span class="stat-value" :class="stats.averageRMultiple >= 1 ? 'text-green-600' : 'text-red-600'">
            {{ stats.averageRMultiple.toFixed(2) }}R
          </span>
        </div>
        
        <div class="stat-item">
          <span class="stat-label">Profit Factor</span>
          <span class="stat-value" :class="stats.profitFactor >= 1 ? 'text-green-600' : 'text-red-600'">
            {{ stats.profitFactor.toFixed(2) }}
          </span>
        </div>
        
        <div class="stat-item">
          <span class="stat-label">Active Trades</span>
          <span class="stat-value text-blue-600">{{ stats.pendingTrades }}</span>
        </div>
      </div>
    </div>
    
    <!-- Marker Config Controls -->
    <div class="marker-controls">
      <button
        @click="toggleMarkers"
        :class="['control-toggle', markersVisible ? 'active' : '']"
        title="Toggle Trade Markers"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
        <span class="ml-1 text-xs">Markers</span>
      </button>
      
      <button
        @click="toggleStats"
        :class="['control-toggle', showStats ? 'active' : '']"
        title="Toggle Statistics"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
        </svg>
        <span class="ml-1 text-xs">Stats</span>
      </button>
      
      <button
        @click="refreshMarkers"
        :disabled="loading"
        class="control-toggle"
        title="Refresh Markers"
      >
        <svg 
          class="w-4 h-4" 
          :class="{ 'animate-spin': loading }"
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Timeframe } from '~/types/chart'
import type { ISeriesApi } from 'lightweight-charts'
import { useTradeMarkers } from '~/composables/useTradeMarkers'

// Props
const props = defineProps<{
  symbol: string
  initialTimeframe?: Timeframe
  height?: number
  showVolume?: boolean
  autoLoad?: boolean
}>()

// Composables
const {
  allMarkers,
  stats,
  loading,
  config,
  loadTrades,
  clearAll,
  hoverMarker,
} = useTradeMarkers()

// Refs
const chartRef = ref<any>(null)
const markersVisible = ref(true)
const showStats = ref(false)
const hoveredMarker = ref<any>(null)
const tooltipVisible = ref(false)
const tooltipPosition = ref({ x: 0, y: 0 })

// Series refs for markers
const markerSeries = ref<Map<string, ISeriesApi<'Line'>>>(new Map())

// Watch for marker changes
watch(allMarkers, () => {
  if (markersVisible.value) {
    updateMarkers()
  }
}, { deep: true })

// Watch for visibility changes
watch(markersVisible, (visible) => {
  if (visible) {
    updateMarkers()
  } else {
    clearMarkers()
  }
})

// Update markers on the chart
const updateMarkers = () => {
  if (!chartRef.value?.candlestickSeries) return
  
  const candleSeries = chartRef.value.candlestickSeries
  
  // Clear existing markers
  clearMarkers()
  
  // Add new markers
  const markerData = allMarkers.value
    .filter(m => config.value.showEntryMarkers || m.type !== 'entry')
    .filter(m => config.value.showExitMarkers || m.type !== 'exit')
    .filter(m => config.value.showStopLoss || m.type !== 'stop-loss')
    .filter(m => config.value.showTakeProfit || m.type !== 'take-profit')
    .filter(m => config.value.showPartialExits || m.type !== 'partial-exit')
    .map(marker => {
      const shape = getMarkerShape(marker.type, marker.side)
      const color = getMarkerColor(marker)
      
      return {
        time: marker.time,
        position: marker.side === 'buy' ? 'belowBar' : 'aboveBar',
        color,
        shape,
        text: config.value.showLabels ? getMarkerLabel(marker) : undefined,
        size: 1,
        id: marker.id,
      }
    })
  
  candleSeries.setMarkers(markerData)
}

// Clear markers from the chart
const clearMarkers = () => {
  if (chartRef.value?.candlestickSeries) {
    chartRef.value.candlestickSeries.setMarkers([])
  }
}

// Get marker shape based on type and side
const getMarkerShape = (type: string, side: string): 'arrowUp' | 'arrowDown' | 'circle' | 'square' => {
  if (type === 'entry') {
    return side === 'buy' ? 'arrowUp' : 'arrowDown'
  } else if (type === 'exit') {
    return side === 'buy' ? 'arrowDown' : 'arrowUp'
  } else if (type === 'partial-exit') {
    return 'circle'
  } else if (type === 'stop-loss') {
    return 'square'
  } else if (type === 'take-profit') {
    return 'square'
  }
  return 'circle'
}

// Get marker color
const getMarkerColor = (marker: any): string => {
  if (marker.type === 'entry') {
    return marker.side === 'buy' ? config.value.colors.buyEntry : config.value.colors.sellEntry
  } else if (marker.type === 'exit') {
    if (marker.pnl !== undefined) {
      if (marker.pnl > 0) return config.value.colors.profitExit
      if (marker.pnl < 0) return config.value.colors.lossExit
      return config.value.colors.breakevenExit
    }
    return '#6b7280'
  } else if (marker.type === 'stop-loss') {
    return config.value.colors.stopLoss
  } else if (marker.type === 'take-profit') {
    return config.value.colors.takeProfit
  }
  return '#6b7280'
}

// Get marker label
const getMarkerLabel = (marker: any): string => {
  if (marker.type === 'entry') {
    return marker.side === 'buy' ? 'L' : 'S'
  } else if (marker.type === 'exit') {
    return 'X'
  } else if (marker.type === 'partial-exit') {
    return 'P'
  } else if (marker.type === 'stop-loss') {
    return 'SL'
  } else if (marker.type === 'take-profit') {
    return 'TP'
  }
  return ''
}

// Chart mounted handler
const handleChartMounted = () => {
  // Load trades if autoLoad is enabled
  if (props.autoLoad !== false) {
    refreshMarkers()
  }
  
  // Add click handler for markers (requires subscribing to chart clicks)
  // This would need lightweight-charts v4+ API for marker clicks
}

// Toggle markers visibility
const toggleMarkers = () => {
  markersVisible.value = !markersVisible.value
}

// Toggle stats overlay
const toggleStats = () => {
  showStats.value = !showStats.value
}

// Refresh markers from API
const refreshMarkers = async () => {
  clearAll()
  
  const symbol = props.symbol
  const timeframe = chartRef.value?.currentTimeframe || props.initialTimeframe || '15m'
  
  await loadTrades(symbol, timeframe)
}

// View trade details
const handleViewTrade = (tradeId: string) => {
  // Emit event or navigate to trade details
  console.log('View trade:', tradeId)
}

// Close position
const handleClosePosition = (tradeId: string) => {
  // Emit event or call API to close position
  console.log('Close position:', tradeId)
}

// Format currency
const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

// Expose methods
defineExpose({
  refreshMarkers,
  toggleMarkers,
  clearAll,
})
</script>

<style scoped>
.chart-with-markers {
  @apply relative;
}

.trade-stats-overlay {
  @apply absolute top-4 right-4;
  @apply bg-white dark:bg-gray-800;
  @apply border border-gray-200 dark:border-gray-700;
  @apply rounded-lg shadow-lg;
  @apply p-4;
  @apply min-w-[250px];
  @apply z-10;
}

.stats-header {
  @apply flex items-center justify-between mb-3;
  @apply pb-2 border-b border-gray-200 dark:border-gray-700;
}

.stats-grid {
  @apply grid grid-cols-2 gap-3;
}

.stat-item {
  @apply flex flex-col;
}

.stat-label {
  @apply text-xs text-gray-600 dark:text-gray-400;
  @apply font-medium mb-1;
}

.stat-value {
  @apply text-sm font-bold;
  @apply text-gray-900 dark:text-white;
}

.marker-controls {
  @apply absolute bottom-4 right-4;
  @apply flex items-center gap-2;
  @apply bg-white dark:bg-gray-800;
  @apply border border-gray-200 dark:border-gray-700;
  @apply rounded-lg shadow-lg;
  @apply p-2;
  @apply z-10;
}

.control-toggle {
  @apply flex items-center px-2 py-1.5;
  @apply rounded-md transition-all;
  @apply text-gray-600 dark:text-gray-400;
  @apply hover:bg-gray-100 dark:hover:bg-gray-700;
  @apply text-xs font-medium;
}

.control-toggle.active {
  @apply bg-blue-500 text-white;
  @apply hover:bg-blue-600;
}

.control-toggle:disabled {
  @apply opacity-50 cursor-not-allowed;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
