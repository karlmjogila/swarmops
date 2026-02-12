<template>
  <div class="multi-timeframe-chart">
    <!-- Chart Header with Timeframe Selector -->
    <div class="chart-header">
      <div class="flex items-center justify-between">
        <!-- Symbol Display -->
        <div class="symbol-info">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ currentSymbol }}
          </h3>
          <span v-if="lastPrice" class="text-sm" :class="priceChangeClass">
            {{ formatPrice(lastPrice) }}
            <span v-if="priceChange" class="ml-1">
              {{ priceChange > 0 ? '+' : '' }}{{ priceChange.toFixed(2) }}%
            </span>
          </span>
        </div>

        <!-- Timeframe Selector -->
        <div class="timeframe-selector">
          <div class="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <button
              v-for="tf in availableTimeframes"
              :key="tf.value"
              @click="handleTimeframeChange(tf.value)"
              :class="[
                'timeframe-btn',
                currentTimeframe === tf.value ? 'active' : ''
              ]"
            >
              {{ tf.label.split(' ')[0] }}
            </button>
          </div>
        </div>

        <!-- Chart Controls -->
        <div class="chart-controls flex items-center gap-2">
          <button
            @click="toggleVolume"
            :class="['control-btn', showVolume ? 'active' : '']"
            title="Toggle Volume"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
            </svg>
          </button>
          
          <button
            @click="fitContent"
            class="control-btn"
            title="Fit Content"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
            </svg>
          </button>

          <button
            @click="refresh"
            :disabled="loading"
            class="control-btn"
            :class="{ 'opacity-50 cursor-not-allowed': loading }"
            title="Refresh Data"
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
    </div>

    <!-- Chart Container -->
    <div class="chart-container relative">
      <div
        ref="chartContainer"
        class="chart-canvas"
        :style="{ height: height + 'px' }"
      />

      <!-- Loading Overlay -->
      <div
        v-if="loading && !chart"
        class="absolute inset-0 flex items-center justify-center bg-white/90 dark:bg-gray-900/90"
      >
        <div class="flex items-center space-x-3">
          <div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <span class="text-gray-600 dark:text-gray-400">Loading chart data...</span>
        </div>
      </div>

      <!-- Error State -->
      <div
        v-if="error"
        class="absolute inset-0 flex items-center justify-center bg-white/90 dark:bg-gray-900/90"
      >
        <div class="text-center p-6">
          <svg class="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 15.5c-.77.833.192 2.5 1.732 2.5z"/>
          </svg>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Chart Error</h3>
          <p class="text-gray-600 dark:text-gray-400 mb-4">{{ error }}</p>
          <button @click="refresh" class="btn-primary">
            Retry
          </button>
        </div>
      </div>

      <!-- Loading Spinner (during refresh) -->
      <div
        v-if="loading && chart"
        class="absolute top-4 right-4 flex items-center gap-2 bg-white dark:bg-gray-800 rounded-lg px-3 py-2 shadow-lg"
      >
        <div class="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        <span class="text-sm text-gray-600 dark:text-gray-400">Updating...</span>
      </div>
    </div>

    <!-- Chart Footer with Statistics -->
    <div class="chart-footer">
      <div class="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
        <div class="flex items-center gap-4">
          <span>Last Update: {{ formatTimestamp(lastUpdate) }}</span>
          <span v-if="candleCount">Candles: {{ candleCount }}</span>
        </div>
        <div class="flex items-center gap-4">
          <span v-if="volumeTotal">24h Volume: {{ formatVolume(volumeTotal) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { createChart, ColorType, CrosshairMode, type IChartApi, type ISeriesApi, type CandlestickData, type UTCTimestamp } from 'lightweight-charts'
import type { Timeframe, CandleData } from '~/types/chart'
import { useChartData } from '~/composables/useChartData'
import { format } from 'date-fns'

// Props
const props = defineProps<{
  symbol?: string
  initialTimeframe?: Timeframe
  height?: number
  showVolume?: boolean
}>()

// Composables
const { 
  currentSymbol, 
  currentTimeframe, 
  loading, 
  error,
  lastUpdate,
  getCurrentData,
  availableTimeframes,
  loadData,
  changeTimeframe,
  changeSymbol,
} = useChartData()

// Refs
const chartContainer = ref<HTMLDivElement | null>(null)
const chart = ref<IChartApi | null>(null)
const candlestickSeries = ref<ISeriesApi<'Candlestick'> | null>(null)
const volumeSeries = ref<ISeriesApi<'Histogram'> | null>(null)
const showVolume = ref(props.showVolume ?? true)

// State
const lastPrice = ref<number | null>(null)
const priceChange = ref<number | null>(null)
const candleCount = computed(() => getCurrentData.value.length)
const volumeTotal = computed(() => {
  return getCurrentData.value.reduce((sum, candle) => sum + (candle.volume || 0), 0)
})

// Computed
const priceChangeClass = computed(() => {
  if (!priceChange.value) return 'text-gray-600 dark:text-gray-400'
  return priceChange.value > 0 
    ? 'text-green-600 dark:text-green-400' 
    : 'text-red-600 dark:text-red-400'
})

// Chart Options
const getChartOptions = (isDark = false) => ({
  layout: {
    background: {
      type: ColorType.Solid,
      color: isDark ? 'rgb(17, 24, 39)' : 'rgb(255, 255, 255)',
    },
    textColor: isDark ? 'rgb(209, 213, 219)' : 'rgb(55, 65, 81)',
    fontSize: 12,
    fontFamily: 'General Sans, -apple-system, BlinkMacSystemFont, sans-serif',
  },
  grid: {
    vertLines: {
      color: isDark ? 'rgb(31, 41, 55)' : 'rgb(243, 244, 246)',
      style: 1,
      visible: true,
    },
    horzLines: {
      color: isDark ? 'rgb(31, 41, 55)' : 'rgb(243, 244, 246)',
      style: 1,
      visible: true,
    },
  },
  crosshair: {
    mode: CrosshairMode.Normal,
    vertLine: {
      width: 1 as const,
      color: isDark ? 'rgb(75, 85, 99)' : 'rgb(156, 163, 175)',
      style: 3,
    },
    horzLine: {
      width: 1 as const,
      color: isDark ? 'rgb(75, 85, 99)' : 'rgb(156, 163, 175)',
      style: 3,
    },
  },
  rightPriceScale: {
    borderColor: isDark ? 'rgb(55, 65, 81)' : 'rgb(209, 213, 219)',
    autoScale: true,
  },
  timeScale: {
    borderColor: isDark ? 'rgb(55, 65, 81)' : 'rgb(209, 213, 219)',
    timeVisible: true,
    secondsVisible: false,
    rightOffset: 12,
    barSpacing: 8,
    minBarSpacing: 4,
  },
  watermark: {
    visible: false,
  },
})

const getCandlestickOptions = () => ({
  upColor: 'rgb(34, 197, 94)',
  downColor: 'rgb(239, 68, 68)',
  borderDownColor: 'rgb(220, 38, 38)',
  borderUpColor: 'rgb(21, 128, 61)',
  wickDownColor: 'rgb(220, 38, 38)',
  wickUpColor: 'rgb(21, 128, 61)',
})

const getVolumeOptions = (isDark = false) => ({
  priceFormat: {
    type: 'volume' as const,
  },
  priceScaleId: 'volume',
  color: isDark ? 'rgba(156, 163, 175, 0.4)' : 'rgba(107, 114, 128, 0.4)',
})

// Format helpers
const formatPrice = (price: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(price)
}

const formatVolume = (volume: number): string => {
  if (volume >= 1e9) return `${(volume / 1e9).toFixed(2)}B`
  if (volume >= 1e6) return `${(volume / 1e6).toFixed(2)}M`
  if (volume >= 1e3) return `${(volume / 1e3).toFixed(2)}K`
  return volume.toFixed(2)
}

const formatTimestamp = (timestamp: number): string => {
  return format(new Date(timestamp), 'MMM dd, HH:mm:ss')
}

// Initialize chart
const initializeChart = () => {
  if (!chartContainer.value || chart.value) return

  const isDark = document.documentElement.classList.contains('dark')
  
  // Create chart
  chart.value = createChart(chartContainer.value, {
    ...getChartOptions(isDark),
    width: chartContainer.value.clientWidth,
    height: props.height || 600,
  })

  // Create candlestick series
  candlestickSeries.value = chart.value.addCandlestickSeries(getCandlestickOptions())

  // Create volume series if enabled
  if (showVolume.value) {
    volumeSeries.value = chart.value.addHistogramSeries({
      ...getVolumeOptions(isDark),
      priceScaleId: 'volume',
    })
    
    // Configure volume scale
    chart.value.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    })
  }

  // Handle resize
  const resizeObserver = new ResizeObserver(() => {
    if (chart.value && chartContainer.value) {
      chart.value.applyOptions({
        width: chartContainer.value.clientWidth,
      })
    }
  })
  resizeObserver.observe(chartContainer.value)

  // Store observer for cleanup
  ;(chart.value as any)._resizeObserver = resizeObserver
}

