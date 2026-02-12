<template>
  <div class="position-manager">
    <!-- Subtle texture overlay -->
    <svg class="noise-overlay" aria-hidden="true">
      <filter id="grain-positions">
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" stitchTiles="stitch"/>
      </filter>
      <rect width="100%" height="100%" filter="url(#grain-positions)"/>
    </svg>

    <div class="container">
      <!-- Hero Section -->
      <header class="hero reveal" :class="{ visible: isVisible }">
        <h1>Position Manager</h1>
        <p>Advanced multi-TP exit management with breakeven trailing and momentum detection</p>
      </header>

      <!-- Dashboard Grid -->
      <div class="dashboard-grid">
        <!-- Main Positions Panel -->
        <div class="card reveal" :class="{ visible: isVisible, loading: loading }">
          <h2>Active Positions</h2>
          
          <div v-if="positions.length > 0" class="position-list">
            <div
              v-for="position in positions"
              :key="position.id"
              class="position-item"
            >
              <div class="position-header">
                <div class="position-info">
                  <span class="position-asset">{{ position.asset }}</span>
                  <span class="position-side" :class="position.side">
                    {{ position.side }}
                  </span>
                  <div class="status-indicator" :class="getStatusClass(position.state)">
                    <div class="status-dot"></div>
                    <span>{{ getStatusText(position.state) }}</span>
                  </div>
                </div>
                <button 
                  class="btn btn-danger"
                  @click="closePosition(position.id)"
                  :disabled="closingPositionId === position.id"
                >
                  {{ closingPositionId === position.id ? 'Closing...' : 'Close' }}
                </button>
              </div>
              
              <div class="position-metrics">
                <div class="metric">
                  <div class="metric-label">Entry Price</div>
                  <div class="metric-value">{{ formatPrice(position.entryPrice) }}</div>
                </div>
                <div class="metric">
                  <div class="metric-label">Current Price</div>
                  <div class="metric-value">{{ formatPrice(position.currentPrice) }}</div>
                </div>
                <div class="metric">
                  <div class="metric-label">Size</div>
                  <div class="metric-value">{{ position.size }}</div>
                </div>
                <div class="metric">
                  <div class="metric-label">Unrealized P&L</div>
                  <div class="metric-value" :class="getPnLClass(position.unrealizedPnL)">
                    {{ formatPnL(position.unrealizedPnL) }}
                  </div>
                </div>
                <div class="metric">
                  <div class="metric-label">R Multiple</div>
                  <div class="metric-value" :class="getPnLClass(position.rMultiple)">
                    {{ position.rMultiple.toFixed(1) }}R
                  </div>
                </div>
                <div class="metric">
                  <div class="metric-label">TP1 / TP2</div>
                  <div class="metric-value">
                    {{ formatPrice(position.tp1Price) }} / {{ formatPrice(position.tp2Price) }}
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div v-else class="empty-state">
            <h3>No Active Positions</h3>
            <p>Your managed positions will appear here when trades are opened</p>
            <button class="btn" @click="refreshPositions">Refresh</button>
          </div>
        </div>

        <!-- Summary Panel -->
        <div class="card reveal" :class="{ visible: isVisible }">
          <h2>Summary</h2>
          <div class="summary-stats">
            <div class="stat-card">
              <div class="stat-number" :class="getPnLClass(stats.totalPnL)">
                {{ formatPnL(stats.totalPnL) }}
              </div>
              <div class="stat-label">Total P&L</div>
            </div>
            
            <div class="stat-card">
              <div class="stat-number">{{ positions.length }}</div>
              <div class="stat-label">Active Positions</div>
            </div>
            
            <div class="stat-card">
              <div class="stat-number">{{ stats.avgRMultiple.toFixed(1) }}R</div>
              <div class="stat-label">Avg R Multiple</div>
            </div>
          </div>

          <!-- Connection status -->
          <div class="connection-status">
            <div class="status-indicator" :class="connectionStatusClass">
              <div class="status-dot"></div>
              <span>{{ connectionStatusText }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Performance Analytics -->
      <div class="card reveal" :class="{ visible: isVisible }">
        <h2>Performance Analytics</h2>
        
        <div class="win-rate-section">
          <div class="win-rate-header">
            <span class="metric-label">Win Rate</span>
            <span class="metric-value">{{ analytics.winRate }}%</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: `${analytics.winRate}%` }"></div>
          </div>
        </div>

        <table class="data-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Value</th>
              <th>Trend</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>TP1 Hit Rate</td>
              <td>{{ analytics.tp1Rate }}</td>
              <td><span class="trend up">↗</span></td>
            </tr>
            <tr>
              <td>TP2 Hit Rate</td>
              <td>{{ analytics.tp2Rate }}</td>
              <td><span class="trend up">↗</span></td>
            </tr>
            <tr>
              <td>Breakeven Stops</td>
              <td>{{ analytics.breakevenCount }}</td>
              <td><span class="trend neutral">→</span></td>
            </tr>
            <tr>
              <td>Momentum Exits</td>
              <td>{{ analytics.momentumExits }}</td>
              <td><span class="trend up">↗</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  toDecimal,
  formatPrice as formatPriceUtil,
  formatCurrency,
  type Decimal,
} from '~/utils/financial'

