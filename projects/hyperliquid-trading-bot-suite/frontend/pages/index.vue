<script setup lang="ts">
import type { Timeframe } from '~/types/chart'
import type { TradeMarker, TradeOverlay } from '~/types/trade-markers'

/**
 * Main Dashboard Page
 * Integrates: Chart, Trade Markers, Replay Controls, Trade Panel, Strategy Manager
 */

// Page metadata
useHead({
  title: 'Trading Dashboard - Hyperliquid AI Bot',
  meta: [
    {
      name: 'description',
      content: 'AI-powered trading dashboard with pattern detection, strategy execution, and real-time market analysis.'
    }
  ]
})

// Composables
const { currentSymbol, currentTimeframe, loading, error, loadData, changeTimeframe, changeSymbol } = useChartData()

// State
const selectedView = ref<'live' | 'backtest' | 'replay'>('live')
const showStrategyManager = ref(false)
const showTradePanel = ref(true)
const showReplayControls = ref(false)
const sidebarCollapsed = ref(false)

// Trade markers state
const tradeMarkers = ref<TradeMarker[]>([])
const tradeOverlays = ref<TradeOverlay[]>([])
const selectedTradeId = ref<string | null>(null)

// Available symbols for trading
const symbols = ref([
  { value: 'ETH/USD', label: 'ETH/USD' },
  { value: 'BTC/USD', label: 'BTC/USD' },
  { value: 'SOL/USD', label: 'SOL/USD' },
  { value: 'AVAX/USD', label: 'AVAX/USD' },
])

// Performance stats (mock data - would come from API)
const performanceStats = computed(() => ({
  totalPnl: 2847.32,
  dailyPnl: 124.56,
  winRate: 0.73,
  totalTrades: 247,
  activeTrades: 3,
  activeStrategies: 2
}))

/**
 * Handle view change (live/backtest/replay)
 */
function handleViewChange(view: 'live' | 'backtest' | 'replay') {
  selectedView.value = view
  showReplayControls.value = view === 'replay'
}

/**
 * Handle timeframe change
 */
async function handleTimeframeChange(timeframe: Timeframe) {
  await changeTimeframe(timeframe)
}

/**
 * Handle symbol change
 */
async function handleSymbolChange(symbol: string) {
  await changeSymbol(symbol)
}

/**
 * Handle trade marker click
 */
function handleTradeMarkerClick(marker: TradeMarker) {
  selectedTradeId.value = marker.tradeId || marker.id
  console.log('Trade marker clicked:', marker)
}

/**
 * Handle trade overlay selection
 */
function handleTradeOverlaySelect(overlay: TradeOverlay) {
  selectedTradeId.value = overlay.tradeId
  console.log('Trade overlay selected:', overlay)
}

/**
 * Toggle strategy manager panel
 */
function toggleStrategyManager() {
  showStrategyManager.value = !showStrategyManager.value
}

/**
 * Toggle trade panel
 */
function toggleTradePanel() {
  showTradePanel.value = !showTradePanel.value
}

/**
 * Toggle sidebar collapse
 */
function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

/**
 * Handle trade submission from TradePanel
 */
async function handleTradeSubmit(tradeData: any) {
  try {
    console.log('Trade submitted:', tradeData)
    // In production, submit to API
    // await $fetch('/api/trades', { method: 'POST', body: tradeData })
  } catch (err) {
    console.error('Trade submission failed:', err)
  }
}

/**
 * Handle strategy activation
 */
async function handleStrategyActivate(strategyId: string) {
  try {
    console.log('Activating strategy:', strategyId)
    // await $fetch(`/api/strategies/${strategyId}/activate`, { method: 'POST' })
  } catch (err) {
    console.error('Strategy activation failed:', err)
  }
}

/**
 * Load initial data
 */
onMounted(async () => {
  try {
    await loadData(currentSymbol.value, currentTimeframe.value)
  } catch (err) {
    console.error('Failed to load initial data:', err)
  }
})
</script>

