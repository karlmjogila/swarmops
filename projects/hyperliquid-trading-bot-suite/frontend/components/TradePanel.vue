<template>
  <div class="trade-panel" :class="{ 'is-expanded': isExpanded }">
    <!-- SVG Noise Texture -->
    <svg class="noise-overlay" aria-hidden="true">
      <filter id="grain-trade">
        <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="4" stitchTiles="stitch"/>
      </filter>
      <rect width="100%" height="100%" filter="url(#grain-trade)"/>
    </svg>

    <!-- Header Section -->
    <header class="panel-header reveal" :class="{ visible: isVisible }">
      <div class="header-content">
        <div class="header-title-group">
          <h2 class="panel-title">Trade</h2>
          <div class="pair-badge" @click="showPairSelector = !showPairSelector">
            <span class="pair-symbol">{{ selectedPair }}</span>
            <svg class="chevron-icon" :class="{ rotated: showPairSelector }" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
            </svg>
          </div>
        </div>
        <div class="header-stats">
          <div class="stat-pill" :class="priceChangeClass">
            <span class="stat-value">{{ displayPrice }}</span>
            <span class="stat-change">{{ priceChangeFormatted }}</span>
          </div>
        </div>
      </div>

      <!-- Pair Selector Dropdown -->
      <transition name="dropdown">
        <div v-if="showPairSelector" class="pair-selector">
          <input 
            v-model="pairSearch" 
            type="text" 
            placeholder="Search pairs..." 
            class="pair-search-input"
            @focus="pairSearch = ''"
          />
          <div class="pair-list">
            <button 
              v-for="pair in filteredPairs" 
              :key="pair" 
              class="pair-option"
              :class="{ active: pair === selectedPair }"
              @click="selectPair(pair)"
            >
              {{ pair }}
            </button>
          </div>
        </div>
      </transition>
    </header>

    <!-- Order Type Tabs -->
    <div class="order-type-tabs reveal" :class="{ visible: isVisible }" :style="{ transitionDelay: '0.1s' }">
      <button 
        v-for="type in orderTypes" 
        :key="type.value"
        class="order-type-tab"
        :class="{ active: orderType === type.value }"
        @click="orderType = type.value"
      >
        {{ type.label }}
      </button>
    </div>

    <!-- Side Toggle (Long/Short) -->
    <div class="side-toggle reveal" :class="{ visible: isVisible }" :style="{ transitionDelay: '0.15s' }">
      <button 
        class="side-button long"
        :class="{ active: side === 'long' }"
        @click="side = 'long'"
      >
        <svg class="side-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M7 17l5-5 5 5M7 12l5-5 5 5"/>
        </svg>
        <span>Long</span>
      </button>
      <button 
        class="side-button short"
        :class="{ active: side === 'short' }"
        @click="side = 'short'"
      >
        <svg class="side-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M7 7l5 5 5-5M7 12l5 5 5-5"/>
        </svg>
        <span>Short</span>
      </button>
      <div class="side-indicator" :class="side"></div>
    </div>

    <!-- Order Form -->
    <form class="order-form" @submit.prevent="submitOrder">
      <!-- Size Input -->
      <div class="input-group reveal" :class="{ visible: isVisible }" :style="{ transitionDelay: '0.2s' }">
        <label class="input-label">Size</label>
        <div class="input-wrapper" :class="{ error: hasFieldError('size') }">
          <input 
            v-model="sizeInput"
            type="text"
            inputmode="decimal"
            placeholder="0.00"
            class="form-input size-input"
          />
          <div class="input-unit-selector">
            <button 
              type="button"
              class="unit-button"
              :class="{ active: sizeUnit === 'coin' }"
              @click="sizeUnit = 'coin'"
            >
              {{ baseCurrency }}
            </button>
            <button 
              type="button"
              class="unit-button"
              :class="{ active: sizeUnit === 'usd' }"
              @click="sizeUnit = 'usd'"
            >
              USD
            </button>
          </div>
        </div>
        <div class="input-helper">
          <span class="helper-text">≈ {{ displayNotional }} USD</span>
          <div class="quick-size-buttons">
            <button type="button" v-for="pct in [25, 50, 75, 100]" :key="pct" @click="setQuickSize(pct)">
              {{ pct }}%
            </button>
          </div>
        </div>
      </div>

      <!-- Limit Price (only for limit orders) -->
      <transition name="slide-fade">
        <div v-if="orderType === 'limit'" class="input-group reveal visible">
          <label class="input-label">Limit Price</label>
          <div class="input-wrapper" :class="{ error: hasFieldError('price') }">
            <input 
              v-model="limitPriceInput"
              type="text"
              inputmode="decimal"
              placeholder="0.00"
              class="form-input"
            />
            <span class="input-suffix">USDC</span>
          </div>
          <div class="input-helper">
            <button type="button" class="price-helper-btn" @click="setMarketPrice">
              Use market price
            </button>
          </div>
        </div>
      </transition>

      <!-- Leverage Slider -->
      <div class="input-group reveal" :class="{ visible: isVisible }" :style="{ transitionDelay: '0.25s' }">
        <div class="input-label-row">
          <label class="input-label">Leverage</label>
          <span class="leverage-value">{{ leverage }}x</span>
        </div>
        <div class="leverage-slider-container">
          <input 
            v-model.number="leverage"
            type="range"
            :min="1"
            :max="maxLeverage"
            step="1"
            class="leverage-slider"
            :style="{ '--progress': `${(leverage / maxLeverage) * 100}%` }"
          />
          <div class="leverage-marks">
            <span v-for="mark in leverageMarks" :key="mark" 
              class="leverage-mark"
              :class="{ active: leverage >= mark }"
              @click="leverage = mark"
            >
              {{ mark }}x
            </span>
          </div>
        </div>
        <div class="leverage-warning" v-if="leverage > 20">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
          </svg>
          <span>High leverage increases liquidation risk</span>
        </div>
      </div>

      <!-- TP/SL Section -->
      <div class="tpsl-section reveal" :class="{ visible: isVisible }" :style="{ transitionDelay: '0.3s' }">
        <button type="button" class="tpsl-toggle" @click="showTPSL = !showTPSL">
          <span>Take Profit / Stop Loss</span>
          <svg class="toggle-chevron" :class="{ rotated: showTPSL }" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
          </svg>
        </button>

        <transition name="expand">
          <div v-if="showTPSL" class="tpsl-inputs">
            <div class="tpsl-row">
              <div class="input-group compact">
                <label class="input-label small">Take Profit</label>
                <div class="input-wrapper" :class="{ error: hasFieldError('takeProfit') }">
                  <input 
                    v-model="takeProfitInput"
                    type="text"
                    inputmode="decimal"
                    placeholder="—"
                    class="form-input tpsl-input tp"
                  />
                  <span class="input-suffix small">USD</span>
                </div>
                <span class="tpsl-pnl positive" v-if="displayTakeProfitPnL">+{{ displayTakeProfitPnL }}</span>
              </div>
              <div class="input-group compact">
                <label class="input-label small">Stop Loss</label>
                <div class="input-wrapper" :class="{ error: hasFieldError('stopLoss') }">
                  <input 
                    v-model="stopLossInput"
                    type="text"
                    inputmode="decimal"
                    placeholder="—"
                    class="form-input tpsl-input sl"
                  />
                  <span class="input-suffix small">USD</span>
                </div>
                <span class="tpsl-pnl negative" v-if="displayStopLossPnL">{{ displayStopLossPnL }}</span>
              </div>
            </div>
          </div>
        </transition>
      </div>

      <!-- Validation Warnings -->
      <transition name="slide-fade">
        <div v-if="validationWarnings.length > 0" class="validation-warnings">
          <div v-for="warning in validationWarnings" :key="warning.code" class="warning-item">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
            </svg>
            <span>{{ warning.message }}</span>
          </div>
        </div>
      </transition>

      <!-- Order Summary -->
      <div class="order-summary reveal" :class="{ visible: isVisible }" :style="{ transitionDelay: '0.35s' }">
        <div class="summary-row">
          <span class="summary-label">Entry Price</span>
          <span class="summary-value">{{ displayEntryPrice }}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">Liquidation Price</span>
          <span class="summary-value liquidation">{{ displayLiquidationPrice }}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">Margin Required</span>
          <span class="summary-value">{{ displayMarginRequired }}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">Est. Fees</span>
          <span class="summary-value muted">{{ displayEstimatedFees }}</span>
        </div>
      </div>

      <!-- Submit Button -->
      <button 
        type="submit" 
        class="submit-button reveal"
        :class="[side, { visible: isVisible, loading: isSubmitting }]"
        :style="{ transitionDelay: '0.4s' }"
        :disabled="!canSubmit || isSubmitting"
      >
        <span class="button-content" v-if="!isSubmitting">
          <span class="button-side">{{ side === 'long' ? 'Buy' : 'Sell' }}</span>
          <span class="button-amount">{{ sizeInput || '0.00' }} {{ baseCurrency }}</span>
        </span>
        <span class="button-loading" v-else>
          <svg class="spinner" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-linecap="round"/>
          </svg>
          <span>Processing...</span>
        </span>
      </button>
    </form>

    <!-- Available Balance -->
    <div class="balance-footer reveal" :class="{ visible: isVisible }" :style="{ transitionDelay: '0.45s' }">
      <div class="balance-row">
        <span class="balance-label">Available</span>
        <span class="balance-value">{{ displayAvailableBalance }} USDC</span>
      </div>
      <div class="balance-row">
        <span class="balance-label">Equity</span>
        <span class="balance-value">{{ displayEquity }} USDC</span>
      </div>
    </div>

    <!-- Order Confirmation Modal -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showConfirmation" class="modal-overlay" @click.self="showConfirmation = false">
          <div class="confirmation-modal">
            <div class="modal-header">
              <h3>Confirm Order</h3>
              <button class="modal-close" @click="showConfirmation = false">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
            <div class="modal-body">
              <div class="order-preview" :class="side">
                <div class="preview-header">
                  <span class="preview-side">{{ side === 'long' ? 'Long' : 'Short' }}</span>
                  <span class="preview-pair">{{ selectedPair }}</span>
                </div>
                <div class="preview-details">
                  <div class="preview-row">
                    <span>Size</span>
                    <span>{{ sizeInput }} {{ baseCurrency }}</span>
                  </div>
                  <div class="preview-row">
                    <span>Leverage</span>
                    <span>{{ leverage }}x</span>
                  </div>
                  <div class="preview-row">
                    <span>Entry Price</span>
                    <span>{{ displayEntryPrice }}</span>
                  </div>
                  <div class="preview-row" v-if="takeProfitInput">
                    <span>Take Profit</span>
                    <span class="positive">{{ takeProfitInput }}</span>
                  </div>
                  <div class="preview-row" v-if="stopLossInput">
                    <span>Stop Loss</span>
                    <span class="negative">{{ stopLossInput }}</span>
                  </div>
                </div>
              </div>
              
              <!-- Show validation errors in modal if any -->
              <div v-if="validationErrors.length > 0" class="modal-errors">
                <div v-for="error in validationErrors" :key="error.code" class="error-item">
                  {{ error.message }}
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button class="modal-btn secondary" @click="showConfirmation = false">Cancel</button>
              <button 
                class="modal-btn primary" 
                :class="side" 
                @click="confirmOrder"
                :disabled="validationErrors.length > 0"
              >
                Confirm {{ side === 'long' ? 'Buy' : 'Sell' }}
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import {
  toDecimal,
  calculateNotional,
  calculateMargin,
  calculateLiquidationPrice,
  calculateFees,
  calculatePnL,
  calculateMaxSize,
  formatPrice,
  formatCurrency,
  type Decimal,
} from '~/utils/financial'

