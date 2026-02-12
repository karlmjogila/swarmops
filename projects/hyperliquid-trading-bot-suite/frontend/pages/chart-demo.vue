<template>
  <div class="chart-demo-page">
    <div class="container mx-auto px-4 py-8">
      <!-- Page Header -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Multi-Timeframe Chart
        </h1>
        <p class="text-gray-600 dark:text-gray-400">
          Advanced trading chart with multiple timeframe support, volume display, and real-time updates
        </p>
      </div>

      <!-- Symbol Selector -->
      <div class="mb-6 bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Select Trading Pair
        </label>
        <div class="flex gap-2">
          <button
            v-for="sym in availableSymbols"
            :key="sym"
            @click="selectedSymbol = sym"
            :class="[
              'px-4 py-2 rounded-lg font-medium transition-all',
              selectedSymbol === sym
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            ]"
          >
            {{ sym }}
          </button>
        </div>
      </div>

      <!-- Main Chart -->
      <div class="mb-8">
        <MultiTimeframeChart
          ref="chartRef"
          :symbol="selectedSymbol"
          :initial-timeframe="'15m'"
          :height="600"
          :show-volume="true"
        />
      </div>

      <!-- Chart Features -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
          <div class="flex items-center mb-4">
            <div class="w-12 h-12 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
              <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            </div>
          </div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Multi-Timeframe
          </h3>
          <p class="text-sm text-gray-600 dark:text-gray-400">
            Switch between 1m, 5m, 15m, 30m, 1h, 4h, 1d, and 1w timeframes instantly
          </p>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
          <div class="flex items-center mb-4">
            <div class="w-12 h-12 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center">
              <svg class="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
              </svg>
            </div>
          </div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Volume Display
          </h3>
          <p class="text-sm text-gray-600 dark:text-gray-400">
            Toggle volume histogram overlay with color-coded buy/sell pressure
          </p>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
          <div class="flex items-center mb-4">
            <div class="w-12 h-12 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
              <svg class="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>
              </svg>
            </div>
          </div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Interactive Controls
          </h3>
          <p class="text-sm text-gray-600 dark:text-gray-400">
            Pan, zoom, crosshair, and fit content controls for detailed analysis
          </p>
        </div>
      </div>

      <!-- Technical Details -->
      <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
        <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Technical Implementation
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Features
            </h3>
            <ul class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
              <li class="flex items-start">
                <svg class="w-5 h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>Built with lightweight-charts for high performance</span>
              </li>
              <li class="flex items-start">
                <svg class="w-5 h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>Reactive data fetching with composable pattern</span>
              </li>
              <li class="flex items-start">
                <svg class="w-5 h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>Dark mode support with automatic theme detection</span>
              </li>
              <li class="flex items-start">
                <svg class="w-5 h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>Responsive design with automatic resize handling</span>
              </li>
              <li class="flex items-start">
                <svg class="w-5 h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>TypeScript for type safety</span>
              </li>
            </ul>
          </div>
          
          <div>
            <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Architecture
            </h3>
            <ul class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
              <li class="flex items-start">
                <svg class="w-5 h-5 text-blue-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>Composition API with <code class="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded">&lt;script setup&gt;</code></span>
              </li>
              <li class="flex items-start">
                <svg class="w-5 h-5 text-blue-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>Reusable composable: <code class="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded">useChartData</code></span>
              </li>
              <li class="flex items-start">
                <svg class="w-5 h-5 text-blue-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>Data caching to minimize API calls</span>
              </li>
              <li class="flex items-start">
                <svg class="w-5 h-5 text-blue-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>Proper lifecycle management and cleanup</span>
              </li>
              <li class="flex items-start">
                <svg class="w-5 h-5 text-blue-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>Exposed methods for programmatic control</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Usage Example -->
      <div class="mt-8 bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
        <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Usage Example
        </h2>
        <pre class="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm"><code>&lt;template&gt;
  &lt;MultiTimeframeChart
    symbol="ETH/USD"
    :initial-timeframe="'15m'"
    :height="600"
    :show-volume="true"
  /&gt;
&lt;/template&gt;

&lt;script setup lang="ts"&gt;
// Component is auto-imported via Nuxt
// Composable useChartData is also available
&lt;/script&gt;</code></pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Timeframe } from '~/types/chart'

// State
const selectedSymbol = ref('ETH/USD')
const chartRef = ref<any>(null)

// Available symbols
const availableSymbols = [
  'BTC/USD',
  'ETH/USD',
  'SOL/USD',
  'ARB/USD',
]

// Page metadata
definePageMeta({
  title: 'Multi-Timeframe Chart Demo',
  description: 'Advanced trading chart with multiple timeframe support',
})

useHead({
  title: 'Multi-Timeframe Chart Demo - Hyperliquid Trading Bot',
})
</script>

<style scoped>
.chart-demo-page {
  @apply min-h-screen bg-gray-50 dark:bg-gray-950;
}

code {
  @apply font-mono text-xs;
}

pre {
  @apply font-mono;
}
</style>