<template>
  <div class="dashboard-container">
    <!-- Top Navigation Bar -->
    <header class="dashboard-header">
      <div class="header-left">
        <button 
          class="sidebar-toggle"
          :class="{ collapsed: sidebarCollapsed }"
          @click="toggleSidebar"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        
        <h1 class="dashboard-title">Trading Dashboard</h1>
        
        <!-- View Switcher -->
        <div class="view-switcher">
          <button 
            class="view-btn"
            :class="{ active: selectedView === 'live' }"
            @click="handleViewChange('live')"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Live
          </button>
          <button 
            class="view-btn"
            :class="{ active: selectedView === 'backtest' }"
            @click="handleViewChange('backtest')"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Backtest
          </button>
          <button 
            class="view-btn"
            :class="{ active: selectedView === 'replay' }"
            @click="handleViewChange('replay')"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Replay
          </button>
        </div>
      </div>
      
      <div class="header-right">
        <!-- Performance Stats -->
        <div class="performance-stats">
          <div class="stat-item">
            <span class="stat-label">P&L Today</span>
            <span class="stat-value" :class="performanceStats.dailyPnl >= 0 ? 'positive' : 'negative'">
              {{ performanceStats.dailyPnl >= 0 ? '+' : '' }}${{ performanceStats.dailyPnl.toFixed(2) }}
            </span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Win Rate</span>
            <span class="stat-value">{{ (performanceStats.winRate * 100).toFixed(0) }}%</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Active</span>
            <span class="stat-value">{{ performanceStats.activeTrades }}</span>
          </div>
        </div>

        <!-- Action Buttons -->
        <button 
          class="action-btn"
          :class="{ active: showStrategyManager }"
          @click="toggleStrategyManager"
          title="Strategy Manager"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </button>
      </div>
    </header>

    <!-- Main Content Area -->
    <div class="dashboard-content">
      <!-- Sidebar (Strategy Manager) -->
      <aside 
        v-if="showStrategyManager"
        class="sidebar strategy-sidebar"
      >
        <StrategyManager
          @strategy-activate="handleStrategyActivate"
          @close="toggleStrategyManager"
        />
      </aside>

      <!-- Center: Chart Area -->
      <main class="chart-area">
        <!-- Chart Controls -->
        <div class="chart-controls">
          <div class="controls-left">
            <!-- Symbol Selector -->
            <select 
              :value="currentSymbol"
              class="symbol-select"
              @change="handleSymbolChange(($event.target as HTMLSelectElement).value)"
            >
              <option 
                v-for="symbol in symbols"
                :key="symbol.value"
                :value="symbol.value"
              >
                {{ symbol.label }}
              </option>
            </select>
            
            <!-- Timeframe Selector -->
            <select 
              :value="currentTimeframe"
              class="timeframe-select"
              @change="handleTimeframeChange(($event.target as HTMLSelectElement).value as Timeframe)"
            >
              <option value="1m">1m</option>
              <option value="5m">5m</option>
              <option value="15m">15m</option>
              <option value="30m">30m</option>
              <option value="1h">1h</option>
              <option value="4h">4h</option>
              <option value="1d">1d</option>
            </select>
          </div>

          <div class="controls-right">
            <button 
              v-if="!showTradePanel"
              class="control-btn"
              @click="toggleTradePanel"
              title="Show Trade Panel"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Error State -->
        <div v-if="error" class="error-banner">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{{ error }}</span>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="loading-overlay">
          <div class="loading-spinner" />
          <p>Loading chart data...</p>
        </div>

        <!-- Chart with Trade Markers -->
        <div class="chart-wrapper">
          <ChartWithTradeMarkers
            :symbol="currentSymbol"
            :timeframe="currentTimeframe"
            :trade-markers="tradeMarkers"
            :trade-overlays="tradeOverlays"
            :selected-trade-id="selectedTradeId"
            :height="showReplayControls ? 520 : 600"
            @marker-click="handleTradeMarkerClick"
            @overlay-select="handleTradeOverlaySelect"
          />
        </div>

        <!-- Replay Controls (when in replay mode) -->
        <div v-if="showReplayControls" class="replay-controls-wrapper">
          <ReplayControls
            :symbol="currentSymbol"
            :timeframe="currentTimeframe"
            @markers-update="tradeMarkers = $event"
            @overlays-update="tradeOverlays = $event"
          />
        </div>
      </main>

      <!-- Right Sidebar: Trade Panel -->
      <aside 
        v-if="showTradePanel"
        class="sidebar trade-sidebar"
      >
        <TradePanel
          :symbol="currentSymbol"
          :current-price="3247.82"
          @trade-submit="handleTradeSubmit"
          @close="toggleTradePanel"
        />
      </aside>
    </div>
  </div>
</template>

<style scoped>
/* Dashboard Layout */
.dashboard-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--color-bg-primary, #0f172a);
  color: var(--color-text-primary, #f1f5f9);
  overflow: hidden;
}