// ===== TYPE DEFINITIONS =====

interface PriceData {
  price: number
  change24h: number
}

interface OrderType {
  value: 'market' | 'limit' | 'stop'
  label: string
}

interface Order {
  pair: string
  side: 'long' | 'short'
  type: 'market' | 'limit' | 'stop'
  size: string
  price: string | null
  leverage: number
  takeProfit: string | null
  stopLoss: string | null
  timestamp: number
}

// ===== PROPS & EMITS =====

const props = defineProps<{
  initialPair?: string
  initialBalance?: number
  priceData?: PriceData
}>()

const emit = defineEmits<{
  'order-submitted': [order: Order]
  'pair-changed': [pair: string]
}>()

// ===== COMPOSABLES =====

const { config, getFeeRate } = useTradingConfig()
const { validateOrder, canSubmitOrder } = useOrderValidation()
const notifications = useNotifications()

// ===== REACTIVE STATE =====

const isVisible = ref(false)
const isExpanded = ref(false)
const showPairSelector = ref(false)
const pairSearch = ref('')
const selectedPair = ref(props.initialPair ?? 'ETH-USDC')
const orderType = ref<'market' | 'limit' | 'stop'>('market')
const side = ref<'long' | 'short'>('long')
const sizeInput = ref('')
const sizeUnit = ref<'coin' | 'usd'>('coin')
const limitPriceInput = ref('')
const leverage = ref(5)
const showTPSL = ref(false)
const takeProfitInput = ref('')
const stopLossInput = ref('')
const isSubmitting = ref(false)
const showConfirmation = ref(false)

