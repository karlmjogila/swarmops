<template>
  <div class="charts-page">
    <!-- Hero Section -->
    <section class="section-lg hero-section">
      <div class="container">
        <div class="text-center mb-12 reveal">
          <h1 class="hero-title mb-6">
            <span class="bg-gradient-primary bg-clip-text text-transparent">TradingView</span>
            Integration
          </h1>
          <p class="hero-subtitle text-xl text-secondary max-w-2xl mx-auto mb-8 leading-relaxed">
            Choose between lightweight charts for fast performance or full TradingView widgets for complete functionality.
          </p>
          <div class="flex items-center justify-center space-x-4">
            <button 
              @click="activeTab = 'lightweight'" 
              :class="['btn', activeTab === 'lightweight' ? 'btn-primary' : 'btn-secondary', 'stagger-1']"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
              Lightweight Charts
            </button>
            <button 
              @click="activeTab = 'widget'" 
              :class="['btn', activeTab === 'widget' ? 'btn-primary' : 'btn-secondary', 'stagger-2']"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
              </svg>
              TradingView Widget
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Chart Section -->
    <section class="section">
      <div class="container">
        <!-- Chart Controls -->
        <div class="card reveal stagger-3 mb-8">
          <div class="card-body">
            <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div class="flex items-center space-x-4">
                <div>
                  <label class="input-label">Symbol</label>
                  <select v-model="currentSymbol" class="form-select">
                    <option value="BINANCE:ETHUSDT">ETH/USDT</option>
                    <option value="BINANCE:BTCUSDT">BTC/USDT</option>
                    <option value="BINANCE:SOLUSDT">SOL/USDT</option>
                    <option value="BINANCE:AVAXUSDT">AVAX/USDT</option>
                    <option value="BINANCE:ADAUSDT">ADA/USDT</option>
                  </select>
                </div>
                <div>
                  <label class="input-label">Timeframe</label>
                  <select v-model="currentTimeframe" class="form-select">
                    <option value="1">1m</option>
                    <option value="5">5m</option>
                    <option value="15">15m</option>
                    <option value="60">1h</option>
                    <option value="240">4h</option>
                    <option value="1D">1D</option>
                  </select>
                </div>
              </div>
              <div class="flex items-center space-x-2">
                <span class="text-sm text-secondary">Theme:</span>
                <button 
                  @click="toggleTheme"
                  class="theme-toggle"
                  :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
                >
                  <svg v-if="isDark" class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.166a.75.75 0 00-1.06-1.06l-1.591 1.59a.75.75 0 101.06 1.061l1.591-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.834 18.894a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 10-1.061 1.06l1.59 1.591zM12 18a.75.75 0 01.75.75V21a.75.75 0 01-1.5 0v-2.25A.75.75 0 0112 18zM7.758 17.303a.75.75 0 00-1.061-1.06l-1.591 1.59a.75.75 0 001.06 1.061l1.591-1.59zM6 12a.75.75 0 01-.75.75H3a.75.75 0 010-1.5h2.25A.75.75 0 016 12zM6.697 7.757a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 00-1.061 1.06l1.59 1.591z" />
                  </svg>
                  <svg v-else class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path fill-rule="evenodd" d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69.75.75 0 01.981.98 10.503 10.503 0 01-9.694 6.46c-5.799 0-10.5-4.701-10.5-10.5 0-4.368 2.667-8.112 6.46-9.694a.75.75 0 01.818.162z" clip-rule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Chart Display -->
        <div class="chart-display reveal stagger-4">
          <!-- Lightweight Charts -->
          <div v-show="activeTab === 'lightweight'" class="chart-container">
            <div class="chart-header">
              <h3 class="chart-title">Lightweight Charts</h3>
              <div class="chart-description">
                Fast, lightweight charting using TradingView's open-source library
              </div>
            </div>
            <div class="chart-wrapper">
              <TradingViewChart 
                :symbol="lightweightSymbol"
                :timeframe="lightweightTimeframe"
                :height="600"
                :theme="isDark ? 'dark' : 'light'"
              />
            </div>
          </div>

          <!-- TradingView Widget -->
          <div v-show="activeTab === 'widget'" class="chart-container">
            <div class="chart-header">
              <h3 class="chart-title">TradingView Widget</h3>
              <div class="chart-description">
                Full-featured TradingView integration with all tools and indicators
              </div>
            </div>
            <div class="chart-wrapper">
              <TradingViewWidget 
                :symbol="currentSymbol"
                :interval="currentTimeframe"
                :height="600"
                :theme="isDark ? 'dark' : 'light'"
                :allow_symbol_change="true"
                :studies="['RSI', 'MACD']"
              />
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features Comparison -->
    <section class="section">
      <div class="container">
        <div class="reveal">
          <h2 class="section-title">Chart Comparison</h2>
        </div>
        
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <!-- Lightweight Charts -->
          <div class="card reveal stagger-1">
            <div class="comparison-card">
              <div class="comparison-header">
                <h3 class="comparison-title">Lightweight Charts</h3>
                <div class="comparison-badge badge-fast">Fast</div>
              </div>
              <div class="comparison-features">
                <div class="feature-item">
                  <svg class="feature-icon text-green-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <span>Ultra-fast rendering</span>
                </div>
                <div class="feature-item">
                  <svg class="feature-icon text-green-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <span>Low memory usage</span>
                </div>
                <div class="feature-item">
                  <svg class="feature-icon text-green-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <span>Custom overlays & indicators</span>
                </div>
                <div class="feature-item">
                  <svg class="feature-icon text-green-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <span>Perfect for real-time trading</span>
                </div>
                <div class="feature-item">
                  <svg class="feature-icon text-yellow-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <span>Limited built-in indicators</span>
                </div>
                <div class="feature-item">
                  <svg class="feature-icon text-yellow-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <span>No drawing tools</span>
                </div>
              </div>
            </div>
          </div>

          <!-- TradingView Widget -->
          <div class="card reveal stagger-2">
            <div class="comparison-card">
              <div class="comparison-header">
                <h3 class="comparison-title">TradingView Widget</h3>
                <div class="comparison-badge badge-full">Full-Featured</div>
              </div>
              <div class="comparison-features">
                <div class="feature-item">
                  <svg class="feature-icon text-green-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <span>100+ technical indicators</span>
                </div>
                <div class="feature-item">
                  <svg class="feature-icon text-green-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <span>Advanced drawing tools</span>
                </div>
                <div class="feature-item">
                  <svg class="feature-icon text-green-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <span>Multiple chart types</span>
                </div>
                <div class="feature-item">
                  <svg class="feature-icon text-green-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <span>Save & share layouts</span>
                </div>
                <div class="feature-item">
                  <svg class="feature-icon text-yellow-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <span>Requires internet connection</span>
                </div>
                <div class="feature-item">
                  <svg class="feature-icon text-yellow-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <span>Higher resource usage</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
