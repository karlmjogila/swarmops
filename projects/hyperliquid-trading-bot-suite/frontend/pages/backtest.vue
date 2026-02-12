<template>
  <div class="backtest-page">
    <section class="section-lg">
      <div class="container">
        <!-- Page Header -->
        <div class="text-center mb-16 reveal">
          <h1 class="mb-6">Strategy Backtesting</h1>
          <p class="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Test your strategies against historical data to validate performance before going live
          </p>
        </div>

        <div class="grid grid-cols-12 gap-8">
          <!-- Configuration Panel -->
          <div class="col-span-12 lg:col-span-4">
            <div class="card reveal stagger-1">
              <div class="card-body">
                <h3 class="text-xl font-display font-semibold mb-6">Backtest Configuration</h3>
                
                <div class="space-y-6">
                  <!-- Strategy Selection -->
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Strategy
                    </label>
                    <select class="w-full px-4 py-3 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                      <option>Breakout Hunter</option>
                      <option>Range Scalper</option>
                      <option>Momentum Rider</option>
                    </select>
                  </div>

                  <!-- Symbol Selection -->
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Trading Pair
                    </label>
                    <select class="w-full px-4 py-3 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                      <option>ETH/USD</option>
                      <option>BTC/USD</option>
                      <option>SOL/USD</option>
                      <option>AVAX/USD</option>
                    </select>
                  </div>

                  <!-- Timeframe -->
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Timeframe
                    </label>
                    <select class="w-full px-4 py-3 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                      <option>5m</option>
                      <option>15m</option>
                      <option>1h</option>
                      <option>4h</option>
                    </select>
                  </div>

                  <!-- Date Range -->
                  <div class="grid grid-cols-2 gap-3">
                    <div>
                      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Start Date
                      </label>
                      <input 
                        type="date" 
                        class="w-full px-4 py-3 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
                        value="2024-01-01"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        End Date
                      </label>
                      <input 
                        type="date" 
                        class="w-full px-4 py-3 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
                        value="2024-12-31"
                      />
                    </div>
                  </div>

                  <!-- Initial Capital -->
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Initial Capital (USD)
                    </label>
                    <input 
                      type="number" 
                      placeholder="10000" 
                      class="w-full px-4 py-3 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
                    />
                  </div>

                  <!-- Risk Per Trade -->
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Risk Per Trade (%)
                    </label>
                    <input 
                      type="number" 
                      step="0.1"
                      placeholder="2.0" 
                      class="w-full px-4 py-3 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
                    />
                  </div>

                  <!-- Run Backtest Button -->
                  <button 
                    class="w-full btn btn-primary"
                    :disabled="isRunning"
                    @click="runBacktest"
                  >
                    <svg v-if="isRunning" class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                    <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h8m-1 1h-6m6 1H9m11-6a8.001 8.001 0 11-16 0 8.001 8.001 0 0116 0z"/>
                    </svg>
                    {{ isRunning ? 'Running Backtest...' : 'Run Backtest' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Results Panel -->
          <div class="col-span-12 lg:col-span-8">
            <!-- Performance Chart -->
            <div class="card reveal stagger-2 mb-8">
              <div class="card-body">
                <div class="flex items-center justify-between mb-6">
                  <h3 class="text-xl font-display font-semibold">Equity Curve</h3>
                  <div class="flex items-center space-x-4 text-sm">
                    <div class="flex items-center space-x-2">
                      <div class="w-3 h-3 bg-blue-500 rounded-full"></div>
                      <span class="text-gray-600 dark:text-gray-400">Portfolio Value</span>
                    </div>
                    <div class="flex items-center space-x-2">
                      <div class="w-3 h-3 bg-gray-400 rounded-full"></div>
                      <span class="text-gray-600 dark:text-gray-400">Buy & Hold</span>
                    </div>
                  </div>
                </div>
                
                <!-- Chart placeholder -->
                <div class="h-80 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg flex items-center justify-center">
                  <div class="text-center">
                    <svg class="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                    </svg>
                    <p class="text-gray-500">Run a backtest to see results</p>
                  </div>
                </div>
              </div>
            </div>

            <!-- Performance Metrics -->
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div class="card reveal stagger-3">
                <div class="card-body text-center">
                  <div class="text-2xl font-bold price-positive mb-1">+24.8%</div>
                  <div class="text-sm text-gray-600 dark:text-gray-400">Total Return</div>
                </div>
              </div>
              
              <div class="card reveal stagger-4">
                <div class="card-body text-center">
                  <div class="text-2xl font-bold text-blue-600 mb-1">1.42</div>
                  <div class="text-sm text-gray-600 dark:text-gray-400">Sharpe Ratio</div>
                </div>
              </div>
              
              <div class="card reveal stagger-5">
                <div class="card-body text-center">
                  <div class="text-2xl font-bold text-purple-600 mb-1">73%</div>
                  <div class="text-sm text-gray-600 dark:text-gray-400">Win Rate</div>
                </div>
              </div>
              
              <div class="card reveal stagger-6">
                <div class="card-body text-center">
                  <div class="text-2xl font-bold price-negative mb-1">-8.2%</div>
                  <div class="text-sm text-gray-600 dark:text-gray-400">Max Drawdown</div>
                </div>
              </div>
            </div>

            <!-- Trade History -->
            <div class="card reveal stagger-7">
              <div class="card-body">
                <h3 class="text-xl font-display font-semibold mb-6">Trade History</h3>
                
                <div class="overflow-x-auto">
                  <table class="w-full text-sm">
                    <thead>
                      <tr class="border-b border-gray-200 dark:border-gray-700">
                        <th class="text-left py-3 font-medium text-gray-600 dark:text-gray-400">Date</th>
                        <th class="text-left py-3 font-medium text-gray-600 dark:text-gray-400">Side</th>
                        <th class="text-left py-3 font-medium text-gray-600 dark:text-gray-400">Entry</th>
                        <th class="text-left py-3 font-medium text-gray-600 dark:text-gray-400">Exit</th>
                        <th class="text-left py-3 font-medium text-gray-600 dark:text-gray-400">P&L</th>
                        <th class="text-left py-3 font-medium text-gray-600 dark:text-gray-400">Return %</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                      <tr v-for="trade in sampleTrades" :key="trade.id">
                        <td class="py-3 text-gray-900 dark:text-white">{{ trade.date }}</td>
                        <td class="py-3">
                          <span class="px-2 py-1 rounded text-xs font-medium" 
                                :class="trade.side === 'Long' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'">
                            {{ trade.side }}
                          </span>
                        </td>
                        <td class="py-3 text-gray-900 dark:text-white">${{ trade.entry }}</td>
                        <td class="py-3 text-gray-900 dark:text-white">${{ trade.exit }}</td>
                        <td class="py-3 font-semibold" :class="trade.pnl > 0 ? 'price-positive' : 'price-negative'">${{ trade.pnl }}</td>
                        <td class="py-3 font-semibold" :class="trade.return > 0 ? 'price-positive' : 'price-negative'">{{ trade.return }}%</td>
                      </tr>
                    </tbody>
                  </table>
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
  title: 'Backtest - Hyperliquid Trading',
  meta: [
    { name: 'description', content: 'Backtest your trading strategies against historical data.' }
  ]
})