/* Header */
.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  background: var(--color-bg-secondary, #1e293b);
  border-bottom: 1px solid var(--color-border, #334155);
  flex-shrink: 0;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem;
  border-radius: 0.5rem;
  background: transparent;
  border: none;
  color: var(--color-text-secondary, #94a3b8);
  cursor: pointer;
  transition: all 0.2s;
}

.sidebar-toggle:hover {
  background: var(--color-bg-tertiary, #334155);
  color: var(--color-text-primary, #f1f5f9);
}

.dashboard-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary, #f1f5f9);
}

/* View Switcher */
.view-switcher {
  display: flex;
  gap: 0.25rem;
  background: var(--color-bg-tertiary, #334155);
  padding: 0.25rem;
  border-radius: 0.5rem;
}

.view-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  background: transparent;
  border: none;
  color: var(--color-text-secondary, #94a3b8);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.view-btn:hover {
  background: var(--color-bg-hover, #475569);
  color: var(--color-text-primary, #f1f5f9);
}

.view-btn.active {
  background: var(--color-accent, #8b5cf6);
  color: white;
}

/* Header Right */
.header-right {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.performance-stats {
  display: flex;
  gap: 1.5rem;
  padding-right: 1.5rem;
  border-right: 1px solid var(--color-border, #334155);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--color-text-muted, #64748b);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary, #f1f5f9);
}

.stat-value.positive {
  color: var(--color-success, #10b981);
}

.stat-value.negative {
  color: var(--color-error, #ef4444);
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem;
  border-radius: 0.5rem;
  background: transparent;
  border: 1px solid var(--color-border, #334155);
  color: var(--color-text-secondary, #94a3b8);
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: var(--color-bg-tertiary, #334155);
  color: var(--color-text-primary, #f1f5f9);
  border-color: var(--color-accent, #8b5cf6);
}

.action-btn.active {
  background: var(--color-accent, #8b5cf6);
  border-color: var(--color-accent, #8b5cf6);
  color: white;
}

/* Main Content */
.dashboard-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Sidebars */
.sidebar {
  width: 380px;
  background: var(--color-bg-secondary, #1e293b);
  border-right: 1px solid var(--color-border, #334155);
  overflow-y: auto;
  flex-shrink: 0;
}

.trade-sidebar {
  border-right: none;
  border-left: 1px solid var(--color-border, #334155);
}

/* Chart Area */
.chart-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-bg-primary, #0f172a);
}

.chart-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  background: var(--color-bg-secondary, #1e293b);
  border-bottom: 1px solid var(--color-border, #334155);
  flex-shrink: 0;
}

.controls-left {
  display: flex;
  gap: 1rem;
}

.controls-right {
  display: flex;
  gap: 0.5rem;
}

.symbol-select,
.timeframe-select {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  background: var(--color-bg-tertiary, #334155);
  border: 1px solid var(--color-border, #475569);
  color: var(--color-text-primary, #f1f5f9);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.symbol-select:hover,
.timeframe-select:hover {
  border-color: var(--color-accent, #8b5cf6);
}

.symbol-select:focus,
.timeframe-select:focus {
  outline: none;
  border-color: var(--color-accent, #8b5cf6);
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}

.control-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem;
  border-radius: 0.5rem;
  background: transparent;
  border: 1px solid var(--color-border, #334155);
  color: var(--color-text-secondary, #94a3b8);
  cursor: pointer;
  transition: all 0.2s;
}

.control-btn:hover {
  background: var(--color-bg-tertiary, #334155);
  color: var(--color-text-primary, #f1f5f9);
}

/* Error Banner */
.error-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  background: rgba(239, 68, 68, 0.1);
  border-bottom: 1px solid rgba(239, 68, 68, 0.3);
  color: var(--color-error, #ef4444);
  font-size: 0.875rem;
}

/* Loading Overlay */
.loading-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  color: var(--color-text-secondary, #94a3b8);
  z-index: 10;
}

.loading-spinner {
  width: 2.5rem;
  height: 2.5rem;
  border: 3px solid var(--color-border, #334155);
  border-top-color: var(--color-accent, #8b5cf6);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Chart Wrapper */
.chart-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}

/* Replay Controls Wrapper */
.replay-controls-wrapper {
  flex-shrink: 0;
  border-top: 1px solid var(--color-border, #334155);
}

/* Responsive Design */
@media (max-width: 1024px) {
  .sidebar {
    position: absolute;
    top: 60px;
    bottom: 0;
    z-index: 20;
  }

  .strategy-sidebar {
    left: 0;
  }

  .trade-sidebar {
    right: 0;
  }

  .performance-stats {
    display: none;
  }
}

@media (max-width: 768px) {
  .dashboard-title {
    display: none;
  }

  .view-switcher {
    gap: 0.125rem;
  }

  .view-btn {
    padding: 0.5rem 0.75rem;
    font-size: 0.8125rem;
  }

  .sidebar {
    width: 100%;
  }

  .chart-controls {
    padding: 0.75rem 1rem;
  }
}
</style>
