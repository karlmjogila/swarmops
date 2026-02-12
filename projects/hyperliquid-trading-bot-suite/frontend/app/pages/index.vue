<template>
  <div class="space-y-8">
    <!-- Hero Section -->
    <section class="text-center py-12 reveal">
      <h1 class="text-6xl font-display font-bold text-text-primary mb-6">
        AI-Powered Trading
        <span class="text-accent">Intelligence</span>
      </h1>
      <p class="text-xl text-text-secondary max-w-3xl mx-auto leading-relaxed">
        Learn trading strategies from educational content, detect patterns with precision,
        and execute trades with confidence. Your personal trading mentor powered by AI.
      </p>
    </section>

    <!-- Status Cards -->
    <section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 reveal">
      <div class="card p-6">
        <h3 class="text-lg font-semibold text-text-primary mb-2">System Status</h3>
        <div class="flex items-center space-x-2">
          <div class="w-3 h-3 bg-green-500 rounded-full"></div>
          <span class="text-text-secondary">Healthy</span>
        </div>
      </div>
      
      <div class="card p-6">
        <h3 class="text-lg font-semibold text-text-primary mb-2">Active Strategies</h3>
        <div class="text-2xl font-bold text-accent">{{ strategies.length }}</div>
      </div>
      
      <div class="card p-6">
        <h3 class="text-lg font-semibold text-text-primary mb-2">Open Positions</h3>
        <div class="text-2xl font-bold text-accent">{{ positions.length }}</div>
      </div>
      
      <div class="card p-6">
        <h3 class="text-lg font-semibold text-text-primary mb-2">Daily P&L</h3>
        <div class="text-2xl font-bold" :class="dailyPnl >= 0 ? 'pnl-positive' : 'pnl-negative'">
          {{ dailyPnl >= 0 ? '+' : '' }}{{ dailyPnl.toFixed(2) }}%
        </div>
      </div>
    </section>

    <!-- Quick Actions -->
    <section class="reveal">
      <h2 class="text-3xl font-display font-semibold text-text-primary mb-6">Quick Actions</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <NuxtLink to="/ingestion" class="card p-6 hover:scale-[1.02] transition-transform duration-200">
          <div class="flex items-center space-x-4">
            <div class="w-12 h-12 bg-accent/10 rounded-lg flex items-center justify-center">
              <Icon name="heroicons:document-plus" class="w-6 h-6 text-accent" />
            </div>
            <div>
              <h3 class="font-semibold text-text-primary">Upload Content</h3>
              <p class="text-text-secondary text-sm">Add PDFs or YouTube videos</p>
            </div>
          </div>
        </NuxtLink>
        
        <NuxtLink to="/backtests/new" class="card p-6 hover:scale-[1.02] transition-transform duration-200">
          <div class="flex items-center space-x-4">
            <div class="w-12 h-12 bg-accent/10 rounded-lg flex items-center justify-center">
              <Icon name="heroicons:chart-bar" class="w-6 h-6 text-accent" />
            </div>
            <div>
              <h3 class="font-semibold text-text-primary">New Backtest</h3>
              <p class="text-text-secondary text-sm">Test strategies on historical data</p>
            </div>
          </div>
        </NuxtLink>
        
        <NuxtLink to="/strategies" class="card p-6 hover:scale-[1.02] transition-transform duration-200">
          <div class="flex items-center space-x-4">
            <div class="w-12 h-12 bg-accent/10 rounded-lg flex items-center justify-center">
              <Icon name="heroicons:cog-6-tooth" class="w-6 h-6 text-accent" />
            </div>
            <div>
              <h3 class="font-semibold text-text-primary">Manage Strategies</h3>
              <p class="text-text-secondary text-sm">Configure and monitor rules</p>
            </div>
          </div>
        </NuxtLink>
      </div>
    </section>

    <!-- Recent Activity -->
    <section class="reveal">
      <h2 class="text-3xl font-display font-semibold text-text-primary mb-6">Recent Activity</h2>
      <div class="card p-6">
        <div v-if="recentTrades.length === 0" class="text-center py-8 text-text-secondary">
          <Icon name="heroicons:chart-bar-square" class="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No recent trading activity</p>
          <p class="text-sm">Upload some educational content to get started</p>
        </div>
        
        <div v-else class="space-y-4">
          <div
            v-for="trade in recentTrades"
            :key="trade.id"
            class="flex justify-between items-center p-4 bg-surface rounded-lg"
          >
            <div>
              <div class="font-medium text-text-primary">{{ trade.symbol }} {{ trade.direction.toUpperCase() }}</div>
              <div class="text-sm text-text-secondary">{{ trade.strategy_name }}</div>
            </div>
            <div class="text-right">
              <div class="font-medium" :class="trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'">
                {{ trade.pnl >= 0 ? '+' : '' }}{{ trade.pnl.toFixed(2) }}%
              </div>
              <div class="text-sm text-text-secondary">{{ formatTime(trade.entry_time) }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
// Meta
useHead({
  title: 'Dashboard - Hyperliquid Trading Bot',
})

// Reactive data
const strategies = ref([])
const positions = ref([])
const recentTrades = ref([])
const dailyPnl = ref(0)

// Load data on mount
onMounted(async () => {
  await Promise.all([
    loadStrategies(),
    loadPositions(),
    loadRecentTrades(),
    loadDailyPnl()
  ])
  
  // Add reveal animation
  nextTick(() => {
    const reveals = document.querySelectorAll('.reveal')
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          setTimeout(() => entry.target.classList.add('visible'), i * 100)
          observer.unobserve(entry.target)
        }
      })
    }, { threshold: 0.1 })
    
    reveals.forEach(el => observer.observe(el))
  })
})

// Data loading functions
async function loadStrategies() {
  try {
    // TODO: Replace with actual API call
    // const { data } = await $fetch('/api/strategies')
    // strategies.value = data
    strategies.value = []
  } catch (error) {
    console.error('Failed to load strategies:', error)
  }
}

async function loadPositions() {
  try {
    // TODO: Replace with actual API call
    // const { data } = await $fetch('/api/trades/positions/current')
    // positions.value = data
    positions.value = []
  } catch (error) {
    console.error('Failed to load positions:', error)
  }
}

async function loadRecentTrades() {
  try {
    // TODO: Replace with actual API call
    // const { data } = await $fetch('/api/trades?limit=5')
    // recentTrades.value = data
    recentTrades.value = []
  } catch (error) {
    console.error('Failed to load recent trades:', error)
  }
}

async function loadDailyPnl() {
  try {
    // TODO: Replace with actual API call
    // const { data } = await $fetch('/api/trades/stats/daily')
    // dailyPnl.value = data.pnl_percent
    dailyPnl.value = 0
  } catch (error) {
    console.error('Failed to load daily P&L:', error)
  }
}

// Utility functions
function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString()
}
</script>

<style scoped>
/* Component-specific styles */
</style>