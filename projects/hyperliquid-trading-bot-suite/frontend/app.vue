<template>
  <div id="app" class="min-h-screen bg-surface">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    
    <!-- Global notification toasts -->
    <NotificationToast />
  </div>
</template>

<script setup lang="ts">
// Meta tags
useHead({
  htmlAttrs: {
    lang: 'en'
  }
})

// Initialize trading config on app load
const { loadConfig } = useTradingConfig()

// Initialize theme and load config
onMounted(async () => {
  // Check for saved theme preference or default to 'dark'
  const savedTheme = localStorage.getItem('theme') || 'dark'
  document.documentElement.setAttribute('data-theme', savedTheme)
  
  // Load trading configuration from backend
  try {
    await loadConfig()
  } catch (err) {
    console.warn('Failed to load trading config, using defaults')
  }
})
</script>

<style>
/* Global styles are imported from assets/css/main.css */
</style>