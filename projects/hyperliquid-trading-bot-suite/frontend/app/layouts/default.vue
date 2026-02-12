<template>
  <div class="min-h-screen bg-surface">
    <!-- Navigation Header -->
    <header class="bg-surface-elevated border-b border-gray-200 dark:border-gray-700">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <!-- Logo -->
          <div class="flex-shrink-0">
            <h1 class="text-2xl font-display font-semibold text-text-primary">
              Hyperliquid Trading Bot
            </h1>
          </div>
          
          <!-- Navigation -->
          <nav class="hidden md:flex space-x-8">
            <NuxtLink
              to="/"
              class="text-text-secondary hover:text-text-primary transition-colors duration-200"
              active-class="text-accent font-medium"
            >
              Dashboard
            </NuxtLink>
            <NuxtLink
              to="/strategies"
              class="text-text-secondary hover:text-text-primary transition-colors duration-200"
              active-class="text-accent font-medium"
            >
              Strategies
            </NuxtLink>
            <NuxtLink
              to="/backtests"
              class="text-text-secondary hover:text-text-primary transition-colors duration-200"
              active-class="text-accent font-medium"
            >
              Backtests
            </NuxtLink>
            <NuxtLink
              to="/trades"
              class="text-text-secondary hover:text-text-primary transition-colors duration-200"
              active-class="text-accent font-medium"
            >
              Trades
            </NuxtLink>
          </nav>
          
          <!-- Theme Toggle -->
          <button
            @click="toggleTheme"
            class="p-2 rounded-lg bg-surface hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-200"
          >
            <Icon
              :name="isDark ? 'heroicons:sun' : 'heroicons:moon'"
              class="w-5 h-5 text-text-secondary"
            />
          </button>
        </div>
      </div>
    </header>
    
    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <slot />
    </main>
    
    <!-- Footer -->
    <footer class="bg-surface-elevated border-t border-gray-200 dark:border-gray-700 mt-auto">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <p class="text-center text-text-secondary text-sm">
          © 2025 Hyperliquid Trading Bot Suite. Built with Vue 3 + Nuxt 3.
        </p>
      </div>
    </footer>
  </div>
</template>

<script setup>
const isDark = ref(false)

onMounted(() => {
  isDark.value = document.documentElement.getAttribute('data-theme') === 'dark'
})

function toggleTheme() {
  isDark.value = !isDark.value
  const theme = isDark.value ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', theme)
  localStorage.setItem('theme', theme)
}
</script>

<style scoped>
/* Component-specific styles */
</style>