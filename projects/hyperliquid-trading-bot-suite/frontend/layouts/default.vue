<template>
  <div class="min-h-screen flex flex-col">
    <!-- Navigation Header -->
    <header class="glass sticky top-0 z-50 border-b border-gray-200/20">
      <nav class="container mx-auto px-6 py-4">
        <div class="flex items-center justify-between">
          <!-- Logo -->
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 bg-gradient-primary rounded-xl flex items-center justify-center">
              <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm5-18v4h3V3h-3z"/>
              </svg>
            </div>
            <div>
              <h1 class="text-xl font-display font-bold text-gray-900 dark:text-white">
                Hyperliquid
              </h1>
              <p class="text-sm text-gray-500 -mt-1">Trading Dashboard</p>
            </div>
          </div>
          
          <!-- Navigation Links -->
          <div class="hidden md:flex items-center space-x-8">
            <NuxtLink 
              to="/" 
              class="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 font-medium transition-colors"
            >
              Dashboard
            </NuxtLink>
            <NuxtLink 
              to="/strategies" 
              class="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 font-medium transition-colors"
            >
              Strategies
            </NuxtLink>
            <NuxtLink 
              to="/backtest" 
              class="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 font-medium transition-colors"
            >
              Backtest
            </NuxtLink>
            <NuxtLink 
              to="/positions" 
              class="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 font-medium transition-colors"
            >
              Positions
            </NuxtLink>
          </div>
          
          <!-- Actions -->
          <div class="flex items-center space-x-4">
            <!-- Theme Toggle -->
            <button 
              @click="toggleTheme"
              class="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              <svg v-if="!isDark" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
              </svg>
              <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
              </svg>
            </button>
            
            <!-- Connection Status -->
            <div class="flex items-center space-x-2">
              <div 
                class="w-2 h-2 rounded-full"
                :class="isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'"
              />
              <span class="text-sm text-gray-600 dark:text-gray-400">
                {{ isConnected ? 'Connected' : 'Disconnected' }}
              </span>
            </div>
          </div>
        </div>
      </nav>
    </header>

    <!-- Main Content -->
    <main class="flex-1">
      <slot />
    </main>

    <!-- Footer -->
    <footer class="border-t border-gray-200/20 bg-gray-50/50 dark:bg-gray-900/50">
      <div class="container mx-auto px-6 py-8">
        <div class="text-center text-sm text-gray-600 dark:text-gray-400">
          <p>&copy; 2024 Hyperliquid Trading Dashboard. Built with AI-powered pattern detection.</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
const isDark = ref(false)
const isConnected = ref(true) // Will be connected to actual WebSocket status

// Theme toggle functionality
const toggleTheme = () => {
  isDark.value = !isDark.value
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('dark', isDark.value)
  }
}

// Initialize theme on mount
onMounted(() => {
  // Check for saved theme preference or default to system preference
  const savedTheme = localStorage.getItem('theme')
  const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  
  isDark.value = savedTheme ? savedTheme === 'dark' : systemDark
  document.documentElement.classList.toggle('dark', isDark.value)
})

// Watch for theme changes and save to localStorage
watch(isDark, (newValue) => {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('theme', newValue ? 'dark' : 'light')
  }
})

// Connection status simulation (will be replaced with actual WebSocket connection)
onMounted(() => {
  const simulateConnection = () => {
    // Simulate occasional disconnections for demo
    setInterval(() => {
      if (Math.random() < 0.05) { // 5% chance
        isConnected.value = false
        setTimeout(() => {
          isConnected.value = true
        }, 2000)
      }
    }, 10000)
  }
  
  simulateConnection()
})
</script>

<style scoped>
/* Navigation link hover effects */
.router-link-active {
  @apply text-blue-600 dark:text-blue-400;
}

/* Smooth transitions for theme changes */
* {
  transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
}
</style>