<template>
  <div class="positions-page">
    <section class="section-lg">
      <div class="container">
        <!-- Page Header -->
        <div class="flex items-center justify-between mb-16 reveal">
          <div>
            <h1 class="mb-2">Active Positions</h1>
            <p class="text-xl text-gray-600 dark:text-gray-400">
              Monitor and manage your live trading positions
            </p>
          </div>
          
          <div class="flex items-center space-x-4">
            <!-- Portfolio Value -->
            <div class="text-right">
              <div class="text-sm text-gray-500">Portfolio Value</div>
              <div class="text-2xl font-bold price-positive">$12,547.82</div>
            </div>
            
            <!-- Refresh Button -->
            <button class="btn btn-secondary" @click="refreshPositions">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              Refresh
            </button>
          </div>
        </div>

        <!-- Portfolio Overview -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
          <div class="card reveal stagger-1">
            <div class="card-body text-center">
              <div class="text-2xl font-bold price-positive mb-1">+$1,247.82</div>
              <div class="text-sm text-gray-600 dark:text-gray-400">Total P&L</div>
              <div class="text-xs text-green-600 dark:text-green-400 mt-1">+11.04%</div>
            </div>
          </div>
          
          <div class="card reveal stagger-2">
            <div class="card-body text-center">
              <div class="text-2xl font-bold text-blue-600 mb-1">5</div>
              <div class="text-sm text-gray-600 dark:text-gray-400">Open Positions</div>
              <div class="text-xs text-blue-600 dark:text-blue-400 mt-1">3 Long • 2 Short</div>
            </div>
          </div>
          
          <div class="card reveal stagger-3">
            <div class="card-body text-center">
              <div class="text-2xl font-bold text-purple-600 mb-1">$890.45</div>
              <div class="text-sm text-gray-600 dark:text-gray-400">Today's P&L</div>
              <div class="text-xs text-green-600 dark:text-green-400 mt-1">+7.65%</div>
            </div>
          </div>
          
          <div class="card reveal stagger-4">
            <div class="card-body text-center">
              <div class="text-2xl font-bold text-orange-600 mb-1">$2,340</div>
              <div class="text-sm text-gray-600 dark:text-gray-400">Available Margin</div>
              <div class="text-xs text-gray-500 mt-1">Used: 68%</div>
            </div>
          </div>
        </div>

        <!-- Positions Table -->
        <div class="card reveal stagger-5">
          <div class="card-body">
            <div class="flex items-center justify-between mb-6">
              <h3 class="text-xl font-display font-semibold">Open Positions</h3>
              <div class="flex items-center space-x-2">
                <span class="text-sm text-gray-500">Auto-refresh</span>
                <button 
                  class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none"
                  :class="autoRefresh ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'"
                  @click="autoRefresh = !autoRefresh"
                >
                  <span 
                    class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                    :class="autoRefresh ? 'translate-x-5' : 'translate-x-0'"
                  />
                </button>
              </div>
            </div>
            
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead>
                  <tr class="border-b border-gray-200 dark:border-gray-700">
                    <th class="text-left py-4 px-2 font-medium text-gray-600 dark:text-gray-400">Symbol</th>
                    <th class="text-left py-4 px-2 font-medium text-gray-600 dark:text-gray-400">Side</th>
                    <th class="text-left py-4 px-2 font-medium text-gray-600 dark:text-gray-400">Size</th>
                    <th class="text-left py-4 px-2 font-medium text-gray-600 dark:text-gray-400">Entry</th>
                    <th class="text-left py-4 px-2 font-medium text-gray-600 dark:text-gray-400">Current</th>
                    <th class="text-left py-4 px-2 font-medium text-gray-600 dark:text-gray-400">P&L</th>
                    <th class="text-left py-4 px-2 font-medium text-gray-600 dark:text-gray-400">P&L %</th>
                    <th class="text-left py-4 px-2 font-medium text-gray-600 dark:text-gray-400">Strategy</th>
                    <th class="text-center py-4 px-2 font-medium text-gray-600 dark:text-gray-400">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                  <tr v-for="position in positions" :key="position.id" class="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <!-- Symbol -->
                    <td class="py-4 px-2">
                      <div class="flex items-center space-x-3">
                        <div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white text-xs font-bold">
                          {{ position.symbol.split('/')[0].slice(0, 2) }}
                        </div>
                        <div>
                          <div class="font-medium text-gray-900 dark:text-white">{{ position.symbol }}</div>
                          <div class="text-sm text-gray-500">{{ position.leverage }}x</div>
                        </div>
                      </div>
                    </td>
                    
                    <!-- Side -->
                    <td class="py-4 px-2">
                      <span class="px-2 py-1 rounded-full text-xs font-medium" 
                            :class="position.side === 'Long' 
                              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' 
                              : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'">
                        {{ position.side }}
                      </span>
                    </td>
                    
                    <!-- Size -->
                    <td class="py-4 px-2 text-gray-900 dark:text-white font-mono">
                      {{ position.size }}
                    </td>
                    
                    <!-- Entry -->
                    <td class="py-4 px-2 text-gray-900 dark:text-white font-mono">
                      ${{ position.entry.toLocaleString() }}
                    </td>
                    
                    <!-- Current -->
                    <td class="py-4 px-2 text-gray-900 dark:text-white font-mono">
                      ${{ position.current.toLocaleString() }}
                      <div class="text-xs mt-1" :class="position.change > 0 ? 'text-green-600' : 'text-red-600'">
                        {{ position.change > 0 ? '+' : '' }}{{ position.change.toFixed(2) }}%
                      </div>
                    </td>
                    
                    <!-- P&L -->
                    <td class="py-4 px-2 font-mono font-semibold" 
                        :class="position.pnl > 0 ? 'price-positive' : 'price-negative'">
                      {{ position.pnl > 0 ? '+' : '' }}${{ position.pnl.toFixed(2) }}
                    </td>
                    
                    <!-- P&L % -->
                    <td class="py-4 px-2 font-mono font-semibold" 
                        :class="position.pnlPercent > 0 ? 'price-positive' : 'price-negative'">
                      {{ position.pnlPercent > 0 ? '+' : '' }}{{ position.pnlPercent.toFixed(2) }}%
                    </td>
                    
                    <!-- Strategy -->
                    <td class="py-4 px-2">
                      <span class="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400 rounded text-xs">
                        {{ position.strategy }}
                      </span>
                    </td>
                    
                    <!-- Actions -->
                    <td class="py-4 px-2">
                      <div class="flex items-center justify-center space-x-2">
                        <button class="p-1 text-gray-400 hover:text-blue-600 transition-colors" title="Edit Position">
                          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                          </svg>
                        </button>
                        <button 
                          class="p-1 text-gray-400 hover:text-red-600 transition-colors" 
                          title="Close Position"
                          @click="closePosition(position.id)"
                        >
                          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Recent Closed Positions -->
        <div class="card reveal stagger-6 mt-8">
          <div class="card-body">
            <h3 class="text-xl font-display font-semibold mb-6">Recent Closed Positions</h3>
            
            <div class="space-y-4">
              <div v-for="closedPosition in closedPositions" :key="closedPosition.id" 
                   class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div class="flex items-center space-x-4">
                  <div class="w-10 h-10 bg-gradient-to-br from-gray-400 to-gray-600 rounded-lg flex items-center justify-center text-white text-xs font-bold">
                    {{ closedPosition.symbol.split('/')[0].slice(0, 2) }}
                  </div>
                  <div>
                    <div class="flex items-center space-x-2">
                      <span class="font-medium text-gray-900 dark:text-white">{{ closedPosition.symbol }}</span>
                      <span class="px-2 py-1 rounded-full text-xs font-medium" 
                            :class="closedPosition.side === 'Long' 
                              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' 
                              : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'">
                        {{ closedPosition.side }}
                      </span>
                    </div>
                    <div class="text-sm text-gray-500">
                      Closed {{ closedPosition.closedAt }} • {{ closedPosition.strategy }}
                    </div>
                  </div>
                </div>
                
                <div class="text-right">
                  <div class="font-semibold" :class="closedPosition.pnl > 0 ? 'price-positive' : 'price-negative'">
                    {{ closedPosition.pnl > 0 ? '+' : '' }}${{ closedPosition.pnl.toFixed(2) }}
                  </div>
                  <div class="text-sm" :class="closedPosition.pnlPercent > 0 ? 'text-green-600' : 'text-red-600'">
                    {{ closedPosition.pnlPercent > 0 ? '+' : '' }}{{ closedPosition.pnlPercent.toFixed(2) }}%
                  </div>
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
  title: 'Positions - Hyperliquid Trading',
  meta: [
    { name: 'description', content: 'Monitor and manage your active trading positions.' }
  ]
})