// Page metadata
useHead({
  title: 'TradingView Charts - Hyperliquid Trading',
  meta: [
    { name: 'description', content: 'Compare lightweight charts vs full TradingView widget integration for optimal trading experience.' }
  ]
})

// Reactive state
const activeTab = ref('lightweight')
const currentSymbol = ref('BINANCE:ETHUSDT')
const currentTimeframe = ref('15')
const isDark = ref(false)

// Convert symbol format for lightweight charts
const lightweightSymbol = computed(() => {
  const symbol = currentSymbol.value.replace('BINANCE:', '').replace('USDT', '/USD')
  return symbol
})

// Convert timeframe format for lightweight charts
const lightweightTimeframe = computed(() => {
  const tf = currentTimeframe.value
  if (tf === '1') return '1m'
  if (tf === '5') return '5m'
  if (tf === '15') return '15m'
  if (tf === '60') return '1h'
  if (tf === '240') return '4h'
  if (tf === '1D') return '1d'
  return '15m'
})

// Theme toggle
const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
}

// Initialize theme
onMounted(() => {
  // Check system preference
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    isDark.value = true
    document.documentElement.classList.add('dark')
  }

  // Initialize reveal animations
  setTimeout(() => {
    const revealElements = document.querySelectorAll('.reveal')
    revealElements.forEach((el, index) => {
      setTimeout(() => {
        el.classList.add('visible')
      }, index * 100)
    })
  }, 300)
})
</script>

