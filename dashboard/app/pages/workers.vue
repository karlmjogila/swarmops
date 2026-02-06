<script setup lang="ts">
interface Worker {
  id: string
  roleId: string
  roleName: string
  taskId?: string
  taskName?: string
  projectName?: string
  status: 'idle' | 'running' | 'completed' | 'error'
  startedAt?: string
  duration?: number
}

useHead({
  title: 'Workers - SwarmOps'
})

const { data: workers, pending, refresh } = useFetch<Worker[]>('/api/orchestrator/workers', {
  default: () => [],
})

// WebSocket for live updates
const { onWorkerUpdate } = useWebSocket()

let unsubscribe: (() => void) | null = null

onMounted(() => {
  unsubscribe = onWorkerUpdate((updatedWorker) => {
    if (workers.value) {
      const index = workers.value.findIndex(w => w.id === updatedWorker.id)
      if (index !== -1) {
        workers.value[index] = updatedWorker
      } else {
        workers.value.push(updatedWorker)
      }
    }
  })
})

onUnmounted(() => {
  if (unsubscribe) {
    unsubscribe()
  }
})

// Logs modal
const showLogsModal = ref(false)
const selectedWorker = ref<Worker | null>(null)
interface LogEntry {
  role: string
  content: string
  timestamp?: string
  toolName?: string
}
const logs = ref<LogEntry[]>([])
const loadingLogs = ref(false)

async function viewLogs(worker: Worker) {
  selectedWorker.value = worker
  loadingLogs.value = true
  showLogsModal.value = true
  
  try {
    // URL-encode session key since it contains colons
    const encodedId = encodeURIComponent(worker.id)
    const response = await $fetch<{ logs: LogEntry[] }>(`/api/orchestrator/workers/${encodedId}/logs`)
    logs.value = response.logs || []
  } catch (err) {
    logs.value = ['Failed to load logs']
  } finally {
    loadingLogs.value = false
  }
}

// Terminate confirmation
const showTerminateConfirm = ref(false)
const workerToTerminate = ref<Worker | null>(null)
const terminating = ref(false)

function confirmTerminate(worker: Worker) {
  workerToTerminate.value = worker
  showTerminateConfirm.value = true
}

async function terminateWorker() {
  if (!workerToTerminate.value) return
  
  terminating.value = true
  try {
    await $fetch(`/api/orchestrator/workers/${workerToTerminate.value.id}/terminate`, {
      method: 'POST',
    })
    showTerminateConfirm.value = false
    workerToTerminate.value = null
    refresh()
  } catch (err) {
    console.error('Failed to terminate worker:', err)
  } finally {
    terminating.value = false
  }
}

// Stats
const stats = computed(() => {
  const all = workers.value || []
  return {
    total: all.length,
    running: all.filter(w => w.status === 'running').length,
    completed: all.filter(w => w.status === 'completed').length,
    idle: all.filter(w => w.status === 'idle').length,
    error: all.filter(w => w.status === 'error').length,
  }
})

// Filter
const statusFilter = ref<string>('all')

const filteredWorkers = computed(() => {
  if (statusFilter.value === 'all') return workers.value
  return workers.value?.filter(w => w.status === statusFilter.value) || []
})

// Group workers by project
const groupedWorkers = computed(() => {
  const groups = new Map<string, Worker[]>()
  
  for (const worker of filteredWorkers.value || []) {
    const projectName = worker.projectName || 'Other'
    if (!groups.has(projectName)) {
      groups.set(projectName, [])
    }
    groups.get(projectName)!.push(worker)
  }
  
  // Sort groups: projects with running workers first, then alphabetically
  return Array.from(groups.entries())
    .sort((a, b) => {
      const aRunning = a[1].some(w => w.status === 'running')
      const bRunning = b[1].some(w => w.status === 'running')
      if (aRunning && !bRunning) return -1
      if (!aRunning && bRunning) return 1
      return a[0].localeCompare(b[0])
    })
})

// Check if we have multiple projects (to show grouping)
const hasMultipleProjects = computed(() => groupedWorkers.value.length > 1)
</script>