// Reactive state
const autoRefresh = ref(true)

// Sample position data
const positions = ref([
  {
    id: 1,
    symbol: 'ETH/USD',
    side: 'Long',
    size: '2.5 ETH',
    entry: 3240,
    current: 3285,
    leverage: '5',
    pnl: 225.50,
    pnlPercent: 2.78,
    change: 1.39,
    strategy: 'Breakout'
  },
  {
    id: 2,
    symbol: 'BTC/USD',
    side: 'Short',
    size: '0.1 BTC',
    entry: 67890,
    current: 67650,
    leverage: '3',
    pnl: 72.00,
    pnlPercent: 1.06,
    change: -0.35,
    strategy: 'Range'
  },
  {
    id: 3,
    symbol: 'SOL/USD',
    side: 'Long',
    size: '50 SOL',
    entry: 198.45,
    current: 202.30,
    leverage: '10',
    pnl: 192.50,
    pnlPercent: 1.94,
    change: 1.94,
    strategy: 'Momentum'
  },
  {
    id: 4,
    symbol: 'AVAX/USD',
    side: 'Long',
    size: '100 AVAX',
    entry: 45.20,
    current: 44.85,
    leverage: '2',
    pnl: -70.00,
    pnlPercent: -1.55,
    change: -0.77,
    strategy: 'Breakout'
  },
  {
    id: 5,
    symbol: 'LINK/USD',
    side: 'Short',
    size: '200 LINK',
    entry: 18.50,
    current: 18.75,
    leverage: '4',
    pnl: -200.00,
    pnlPercent: -2.70,
    change: 1.35,
    strategy: 'Range'
  }
])

