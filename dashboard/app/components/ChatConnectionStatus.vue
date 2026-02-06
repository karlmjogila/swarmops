<script setup lang="ts">
const props = defineProps<{
  connected: boolean
  reconnecting?: boolean
}>()

const emit = defineEmits<{
  reconnect: []
}>()
</script>

<template>
  <div
    class="chat-connection-status"
    :class="{
      'is-connected': connected,
      'is-disconnected': !connected,
      'is-reconnecting': reconnecting
    }"
    :title="connected ? 'Connected' : 'Disconnected - Click to reconnect'"
    @click="!connected && emit('reconnect')"
  >
    <span class="status-indicator">
      <span v-if="connected" class="pulse" />
    </span>
    <span class="status-text">
      <template v-if="reconnecting">Reconnecting...</template>
      <template v-else-if="connected">Connected</template>
      <template v-else>Offline</template>
    </span>
    <UIcon 
      v-if="!connected && !reconnecting"
      name="i-heroicons-arrow-path" 
      class="reconnect-icon"
    />
  </div>
</template>

<style scoped>
.chat-connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.3px;
  transition: all 0.2s ease;
}

.is-connected {
  background: rgba(16, 185, 129, 0.1);
  color: var(--swarm-success);
}

.is-disconnected {
  background: rgba(239, 68, 68, 0.1);
  color: var(--swarm-error);
  cursor: pointer;
}

.is-disconnected:hover {
  background: rgba(239, 68, 68, 0.15);
}

.is-reconnecting {
  background: rgba(251, 191, 36, 0.1);
  color: var(--swarm-warning);
}

.status-indicator {
  position: relative;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.is-connected .status-indicator {
  background: var(--swarm-success);
}

.is-disconnected .status-indicator {
  background: var(--swarm-error);
}

.is-reconnecting .status-indicator {
  background: var(--swarm-warning);
  animation: blink 1s ease-in-out infinite;
}

.pulse {
  position: absolute;
  inset: -2px;
  border-radius: 50%;
  background: var(--swarm-success);
  opacity: 0.4;
  animation: pulse 2s ease-out infinite;
}

.reconnect-icon {
  width: 12px;
  height: 12px;
  margin-left: 2px;
}

@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 0.4;
  }
  70%, 100% {
    transform: scale(2);
    opacity: 0;
  }
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}
</style>