// Update chart data
const updateChartData = () => {
  if (!candlestickSeries.value || !getCurrentData.value.length) return

  const data = getCurrentData.value.map(candle => ({
    time: candle.time as UTCTimestamp,
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
  }))

  candlestickSeries.value.setData(data)

  // Update volume data if enabled
  if (showVolume.value && volumeSeries.value) {
    const volumeData = getCurrentData.value
      .filter(candle => candle.volume !== undefined)
      .map(candle => ({
        time: candle.time as UTCTimestamp,
        value: candle.volume!,
        color: candle.close >= candle.open 
          ? 'rgba(34, 197, 94, 0.5)' 
          : 'rgba(239, 68, 68, 0.5)',
      }))
    
    volumeSeries.value.setData(volumeData)
  }

  // Update last price and change
  if (data.length > 0) {
    const firstPrice = data[0].open
    const currentPrice = data[data.length - 1].close
    lastPrice.value = currentPrice
    priceChange.value = ((currentPrice - firstPrice) / firstPrice) * 100
  }

  // Fit content
  chart.value?.timeScale().fitContent()
}

// Handle timeframe change
const handleTimeframeChange = async (timeframe: Timeframe) => {
  try {
    await changeTimeframe(timeframe)
  } catch (err) {
    console.error('Error changing timeframe:', err)
  }
}

