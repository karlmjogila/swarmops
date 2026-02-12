<template>
  <div class="tradingview-widget-container">
    <div 
      ref="widgetContainer" 
      class="widget-wrapper"
      :style="{ height: height + 'px' }"
    />
    
    <!-- Loading overlay -->
    <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-white/90 dark:bg-gray-900/90 rounded-lg">
      <div class="flex items-center space-x-3">
        <div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        <span class="text-gray-600 dark:text-gray-400">Loading TradingView...</span>
      </div>
    </div>
    
    <!-- Error state -->
    <div v-if="error" class="absolute inset-0 flex items-center justify-center bg-white/90 dark:bg-gray-900/90 rounded-lg">
      <div class="text-center">
        <svg class="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 15.5c-.77.833.192 2.5 1.732 2.5z"/>
        </svg>
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Widget Error</h3>
        <p class="text-gray-600 dark:text-gray-400 mb-4">{{ error }}</p>
        <button @click="initializeWidget" class="btn btn-primary">
          Retry
        </button>
      </div>
    </div>

    <!-- TradingView Attribution -->
    <div class="tradingview-attribution">
      <a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank">
        <span class="blue-text">Track all markets on TradingView</span>
      </a>
    </div>
  </div>
</template>

<script setup>
// Props
const props = defineProps({
  symbol: {
    type: String,
    default: 'BINANCE:ETHUSDT'
  },
  interval: {
    type: String,
    default: '15'
  },
  height: {
    type: Number,
    default: 500
  },
  theme: {
    type: String,
    default: 'light', // light or dark
    validator: (value) => ['light', 'dark'].includes(value)
  },
  style: {
    type: String,
    default: '1', // 1: candles, 2: hollow candles, 3: heikin ashi, etc.
  },
  toolbar_bg: {
    type: String,
    default: '#f1f3f6'
  },
  enable_publishing: {
    type: Boolean,
    default: false
  },
  withdateranges: {
    type: Boolean,
    default: false
  },
  hide_side_toolbar: {
    type: Boolean,
    default: false
  },
  allow_symbol_change: {
    type: Boolean,
    default: true
  },
  studies: {
    type: Array,
    default: () => []
  },
  show_popup_button: {
    type: Boolean,
    default: false
  },
  popup_width: {
    type: String,
    default: '1000'
  },
  popup_height: {
    type: String,
    default: '650'
  }
})

// Refs
const widgetContainer = ref(null)
const widget = ref(null)
const loading = ref(true)
const error = ref(null)

