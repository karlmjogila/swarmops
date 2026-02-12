<template>
  <div
    v-if="visible && marker"
    class="trade-marker-tooltip"
    :style="tooltipStyle"
  >
    <div class="tooltip-header" :class="headerClass">
      <div class="flex items-center justify-between">
        <span class="font-semibold text-sm">
          {{ markerTypeLabel }}
        </span>
        <span class="text-xs opacity-75">
          {{ formatTime(marker.time) }}
        </span>
      </div>
    </div>
    
    <div class="tooltip-body">
      <!-- Price and Quantity -->
      <div class="tooltip-row">
        <span class="label">Price:</span>
        <span class="value">{{ formatPrice(marker.price) }}</span>
      </div>
      
      <div class="tooltip-row">
        <span class="label">Quantity:</span>
        <span class="value">{{ marker.quantity.toFixed(4) }}</span>
      </div>
      
      <!-- P&L Information (for exits) -->
      <template v-if="marker.type !== 'entry' && marker.pnl !== undefined">
        <div class="tooltip-divider"></div>
        
        <div class="tooltip-row">
          <span class="label">P&L:</span>
          <span class="value" :class="pnlClass">
            {{ formatPnL(marker.pnl) }}
            <span v-if="marker.pnlPercent" class="text-xs ml-1">
              ({{ marker.pnlPercent > 0 ? '+' : '' }}{{ marker.pnlPercent.toFixed(2) }}%)
            </span>
          </span>
        </div>
        
        <div v-if="marker.rMultiple" class="tooltip-row">
          <span class="label">R-Multiple:</span>
          <span class="value" :class="pnlClass">
            {{ marker.rMultiple.toFixed(2) }}R
          </span>
        </div>
        
        <div v-if="marker.fees" class="tooltip-row">
          <span class="label">Fees:</span>
          <span class="value text-gray-600">
            {{ formatPrice(marker.fees) }}
          </span>
        </div>
      </template>
      
      <!-- Reason/Context -->
      <template v-if="marker.reason">
        <div class="tooltip-divider"></div>
        
        <div class="tooltip-section">
          <span class="label block mb-1">
            {{ marker.type === 'entry' ? 'Entry Reason:' : 'Exit Reason:' }}
          </span>
          <span class="text-xs text-gray-700 dark:text-gray-300">
            {{ marker.reason }}
          </span>
        </div>
      </template>
      
      <!-- Trade ID (if available) -->
      <template v-if="marker.tradeId && showTradeId">
        <div class="tooltip-divider"></div>
        
        <div class="tooltip-row">
          <span class="label">Trade ID:</span>
          <span class="value text-xs font-mono">
            {{ marker.tradeId.slice(0, 8) }}...
          </span>
        </div>
      </template>
    </div>
    
    <!-- Actions (optional) -->
    <div v-if="showActions" class="tooltip-actions">
      <button
        @click="handleViewTrade"
        class="action-btn"
        title="View Trade Details"
      >
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
        </svg>
      </button>
      
      <button
        v-if="marker.type === 'entry'"
        @click="handleClosePosition"
        class="action-btn text-red-600"
        title="Close Position"
      >
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TradeMarker } from '~/types/trade-markers'
import { format } from 'date-fns'

// Props
const props = defineProps<{
  marker: TradeMarker | null
  visible: boolean
  position?: { x: number; y: number }
  showTradeId?: boolean
  showActions?: boolean
}>()

// Emits
const emit = defineEmits<{
  viewTrade: [tradeId: string]
  closePosition: [tradeId: string]
}>()

// Computed
const markerTypeLabel = computed(() => {
  if (!props.marker) return ''
  
  const typeLabels: Record<string, string> = {
    'entry': props.marker.side === 'buy' ? 'Long Entry' : 'Short Entry',
    'exit': 'Exit',
    'partial-exit': 'Partial Exit',
    'stop-loss': 'Stop Loss Hit',
    'take-profit': 'Take Profit Hit',
  }
  
  return typeLabels[props.marker.type] || 'Trade'
})

const headerClass = computed(() => {
  if (!props.marker) return ''
  
  const classes: Record<string, string> = {
    'entry': props.marker.side === 'buy' ? 'bg-green-500' : 'bg-red-500',
    'exit': props.marker.pnl && props.marker.pnl > 0 ? 'bg-green-600' : 'bg-red-600',
    'partial-exit': 'bg-blue-500',
    'stop-loss': 'bg-amber-500',
    'take-profit': 'bg-blue-600',
  }
  
  return classes[props.marker.type] || 'bg-gray-500'
})

const pnlClass = computed(() => {
  if (!props.marker || props.marker.pnl === undefined) return ''
  
  if (props.marker.pnl > 0) return 'text-green-600 dark:text-green-400'
  if (props.marker.pnl < 0) return 'text-red-600 dark:text-red-400'
  return 'text-gray-600 dark:text-gray-400'
})

const tooltipStyle = computed(() => {
  if (!props.position) return {}
  
  return {
    left: `${props.position.x}px`,
    top: `${props.position.y}px`,
  }
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

const formatPnL = (pnl: number): string => {
  const prefix = pnl > 0 ? '+' : ''
  return prefix + new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(pnl)
}

const formatTime = (timestamp: number): string => {
  return format(new Date(timestamp * 1000), 'MMM dd, HH:mm')
}

// Actions
const handleViewTrade = () => {
  if (props.marker?.tradeId) {
    emit('viewTrade', props.marker.tradeId)
  }
}

const handleClosePosition = () => {
  if (props.marker?.tradeId) {
    emit('closePosition', props.marker.tradeId)
  }
}
</script>

<style scoped>
.trade-marker-tooltip {
  @apply absolute z-50 pointer-events-auto;
  @apply bg-white dark:bg-gray-800;
  @apply border border-gray-200 dark:border-gray-700;
  @apply rounded-lg shadow-xl;
  @apply min-w-[200px] max-w-[300px];
  transform: translate(-50%, -100%);
  margin-top: -10px;
}

.tooltip-header {
  @apply px-3 py-2 rounded-t-lg;
  @apply text-white;
}

.tooltip-body {
  @apply px-3 py-2;
  @apply text-sm;
}

.tooltip-row {
  @apply flex items-center justify-between;
  @apply py-1;
}

.label {
  @apply text-gray-600 dark:text-gray-400;
  @apply text-xs font-medium;
}

.value {
  @apply text-gray-900 dark:text-gray-100;
  @apply font-semibold;
}

.tooltip-divider {
  @apply border-t border-gray-200 dark:border-gray-700;
  @apply my-2;
}

.tooltip-section {
  @apply py-1;
}

.tooltip-actions {
  @apply flex items-center gap-2;
  @apply px-3 py-2;
  @apply border-t border-gray-200 dark:border-gray-700;
  @apply bg-gray-50 dark:bg-gray-900/50;
  @apply rounded-b-lg;
}

.action-btn {
  @apply p-1.5 rounded;
  @apply text-gray-600 dark:text-gray-400;
  @apply hover:bg-gray-200 dark:hover:bg-gray-700;
  @apply transition-colors;
}

.action-btn:hover {
  @apply text-gray-900 dark:text-gray-100;
}
</style>