// ===== TYPE DEFINITIONS =====

interface Position {
  id: string
  asset: string
  side: 'long' | 'short'
  state: 'active' | 'partial_tp1' | 'partial_tp2' | 'closed'
  entryPrice: number
  currentPrice: number
  size: number
  unrealizedPnL: number
  rMultiple: number
  tp1Price: number
  tp2Price: number
  currentStop: number
  tp1Filled: boolean
  tp2Filled: boolean
  breakevenActivated: boolean
}

interface PositionStats {
  totalPnL: number
  avgRMultiple: number
}

interface Analytics {
  winRate: number
  tp1Rate: string
  tp2Rate: string
  breakevenCount: number
  momentumExits: number
}

// ===== PROPS & EMITS =====

const emit = defineEmits<{
  'position-closed': [positionId: string]
}>()

// ===== COMPOSABLES =====

const notifications = useNotifications()
const { status: wsStatus } = useWebSocket()

// ===== STATE =====

const isVisible = ref(false)
const loading = ref(false)
const positions = ref<Position[]>([])
const closingPositionId = ref<string | null>(null)
const updateInterval = ref<ReturnType<typeof setInterval> | null>(null)

// ===== COMPUTED =====

const stats = computed((): PositionStats => {
  const totalPnL = positions.value.reduce((sum, p) => sum + p.unrealizedPnL, 0)
  const avgRMultiple = positions.value.length > 0
    ? positions.value.reduce((sum, p) => sum + p.rMultiple, 0) / positions.value.length
    : 0
  
  return { totalPnL, avgRMultiple }
})

const analytics = computed((): Analytics => {
  const total = positions.value.length
  const tp1Hits = positions.value.filter(p => p.tp1Filled).length
  const tp2Hits = positions.value.filter(p => p.tp2Filled).length
  const breakevenCount = positions.value.filter(p => p.breakevenActivated).length
  
  return {
    winRate: 75, // Mock - would come from API
    tp1Rate: `${tp1Hits}/${total}`,
    tp2Rate: `${tp2Hits}/${total}`,
    breakevenCount,
    momentumExits: 3, // Mock
  }
})

const connectionStatusClass = computed(() => {
  switch (wsStatus.value) {
    case 'connected': return 'status-active'
    case 'connecting': return 'status-partial'
    case 'error': return 'status-error'
    default: return 'status-closed'
  }
})

const connectionStatusText = computed(() => {
  switch (wsStatus.value) {
    case 'connected': return 'Connected'
    case 'connecting': return 'Connecting...'
    case 'error': return 'Error'
    default: return 'Disconnected'
  }
})

// ===== METHODS =====

const formatPrice = (value: number): string => {
  return `$${formatPriceUtil(value)}`
}

const formatPnL = (value: number): string => {
  const prefix = value >= 0 ? '+$' : '-$'
  return `${prefix}${formatCurrency(Math.abs(value))}`
}

