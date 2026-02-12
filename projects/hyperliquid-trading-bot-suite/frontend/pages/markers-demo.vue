<template>
  <div class="markers-demo-page">
    <div class="container mx-auto px-4 py-8">
      <!-- Page Header -->
      <div class="page-header mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Trade Markers Demo
        </h1>
        <p class="text-gray-600 dark:text-gray-400">
          Interactive demonstration of trade markers and overlays on price charts
        </p>
      </div>

      <!-- Control Panel -->
      <div class="control-panel mb-6">
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Configuration
          </h2>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <!-- Symbol and Timeframe -->
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Symbol
              </label>
              <select
                v-model="symbol"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="ETH/USD">ETH/USD</option>
                <option value="BTC/USD">BTC/USD</option>
                <option value="SOL/USD">SOL/USD</option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Timeframe
              </label>
              <select
                v-model="timeframe"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="1m">1 Minute</option>
                <option value="5m">5 Minutes</option>
                <option value="15m">15 Minutes</option>
                <option value="1h">1 Hour</option>
                <option value="4h">4 Hours</option>
                <option value="1d">1 Day</option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Chart Height
              </label>
              <input
                v-model.number="chartHeight"
                type="range"
                min="400"
                max="1000"
                step="50"
                class="w-full"
              />
              <span class="text-sm text-gray-600 dark:text-gray-400">{{ chartHeight }}px</span>
            </div>
          </div>

          <!-- Marker Display Options -->
          <div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-3">
              Display Options
            </h3>
            
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <label class="flex items-center space-x-2">
                <input
                  v-model="markerConfig.showEntryMarkers"
                  type="checkbox"
                  class="rounded text-blue-500"
                />
                <span class="text-sm text-gray-700 dark:text-gray-300">Entry Markers</span>
              </label>

              <label class="flex items-center space-x-2">
                <input
                  v-model="markerConfig.showExitMarkers"
                  type="checkbox"
                  class="rounded text-blue-500"
                />
                <span class="text-sm text-gray-700 dark:text-gray-300">Exit Markers</span>
              </label>

              <label class="flex items-center space-x-2">
                <input
                  v-model="markerConfig.showStopLoss"
                  type="checkbox"
                  class="rounded text-blue-500"
                />
                <span class="text-sm text-gray-700 dark:text-gray-300">Stop Loss</span>
              </label>

              <label class="flex items-center space-x-2">
                <input
                  v-model="markerConfig.showTakeProfit"
                  type="checkbox"
                  class="rounded text-blue-500"
                />
                <span class="text-sm text-gray-700 dark:text-gray-300">Take Profit</span>
              </label>

              <label class="flex items-center space-x-2">
                <input
                  v-model="markerConfig.showPartialExits"
                  type="checkbox"
                  class="rounded text-blue-500"
                />
                <span class="text-sm text-gray-700 dark:text-gray-300">Partial Exits</span>
              </label>

              <label class="flex items-center space-x-2">
                <input
                  v-model="markerConfig.showTradeZones"
                  type="checkbox"
                  class="rounded text-blue-500"
                />
                <span class="text-sm text-gray-700 dark:text-gray-300">Trade Zones</span>
              </label>

              <label class="flex items-center space-x-2">
                <input
                  v-model="markerConfig.showPriceLines"
                  type="checkbox"
                  class="rounded text-blue-500"
                />
                <span class="text-sm text-gray-700 dark:text-gray-300">Price Lines</span>
              </label>

              <label class="flex items-center space-x-2">
                <input
                  v-model="markerConfig.showLabels"
                  type="checkbox"
                  class="rounded text-blue-500"
                />
                <span class="text-sm text-gray-700 dark:text-gray-300">Labels</span>
              </label>
            </div>
          </div>

          <!-- Demo Actions -->
          <div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-3">
              Demo Actions
            </h3>
            
            <div class="flex flex-wrap gap-3">
              <button
                @click="loadSampleTrades"
                class="btn-primary"
              >
                Load Sample Trades
              </button>

              <button
                @click="addRandomTrade"
                class="btn-secondary"
              >
                Add Random Trade
              </button>

              <button
                @click="clearAllTrades"
                class="btn-secondary text-red-600"
              >
                Clear All
              </button>

              <button
                @click="refreshChart"
                class="btn-secondary"
              >
                Refresh Chart
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Chart with Markers -->
      <div class="chart-section mb-6">
        <ChartWithTradeMarkers
          ref="chartRef"
          :symbol="symbol"
          :initial-timeframe="timeframe"
          :height="chartHeight"
          :show-volume="true"
          :auto-load="false"
        />
      </div>

      <!-- Statistics Panel -->
      <div class="stats-panel">
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Performance Statistics
          </h2>
          
          <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <div class="stat-card">
              <div class="stat-label">Total Trades</div>
              <div class="stat-value">{{ stats.totalTrades }}</div>
            </div>

            <div class="stat-card">
              <div class="stat-label">Win Rate</div>
              <div class="stat-value" :class="stats.winRate >= 50 ? 'text-green-600' : 'text-red-600'">
                {{ stats.winRate.toFixed(1) }}%
              </div>
            </div>

            <div class="stat-card">
              <div class="stat-label">Profit Factor</div>
              <div class="stat-value" :class="stats.profitFactor >= 1 ? 'text-green-600' : 'text-red-600'">
                {{ stats.profitFactor.toFixed(2) }}
              </div>
            </div>

            <div class="stat-card">
              <div class="stat-label">Avg R-Multiple</div>
              <div class="stat-value" :class="stats.averageRMultiple >= 1 ? 'text-green-600' : 'text-red-600'">
                {{ stats.averageRMultiple.toFixed(2) }}R
              </div>
            </div>

            <div class="stat-card">
              <div class="stat-label">Net P&L</div>
              <div class="stat-value" :class="stats.netPnl >= 0 ? 'text-green-600' : 'text-red-600'">
                {{ formatCurrency(stats.netPnl) }}
              </div>
            </div>

            <div class="stat-card">
              <div class="stat-label">Active Trades</div>
              <div class="stat-value text-blue-600">{{ stats.pendingTrades }}</div>
            </div>
          </div>

          <!-- Detailed Breakdown -->
          <div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div class="text-center">
                <div class="text-2xl font-bold text-green-600">{{ stats.winningTrades }}</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Wins</div>
              </div>

              <div class="text-center">
                <div class="text-2xl font-bold text-red-600">{{ stats.losingTrades }}</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Losses</div>
              </div>

              <div class="text-center">
                <div class="text-2xl font-bold text-gray-600">{{ stats.breakevenTrades }}</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Breakeven</div>
              </div>

              <div class="text-center">
                <div class="text-2xl font-bold text-blue-600">{{ stats.pendingTrades }}</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Pending</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Timeframe } from '~/types/chart'