// Mock account state - in production, fetch from API
const availableBalance = ref(toDecimal(props.initialBalance ?? 10000))
const equity = ref(toDecimal((props.initialBalance ?? 10000) * 1.05))
const currentDailyPnL = ref(toDecimal(0))
const openPositions = ref(0)

// ===== STATIC DATA =====

const orderTypes: OrderType[] = [
  { value: 'market', label: 'Market' },
  { value: 'limit', label: 'Limit' },
  { value: 'stop', label: 'Stop' }
]

const tradingPairs = [
  'BTC-USDC', 'ETH-USDC', 'SOL-USDC', 'ARB-USDC', 'OP-USDC',
  'AVAX-USDC', 'MATIC-USDC', 'DOGE-USDC', 'LINK-USDC', 'UNI-USDC'
]

// ===== COMPUTED (with Decimal precision) =====

const baseCurrency = computed(() => selectedPair.value.split('-')[0])

const currentPrice = computed((): Decimal => 
  toDecimal(props.priceData?.price ?? 0)
)

const priceChange = computed(() => props.priceData?.change24h ?? 0)

const priceChangeClass = computed(() => ({
  positive: priceChange.value > 0,
  negative: priceChange.value < 0
}))

const priceChangeFormatted = computed(() => {
  const sign = priceChange.value >= 0 ? '+' : ''
  return `${sign}${priceChange.value.toFixed(2)}%`
})

