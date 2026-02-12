<template>
  <div class="replay-demo-page">
    <section class="section-lg">
      <div class="container">
        <!-- Page Header -->
        <div class="text-center mb-12">
          <h1 class="mb-4">Replay Controls Demo</h1>
          <p class="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Interactive demo of the ReplayControls component for historical data playback
          </p>
        </div>

        <!-- Demo Container -->
        <div class="max-w-6xl mx-auto space-y-8">
          <!-- Chart Visualization (Placeholder) -->
          <div class="card">
            <div class="card-body">
              <h2 class="text-xl font-semibold mb-4">Chart Visualization</h2>
              
              <!-- Chart Placeholder -->
              <div class="relative h-96 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg flex items-center justify-center">
                <div class="text-center">
                  <!-- Current Candle Info -->
                  <div v-if="currentCandle" class="bg-white/90 dark:bg-gray-800/90 p-6 rounded-lg shadow-lg">
                    <div class="text-3xl font-bold mb-2" :class="priceChangeClass">
                      {{ formatPrice(currentCandle.close) }}
                    </div>
                    <div class="grid grid-cols-4 gap-4 text-sm">
                      <div>
                        <div class="text-gray-500 dark:text-gray-400">Open</div>
                        <div class="font-semibold">{{ formatPrice(currentCandle.open) }}</div>
                      </div>
                      <div>
                        <div class="text-gray-500 dark:text-gray-400">High</div>
                        <div class="font-semibold">{{ formatPrice(currentCandle.high) }}</div>
                      </div>
                      <div>
                        <div class="text-gray-500 dark:text-gray-400">Low</div>
                        <div class="font-semibold">{{ formatPrice(currentCandle.low) }}</div>
                      </div>
                      <div>
                        <div class="text-gray-500 dark:text-gray-400">Volume</div>
                        <div class="font-semibold">{{ formatVolume(currentCandle.volume || 0) }}</div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="text-gray-500">
                    <p>Load sample data to begin</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Replay Controls -->
          <ReplayControls
            v-if="sampleData.length > 0"
            :total-points="sampleData.length"
            :current-time="currentCandle?.time || 0"
            :start-time="startTime"
            :end-time="endTime"
            :markers="tradeMarkers"
            :current-price="currentCandle?.close"
            :current-volume="currentCandle?.volume"
            :show-status-bar="true"
            :show-stats="true"
            @play="handlePlay"
            @pause="handlePause"
            @seek="handleSeek"
            @step="handleStep"
            @reset="handleReset"
            @speed-change="handleSpeedChange"
            @settings="handleSettings"
          />

          <!-- Controls -->
          <div class="card">
            <div class="card-body">
              <h3 class="text-lg font-semibold mb-4">Demo Controls</h3>
              
              <div class="flex gap-4">
                <button
                  v-if="sampleData.length === 0"
                  @click="loadSampleData"
                  class="btn btn-primary"
                >
                  Load Sample Data
                </button>
                
                <button
                  v-else
                  @click="clearData"
                  class="btn btn-secondary"
                >
                  Clear Data
                </button>

                <button
                  @click="addTradeMarker"
                  :disabled="!currentCandle"
                  class="btn btn-secondary"
                >
                  Add Trade Marker
                </button>
              </div>
            </div>
          </div>

          <!-- Event Log -->
          <div class="card">
            <div class="card-body">
              <h3 class="text-lg font-semibold mb-4">Event Log</h3>
              
              <div class="max-h-48 overflow-y-auto space-y-2">
                <div
                  v-for="(event, index) in eventLog"
                  :key="index"
                  class="text-sm font-mono bg-gray-50 dark:bg-gray-800 p-2 rounded"
                >
                  <span class="text-gray-500">{{ event.time }}</span>
                  <span class="ml-2 font-semibold">{{ event.type }}</span>
                  <span v-if="event.data" class="ml-2 text-gray-600 dark:text-gray-400">
                    {{ event.data }}
                  </span>
                </div>
                
                <div v-if="eventLog.length === 0" class="text-gray-500 text-center py-4">
                  No events yet
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { CandleData, TradeMarker } from '~/types/chart'

// Page metadata
useHead({
  title: 'Replay Controls Demo - Hyperliquid Trading',
  meta: [
    { name: 'description', content: 'Interactive demo of replay controls for backtesting.' }
  ]
})