const getPnLClass = (value: number): string => {
  if (value > 0) return 'positive'
  if (value < 0) return 'negative'
  return ''
}

const getStatusClass = (state: string): string => {
  switch (state) {
    case 'active': return 'status-active'
    case 'partial_tp1':
    case 'partial_tp2': return 'status-partial'
    case 'closed': return 'status-closed'
    default: return 'status-active'
  }
}

const getStatusText = (state: string): string => {
  switch (state) {
    case 'active': return 'Active'
    case 'partial_tp1': return 'TP1 Hit'
    case 'partial_tp2': return 'TP2 Hit'
    case 'closed': return 'Closed'
    default: return 'Active'
  }
}

const loadPositions = async (): Promise<void> => {
  loading.value = true
  
  try {
    // In production, fetch from API
    // const response = await $fetch('/api/positions')
    // positions.value = response.positions
    
    // Mock data for development
    positions.value = [
      {
        id: 'pos_1',
        asset: 'ETH-USD',
        side: 'long',
        state: 'active',
        entryPrice: 3450.00,
        currentPrice: 3520.00,
        size: 0.5,
        unrealizedPnL: 35.00,
        rMultiple: 0.4,
        tp1Price: 3520.00,
        tp2Price: 3590.00,
        currentStop: 3380.00,
        tp1Filled: false,
        tp2Filled: false,
        breakevenActivated: false,
      },
      {
        id: 'pos_2',
        asset: 'BTC-USD',
        side: 'short',
        state: 'partial_tp1',
        entryPrice: 65000,
        currentPrice: 64200,
        size: 0.1,
        unrealizedPnL: 80.00,
        rMultiple: 1.2,
        tp1Price: 64000,
        tp2Price: 63000,
        currentStop: 65000,
        tp1Filled: true,
        tp2Filled: false,
        breakevenActivated: true,
      }
    ]
  } catch (err) {
    notifications.error({
      title: 'Failed to load positions',
      message: err instanceof Error ? err.message : 'Unknown error',
    })
  } finally {
    loading.value = false
  }
}

const refreshPositions = async (): Promise<void> => {
  await loadPositions()
  notifications.info('Positions refreshed')
}

const closePosition = async (positionId: string): Promise<void> => {
  const confirmed = window.confirm('Are you sure you want to close this position?')
  if (!confirmed) return
  
  closingPositionId.value = positionId
  
  try {
    // In production, call API to close position
    // await $fetch(`/api/positions/${positionId}/close`, { method: 'POST' })
    
    // Mock: remove from list
    await new Promise(resolve => setTimeout(resolve, 1000))
    positions.value = positions.value.filter(p => p.id !== positionId)
    
    emit('position-closed', positionId)
    notifications.positionClosed(
      positions.value.find(p => p.id === positionId)?.asset || 'Position',
      '+$35.00'
    )
  } catch (err) {
    notifications.error({
      title: 'Failed to close position',
      message: err instanceof Error ? err.message : 'Unknown error',
    })
  } finally {
    closingPositionId.value = null
  }
}

const simulatePriceUpdates = (): void => {
  positions.value.forEach(position => {
    // Simulate price movement
    const change = (Math.random() - 0.5) * 20
    position.currentPrice += change
    position.unrealizedPnL += change * position.size * (position.side === 'long' ? 1 : -1)
    position.rMultiple = position.unrealizedPnL / 87.50 // Assuming $87.50 risk
  })
}

// ===== LIFECYCLE =====

onMounted(async () => {
  // Trigger reveal animation
  setTimeout(() => {
    isVisible.value = true
  }, 100)
  
  await loadPositions()
  
  // Simulate real-time updates (replace with WebSocket in production)
  updateInterval.value = setInterval(simulatePriceUpdates, 5000)
})

onUnmounted(() => {
  if (updateInterval.value) {
    clearInterval(updateInterval.value)
  }
})
</script>

