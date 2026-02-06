<template>
  <div class="sessions-list">
    <div class="sessions-header">
      <h3 class="sessions-title">Running Sessions</h3>
      <button class="swarm-btn swarm-btn-ghost btn-icon-sm" @click="refresh" title="Refresh">
        <UIcon name="i-heroicons-arrow-path" class="w-3.5 h-3.5" :class="{ 'animate-spin': loading }" />
      </button>
    </div>
    
    <div v-if="loading && !sessions.length" class="sessions-empty">
      Loading sessions...
    </div>
    
    <div v-else-if="!sessions.length" class="sessions-empty">
      No active sessions
    </div>
    
    <div v-else class="sessions-grid">
      <div 
        v-for="session in sessions" 
        :key="session.key"
        class="session-card"
      >
        <div class="session-header">
          <span class="session-label">{{ session.label || 'Unnamed' }}</span>
          <span 
            class="session-status"
            :class="session.status === 'active' ? 'status-active' : 'status-inactive'"
          >
            {{ session.status }}
          </span>
        </div>
        <div class="session-meta">
          {{ session.model }} · {{ formatTokens(session.tokens) }} tokens
        </div>
        <div class="session-time">
          {{ formatTime(session.updatedAt) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Session {
  key: string
  label?: string
  status: string
  model: string
  updatedAt: number
  tokens: number
}

const sessions = ref<Session[]>([])
const loading = ref(false)

const formatTokens = (n: number) => n ? `${(n / 1000).toFixed(1)}k` : '0'
const formatTime = (ts: number) => {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleTimeString()
}

const refresh = async () => {
  loading.value = true
  try {
    const res = await $fetch<{ sessions: Session[] }>('/api/sessions')
    sessions.value = res.sessions || []
  } catch (e) {
    console.error('Failed to fetch sessions:', e)
  } finally {
    loading.value = false
  }
}

// Auto-refresh every 30 seconds
let interval: ReturnType<typeof setInterval>
onMounted(() => {
  refresh()
  interval = setInterval(refresh, 30000)
})
onUnmounted(() => clearInterval(interval))
</script>

<style scoped>
.sessions-list {
  padding: 16px;
}

.sessions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.sessions-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--swarm-text-primary);
}

.sessions-empty {
  font-size: 14px;
  color: var(--swarm-text-muted);
}

.sessions-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-card {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 8px;
  padding: 12px;
}

.session-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.session-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--swarm-text-primary);
}

.session-status {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
}

.status-active {
  color: var(--swarm-accent);
  background: var(--swarm-accent-bg);
}

.status-inactive {
  color: var(--swarm-text-muted);
  background: var(--swarm-bg-hover);
}

.session-meta {
  font-size: 12px;
  color: var(--swarm-text-muted);
  margin-bottom: 4px;
}

.session-time {
  font-size: 12px;
  color: var(--swarm-text-muted);
  opacity: 0.7;
}
.btn-icon-sm {
  padding: 4px !important;
}
</style>