// State
const sampleData = ref<CandleData[]>([])
const currentIndex = ref(0)
const tradeMarkers = ref<TradeMarker[]>([])
const eventLog = ref<Array<{ time: string; type: string; data?: string }>>([])

// Computed
const currentCandle = computed(() => {
  return sampleData.value[currentIndex.value]
})

const startTime = computed(() => {
  return sampleData.value[0]?.time || 0
})

const endTime = computed(() => {
  return sampleData.value[sampleData.value.length - 1]?.time || 0
})

const priceChangeClass = computed(() => {
  if (!currentCandle.value) return ''
  return currentCandle.value.close >= currentCandle.value.open
    ? 'text-green-600 dark:text-green-400'
    : 'text-red-600 dark:text-red-400'
})

// Methods
function loadSampleData() {
  const now = Date.now()
  const data: CandleData[] = []
  let price = 3200
  
  // Generate 500 sample candles (5-minute intervals)
  for (let i = 0; i < 500; i++) {
    const time = Math.floor((now - (500 - i) * 5 * 60 * 1000) / 1000)
    const change = (Math.random() - 0.5) * 40
    const open = price
    const close = price + change
    const high = Math.max(open, close) + Math.random() * 10
    const low = Math.min(open, close) - Math.random() * 10
    const volume = Math.random() * 1000 + 100
    
    data.push({
      time,
      open: parseFloat(open.toFixed(2)),
      high: parseFloat(high.toFixed(2)),
      low: parseFloat(low.toFixed(2)),
      close: parseFloat(close.toFixed(2)),
      volume: parseFloat(volume.toFixed(2)),
    })
    
    price = close
  }
  
  sampleData.value = data
  currentIndex.value = 0
  
  logEvent('DATA_LOADED', `${data.length} candles`)
  
  // Add some sample trade markers
  tradeMarkers.value = [
    {
      id: '1',
      time: data[100].time,
      type: 'entry',
      side: 'buy',
      price: data[100].close,
      quantity: 1.5,
      reason: 'Sample entry'
    },
    {
      id: '2',
      time: data[150].time,
      type: 'exit',
      side: 'sell',
      price: data[150].close,
      quantity: 1.5,
      pnl: (data[150].close - data[100].close) * 1.5,
      reason: 'Sample exit'
    },
  ]
}

function clearData() {
  sampleData.value = []
  currentIndex.value = 0
  tradeMarkers.value = []
  eventLog.value = []
}

function addTradeMarker() {
  if (!currentCandle.value) return
  
  const side = Math.random() > 0.5 ? 'buy' : 'sell' as const
  const marker: TradeMarker = {
    id: `marker-${Date.now()}`,
    time: currentCandle.value.time,
    type: 'entry',
    side: side,
    price: currentCandle.value.close,
    quantity: Math.random() * 2 + 0.5,
  }
  
  tradeMarkers.value.push(marker)
  logEvent('MARKER_ADDED', `${marker.side} @ ${formatPrice(marker.price)}`)
}

function handlePlay() {
  logEvent('PLAY', 'Playback started')
}

function handlePause() {
  logEvent('PAUSE', 'Playback paused')
}

function handleSeek(index: number) {
  currentIndex.value = index
  logEvent('SEEK', `Index: ${index}`)
}

function handleStep(direction: 'forward' | 'backward') {
  logEvent('STEP', direction)
}

function handleReset() {
  currentIndex.value = 0
  logEvent('RESET', 'Reset to start')
}

function handleSpeedChange(speed: number) {
  logEvent('SPEED_CHANGE', `${speed}x`)
}

function handleSettings() {
  logEvent('SETTINGS', 'Settings clicked')
}

function logEvent(type: string, data?: string) {
  const time = new Date().toLocaleTimeString()
  eventLog.value.unshift({ time, type, data })
  
  // Keep only last 50 events
  if (eventLog.value.length > 50) {
    eventLog.value = eventLog.value.slice(0, 50)
  }
}

function formatPrice(price: number): string {
  return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatVolume(volume: number): string {
  if (volume >= 1000000) {
    return `${(volume / 1000000).toFixed(2)}M`
  } else if (volume >= 1000) {
    return `${(volume / 1000).toFixed(2)}K`
  }
  return volume.toFixed(2)
}

// Auto-load sample data on mount
onMounted(() => {
  loadSampleData()
})
</script>

<style scoped>
.replay-demo-page {
  min-height: 100vh;
  padding-bottom: 4rem;
}
</style>
