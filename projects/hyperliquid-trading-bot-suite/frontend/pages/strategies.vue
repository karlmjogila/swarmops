<template>
  <div class="strategies-page">
    <StrategyManager />
  </div>
</template>

<script setup>
// Page metadata
useHead({
  title: 'Strategies - Hyperliquid Trading',
  meta: [
    { name: 'description', content: 'Manage and monitor your AI-powered trading strategies.' }
  ]
})
</script>

<style scoped>
.strategies-page {
  min-height: 100vh;
}
</style>