const filteredPairs = computed(() => {
  if (!pairSearch.value) return tradingPairs
  return tradingPairs.filter(p => 
    p.toLowerCase().includes(pairSearch.value.toLowerCase())
  )
})

// Parse size as Decimal
const sizeDecimal = computed((): Decimal => {
  const input = sizeInput.value.trim()
  if (!input) return toDecimal(0)
  return toDecimal(input)
})

// Notional value with Decimal precision
const notionalValue = computed((): Decimal => {
  if (sizeDecimal.value.isZero()) return toDecimal(0)
  
  if (sizeUnit.value === 'usd') {
    return sizeDecimal.value
  }
  return calculateNotional(sizeDecimal.value, currentPrice.value)
})

// Entry price with Decimal precision
const entryPrice = computed((): Decimal => {
  if (orderType.value === 'limit' && limitPriceInput.value) {
    return toDecimal(limitPriceInput.value)
  }
  return currentPrice.value
})

// Liquidation price with Decimal precision
const liquidationPrice = computed((): Decimal => {
  if (sizeDecimal.value.isZero() || entryPrice.value.isZero()) {
    return toDecimal(0)
  }
  return calculateLiquidationPrice(
    entryPrice.value,
    leverage.value,
    side.value === 'long'
  )
})

// Margin required with Decimal precision
const marginRequired = computed((): Decimal => {
  return calculateMargin(notionalValue.value, leverage.value)
})

// Estimated fees with configurable rates
const estimatedFees = computed((): Decimal => {
  const feeRate = getFeeRate(orderType.value)
  return calculateFees(notionalValue.value, feeRate)
})

// Take profit P&L
const takeProfitPnL = computed((): Decimal | null => {
  if (!takeProfitInput.value || sizeDecimal.value.isZero() || entryPrice.value.isZero()) {
    return null
  }
  return calculatePnL(
    entryPrice.value,
    toDecimal(takeProfitInput.value),
    sizeDecimal.value,
    side.value === 'long'
  )
})

// Stop loss P&L
const stopLossPnL = computed((): Decimal | null => {
  if (!stopLossInput.value || sizeDecimal.value.isZero() || entryPrice.value.isZero()) {
    return null
  }
  return calculatePnL(
    entryPrice.value,
    toDecimal(stopLossInput.value),
    sizeDecimal.value,
    side.value === 'long'
  )
})

// Max leverage from config
const maxLeverage = computed(() => config.value.positionLimits.maxLeverage)

const leverageMarks = computed(() => {
  const max = maxLeverage.value
  if (max <= 10) return [1, 5, 10]
  if (max <= 25) return [1, 10, 25]
  return [1, 10, 25, max]
})

// ===== VALIDATION =====

// Build order params for validation
const orderParams = computed(() => ({
  pair: selectedPair.value,
  side: side.value,
  orderType: orderType.value,
  size: sizeInput.value,
  price: orderType.value === 'limit' ? limitPriceInput.value : entryPrice.value.toString(),
  leverage: leverage.value,
  stopLoss: stopLossInput.value || undefined,
  takeProfit: takeProfitInput.value || undefined,
}))

const accountState = computed(() => ({
  availableBalance: availableBalance.value.toString(),
  equity: equity.value.toString(),
  currentDailyPnL: currentDailyPnL.value.toString(),
  openPositions: openPositions.value,
}))

const marketState = computed(() => ({
  currentPrice: currentPrice.value.toString(),
}))

// Run validation
const validationResult = computed(() => {
  return validateOrder(orderParams.value, accountState.value, marketState.value)
})

const validationErrors = computed(() => validationResult.value.errors)
const validationWarnings = computed(() => validationResult.value.warnings)

const hasFieldError = (field: string): boolean => {
  return validationErrors.value.some(e => e.field === field)
}

// Can submit check
const canSubmit = computed(() => {
  // Basic checks
  if (sizeDecimal.value.isZero()) return false
  if (orderType.value === 'limit' && !limitPriceInput.value) return false
  if (marginRequired.value.greaterThan(availableBalance.value)) return false
  
  // No critical errors (warnings are OK)
  return validationErrors.value.length === 0
})

// ===== DISPLAY FORMATTERS =====