// Sample closed positions
const closedPositions = ref([
  {
    id: 101,
    symbol: 'ETH/USD',
    side: 'Long',
    pnl: 145.30,
    pnlPercent: 2.1,
    closedAt: '2 hours ago',
    strategy: 'Breakout'
  },
  {
    id: 102,
    symbol: 'BTC/USD',
    side: 'Short',
    pnl: -85.20,
    pnlPercent: -0.8,
    closedAt: '4 hours ago',
    strategy: 'Momentum'
  },
  {
    id: 103,
    symbol: 'SOL/USD',
    side: 'Long',
    pnl: 320.45,
    pnlPercent: 3.2,
    closedAt: '6 hours ago',
    strategy: 'Range'
  }
])

// Functions
const refreshPositions = () => {
  console.log('Refreshing positions...')
  // In a real implementation, this would make an API call
}

const closePosition = (positionId) => {
  console.log(`Closing position ${positionId}`)
  // In a real implementation, this would make an API call
}

// Initialize reveal animations
onMounted(() => {
  setTimeout(() => {
    const revealElements = document.querySelectorAll('.reveal')
    revealElements.forEach((el, index) => {
      setTimeout(() => {
        el.classList.add('visible')
      }, index * 100)
    })
  }, 300)
  
  // Auto-refresh positions if enabled
  const refreshInterval = setInterval(() => {
    if (autoRefresh.value) {
      // Simulate price updates
      positions.value.forEach(position => {
        const change = (Math.random() - 0.5) * 20 // +/- $10
        position.current += change
        position.change = ((position.current - position.entry) / position.entry) * 100
        
        const sizeValue = parseFloat(position.size.split(' ')[0])
        const multiplier = position.side === 'Long' ? 1 : -1
        position.pnl = (position.current - position.entry) * sizeValue * multiplier
        position.pnlPercent = position.change * multiplier
      })
    }
  }, 5000) // Update every 5 seconds
  
  onUnmounted(() => {
    clearInterval(refreshInterval)
  })
})
</script>

<style scoped>
.positions-page {
  min-height: 100vh;
}

/* Table hover effects */
tbody tr:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

/* Responsive table */
@media (max-width: 1024px) {
  .overflow-x-auto {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  
  table {
    min-width: 800px;
  }
}
</style>