<style scoped>
/* Import the same design system variables */
:root {
  --color-surface: hsl(220, 20%, 97%);
  --color-surface-elevated: hsl(0, 0%, 100%);
  --color-accent: hsl(250, 75%, 60%);
  --color-accent-glow: hsl(250, 75%, 60%, 0.15);
  --color-text-primary: hsl(220, 25%, 12%);
  --color-text-secondary: hsl(220, 15%, 45%);
  
  --space-xs: 0.5rem;
  --space-sm: 1rem;
  --space-md: 2rem;
  --space-lg: 4rem;
  --space-xl: 8rem;
  
  --shadow-sm: 0 1px 2px hsl(220 20% 20% / 0.04), 0 1px 3px hsl(220 20% 20% / 0.06);
  --shadow-md: 0 4px 6px hsl(220 20% 20% / 0.04), 0 8px 20px hsl(220 20% 20% / 0.06);
  --shadow-lg: 0 8px 16px hsl(220 20% 20% / 0.04), 0 20px 50px hsl(220 20% 20% / 0.08);
  --shadow-glow: 0 0 30px var(--color-accent-glow);
}

.charts-page {
  min-height: 100vh;
  background: 
    radial-gradient(ellipse at 20% 50%, hsl(250 80% 65% / 0.06) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, hsl(330 70% 60% / 0.04) 0%, transparent 50%),
    var(--color-surface);
}

/* Hero Section */
.hero-section {
  padding: var(--space-xl) 0;
}

.hero-title {
  font-size: clamp(2.5rem, 6vw, 4rem);
  font-weight: 900;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: var(--color-text-primary);
}

.hero-subtitle {
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* Animations */
.reveal {
  opacity: 0;
  transform: translateY(30px) scale(0.95);
  transition: all 0.7s cubic-bezier(0.16, 1, 0.3, 1);
}

.reveal.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.stagger-1.visible { animation-delay: 0.1s; }
.stagger-2.visible { animation-delay: 0.2s; }
.stagger-3.visible { animation-delay: 0.3s; }
.stagger-4.visible { animation-delay: 0.4s; }

/* Cards */
.card {
  background: var(--color-surface-elevated);
  border-radius: 1rem;
  box-shadow: var(--shadow-md);
  border: 1px solid hsl(220 20% 90% / 0.5);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.card-body {
  padding: var(--space-md);
}

/* Form Elements */
.input-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.form-select {
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  background: hsl(220, 15%, 96%);
  border: 1px solid hsl(220 20% 85%);
  transition: all 0.2s ease;
  font-size: 0.875rem;
  min-width: 120px;
}

.form-select:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px hsl(250 60% 70% / 0.1);
  background: white;
}

/* Theme Toggle */
.theme-toggle {
  padding: 0.5rem;
  border-radius: 0.5rem;
  background: hsl(220, 15%, 96%);
  border: 1px solid hsl(220 20% 85%);
  transition: all 0.2s ease;
  cursor: pointer;
}

.theme-toggle:hover {
  background: hsl(220, 15%, 92%);
  border-color: var(--color-accent);
}

/* Chart Display */
.chart-display {
  min-height: 700px;
}

.chart-container {
  border-radius: 1rem;
  overflow: hidden;
  background: var(--color-surface-elevated);
  box-shadow: var(--shadow-md);
}

.chart-header {
  padding: var(--space-md);
  border-bottom: 1px solid hsl(220 20% 90% / 0.3);
  background: linear-gradient(135deg, hsl(250 60% 98%) 0%, hsl(220 30% 97%) 100%);
}

.chart-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 0.5rem;
}