import { useTradeMarkers } from '~/composables/useTradeMarkers'

// Page metadata
definePageMeta({
  title: 'Trade Markers Demo',
  layout: 'default',
})

// Composables
const {
  stats,
  config,
  createTradeMarkers,
  clearAll,
  updateConfig,
} = useTradeMarkers()

// Refs
const chartRef = ref<any>(null)
const symbol = ref('ETH/USD')
const timeframe = ref<Timeframe>('15m')
const chartHeight = ref(700)

// Config binding
const markerConfig = config

// Watch for config changes
watch(markerConfig, (newConfig) => {
  updateConfig(newConfig)
}, { deep: true })

// Watch for symbol/timeframe changes
watch([symbol, timeframe], () => {
  // Could reload trades here
})

// Load sample trades
const loadSampleTrades = () => {
  clearAll()
  
  const now = Math.floor(Date.now() / 1000)
  const oneHour = 3600
  
  // Sample trade 1: Winning long trade
  createTradeMarkers({
    id: 'sample-1',
    strategy_rule_id: 'strategy-1',
    asset: symbol.value.replace('/', ''),
    direction: 'buy',
    entry_price: 2400,
    entry_time: new Date((now - oneHour * 48) * 1000).toISOString(),
    quantity: 1.5,
    exit_price: 2460,
    exit_time: new Date((now - oneHour * 24) * 1000).toISOString(),
    exit_reason: 'take_profit',
    outcome: 'win',
    pnl_absolute: 90,
    pnl_r_multiple: 2.0,
    fees_paid: 3.6,
    reasoning: 'LE candle at demand zone with HTF bullish bias',
    initial_stop_loss: 2370,
    current_stop_loss: 2400,
    take_profit_levels: [2430, 2460],
    partial_exits: [],
    trading_mode: 'paper',
  })
  
  // Sample trade 2: Losing short trade
  createTradeMarkers({
    id: 'sample-2',
    strategy_rule_id: 'strategy-1',
    asset: symbol.value.replace('/', ''),
    direction: 'sell',
    entry_price: 2440,
    entry_time: new Date((now - oneHour * 36) * 1000).toISOString(),
    quantity: 1.0,
    exit_price: 2465,
    exit_time: new Date((now - oneHour * 30) * 1000).toISOString(),
    exit_reason: 'stop_loss',
    outcome: 'loss',
    pnl_absolute: -25,
    pnl_r_multiple: -1.0,
    fees_paid: 2.4,
    reasoning: 'Failed breakdown at support',
    initial_stop_loss: 2465,
    current_stop_loss: 2465,
    take_profit_levels: [2410, 2380],
    partial_exits: [],
    trading_mode: 'paper',
  })
  
  // Sample trade 3: Active long trade
  createTradeMarkers({
    id: 'sample-3',
    strategy_rule_id: 'strategy-1',
    asset: symbol.value.replace('/', ''),
    direction: 'buy',
    entry_price: 2450,
    entry_time: new Date((now - oneHour * 12) * 1000).toISOString(),
    quantity: 2.0,
    exit_price: null,
    exit_time: null,
    exit_reason: null,
    outcome: 'pending',
    pnl_absolute: 0,
    pnl_r_multiple: 0,
    fees_paid: 2.45,
    reasoning: 'Breakout above resistance with strong volume',
    initial_stop_loss: 2430,
    current_stop_loss: 2445,
    take_profit_levels: [2470, 2490, 2510],
    partial_exits: [],
    trading_mode: 'paper',
  })
  
  // Sample trade 4: Trade with partial exits
  createTradeMarkers({
    id: 'sample-4',
    strategy_rule_id: 'strategy-1',
    asset: symbol.value.replace('/', ''),
    direction: 'buy',
    entry_price: 2380,
    entry_time: new Date((now - oneHour * 60) * 1000).toISOString(),
    quantity: 3.0,
    exit_price: 2425,
    exit_time: new Date((now - oneHour * 40) * 1000).toISOString(),
    exit_reason: 'manual',
    outcome: 'win',
    pnl_absolute: 120,
    pnl_r_multiple: 1.8,
    fees_paid: 7.2,
    reasoning: 'Range bounce play with HTF confirmation',
    initial_stop_loss: 2360,
    current_stop_loss: 2380,
    take_profit_levels: [2410, 2440],
    partial_exits: [
      {
        time: new Date((now - oneHour * 48) * 1000).toISOString(),
        price: 2410,
        quantity: 1.0,
        pnl: 30,
      },
      {
        time: new Date((now - oneHour * 44) * 1000).toISOString(),
        price: 2420,
        quantity: 1.0,
        pnl: 40,
      },
    ],
    trading_mode: 'paper',
  })
}