const displayPrice = computed(() => formatPrice(currentPrice.value))
const displayNotional = computed(() => formatCurrency(notionalValue.value))
const displayEntryPrice = computed(() => formatPrice(entryPrice.value))
const displayLiquidationPrice = computed(() => formatPrice(liquidationPrice.value))
const displayMarginRequired = computed(() => formatCurrency(marginRequired.value))
const displayEstimatedFees = computed(() => formatCurrency(estimatedFees.value))
const displayAvailableBalance = computed(() => formatCurrency(availableBalance.value))
const displayEquity = computed(() => formatCurrency(equity.value))

const displayTakeProfitPnL = computed(() => {
  if (!takeProfitPnL.value) return null
  return formatCurrency(takeProfitPnL.value)
})

const displayStopLossPnL = computed(() => {
  if (!stopLossPnL.value) return null
  return formatCurrency(stopLossPnL.value)
})

// ===== METHODS =====

const selectPair = (pair: string): void => {
  selectedPair.value = pair
  showPairSelector.value = false
  emit('pair-changed', pair)
}

const setQuickSize = (percentage: number): void => {
  if (currentPrice.value.isZero()) return
  
  const maxSize = calculateMaxSize(availableBalance.value, leverage.value, currentPrice.value)
  const targetSize = maxSize.times(percentage).dividedBy(100)
  sizeInput.value = targetSize.toFixed(4)
}

const setMarketPrice = (): void => {
  limitPriceInput.value = currentPrice.value.toFixed(2)
}

const submitOrder = (): void => {
  // Re-validate before showing confirmation
  const result = validateOrder(orderParams.value, accountState.value, marketState.value)
  
  if (result.errors.length > 0) {
    // Show first error as notification
    notifications.validationError(result.errors[0].message)
    return
  }
  
  showConfirmation.value = true
}

const confirmOrder = async (): Promise<void> => {
  // Final validation
  const result = validateOrder(orderParams.value, accountState.value, marketState.value)
  if (result.errors.length > 0) {
    notifications.validationError(result.errors[0].message)
    showConfirmation.value = false
    return
  }
  
  isSubmitting.value = true
  showConfirmation.value = false

  try {
    // Simulate API call - replace with actual API in production
    await new Promise(resolve => setTimeout(resolve, 1500))

    const order: Order = {
      pair: selectedPair.value,
      side: side.value,
      type: orderType.value,
      size: sizeInput.value,
      price: orderType.value === 'limit' ? limitPriceInput.value : null,
      leverage: leverage.value,
      takeProfit: takeProfitInput.value || null,
      stopLoss: stopLossInput.value || null,
      timestamp: Date.now()
    }

    emit('order-submitted', order)
    
    // Show success notification
    notifications.orderSubmitted(
      selectedPair.value,
      side.value,
      `${sizeInput.value} ${baseCurrency.value}`
    )

    // Reset form
    sizeInput.value = ''
    limitPriceInput.value = ''
    takeProfitInput.value = ''
    stopLossInput.value = ''

  } catch (error: unknown) {
    // Show error notification to user
    const errorMessage = error instanceof Error ? error.message : 'Order submission failed. Please try again.'
    notifications.orderFailed(errorMessage)
  } finally {
    isSubmitting.value = false
  }
}

// ===== LIFECYCLE =====

onMounted(() => {
  // Trigger reveal animation
  setTimeout(() => {
    isVisible.value = true
  }, 100)
})

// ===== EXPOSE =====

defineExpose({
  selectedPair,
  side,
  orderType
})
</script>

<style scoped>
/* Design System Variables */
.trade-panel {
  --color-surface: hsl(210, 25%, 98%);
  --color-surface-elevated: hsl(0, 0%, 100%);
  --color-surface-deep: hsl(210, 20%, 96%);
  --color-accent: hsl(190, 85%, 45%);
  --color-accent-soft: hsl(190, 75%, 55%);
  --color-accent-glow: hsl(190, 85%, 45%, 0.12);
  --color-text-primary: hsl(210, 25%, 8%);
  --color-text-secondary: hsl(210, 15%, 45%);
  --color-text-tertiary: hsl(210, 12%, 65%);
  --color-border: hsl(210, 20%, 90%);
  --color-border-focus: hsl(190, 70%, 60%);
  
  --color-long: hsl(142, 76%, 36%);
  --color-long-soft: hsl(142, 65%, 94%);
  --color-long-glow: hsl(142, 76%, 36%, 0.15);
  
  --color-short: hsl(0, 84%, 60%);
  --color-short-soft: hsl(0, 70%, 95%);
  --color-short-glow: hsl(0, 84%, 60%, 0.15);
  
  --color-warning: hsl(38, 92%, 50%);
  --color-warning-soft: hsl(38, 90%, 95%);
  
  --color-error: hsl(0, 84%, 60%);
  --color-error-soft: hsl(0, 70%, 95%);

  --shadow-sm: 0 1px 2px hsl(210 20% 20% / 0.04), 0 1px 3px hsl(210 20% 20% / 0.06);
  --shadow-md: 0 4px 6px hsl(210 20% 20% / 0.04), 0 8px 20px hsl(210 20% 20% / 0.06);
  --shadow-lg: 0 8px 16px hsl(210 20% 20% / 0.04), 0 20px 50px hsl(210 20% 20% / 0.08);

  --font-display: 'Instrument Serif', 'Playfair Display', serif;
  --font-body: 'Inter', 'General Sans', sans-serif;
  --font-mono: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;

  position: relative;
  background: var(--color-surface-elevated);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-lg), inset 0 1px 0 hsl(0 0% 100% / 0.8);
  padding: 1.5rem;
  font-family: var(--font-body);
  overflow: hidden;
}