.chart-description {
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.chart-wrapper {
  position: relative;
}

/* Section Title */
.section-title {
  font-size: clamp(2rem, 4vw, 2.5rem);
  font-weight: 700;
  text-align: center;
  margin-bottom: 3rem;
  color: var(--color-text-primary);
}

/* Comparison Cards */
.comparison-card {
  padding: var(--space-md);
  height: 100%;
}

.comparison-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
}

.comparison-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.comparison-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.badge-fast {
  background: hsl(142, 76%, 90%);
  color: hsl(142, 76%, 36%);
}

.badge-full {
  background: hsl(221, 83%, 90%);
  color: hsl(221, 83%, 53%);
}

.comparison-features {
  space-y: 1rem;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0;
}

.feature-icon {
  width: 1.25rem;
  height: 1.25rem;
  flex-shrink: 0;
}

/* Button Styles */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  border-radius: 0.75rem;
  font-weight: 600;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  cursor: pointer;
  border: none;
  text-decoration: none;
  font-size: 0.875rem;
}

.btn-primary {
  background: var(--color-accent);
  color: white;
  box-shadow: var(--shadow-sm);
}

.btn-primary:hover {
  background: hsl(250, 75%, 55%);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md), var(--shadow-glow);
}

.btn-secondary {
  background: white;
  color: var(--color-text-primary);
  border: 1px solid hsl(220 20% 85%);
  box-shadow: var(--shadow-sm);
}

.btn-secondary:hover {
  background: hsl(220, 15%, 96%);
  border-color: hsl(220 20% 75%);
}

/* Gradient */
.bg-gradient-primary {
  background: linear-gradient(135deg, var(--color-accent), hsl(280, 70%, 65%));
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  :root {
    --color-surface: hsl(220, 20%, 7%);
    --color-surface-elevated: hsl(220, 15%, 10%);
    --color-text-primary: hsl(220, 25%, 88%);
    --color-text-secondary: hsl(220, 15%, 65%);
  }
}

.dark {
  --color-surface: hsl(220, 20%, 7%);
  --color-surface-elevated: hsl(220, 15%, 10%);
  --color-text-primary: hsl(220, 25%, 88%);
  --color-text-secondary: hsl(220, 15%, 65%);
}

/* Responsive Design */
@media (max-width: 768px) {
  .hero-title {
    font-size: clamp(2rem, 8vw, 3rem);
  }
  
  .comparison-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}

/* Container and Layout */
.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 2rem;
}

.section {
  padding: 4rem 0;
}

.section-lg {
  padding: 6rem 0;
}

/* Grid System */
.grid {
  display: grid;
}

.grid-cols-1 {
  grid-template-columns: repeat(1, minmax(0, 1fr));
}

.grid-cols-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.gap-4 { gap: 1rem; }
.gap-6 { gap: 1.5rem; }
.gap-8 { gap: 2rem; }

@media (min-width: 640px) {
  .sm\:flex-row { flex-direction: row; }
  .sm\:items-center { align-items: center; }
}

@media (min-width: 1024px) {
  .lg\:grid-cols-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* Utilities */
.text-center { text-align: center; }
.text-sm { font-size: 0.875rem; }
.text-xl { font-size: 1.25rem; }
.text-2xl { font-size: 1.5rem; }
.text-secondary { color: var(--color-text-secondary); }

.flex { display: flex; }
.items-center { align-items: center; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.space-x-2 > * + * { margin-left: 0.5rem; }
.space-x-4 > * + * { margin-left: 1rem; }
.space-y-1rem > * + * { margin-top: 1rem; }

.max-w-2xl { max-width: 42rem; }
.mx-auto { margin: 0 auto; }
.mb-4 { margin-bottom: 1rem; }
.mb-6 { margin-bottom: 1.5rem; }
.mb-8 { margin-bottom: 2rem; }
.mb-12 { margin-bottom: 3rem; }

.leading-relaxed { line-height: 1.625; }
</style>