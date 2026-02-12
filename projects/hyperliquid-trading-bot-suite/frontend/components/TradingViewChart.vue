<template>
  <div class="trading-chart-container">
    <div 
      ref="chartContainer" 
      class="chart-wrapper"
      :style="{ height: height + 'px' }"
    />
    
    <!-- Loading overlay -->
    <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80">
      <div class="flex items-center space-x-3">
        <div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        <span class="text-gray-600 dark:text-gray-400">Loading chart data...</span>
      </div>
    </div>
    
    <!-- Error state -->
    <div v-if="error" class="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80">
      <div class="text-center">
        <svg class="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 15.5c-.77.833.192 2.5 1.732 2.5z"/>
        </svg>
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Chart Error</h3>
        <p class="text-gray-600 dark:text-gray-400 mb-4">{{ error }}</p>
        <button @click="initializeChart" class="btn btn-primary">
          Retry
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { createChart } from 'lightweight-charts'

// Props
const props = defineProps({
  symbol: {
    type: String,
    default: 'ETH/USD'
  },
  timeframe: {
    type: String,
    default: '15m'
  },
  height: {
    type: Number,
    default: 400
  },
  theme: {
    type: String,
    default: 'light'
  }
})

// Refs
const chartContainer = ref(null)
const chart = ref(null)
const candlestickSeries = ref(null)
const loading = ref(true)
const error = ref(null)

// Chart configuration
const getChartOptions = (isDark = false) => ({
  layout: {
    background: {
      type: 'solid',
      color: isDark ? 'rgb(17, 24, 39)' : 'rgb(255, 255, 255)',
    },
    textColor: isDark ? 'rgb(209, 213, 219)' : 'rgb(55, 65, 81)',
    fontSize: 14,
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
    mode: 1, // Normal crosshair
    vertLine: {
      width: 1,
      color: isDark ? 'rgb(75, 85, 99)' : 'rgb(156, 163, 175)',
      style: 3, // Dashed
    },
    horzLine: {
      width: 1,
      color: isDark ? 'rgb(75, 85, 99)' : 'rgb(156, 163, 175)',
      style: 3, // Dashed
    },
  },
  priceScale: {
    borderColor: isDark ? 'rgb(55, 65, 81)' : 'rgb(209, 213, 219)',
    autoScale: true,
  },
  timeScale: {
    borderColor: isDark ? 'rgb(55, 65, 81)' : 'rgb(209, 213, 219)',
    timeVisible: true,
    secondsVisible: false,
  },
  watermark: {
    visible: false,
  },
})

// Candlestick series configuration
const getCandlestickOptions = (isDark = false) => ({
  upColor: 'rgb(34, 197, 94)', // Green
  downColor: 'rgb(239, 68, 68)', // Red
  borderDownColor: 'rgb(220, 38, 38)',
  borderUpColor: 'rgb(21, 128, 61)',
  wickDownColor: 'rgb(220, 38, 38)',
  wickUpColor: 'rgb(21, 128, 61)',
})

// Generate sample data (will be replaced with real data)
const generateSampleData = () => {
  const data = []
  const basePrice = 3200
  let currentPrice = basePrice
  const startTime = Date.now() - (500 * 15 * 60 * 1000) // 500 candles ago

  for (let i = 0; i < 500; i++) {
    const time = startTime + (i * 15 * 60 * 1000) // 15 minutes per candle
    const change = (Math.random() - 0.5) * 40
    const open = currentPrice
    const volatility = Math.random() * 50 + 10
    const high = open + Math.random() * volatility
    const low = open - Math.random() * volatility
    const close = open + change
    
    data.push({
      time: Math.floor(time / 1000),
      open: parseFloat(open.toFixed(2)),
      high: parseFloat(high.toFixed(2)),
      low: parseFloat(low.toFixed(2)),
      close: parseFloat(close.toFixed(2)),
    })
    
    currentPrice = close
  }
  
  return data
}

// Initialize chart
const initializeChart = async () => {
  try {
    loading.value = true
    error.value = null
    
    if (!chartContainer.value) {
      throw new Error('Chart container not found')
    }

    // Create chart
    const isDark = document.documentElement.classList.contains('dark')
    chart.value = createChart(chartContainer.value, {
      ...getChartOptions(isDark),
      width: chartContainer.value.clientWidth,
      height: props.height,
    })

    // Create candlestick series
    candlestickSeries.value = chart.value.addCandlestickSeries(getCandlestickOptions(isDark))

    // Load sample data
    const data = generateSampleData()
    candlestickSeries.value.setData(data)

    // Auto-fit content
    chart.value.timeScale().fitContent()

    // Handle resize
    const resizeObserver = new ResizeObserver(() => {
      if (chart.value && chartContainer.value) {
        chart.value.applyOptions({
          width: chartContainer.value.clientWidth,
        })
      }
    })
    resizeObserver.observe(chartContainer.value)

    loading.value = false
  } catch (err) {
    console.error('Chart initialization error:', err)
    error.value = err.message
    loading.value = false
  }
}

// Update chart theme
const updateChartTheme = () => {
  if (!chart.value) return
  
  const isDark = document.documentElement.classList.contains('dark')
  chart.value.applyOptions(getChartOptions(isDark))
  
  if (candlestickSeries.value) {
    candlestickSeries.value.applyOptions(getCandlestickOptions(isDark))
  }
}

// Watch for symbol/timeframe changes
watch([() => props.symbol, () => props.timeframe], () => {
  if (chart.value) {
    // In a real implementation, this would fetch new data
    console.log(`Loading data for ${props.symbol} on ${props.timeframe}`)
    // For now, just regenerate sample data
    const data = generateSampleData()
    candlestickSeries.value?.setData(data)
  }
})

// Listen for theme changes
onMounted(() => {
  initializeChart()
  
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
    chart.value.remove()
    chart.value = null
  }
})

// Expose methods for parent component
defineExpose({
  chart,
  candlestickSeries,
  updateData: (data) => {
    if (candlestickSeries.value) {
      candlestickSeries.value.setData(data)
    }
  }
})
</script>

<style scoped>
.trading-chart-container {
  position: relative;
  border-radius: 0;
  overflow: hidden;
  background: white;
}

.dark .trading-chart-container {
  background: rgb(17, 24, 39);
}

.chart-wrapper {
  width: 100%;
  position: relative;
}

/* Loading animation */
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}

/* Ensure chart renders properly */
.chart-wrapper > div {
  border-radius: 0 !important;
}
</style>