/* Dark Mode */
:root[data-theme="dark"] .trade-panel,
.dark .trade-panel {
  --color-surface: hsl(220, 20%, 8%);
  --color-surface-elevated: hsl(220, 18%, 12%);
  --color-surface-deep: hsl(220, 22%, 6%);
  --color-text-primary: hsl(220, 15%, 92%);
  --color-text-secondary: hsl(220, 10%, 65%);
  --color-text-tertiary: hsl(220, 8%, 50%);
  --color-border: hsl(220, 15%, 22%);
  --color-border-focus: hsl(190, 70%, 50%);
  
  --color-long-soft: hsl(142, 50%, 15%);
  --color-short-soft: hsl(0, 50%, 15%);
  --color-warning-soft: hsl(38, 50%, 15%);
  --color-error-soft: hsl(0, 50%, 15%);
}

/* Noise Overlay */
.noise-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
  opacity: 0.03;
}

/* Reveal Animation */
.reveal {
  opacity: 0;
  transform: translateY(12px);
  transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1), 
              transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.reveal.visible {
  opacity: 1;
  transform: translateY(0);
}

/* Header */
.panel-header {
  position: relative;
  z-index: 10;
  margin-bottom: 1.25rem;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-title-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.panel-title {
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 400;
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: -0.02em;
}

.pair-badge {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.65rem;
  background: var(--color-surface-deep);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.pair-badge:hover {
  background: var(--color-surface);
  border-color: var(--color-border);
}

.pair-symbol {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--color-text-primary);
}

.chevron-icon {
  width: 16px;
  height: 16px;
  color: var(--color-text-tertiary);
  transition: transform 0.2s ease;
}

.chevron-icon.rotated {
  transform: rotate(180deg);
}

/* Header Stats */
.stat-pill {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  padding: 0.5rem 0.75rem;
  background: var(--color-surface-deep);
  border-radius: var(--radius-md);
}

.stat-value {
  font-family: var(--font-mono);
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.stat-change {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 500;
}

.stat-pill.positive .stat-change { color: var(--color-long); }
.stat-pill.negative .stat-change { color: var(--color-short); }

/* Pair Selector Dropdown */
.pair-selector {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 0.5rem;
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  z-index: 100;
}

.pair-search-input {
  width: 100%;
  padding: 0.875rem 1rem;
  border: none;
  border-bottom: 1px solid var(--color-border);
  background: transparent;
  font-family: var(--font-body);
  font-size: 0.9rem;
  color: var(--color-text-primary);
  outline: none;
}

.pair-search-input::placeholder {
  color: var(--color-text-tertiary);
}

.pair-list {
  max-height: 200px;
  overflow-y: auto;
  padding: 0.5rem;
}

.pair-option {
  width: 100%;
  padding: 0.65rem 0.875rem;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  text-align: left;
  cursor: pointer;
  transition: all 0.15s ease;
}

.pair-option:hover {
  background: var(--color-surface-deep);
  color: var(--color-text-primary);
}

.pair-option.active {
  background: var(--color-accent-glow);
  color: var(--color-accent);
}

/* Order Type Tabs */
.order-type-tabs {
  display: flex;
  gap: 0.35rem;
  padding: 0.35rem;
  background: var(--color-surface-deep);
  border-radius: var(--radius-md);
  margin-bottom: 1rem;
}

.order-type-tab {
  flex: 1;
  padding: 0.625rem 1rem;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.order-type-tab:hover {
  color: var(--color-text-primary);
}

.order-type-tab.active {
  background: var(--color-surface-elevated);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-sm);
}

/* Side Toggle */
.side-toggle {
  display: flex;
  position: relative;
  padding: 0.25rem;
  background: var(--color-surface-deep);
  border-radius: var(--radius-md);
  margin-bottom: 1.25rem;
}

.side-button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.875rem;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  z-index: 2;
}

.side-button.long {
  color: var(--color-text-secondary);
}

.side-button.long.active {
  color: var(--color-long);
}

.side-button.short {
  color: var(--color-text-secondary);
}

.side-button.short.active {
  color: var(--color-short);
}

.side-icon {
  width: 18px;
  height: 18px;
}

.side-indicator {
  position: absolute;
  top: 0.25rem;
  left: 0.25rem;
  width: calc(50% - 0.25rem);
  height: calc(100% - 0.5rem);
  background: var(--color-surface-elevated);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease;
  z-index: 1;
}

.side-indicator.long {
  transform: translateX(0);
  box-shadow: var(--shadow-md), 0 0 20px var(--color-long-glow);
}

.side-indicator.short {
  transform: translateX(100%);
  box-shadow: var(--shadow-md), 0 0 20px var(--color-short-glow);
}

/* Form Inputs */
.order-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.input-group.compact {
  gap: 0.35rem;
}

.input-label {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.input-label.small {
  font-size: 0.7rem;
}

.input-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.leverage-value {
  font-family: var(--font-mono);
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-accent);
}

.input-wrapper {
  display: flex;
  align-items: stretch;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all 0.2s ease;
}

.input-wrapper:focus-within {
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 3px var(--color-accent-glow);
}

.input-wrapper.error {
  border-color: var(--color-error);
  box-shadow: 0 0 0 3px var(--color-error-soft);
}

.form-input {
  flex: 1;
  padding: 0.875rem 1rem;
  background: transparent;
  border: none;
  font-family: var(--font-mono);
  font-size: 1rem;
  color: var(--color-text-primary);
  outline: none;
}

.form-input::placeholder {
  color: var(--color-text-tertiary);
}

.input-suffix {
  display: flex;
  align-items: center;
  padding: 0 1rem;
  background: var(--color-surface-deep);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.input-suffix.small {
  padding: 0 0.75rem;
  font-size: 0.75rem;
}

.input-unit-selector {
  display: flex;
  padding: 0.375rem;
  background: var(--color-surface-deep);
}

.unit-button {
  padding: 0.375rem 0.75rem;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.unit-button:hover {
  color: var(--color-text-secondary);
}

.unit-button.active {
  background: var(--color-surface-elevated);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-sm);
}

/* Input Helpers */
.input-helper {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.helper-text {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
}

.quick-size-buttons {
  display: flex;
  gap: 0.25rem;
}

.quick-size-buttons button {
  padding: 0.25rem 0.5rem;
  background: var(--color-surface-deep);
  border: none;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-size-buttons button:hover {
  background: var(--color-surface);
  color: var(--color-accent);
}

.price-helper-btn {
  padding: 0.25rem 0.5rem;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--color-accent);
  cursor: pointer;
  transition: all 0.15s ease;
}

.price-helper-btn:hover {
  background: var(--color-accent-glow);
}

/* Leverage Slider */
.leverage-slider-container {
  padding: 0.5rem 0;
}

.leverage-slider {
  width: 100%;
  height: 6px;
  background: var(--color-surface-deep);
  border-radius: 3px;
  outline: none;
  appearance: none;
  cursor: pointer;
  position: relative;
}

.leverage-slider::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: var(--progress, 10%);
  background: linear-gradient(90deg, var(--color-accent), var(--color-accent-soft));
  border-radius: 3px;
  pointer-events: none;
}

.leverage-slider::-webkit-slider-thumb {
  appearance: none;
  width: 20px;
  height: 20px;
  background: var(--color-surface-elevated);
  border: 3px solid var(--color-accent);
  border-radius: 50%;
  box-shadow: var(--shadow-md);
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  position: relative;
  z-index: 2;
}

.leverage-slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
  box-shadow: var(--shadow-lg), 0 0 15px var(--color-accent-glow);
}

.leverage-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
}