// Toggle volume display
const toggleVolume = () => {
  showVolume.value = !showVolume.value
  
  if (showVolume.value && !volumeSeries.value && chart.value) {
    // Add volume series
    const isDark = document.documentElement.classList.contains('dark')
    volumeSeries.value = chart.value.addHistogramSeries({
      ...getVolumeOptions(isDark),
      priceScaleId: 'volume',
    })
    
    chart.value.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    })
    
    updateChartData()
  } else if (!showVolume.value && volumeSeries.value && chart.value) {
    // Remove volume series
    chart.value.removeSeries(volumeSeries.value)
    volumeSeries.value = null
  }
}

// Fit content
const fitContent = () => {
  chart.value?.timeScale().fitContent()
}

// Refresh data
const refresh = async () => {
  try {
    await loadData(currentSymbol.value, currentTimeframe.value)
  } catch (err) {
    console.error('Error refreshing data:', err)
  }
}

// Update chart theme
const updateChartTheme = () => {
  if (!chart.value) return
  
  const isDark = document.documentElement.classList.contains('dark')
  chart.value.applyOptions(getChartOptions(isDark))
  
  if (volumeSeries.value) {
    volumeSeries.value.applyOptions(getVolumeOptions(isDark))
  }
}

// Watch for data changes
watch(getCurrentData, () => {
  if (chart.value) {
    updateChartData()
  }
}, { deep: true })

// Watch for symbol changes from props
watch(() => props.symbol, (newSymbol) => {
  if (newSymbol && newSymbol !== currentSymbol.value) {
    changeSymbol(newSymbol)
  }
})

// Initialize on mount
onMounted(async () => {
  // Set initial values
  if (props.symbol) {
    currentSymbol.value = props.symbol
  }
  if (props.initialTimeframe) {
    currentTimeframe.value = props.initialTimeframe
  }

  // Initialize chart
  await nextTick()
  initializeChart()

  // Load initial data
  await loadData(currentSymbol.value, currentTimeframe.value)

  // Listen for theme changes
  const observer = new MutationObserver(() => {
    updateChartTheme()
  })
  
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class']
  })

  onUnmounted(() => {
    observer.disconnect()
  })
})

// Cleanup on unmount
onUnmounted(() => {
  if (chart.value) {
    const resizeObserver = (chart.value as any)._resizeObserver
    if (resizeObserver) {
      resizeObserver.disconnect()
    }
    chart.value.remove()
    chart.value = null
  }
})

// Expose methods for parent components
defineExpose({
  chart,
  candlestickSeries,
  volumeSeries,
  refresh,
  fitContent,
  changeTimeframe: handleTimeframeChange,
  changeSymbol,
})
</script>

<style scoped>
.multi-timeframe-chart {
  @apply bg-white dark:bg-gray-900 rounded-lg shadow-lg overflow-hidden;
}

.chart-header {
  @apply border-b border-gray-200 dark:border-gray-700 px-4 py-3;
}

.symbol-info {
  @apply flex flex-col gap-1;
}

.timeframe-selector {
  @apply flex items-center;
}

.timeframe-btn {
  @apply px-3 py-1.5 text-xs font-medium rounded-md transition-all;
  @apply text-gray-600 dark:text-gray-400;
  @apply hover:bg-gray-200 dark:hover:bg-gray-700;
}

.timeframe-btn.active {
  @apply bg-blue-500 text-white;
  @apply hover:bg-blue-600;
}

.control-btn {
  @apply p-2 rounded-lg transition-all;
  @apply text-gray-600 dark:text-gray-400;
  @apply hover:bg-gray-100 dark:hover:bg-gray-800;
  @apply border border-gray-200 dark:border-gray-700;
}

.control-btn.active {
  @apply bg-blue-500 text-white border-blue-500;
  @apply hover:bg-blue-600;
}

.chart-container {
  @apply relative;
}

.chart-canvas {
  @apply w-full;
}

.chart-footer {
  @apply border-t border-gray-200 dark:border-gray-700 px-4 py-2;
}

.btn-primary {
  @apply px-4 py-2 bg-blue-500 text-white rounded-lg;
  @apply hover:bg-blue-600 transition-colors;
  @apply font-medium text-sm;
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