<style scoped>
/* Design System Variables */
.position-manager {
  --color-surface: hsl(210, 25%, 98%);
  --color-surface-elevated: hsl(210, 30%, 99%);
  --color-surface-deep: hsl(210, 20%, 96%);
  --color-accent: hsl(190, 85%, 45%);
  --color-accent-soft: hsl(190, 75%, 55%);
  --color-accent-glow: hsl(190, 85%, 45%, 0.12);
  --color-text-primary: hsl(210, 25%, 8%);
  --color-text-secondary: hsl(210, 15%, 45%);
  --color-text-tertiary: hsl(210, 12%, 65%);
  
  --color-success: hsl(142, 76%, 36%);
  --color-success-glow: hsl(142, 76%, 36%, 0.1);
  --color-warning: hsl(38, 92%, 50%);
  --color-danger: hsl(0, 84%, 60%);
  --color-neutral: hsl(210, 16%, 82%);

  --shadow-sm: 0 1px 2px hsl(210 20% 20% / 0.04), 0 1px 3px hsl(210 20% 20% / 0.06);
  --shadow-md: 0 4px 6px hsl(210 20% 20% / 0.04), 0 8px 20px hsl(210 20% 20% / 0.06);
  --shadow-lg: 0 8px 16px hsl(210 20% 20% / 0.04), 0 20px 50px hsl(210 20% 20% / 0.08);
  --shadow-glow: 0 0 30px var(--color-accent-glow);

  --font-display: 'Instrument Serif', serif;
  --font-body: 'Inter', sans-serif;

  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;

  position: relative;
  min-height: 100vh;
  background: radial-gradient(ellipse at 20% 30%, hsl(190 80% 65% / 0.08) 0%, transparent 60%),
              radial-gradient(ellipse at 80% 70%, hsl(210 60% 70% / 0.06) 0%, transparent 60%),
              var(--color-surface);
  font-family: var(--font-body);
  color: var(--color-text-primary);
}

/* Dark Mode */
:root[data-theme="dark"] .position-manager,
.dark .position-manager {
  --color-surface: hsl(220, 20%, 8%);
  --color-surface-elevated: hsl(220, 18%, 12%);
  --color-surface-deep: hsl(220, 22%, 6%);
  --color-text-primary: hsl(220, 15%, 92%);
  --color-text-secondary: hsl(220, 10%, 65%);
  --color-text-tertiary: hsl(220, 8%, 50%);
}

/* Noise Overlay */
.noise-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
  opacity: 0.025;
}

/* Container */
.container {
  position: relative;
  z-index: 2;
  max-width: 1400px;
  margin: 0 auto;
  padding: 4rem 2rem;
}

/* Reveal Animation */
.reveal {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.7s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);
}

.reveal.visible {
  opacity: 1;
  transform: translateY(0);
}

/* Hero */
.hero {
  text-align: left;
  margin-bottom: 4rem;
}

.hero h1 {
  font-family: var(--font-display);
  font-size: clamp(2.5rem, 6vw, 4.5rem);
  font-weight: 400;
  line-height: 1.1;
  margin: 0 0 1rem 0;
  letter-spacing: -0.02em;
}

.hero p {
  font-size: 1.25rem;
  color: var(--color-text-secondary);
  max-width: 600px;
  margin: 0;
}

/* Dashboard Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 2rem;
  margin-bottom: 2rem;
}

@media (max-width: 768px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

/* Cards */
.card {
  background: var(--color-surface-elevated);
  border-radius: var(--radius-xl);
  padding: 2rem;
  border: 1px solid hsl(210 20% 88% / 0.6);
  box-shadow: var(--shadow-lg), inset 0 1px 0 hsl(0 0% 100% / 0.8);
  backdrop-filter: blur(10px);
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  overflow: hidden;
}

.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-accent-soft), transparent);
  opacity: 0;
  transition: opacity 0.4s ease;
}

.card:hover::before {
  opacity: 1;
}

.card.loading {
  opacity: 0.6;
  pointer-events: none;
}

.card h2 {
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 400;
  margin: 0 0 1.5rem 0;
  letter-spacing: -0.01em;
}

