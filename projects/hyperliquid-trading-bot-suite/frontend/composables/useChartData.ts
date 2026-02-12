/**
 * useChartData - Composable for managing multi-timeframe chart data
 * 
 * Handles data fetching, caching, and real-time updates for trading charts.
 * Includes rate limiting to prevent exceeding API limits.
 */

import type { CandleData, Timeframe, TimeframeConfig, MarketData } from '~/types/chart'
import { RateLimiter, debounce } from '~/utils/rate-limiter'

// Rate limiter for market data - 120 requests per minute with 80% headroom
const marketDataRateLimiter = new RateLimiter({
  maxRequests: 120,
  windowMs: 60000,
  headroom: 0.8,
  retryAfterMs: 1000,
})

// Timeframe configurations
export const TIMEFRAMES: TimeframeConfig[] = [
  { value: '1m', label: '1 Minute', seconds: 60, chartInterval: '1' },
  { value: '5m', label: '5 Minutes', seconds: 300, chartInterval: '5' },
  { value: '15m', label: '15 Minutes', seconds: 900, chartInterval: '15' },
  { value: '30m', label: '30 Minutes', seconds: 1800, chartInterval: '30' },
  { value: '1h', label: '1 Hour', seconds: 3600, chartInterval: '60' },
  { value: '4h', label: '4 Hours', seconds: 14400, chartInterval: '240' },
  { value: '1d', label: '1 Day', seconds: 86400, chartInterval: 'D' },
  { value: '1w', label: '1 Week', seconds: 604800, chartInterval: 'W' },
]