.leverage-mark {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: color 0.15s ease;
}

.leverage-mark:hover,
.leverage-mark.active {
  color: var(--color-accent);
}

/* Leverage Warning */
.leverage-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 0.875rem;
  background: var(--color-warning-soft);
  border-radius: var(--radius-sm);
  margin-top: 0.5rem;
}

.leverage-warning svg {
  width: 16px;
  height: 16px;
  color: var(--color-warning);
  flex-shrink: 0;
}

.leverage-warning span {
  font-size: 0.75rem;
  color: var(--color-warning);
  font-weight: 500;
}

/* Validation Warnings */
.validation-warnings {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--color-warning-soft);
  border-radius: var(--radius-md);
  border: 1px solid hsl(38 92% 50% / 0.2);
}

.warning-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--color-warning);
}

.warning-item svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  margin-top: 1px;
}

/* TP/SL Section */
.tpsl-section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.tpsl-toggle {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.875rem 1rem;
  background: var(--color-surface-deep);
  border: none;
  font-family: var(--font-body);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.tpsl-toggle:hover {
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.toggle-chevron {
  width: 18px;
  height: 18px;
  transition: transform 0.25s ease;
}

.toggle-chevron.rotated {
  transform: rotate(180deg);
}

.tpsl-inputs {
  padding: 1rem;
  background: var(--color-surface-elevated);
}

.tpsl-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.tpsl-input.tp:focus {
  border-color: var(--color-long);
}

.tpsl-input.sl:focus {
  border-color: var(--color-short);
}

.tpsl-pnl {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
}

.tpsl-pnl.positive { color: var(--color-long); }
.tpsl-pnl.negative { color: var(--color-short); }

/* Order Summary */
.order-summary {
  padding: 1rem;
  background: var(--color-surface-deep);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-label {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.summary-value {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-primary);
}

.summary-value.liquidation {
  color: var(--color-short);
}

.summary-value.muted {
  color: var(--color-text-tertiary);
}

/* Submit Button */
.submit-button {
  width: 100%;
  padding: 1.125rem;
  border: none;
  border-radius: var(--radius-lg);
  font-family: var(--font-body);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  overflow: hidden;
}

.submit-button.long {
  background: linear-gradient(135deg, var(--color-long) 0%, hsl(142, 70%, 42%) 100%);
  color: white;
  box-shadow: var(--shadow-md), 0 4px 20px var(--color-long-glow);
}

.submit-button.long:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg), 0 8px 30px var(--color-long-glow);
}

.submit-button.short {
  background: linear-gradient(135deg, var(--color-short) 0%, hsl(0, 75%, 55%) 100%);
  color: white;
  box-shadow: var(--shadow-md), 0 4px 20px var(--color-short-glow);
}

.submit-button.short:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg), 0 8px 30px var(--color-short-glow);
}

