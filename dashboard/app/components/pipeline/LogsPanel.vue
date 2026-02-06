<script setup lang="ts">
import type { ExecutionStatus } from '~/types/pipeline'

interface LogMessage {
  role: 'user' | 'assistant' | 'tool'
  content: string
  timestamp?: string
  toolName?: string
}

interface Props {
  status?: ExecutionStatus
  sessionId?: string | null
  pollInterval?: number
}

const props = withDefaults(defineProps<Props>(), {
  status: 'idle',
  pollInterval: 2000,
})

const logs = ref<LogMessage[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const logsContainer = ref<HTMLElement | null>(null)

// Collapsible state - start collapsed when idle
const isExpanded = ref(false)
const showToolResults = ref(false)
const searchQuery = ref('')

// Auto-expand when running, collapse when idle
watch(() => props.status, (status) => {
  if (status === 'running') {
    isExpanded.value = true
  }
}, { immediate: true })

let pollTimer: ReturnType<typeof setInterval> | null = null

const filteredLogs = computed(() => {
  let result = logs.value
  
  if (!showToolResults.value) {
    result = result.filter(log => log.role !== 'tool')
  }
  
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(log => 
      log.content.toLowerCase().includes(query) ||
      log.toolName?.toLowerCase().includes(query)
    )
  }
  
  return result
})

const hasLogs = computed(() => logs.value.length > 0)

async function fetchLogs() {
  if (!props.sessionId) {
    logs.value = []
    return
  }
  
  loading.value = logs.value.length === 0
  error.value = null
  
  try {
    const data = await $fetch<{ logs: LogMessage[] }>(
      `/api/orchestrator/workers/${props.sessionId}/logs`
    )
    logs.value = data.logs
    
    // Auto-scroll when expanded
    if (isExpanded.value && logsContainer.value) {
      nextTick(() => {
        if (logsContainer.value) {
          logsContainer.value.scrollTop = logsContainer.value.scrollHeight
        }
      })
    }
  } catch (e: any) {
    if (e.statusCode === 404) {
      error.value = 'Session not found'
    } else {
      error.value = e.message || 'Failed to fetch logs'
    }
  } finally {
    loading.value = false
  }
}

function startPolling() {
  if (pollTimer) return
  fetchLogs()
  pollTimer = setInterval(fetchLogs, props.pollInterval)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function getStatusColor(): string {
  switch (props.status) {
    case 'running': return 'var(--swarm-info)'
    case 'completed': return 'var(--swarm-success)'
    case 'error': return 'var(--swarm-error)'
    case 'pending': return 'var(--swarm-warning)'
    default: return 'var(--swarm-text-muted)'
  }
}

function getStatusText(): string {
  switch (props.status) {
    case 'running': return 'Running'
    case 'completed': return 'Completed'
    case 'error': return 'Error'
    case 'pending': return 'Pending'
    default: return 'Idle'
  }
}

function formatTimestamp(ts?: string): string {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  } catch {
    return ''
  }
}

watch(() => props.status, (status) => {
  if (status === 'running') {
    startPolling()
  } else {
    stopPolling()
    if (props.sessionId) {
      fetchLogs()
    }
  }
}, { immediate: true })