export function useChartData() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl
  
  // State
  const currentSymbol = ref<string>('ETH/USD')
  const currentTimeframe = ref<Timeframe>('15m')
  const marketData = ref<Map<string, MarketData>>(new Map())
  const loading = ref<boolean>(false)
  const error = ref<string | null>(null)
  const lastUpdate = ref<number>(Date.now())

  /**
   * Get cache key for symbol and timeframe combination
   */
  const getCacheKey = (symbol: string, timeframe: Timeframe): string => {
    return `${symbol}:${timeframe}`
  }

  /**
   * Get timeframe configuration
   */
  const getTimeframeConfig = (timeframe: Timeframe): TimeframeConfig | undefined => {
    return TIMEFRAMES.find(tf => tf.value === timeframe)
  }

  /**
   * Generate sample candle data for development/testing
   */
  const generateSampleData = (
    symbol: string,
    timeframe: Timeframe,
    count: number = 500
  ): CandleData[] => {
    const data: CandleData[] = []
    const basePrice = symbol.includes('ETH') ? 3200 : symbol.includes('BTC') ? 65000 : 100
    let currentPrice = basePrice
    
    const tfConfig = getTimeframeConfig(timeframe)
    if (!tfConfig) return data
    
    const startTime = Date.now() - (count * tfConfig.seconds * 1000)

    for (let i = 0; i < count; i++) {
      const time = startTime + (i * tfConfig.seconds * 1000)
      const change = (Math.random() - 0.5) * (basePrice * 0.02) // 2% max change
      const open = currentPrice
      const volatility = basePrice * (Math.random() * 0.01 + 0.005) // 0.5-1.5% volatility
      const high = open + Math.random() * volatility
      const low = open - Math.random() * volatility
      const close = open + change
      const volume = Math.random() * 1000 + 100
      
      data.push({
        time: Math.floor(time / 1000), // Unix timestamp in seconds
        open: parseFloat(open.toFixed(2)),
        high: parseFloat(Math.max(high, open, close).toFixed(2)),
        low: parseFloat(Math.min(low, open, close).toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        volume: parseFloat(volume.toFixed(2)),
      })
      
      currentPrice = close
    }
    
    return data
  }

  /**
   * Fetch candle data from API with rate limiting
   */
  const fetchCandleData = async (
    symbol: string,
    timeframe: Timeframe,
    limit: number = 500
  ): Promise<CandleData[]> => {
    // Check rate limit before making request
    if (!marketDataRateLimiter.canRequest()) {
      const waitTime = marketDataRateLimiter.getWaitTime()
      console.warn(`Rate limited: waiting ${waitTime}ms before next market data request`)
      await marketDataRateLimiter.waitForSlot()
    }
    
    try {
      // Record this request
      marketDataRateLimiter.recordRequest()
      
      // In production, this would call the actual API
      // For now, using sample data
      
      // Example API call (commented out):
      // const response = await $fetch<{ candles: CandleData[] }>(
      //   `${apiBaseUrl}/api/market/candles`,
      //   {
      //     query: {
      //       symbol: symbol.replace('/', ''),
      //       timeframe,
      //       limit,
      //     },
      //     timeout: 10000,
      //   }
      // )
      // return response.candles

      // Generate sample data for development
      return generateSampleData(symbol, timeframe, limit)
    } catch (err: any) {
      // Check for rate limit response (429)
      if (err.statusCode === 429) {
        const retryAfter = parseInt(err.headers?.['retry-after'] || '60', 10) * 1000
        marketDataRateLimiter.markLimited(retryAfter)
        throw new Error(`Rate limited. Please wait ${Math.ceil(retryAfter / 1000)} seconds.`)
      }
      console.error('Error fetching candle data:', err)
      throw new Error(`Failed to fetch candle data: ${err.message}`)
    }
  }

  /**
   * Load data for a specific symbol and timeframe
   */
  const loadData = async (symbol: string, timeframe: Timeframe): Promise<void> => {
    try {
      loading.value = true
      error.value = null

      const cacheKey = getCacheKey(symbol, timeframe)
      
      // Check cache first
      const cached = marketData.value.get(cacheKey)
      const now = Date.now()
      const tfConfig = getTimeframeConfig(timeframe)
      
      // Use cache if it's less than half a timeframe old
      if (cached && tfConfig && (now - cached.lastUpdate) < (tfConfig.seconds * 500)) {
        console.log(`Using cached data for ${cacheKey}`)
        return
      }

      // Fetch fresh data
      const candles = await fetchCandleData(symbol, timeframe)
      
      // Update cache
      marketData.value.set(cacheKey, {
        symbol,
        timeframe,
        candles,
        lastUpdate: now,
      })
      
      lastUpdate.value = now
      loading.value = false
    } catch (err: any) {
      error.value = err.message
      loading.value = false
      throw err
    }
  }

  /**
   * Get data for current symbol and timeframe
   */
  const getCurrentData = computed<CandleData[]>(() => {
    const cacheKey = getCacheKey(currentSymbol.value, currentTimeframe.value)
    const data = marketData.value.get(cacheKey)
    return data?.candles || []
  })

  /**
   * Switch to a different timeframe
   */
  const changeTimeframe = async (timeframe: Timeframe): Promise<void> => {
    currentTimeframe.value = timeframe
    await loadData(currentSymbol.value, timeframe)
  }

  /**
   * Switch to a different symbol
   */
  const changeSymbol = async (symbol: string): Promise<void> => {
    currentSymbol.value = symbol
    await loadData(symbol, currentTimeframe.value)
  }

  /**
   * Update latest candle with new data (for real-time updates)
   */
  const updateLatestCandle = (candle: Partial<CandleData>): void => {
    const cacheKey = getCacheKey(currentSymbol.value, currentTimeframe.value)
    const data = marketData.value.get(cacheKey)
    
    if (data && data.candles.length > 0) {
      const lastCandle = data.candles[data.candles.length - 1]
      
      // Update or append based on timestamp
      if (candle.time && candle.time === lastCandle.time) {
        // Update existing candle
        Object.assign(lastCandle, candle)
      } else if (candle.time && candle.time > lastCandle.time) {
        // New candle - append
        data.candles.push(candle as CandleData)
      }
      
      data.lastUpdate = Date.now()
      lastUpdate.value = data.lastUpdate
    }
  }

  /**
   * Clear all cached data
   */
  const clearCache = (): void => {
    marketData.value.clear()
  }

  /**
   * Get available timeframes
   */
  const availableTimeframes = computed(() => TIMEFRAMES)

  /**
   * Debounced version of changeTimeframe
   */
  const changeTimeframeDebounced = debounce(
    (timeframe: Timeframe) => changeTimeframe(timeframe),
    300
  )

  /**
   * Debounced version of changeSymbol
   */
  const changeSymbolDebounced = debounce(
    (symbol: string) => changeSymbol(symbol),
    300
  )

  /**
   * Get rate limiter state (for debugging/monitoring)
   */
  const getRateLimitState = () => marketDataRateLimiter.getState()

  return {
    // State
    currentSymbol,
    currentTimeframe,
    loading,
    error,
    lastUpdate,
    
    // Computed
    getCurrentData,
    availableTimeframes,
    
    // Methods
    loadData,
    changeTimeframe,
    changeSymbol,
    changeTimeframeDebounced,
    changeSymbolDebounced,
    updateLatestCandle,
    clearCache,
    getTimeframeConfig,
    getRateLimitState,
  }
}