// Add random trade
const addRandomTrade = () => {
  const now = Math.floor(Date.now() / 1000)
  const basePrice = 2400
  const priceVariation = Math.random() * 100 - 50
  const entryPrice = basePrice + priceVariation
  const isLong = Math.random() > 0.5
  const isWin = Math.random() > 0.4
  
  const stopDistance = entryPrice * 0.015
  const tpDistance = entryPrice * 0.025
  
  const exitPrice = isWin
    ? (isLong ? entryPrice + tpDistance : entryPrice - tpDistance)
    : (isLong ? entryPrice - stopDistance : entryPrice + stopDistance)
  
  createTradeMarkers({
    id: `random-${Date.now()}`,
    strategy_rule_id: 'strategy-1',
    asset: symbol.value.replace('/', ''),
    direction: isLong ? 'buy' : 'sell',
    entry_price: entryPrice,
    entry_time: new Date((now - 3600 * 24) * 1000).toISOString(),
    quantity: 1.0,
    exit_price: exitPrice,
    exit_time: new Date((now - 3600 * 12) * 1000).toISOString(),
    exit_reason: isWin ? 'take_profit' : 'stop_loss',
    outcome: isWin ? 'win' : 'loss',
    pnl_absolute: isWin ? tpDistance : -stopDistance,
    pnl_r_multiple: isWin ? 1.5 : -1.0,
    fees_paid: 2.0,
    reasoning: 'Random test trade',
    initial_stop_loss: isLong ? entryPrice - stopDistance : entryPrice + stopDistance,
    current_stop_loss: isLong ? entryPrice - stopDistance : entryPrice + stopDistance,
    take_profit_levels: isLong 
      ? [entryPrice + tpDistance, entryPrice + tpDistance * 1.5] 
      : [entryPrice - tpDistance, entryPrice - tpDistance * 1.5],
    partial_exits: [],
    trading_mode: 'paper',
  })
}

// Clear all trades
const clearAllTrades = () => {
  clearAll()
}

// Refresh chart
const refreshChart = () => {
  chartRef.value?.refresh()
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

// Load sample trades on mount
onMounted(() => {
  loadSampleTrades()
})
</script>

<style scoped>
.markers-demo-page {
  @apply min-h-screen bg-gray-50 dark:bg-gray-900;
}

.page-header {
  @apply border-b border-gray-200 dark:border-gray-700 pb-4;
}

.btn-primary {
  @apply px-4 py-2 bg-blue-500 text-white rounded-lg;
  @apply hover:bg-blue-600 transition-colors;
  @apply font-medium text-sm;
}

.btn-secondary {
  @apply px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg;
  @apply hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors;
  @apply font-medium text-sm;
}

.stat-card {
  @apply text-center;
}

.stat-label {
  @apply text-xs text-gray-600 dark:text-gray-400 font-medium mb-1;
}

.stat-value {
  @apply text-lg font-bold text-gray-900 dark:text-white;
}
</style>
