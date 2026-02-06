<script setup lang="ts">
const { connected, reconnect } = useWebSocket()
</script>

<template>
  <div 
    class="flex items-center gap-3 px-3 py-2 rounded-lg text-xs cursor-pointer"
    :style="{
      background: connected ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
      border: connected ? '1px solid rgba(16, 185, 129, 0.15)' : '1px solid rgba(239, 68, 68, 0.15)'
    }"
    :title="connected ? 'Connected' : 'Click to reconnect'"
    @click="!connected && reconnect()"
  >
    <span 
      class="w-2 h-2 rounded-full" 
      :style="{ background: connected ? 'var(--swarm-success)' : 'var(--swarm-error)' }"
    />
    <span 
      class="font-medium"
      :style="{ color: connected ? 'var(--swarm-success)' : 'var(--swarm-error)' }"
    >
      {{ connected ? 'Connected' : 'Offline' }}
    </span>
    <UIcon 
      v-if="!connected"
      name="i-heroicons-arrow-path" 
      class="w-3.5 h-3.5 ml-auto" 
      style="color: var(--swarm-error);" 
    />
  </div>
</template>