watch(() => props.sessionId, () => {
  logs.value = []
  if (props.status === 'running') {
    startPolling()
  } else if (props.sessionId) {
    fetchLogs()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="logs-panel" :class="{ expanded: isExpanded, 'has-logs': hasLogs }">
    <!-- Collapsed header bar -->
    <button class="panel-header" @click="isExpanded = !isExpanded">
      <div class="header-left">
        <UIcon name="i-heroicons-document-text" class="w-4 h-4" />
        <span class="header-title">Logs</span>
        <span class="status-indicator">
          <span class="status-dot" :style="{ backgroundColor: getStatusColor() }" />
          {{ getStatusText() }}
        </span>
        <span v-if="hasLogs" class="log-count">{{ logs.length }}</span>
      </div>
      <div class="header-right">
        <span v-if="status === 'running'" class="streaming-badge">
          <span class="streaming-dot" />
          Live
        </span>
        <UIcon 
          :name="isExpanded ? 'i-heroicons-chevron-up' : 'i-heroicons-chevron-down'" 
          class="w-4 h-4 chevron" 
        />
      </div>
    </button>

    <!-- Expanded content -->
    <Transition name="expand">
      <div v-if="isExpanded" class="panel-content">
        <!-- Toolbar -->
        <div class="panel-toolbar">
          <UInput
            v-model="searchQuery"
            placeholder="Search logs..."
            icon="i-heroicons-magnifying-glass"
            size="xs"
            class="search-input"
          />
          <label class="toggle-label">
            <input v-model="showToolResults" type="checkbox" class="toggle-checkbox" />
            <span>Show tool results</span>
          </label>
          <UButton variant="ghost" size="xs" @click="fetchLogs">
            <UIcon name="i-heroicons-arrow-path" class="w-3 h-3" />
            Refresh
          </UButton>
        </div>

        <!-- Logs container -->
        <div ref="logsContainer" class="logs-container">
          <div v-if="loading" class="state-message">
            <UIcon name="i-heroicons-arrow-path" class="w-5 h-5 animate-spin" />
            <span>Loading...</span>
          </div>

          <div v-else-if="error" class="state-message error">
            <UIcon name="i-heroicons-exclamation-triangle" class="w-5 h-5" />
            <span>{{ error }}</span>
          </div>

          <div v-else-if="!filteredLogs.length" class="state-message">
            <UIcon name="i-heroicons-document-text" class="w-5 h-5" />
            <span v-if="searchQuery">No matching logs</span>
            <span v-else-if="status === 'running'">Waiting for logs...</span>
            <span v-else>No logs available</span>
          </div>

          <div v-else class="log-entries">
            <div
              v-for="(log, index) in filteredLogs"
              :key="index"
              class="log-entry"
              :class="`log-${log.role}`"
            >
              <div class="log-meta">
                <span class="log-role">{{ log.role }}</span>
                <span v-if="log.toolName" class="log-tool">{{ log.toolName }}</span>
                <span v-if="log.timestamp" class="log-time">{{ formatTimestamp(log.timestamp) }}</span>
              </div>
              <pre class="log-content">{{ log.content }}</pre>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="panel-footer">
          <span class="entry-count">{{ filteredLogs.length }} entries</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.logs-panel {
  background: var(--swarm-bg-card, var(--swarm-bg-card));
  border: 1px solid var(--swarm-border, var(--swarm-border));
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s ease;
}

/* Header bar - always visible */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 10px 14px;
  background: var(--swarm-bg-hover, var(--swarm-bg-primary));
  border: none;
  cursor: pointer;
  transition: background 0.15s;
}

.panel-header:hover {
  background: var(--swarm-bg-card, var(--swarm-bg-card));
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--swarm-text-primary, var(--swarm-text-primary));
}

.header-title {
  font-size: 13px;
  font-weight: 600;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--swarm-text-muted, var(--swarm-text-muted));
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.log-count {
  background: var(--swarm-accent, var(--swarm-info));
  color: var(--swarm-bg, var(--swarm-bg-primary));
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 10px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--swarm-text-muted, var(--swarm-text-muted));
}

.streaming-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  font-weight: 500;
  color: var(--swarm-info);
  background: rgba(59, 130, 246, 0.15);
  padding: 2px 8px;
  border-radius: 10px;
}

.streaming-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #3b82f6;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.chevron {
  transition: transform 0.2s;
}

.expanded .chevron {
  transform: rotate(180deg);
}

/* Expanded content */
.panel-content {
  border-top: 1px solid var(--swarm-border, var(--swarm-border));
}

.panel-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--swarm-bg-card, var(--swarm-bg-card));
  border-bottom: 1px solid var(--swarm-border, var(--swarm-border));
}

.search-input {
  width: 180px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--swarm-text-muted, var(--swarm-text-muted));
  cursor: pointer;
}

.toggle-checkbox {
  width: 12px;
  height: 12px;
}

/* Logs container - fixed max height */
.logs-container {
  max-height: 200px;
  overflow-y: auto;
  background: var(--swarm-bg, var(--swarm-bg-primary));
}

.state-message {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: var(--swarm-text-muted, var(--swarm-text-muted));
  font-size: 12px;
}

.state-message.error {
  color: var(--swarm-error);
}

.log-entries {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.log-entry {
  padding: 8px 10px;
  background: var(--swarm-bg-card, var(--swarm-bg-card));
  border-radius: 6px;
  border-left: 2px solid var(--swarm-border, var(--swarm-border));
}

.log-entry.log-user {
  border-left-color: var(--swarm-success);
}

.log-entry.log-assistant {
  border-left-color: var(--swarm-info);
}

.log-entry.log-tool {
  border-left-color: var(--swarm-warning);
}

.log-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  font-size: 10px;
}

.log-role {
  font-weight: 600;
  text-transform: capitalize;
  color: var(--swarm-text-secondary, var(--swarm-text-secondary));
}

.log-tool {
  background: rgba(249, 226, 175, 0.15);
  color: var(--swarm-warning);
  padding: 1px 5px;
  border-radius: 3px;
  font-family: monospace;
}

.log-time {
  color: var(--swarm-text-muted, var(--swarm-text-muted));
  margin-left: auto;
}

.log-content {
  margin: 0;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--swarm-text-primary, var(--swarm-text-primary));
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.4;
}

.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: var(--swarm-bg-hover, var(--swarm-bg-primary));
  border-top: 1px solid var(--swarm-border, var(--swarm-border));
}

.entry-count {
  font-size: 11px;
  color: var(--swarm-text-muted, var(--swarm-text-muted));
}

/* Transition */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}

.expand-enter-to,
.expand-leave-from {
  max-height: 350px;
  opacity: 1;
}

/* Scrollbar */
.logs-container::-webkit-scrollbar {
  width: 6px;
}

.logs-container::-webkit-scrollbar-track {
  background: transparent;
}

.logs-container::-webkit-scrollbar-thumb {
  background: var(--swarm-border, var(--swarm-border));
  border-radius: 3px;
}
</style>