/* Position List */
.position-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.position-item {
  background: var(--color-surface-deep);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  border: 1px solid hsl(210 15% 90% / 0.8);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.position-item:hover {
  transform: translateX(4px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-accent);
}

.position-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.position-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.position-asset {
  font-weight: 600;
  font-size: 1.1rem;
}

.position-side {
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.position-side.long {
  background: var(--color-success-glow);
  color: var(--color-success);
}

.position-side.short {
  background: hsl(0, 84%, 60%, 0.1);
  color: var(--color-danger);
}

/* Metrics Grid */
.position-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
}

.metric-label {
  font-size: 0.8rem;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}

.metric-value {
  font-size: 1.1rem;
  font-weight: 600;
}

.metric-value.positive { color: var(--color-success); }
.metric-value.negative { color: var(--color-danger); }

/* Status Indicators */
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 25px;
  font-size: 0.9rem;
  font-weight: 500;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.status-active {
  background: var(--color-success-glow);
  color: var(--color-success);
}
.status-active .status-dot { background: var(--color-success); }

.status-partial {
  background: hsl(38, 92%, 50%, 0.1);
  color: var(--color-warning);
}
.status-partial .status-dot { background: var(--color-warning); }

.status-closed {
  background: hsl(210 16% 82% / 0.2);
  color: var(--color-text-secondary);
}
.status-closed .status-dot { background: var(--color-neutral); }

.status-error {
  background: hsl(0, 84%, 60%, 0.1);
  color: var(--color-danger);
}
.status-error .status-dot { background: var(--color-danger); }

/* Summary Stats */
.summary-stats {
  display: grid;
  gap: 1rem;
}

.stat-card {
  background: linear-gradient(135deg, var(--color-surface-elevated), var(--color-surface-deep));
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  text-align: center;
  border: 1px solid hsl(210 15% 90% / 0.6);
  transition: transform 0.3s ease;
}

.stat-card:hover {
  transform: scale(1.02);
}

.stat-number {
  font-family: var(--font-display);
  font-size: 2.5rem;
  font-weight: 400;
  line-height: 1;
  margin-bottom: 0.5rem;
}

.stat-number.positive { color: var(--color-success); }
.stat-number.negative { color: var(--color-danger); }

.stat-label {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Connection Status */
.connection-status {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid hsl(210 15% 90% / 0.5);
}

/* Buttons */
.btn {
  background: var(--color-accent);
  color: white;
  border: none;
  padding: 0.75rem 2rem;
  border-radius: 25px;
  font-weight: 500;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: var(--shadow-sm);
}

.btn:hover:not(:disabled) {
  background: var(--color-accent-soft);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger {
  background: var(--color-danger);
}

.btn-danger:hover:not(:disabled) {
  background: hsl(0, 84%, 55%);
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  color: var(--color-text-secondary);
}

.empty-state h3 {
  font-family: var(--font-display);
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
  color: var(--color-text-primary);
}

.empty-state p {
  margin-bottom: 1.5rem;
}

/* Win Rate Section */
.win-rate-section {
  margin-bottom: 1.5rem;
}

.win-rate-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

/* Progress Bar */
.progress-bar {
  width: 100%;
  height: 6px;
  background: var(--color-surface-deep);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-accent), var(--color-accent-soft));
  border-radius: 3px;
  transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 0 10px var(--color-accent-glow);
}

/* Data Table */
.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  text-align: left;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid hsl(210 15% 90% / 0.5);
}

.data-table th {
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.data-table tr:hover {
  background: var(--color-surface-deep);
}

.trend {
  font-size: 1.2rem;
}

.trend.up { color: var(--color-success); }
.trend.down { color: var(--color-danger); }
.trend.neutral { color: var(--color-neutral); }

/* Responsive */
@media (max-width: 768px) {
  .container {
    padding: 2rem 1rem;
  }
  
  .position-metrics {
    grid-template-columns: 1fr 1fr;
  }
  
  .hero h1 {
    font-size: clamp(2rem, 8vw, 3rem);
  }
}
</style>