<template>
  <div class="workers-page">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">Workers</h1>
        <p class="page-subtitle">Monitor active agent workers in real-time</p>
      </div>
    </div>

    <!-- Stats bar (clickable filters) -->
    <div class="stats-bar">
      <button 
        class="stat-item" 
        :class="{ active: statusFilter === 'all' }"
        @click="statusFilter = 'all'"
      >
        <span class="stat-value">{{ stats.total }}</span>
        <span class="stat-label">Total</span>
      </button>
      <button 
        class="stat-item running" 
        :class="{ active: statusFilter === 'running' }"
        @click="statusFilter = 'running'"
      >
        <span class="stat-value">{{ stats.running }}</span>
        <span class="stat-label">Running</span>
      </button>
      <button 
        class="stat-item completed" 
        :class="{ active: statusFilter === 'completed' }"
        @click="statusFilter = 'completed'"
      >
        <span class="stat-value">{{ stats.completed }}</span>
        <span class="stat-label">Completed</span>
      </button>
      <button 
        class="stat-item idle" 
        :class="{ active: statusFilter === 'idle' }"
        @click="statusFilter = 'idle'"
      >
        <span class="stat-value">{{ stats.idle }}</span>
        <span class="stat-label">Idle</span>
      </button>
      <button 
        class="stat-item error" 
        :class="{ active: statusFilter === 'error' }"
        @click="statusFilter = 'error'"
      >
        <span class="stat-value">{{ stats.error }}</span>
        <span class="stat-label">Error</span>
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="pending && !workers?.length" class="loading-state">
      <UIcon name="i-heroicons-cpu-chip" class="w-8 h-8 animate-pulse" />
      <p>Loading workers...</p>
    </div>

    <!-- Empty state -->
    <UiEmptyState
      v-else-if="!workers?.length"
      icon="i-heroicons-cpu-chip"
      title="No active workers"
      description="Workers will appear here when pipelines are running"
    />

    <!-- Workers grouped by project -->
    <div v-else class="workers-container">
      <!-- Show groups when multiple projects -->
      <template v-if="hasMultipleProjects">
        <div 
          v-for="[projectName, projectWorkers] in groupedWorkers" 
          :key="projectName"
          class="project-group"
        >
          <div class="project-header">
            <h2 class="project-name">{{ projectName }}</h2>
            <span class="project-count">{{ projectWorkers.length }} worker{{ projectWorkers.length !== 1 ? 's' : '' }}</span>
          </div>
          <div class="workers-grid">
            <WorkerCard
              v-for="worker in projectWorkers"
              :key="worker.id"
              :worker="worker"
              @view-logs="viewLogs"
              @terminate="confirmTerminate"
            />
          </div>
        </div>
      </template>
      
      <!-- Single flat grid when only one project -->
      <div v-else class="workers-grid">
        <WorkerCard
          v-for="worker in filteredWorkers"
          :key="worker.id"
          :worker="worker"
          @view-logs="viewLogs"
          @terminate="confirmTerminate"
        />
      </div>
    </div>

    <!-- Logs Modal -->
    <AppModal 
      v-model:open="showLogsModal" 
      :title="`Worker Logs: ${selectedWorker?.roleName || ''}`"
      size="2xl"
    >
      <div class="logs-container">
        <div v-if="loadingLogs" class="logs-loading">
          <UIcon name="i-heroicons-arrow-path" class="w-5 h-5 animate-spin" />
          <span>Loading logs...</span>
        </div>
        <div v-else-if="!logs.length" class="logs-empty">
          No logs available
        </div>
        <div v-else class="logs-content">
          <div v-for="(log, idx) in logs" :key="idx" class="log-entry" :class="`log-${log.role}`">
            <div class="log-header">
              <span class="log-role">{{ log.role }}</span>
              <span v-if="log.toolName" class="log-tool">{{ log.toolName }}</span>
              <span v-if="log.timestamp" class="log-time">{{ new Date(log.timestamp).toLocaleTimeString() }}</span>
            </div>
            <pre class="log-content">{{ log.content }}</pre>
          </div>
        </div>
      </div>
    </AppModal>

    <!-- Terminate Confirmation Modal -->
    <AppModal v-model:open="showTerminateConfirm" title="Terminate Worker">
      <div class="text-center py-4">
        <UIcon name="i-heroicons-exclamation-triangle" class="w-12 h-12 text-amber-500 mx-auto mb-4" />
        <p>Are you sure you want to terminate worker <strong>{{ workerToTerminate?.roleName }}</strong>?</p>
        <p class="text-sm text-muted mt-2">This will stop any running task immediately.</p>
      </div>
      
      <template #footer>
        <div class="flex justify-end gap-2">
          <button class="swarm-btn swarm-btn-ghost" @click="showTerminateConfirm = false">Cancel</button>
          <button class="swarm-btn swarm-btn-danger" :disabled="terminating" @click="terminateWorker">
            <UIcon v-if="terminating" name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
            Terminate
          </button>
        </div>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.workers-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--swarm-text-muted);
}