.submit-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
}

.submit-button:active:not(:disabled) {
  transform: translateY(0);
}

.button-content {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
}

.button-side {
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.button-amount {
  font-family: var(--font-mono);
}

.button-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.spinner {
  width: 20px;
  height: 20px;
  animation: spin 1s linear infinite;
}

.spinner circle {
  stroke-dasharray: 50;
  stroke-dashoffset: 40;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Balance Footer */
.balance-footer {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.balance-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.balance-label {
  font-size: 0.8rem;
  color: var(--color-text-tertiary);
}

.balance-value {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-secondary);
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: hsla(210, 25%, 8%, 0.7);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.confirmation-modal {
  width: 100%;
  max-width: 400px;
  background: var(--color-surface-elevated);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

.modal-header h3 {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 400;
  color: var(--color-text-primary);
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-deep);
  border: none;
  border-radius: 50%;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.modal-close:hover {
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.modal-close svg {
  width: 16px;
  height: 16px;
}

.modal-body {
  padding: 1.5rem;
}

.order-preview {
  padding: 1.25rem;
  border-radius: var(--radius-lg);
}

.order-preview.long {
  background: var(--color-long-soft);
  border: 1px solid hsla(142, 76%, 36%, 0.2);
}

.order-preview.short {
  background: var(--color-short-soft);
  border: 1px solid hsla(0, 84%, 60%, 0.2);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.preview-side {
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.order-preview.long .preview-side { color: var(--color-long); }
.order-preview.short .preview-side { color: var(--color-short); }

.preview-pair {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--color-text-primary);
}

.preview-details {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.preview-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
}

.preview-row span:first-child {
  color: var(--color-text-secondary);
}

.preview-row span:last-child {
  font-family: var(--font-mono);
  font-weight: 500;
  color: var(--color-text-primary);
}

.preview-row .positive { color: var(--color-long); }
.preview-row .negative { color: var(--color-short); }

.modal-errors {
  margin-top: 1rem;
  padding: 0.75rem;
  background: var(--color-error-soft);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-error);
}

.error-item {
  font-size: 0.85rem;
  color: var(--color-error);
}

.modal-footer {
  display: flex;
  gap: 0.75rem;
  padding: 1.25rem 1.5rem;
  border-top: 1px solid var(--color-border);
}

.modal-btn {
  flex: 1;
  padding: 0.875rem 1.25rem;
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.modal-btn.secondary {
  background: var(--color-surface-deep);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}

.modal-btn.secondary:hover {
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.modal-btn.primary {
  border: none;
  color: white;
}

.modal-btn.primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-btn.primary.long {
  background: var(--color-long);
}

.modal-btn.primary.long:hover:not(:disabled) {
  background: hsl(142, 76%, 32%);
}

.modal-btn.primary.short {
  background: var(--color-short);
}

.modal-btn.primary.short:hover:not(:disabled) {
  background: hsl(0, 84%, 55%);
}

/* Transitions */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.expand-enter-to,
.expand-leave-from {
  max-height: 200px;
}

.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .confirmation-modal,
.modal-leave-to .confirmation-modal {
  transform: scale(0.95) translateY(20px);
}

/* Responsive */
@media (max-width: 480px) {
  .trade-panel {
    padding: 1rem;
    border-radius: var(--radius-lg);
  }

  .panel-title {
    font-size: 1.5rem;
  }

  .tpsl-row {
    grid-template-columns: 1fr;
  }
}
</style>