// Get current theme from system/user preference
const getTheme = () => {
  if (props.theme !== 'auto') return props.theme
  
  // Check for system dark mode preference
  if (typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return 'light'
}

// Widget configuration
const getWidgetConfig = () => {
  const currentTheme = getTheme()
  
  return {
    width: '100%',
    height: props.height,
    symbol: props.symbol,
    interval: props.interval,
    timezone: 'Etc/UTC',
    theme: currentTheme,
    style: props.style,
    locale: 'en',
    toolbar_bg: currentTheme === 'dark' ? '#1f2937' : props.toolbar_bg,
    enable_publishing: props.enable_publishing,
    withdateranges: props.withdateranges,
    hide_side_toolbar: props.hide_side_toolbar,
    allow_symbol_change: props.allow_symbol_change,
    studies: props.studies,
    show_popup_button: props.show_popup_button,
    popup_width: props.popup_width,
    popup_height: props.popup_height,
    container_id: 'tradingview-widget'
  }
}

// Load TradingView widget script
const loadTradingViewScript = () => {
  return new Promise((resolve, reject) => {
    // Check if script is already loaded
    if (window.TradingView) {
      resolve()
      return
    }

    // Check if script tag already exists
    const existingScript = document.querySelector('script[src*="tradingview.com/external-embedding"]')
    if (existingScript) {
      existingScript.addEventListener('load', resolve)
      existingScript.addEventListener('error', reject)
      return
    }

    // Create and load script
    const script = document.createElement('script')
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js'
    script.async = true
    script.onload = resolve
    script.onerror = () => reject(new Error('Failed to load TradingView script'))
    
    document.head.appendChild(script)
  })
}

// Initialize widget
const initializeWidget = async () => {
  try {
    loading.value = true
    error.value = null

    if (!widgetContainer.value) {
      throw new Error('Widget container not found')
    }

    // Clear existing content
    widgetContainer.value.innerHTML = ''

    // Load TradingView script if needed
    await loadTradingViewScript()

    // Wait a bit for script to be ready
    await new Promise(resolve => setTimeout(resolve, 100))

    // Create widget container div
    const widgetDiv = document.createElement('div')
    widgetDiv.id = 'tradingview-widget'
    widgetDiv.style.width = '100%'
    widgetDiv.style.height = '100%'
    widgetContainer.value.appendChild(widgetDiv)

    // Initialize widget
    if (window.TradingView && window.TradingView.widget) {
      widget.value = new window.TradingView.widget(getWidgetConfig())
      
      // Widget ready callback
      widget.value.onChartReady(() => {
        loading.value = false
        console.log('TradingView widget loaded successfully')
      })
    } else {
      throw new Error('TradingView widget not available')
    }

  } catch (err) {
    console.error('TradingView widget initialization error:', err)
    error.value = err.message
    loading.value = false
  }
}

// Watch for prop changes
watch([() => props.symbol, () => props.interval, () => props.theme], () => {
  if (widget.value) {
    // Re-initialize widget with new configuration
    initializeWidget()
  }
})

// Initialize on mount
onMounted(() => {
  // Small delay to ensure DOM is ready
  nextTick(() => {
    initializeWidget()
  })

  // Listen for theme changes if theme is set to auto
  if (props.theme === 'auto' && typeof window !== 'undefined') {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleThemeChange = () => {
      if (widget.value) {
        initializeWidget()
      }
    }
    
    mediaQuery.addListener(handleThemeChange)
    
    onUnmounted(() => {
      mediaQuery.removeListener(handleThemeChange)
    })
  }
})

// Cleanup on unmount
onUnmounted(() => {
  if (widget.value && typeof widget.value.remove === 'function') {
    widget.value.remove()
    widget.value = null
  }
})

// Expose methods for parent component
defineExpose({
  widget,
  reinitialize: initializeWidget,
  updateSymbol: (newSymbol) => {
    if (widget.value && typeof widget.value.setSymbol === 'function') {
      widget.value.setSymbol(newSymbol)
    }
  }
})
</script>

<style scoped>
.tradingview-widget-container {
  position: relative;
  width: 100%;
  border-radius: 1rem;
  overflow: hidden;
  background: white;
  box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.1));
}

.dark .tradingview-widget-container {
  background: rgb(31, 41, 55);
}

.widget-wrapper {
  width: 100%;
  position: relative;
  border-radius: 1rem;
  overflow: hidden;
}

/* TradingView attribution styling */
.tradingview-attribution {
  position: absolute;
  bottom: 0;
  right: 0;
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.9);
  font-size: 0.75rem;
  border-radius: 0.5rem 0 1rem 0;
  backdrop-filter: blur(4px);
}

.dark .tradingview-attribution {
  background: rgba(31, 41, 55, 0.9);
}

.tradingview-attribution a {
  text-decoration: none;
  color: #2563eb;
  font-weight: 500;
}

.tradingview-attribution a:hover {
  text-decoration: underline;
}

.dark .tradingview-attribution a {
  color: #60a5fa;
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

/* Button styles */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 600;
  transition: all 0.2s ease;
  cursor: pointer;
  border: none;
  text-decoration: none;
}

.btn-primary {
  background: #2563eb;
  color: white;
}

.btn-primary:hover {
  background: #1d4ed8;
  transform: translateY(-1px);
}

/* Ensure widget fills container properly */
:deep(.tradingview-widget-container iframe) {
  border-radius: 1rem;
}

/* Hide TradingView branding if needed (be careful with ToS) */
:deep(.tv-embed-widget-wrapper) {
  border-radius: 1rem;
  overflow: hidden;
}
</style>