// Reactive state
const isRunning = ref(false)

// Sample trade data
const sampleTrades = ref([
  { id: 1, date: '2024-02-10', side: 'Long', entry: '3,240', exit: '3,285', pnl: '+24.50', return: '+1.4' },
  { id: 2, date: '2024-02-09', side: 'Short', entry: '3,295', exit: '3,275', pnl: '+18.30', return: '+0.6' },
  { id: 3, date: '2024-02-08', side: 'Long', entry: '3,180', exit: '3,165', pnl: '-12.40', return: '-0.5' },
  { id: 4, date: '2024-02-07', side: 'Long', entry: '3,120', exit: '3,198', pnl: '+45.20', return: '+2.5' },
  { id: 5, date: '2024-02-06', side: 'Short', entry: '3,250', exit: '3,270', pnl: '-15.80', return: '-0.6' },
])

// Run backtest function
const runBacktest = async () => {
  isRunning.value = true
  
  // Simulate backtest running
  setTimeout(() => {
    isRunning.value = false
    // In a real implementation, this would make an API call
    console.log('Backtest completed')
  }, 3000)
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
})
</script>

<style scoped>
.backtest-page {
  min-height: 100vh;
}

/* Table styles */
table {
  border-collapse: collapse;
}

/* Responsive table */
@media (max-width: 768px) {
  .overflow-x-auto {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
}
</style>