.stats-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px;
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 24px;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.stat-item:hover {
  background: var(--swarm-bg-hover);
}

.stat-item.active {
  background: var(--swarm-accent-bg);
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--swarm-text-primary);
}

.stat-label {
  font-size: 12px;
  color: var(--swarm-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.stat-item.running .stat-value {
  color: #10b981;
}

.stat-item.running.active {
  background: rgba(16, 185, 129, 0.1);
}

.stat-item.completed .stat-value {
  color: #3b82f6;
}

.stat-item.completed.active {
  background: rgba(59, 130, 246, 0.1);
}

.stat-item.idle .stat-value {
  color: #f59e0b;
}

.stat-item.idle.active {
  background: rgba(245, 158, 11, 0.1);
}

.stat-item.error .stat-value {
  color: #ef4444;
}

.stat-item.error.active {
  background: rgba(239, 68, 68, 0.1);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  text-align: center;
  color: var(--swarm-text-muted);
  gap: 12px;
}

.empty-state h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin: 0;
}

.empty-state p {
  font-size: 14px;
  margin: 0;
}

.workers-container {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.project-group {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 16px;
  padding: 20px;
}

.project-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--swarm-border);
}

.project-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--swarm-accent);
  margin: 0;
}

.project-count {
  font-size: 12px;
  color: var(--swarm-text-muted);
  background: var(--swarm-bg-hover);
  padding: 4px 10px;
  border-radius: 12px;
}

.workers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.modal-content {
  padding: 20px;
  min-width: 400px;
  max-width: 500px;
}

.modal-content.wide {
  max-width: 700px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin: 0;
}

.logs-container {
  background: var(--swarm-bg-secondary);
  border: 1px solid var(--swarm-border);
  border-radius: 8px;
  max-height: 60vh;
  overflow-y: auto;
}

.logs-loading,
.logs-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px;
  color: var(--swarm-text-muted);
  font-size: 13px;
}

.logs-content {
  padding: 16px;
}

.log-entry {
  margin-bottom: 16px;
  padding: 12px;
  border-radius: 8px;
  background: var(--swarm-bg-hover);
}

.log-entry.log-user {
  border-left: 3px solid var(--swarm-accent);
}

.log-entry.log-assistant {
  border-left: 3px solid #10b981;
}

.log-entry.log-tool {
  border-left: 3px solid #f59e0b;
}

.log-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
}

.log-role {
  font-weight: 600;
  text-transform: capitalize;
  color: var(--swarm-text-primary);
}

.log-tool {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 11px;
}

.log-time {
  color: var(--swarm-text-muted);
  margin-left: auto;
}

.log-content {
  margin: 0;
  font-size: 13px;
  font-family: monospace;
  color: var(--swarm-text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

.delete-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
  padding: 20px 0;
}

.delete-message p {
  margin: 0;
  color: var(--swarm-text-secondary);
}

.delete-message .text-muted {
  color: var(--swarm-text-muted);
}

@media (max-width: 640px) {
  .workers-page {
    padding: 16px;
  }
  
  .stats-bar {
    flex-wrap: wrap;
  }
  
  .stat-item {
    flex: 1;
    min-width: 80px;
    border-right: none;
  }
  
  .workers-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-content {
    min-width: unset;
    width: 100%;
  }
}
</style>
