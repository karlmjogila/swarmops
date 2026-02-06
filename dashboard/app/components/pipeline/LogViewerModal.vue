<script setup lang="ts">
import type { ExecutionStatus } from '~/types/pipeline'

interface LogMessage {
  role: 'user' | 'assistant' | 'tool'
  content: string
  timestamp?: string
  toolName?: string
}

interface Props {
  modelValue: boolean
  nodeId: string
  nodeName: string
  sessionId?: string | null
  status: ExecutionStatus
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const isOpen = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const logs = ref<LogMessage[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const logsContainer = ref<HTMLElement | null>(null)
const autoScroll = ref(true)

// Filter state
const showToolResults = ref(false)
const searchQuery = ref('')

// Poll interval for streaming
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
    
    // Auto-scroll to bottom
    if (autoScroll.value) {
      nextTick(() => scrollToBottom())
    }
  } catch (e: any) {
    if (e.statusCode === 404) {
      error.value = 'Session logs not found. The session may still be initializing.'
    } else {
      error.value = e.message || 'Failed to fetch logs'
    }
  } finally {
    loading.value = false
  }
}

function scrollToBottom() {
  if (logsContainer.value) {
    logsContainer.value.scrollTop = logsContainer.value.scrollHeight
  }
}

function startPolling() {
  if (pollTimer) return
  
  fetchLogs()
  pollTimer = setInterval(fetchLogs, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function formatTimestamp(ts?: string): string {
  if (!ts) return ''
  try {
    const date = new Date(ts)
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  } catch {
    return ''
  }
}

function getRoleBadgeClass(role: string): string {
  switch (role) {
    case 'user': return 'badge-user'
    case 'assistant': return 'badge-assistant'
    case 'tool': return 'badge-tool'
    default: return ''
  }
}

function getRoleIcon(role: string): string {
  switch (role) {
    case 'user': return 'i-heroicons-user'
    case 'assistant': return 'i-heroicons-cpu-chip'
    case 'tool': return 'i-heroicons-wrench-screwdriver'
    default: return 'i-heroicons-chat-bubble-left'
  }
}

function getStatusColor(): string {
  switch (props.status) {
    case 'running': return '#3b82f6'
    case 'completed': return '#10b981'
    case 'error': return '#ef4444'
    case 'pending': return '#f59e0b'
    default: return '#6c7086'
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

// Handle scroll events for auto-scroll toggle
function onScroll() {
  if (!logsContainer.value) return
  
  const { scrollTop, scrollHeight, clientHeight } = logsContainer.value
  const isAtBottom = scrollHeight - scrollTop - clientHeight < 50
  autoScroll.value = isAtBottom
}

watch(isOpen, (open) => {
  if (open) {
    if (props.status === 'running') {
      startPolling()
    } else {
      fetchLogs()
    }
  } else {
    stopPolling()
  }
})

watch(() => props.status, (status) => {
  if (isOpen.value) {
    if (status === 'running') {
      startPolling()
    } else {
      stopPolling()
      fetchLogs()
    }
  }
})

watch(() => props.sessionId, () => {
  if (isOpen.value) {
    // Clear existing polling to prevent timer leak when sessionId changes
    stopPolling()
    
    // Reset logs for new session
    logs.value = []
    
    // Restart polling or fetch based on current status
    if (props.status === 'running') {
      startPolling()
    } else {
      fetchLogs()
    }
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <UModal v-model="isOpen" :ui="{ width: 'sm:max-w-4xl' }">
    <div class="log-viewer">
      <!-- Header -->
      <header class="log-header">
        <div class="header-info">
          <h2 class="header-title">
            <UIcon name="i-heroicons-document-text" class="w-5 h-5" />
            {{ nodeName }} Logs
          </h2>
          <div class="header-status">
            <span class="status-dot" :style="{ backgroundColor: getStatusColor() }" />
            <span class="status-text">{{ getStatusText() }}</span>
            <span v-if="status === 'running'" class="streaming-indicator">
              <span class="streaming-dot" />
              Live
            </span>
          </div>
        </div>
        <button type="button" class="close-btn" @click.stop="isOpen = false">
          <UIcon name="i-heroicons-x-mark" class="w-5 h-5" />
        </button>
      </header>

      <!-- Toolbar -->
      <div class="log-toolbar">
        <div class="toolbar-left">
          <UInput
            v-model="searchQuery"
            placeholder="Search logs..."
            icon="i-heroicons-magnifying-glass"
            size="sm"
            class="search-input"
          />
        </div>
        <div class="toolbar-right">
          <label class="toggle-label">
            <input v-model="showToolResults" type="checkbox" class="toggle-checkbox" />
            <span>Show tool results</span>
          </label>
          <UButton
            v-if="!autoScroll && status === 'running'"
            size="xs"
            variant="soft"
            @click="scrollToBottom(); autoScroll = true"
          >
            <UIcon name="i-heroicons-arrow-down" class="w-3 h-3" />
            Follow
          </UButton>
        </div>
      </div>

      <!-- Logs Container -->
      <div
        ref="logsContainer"
        class="logs-container"
        @scroll="onScroll"
      >
        <!-- Loading State -->
        <div v-if="loading" class="loading-state">
          <UIcon name="i-heroicons-arrow-path" class="w-6 h-6 animate-spin" />
          <span>Loading logs...</span>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="error-state">
          <UIcon name="i-heroicons-exclamation-triangle" class="w-6 h-6" />
          <span>{{ error }}</span>
          <UButton size="sm" variant="soft" @click="fetchLogs">
            Retry
          </UButton>
        </div>

        <!-- Empty State -->
        <div v-else-if="!filteredLogs.length" class="empty-state">
          <UIcon name="i-heroicons-document-text" class="w-8 h-8" />
          <span v-if="logs.length && searchQuery">No logs match your search</span>
          <span v-else-if="status === 'pending'">Waiting for execution to start...</span>
          <span v-else-if="status === 'running'">Waiting for logs...</span>
          <span v-else>No logs available</span>
        </div>

        <!-- Log Entries -->
        <div v-else class="log-entries">
          <div
            v-for="(log, index) in filteredLogs"
            :key="index"
            class="log-entry"
            :class="`log-entry--${log.role}`"
          >
            <div class="log-meta">
              <span class="log-badge" :class="getRoleBadgeClass(log.role)">
                <UIcon :name="getRoleIcon(log.role)" class="w-3 h-3" />
                <span v-if="log.role === 'tool' && log.toolName">{{ log.toolName }}</span>
                <span v-else>{{ log.role }}</span>
              </span>
              <span v-if="log.timestamp" class="log-timestamp">
                {{ formatTimestamp(log.timestamp) }}
              </span>
            </div>
            <pre class="log-content">{{ log.content }}</pre>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <footer class="log-footer">
        <div class="footer-stats">
          <span>{{ filteredLogs.length }} {{ filteredLogs.length === 1 ? 'entry' : 'entries' }}</span>
          <span v-if="searchQuery && filteredLogs.length !== logs.length" class="filtered-hint">
            ({{ logs.length }} total)
          </span>
        </div>
        <div class="footer-actions">
          <UButton variant="ghost" size="sm" @click="fetchLogs">
            <UIcon name="i-heroicons-arrow-path" class="w-4 h-4" />
            Refresh
          </UButton>
        </div>
      </footer>
    </div>
  </UModal>
</template>

<style scoped>
.log-viewer {
  display: flex;
  flex-direction: column;
  background: var(--swarm-bg-card, #1e1e2e);
  border-radius: 12px;
  overflow: hidden;
  max-height: 80vh;
}

/* Header */
.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--swarm-bg, #11111b);
  border-bottom: 1px solid var(--swarm-border, #313244);
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--swarm-text-primary, #cdd6f4);
  margin: 0;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--swarm-text-muted, #6c7086);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.streaming-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3b82f6;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  color: var(--swarm-text-muted, #6c7086);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
  z-index: 10;
  pointer-events: auto;
}

.close-btn:hover {
  background: var(--swarm-bg-hover, #181825);
  color: var(--swarm-text-primary, #cdd6f4);
}

/* Toolbar */
.log-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--swarm-bg-card, #1e1e2e);
  border-bottom: 1px solid var(--swarm-border, #313244);
  gap: 16px;
}

.toolbar-left {
  flex: 1;
  max-width: 300px;
}

.search-input {
  width: 100%;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--swarm-text-secondary, #a6adc8);
  cursor: pointer;
  user-select: none;
}

.toggle-checkbox {
  width: 14px;
  height: 14px;
  accent-color: var(--swarm-accent, #89b4fa);
  cursor: pointer;
}

/* Logs Container */
.logs-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  min-height: 300px;
  max-height: 500px;
  background: var(--swarm-bg, #11111b);
}

/* States */
.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px 24px;
  color: var(--swarm-text-muted, #6c7086);
  text-align: center;
}

.error-state {
  color: #ef4444;
}

/* Log Entries */
.log-entries {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-entry {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: var(--swarm-bg-card, #1e1e2e);
  border-radius: 8px;
  border-left: 3px solid var(--swarm-border, #313244);
}

.log-entry--user {
  border-left-color: #a6e3a1;
}

.log-entry--assistant {
  border-left-color: #89b4fa;
}

.log-entry--tool {
  border-left-color: #f9e2af;
}

.log-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.log-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-radius: 4px;
}

.badge-user {
  background: rgba(166, 227, 161, 0.15);
  color: #a6e3a1;
}

.badge-assistant {
  background: rgba(137, 180, 250, 0.15);
  color: #89b4fa;
}

.badge-tool {
  background: rgba(249, 226, 175, 0.15);
  color: #f9e2af;
}

.log-timestamp {
  font-size: 11px;
  color: var(--swarm-text-muted, #6c7086);
  font-family: monospace;
}

.log-content {
  margin: 0;
  font-size: 13px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: var(--swarm-text-primary, #cdd6f4);
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
}

/* Footer */
.log-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--swarm-bg-card, #1e1e2e);
  border-top: 1px solid var(--swarm-border, #313244);
}

.footer-stats {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--swarm-text-muted, #6c7086);
}

.filtered-hint {
  opacity: 0.7;
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Scrollbar */
.logs-container::-webkit-scrollbar {
  width: 8px;
}

.logs-container::-webkit-scrollbar-track {
  background: transparent;
}

.logs-container::-webkit-scrollbar-thumb {
  background: var(--swarm-border, #313244);
  border-radius: 4px;
}

.logs-container::-webkit-scrollbar-thumb:hover {
  background: var(--swarm-text-muted, #6c7086);
}
</style>
