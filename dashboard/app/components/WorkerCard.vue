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

const props = defineProps<{
  worker: Worker
}>()

const emit = defineEmits<{
  'view-logs': [worker: Worker]
  'terminate': [worker: Worker]
}>()

// Extract meaningful task name from taskName/taskId
// Handles formats like "build:fix-modal" -> "fix-modal"
// or "builder:project:task" -> "task"
const displayTaskName = computed(() => {
  const taskName = props.worker.taskName || props.worker.taskId
  if (!taskName) return null
  
  // If taskName contains colons, extract the meaningful part
  // Patterns: "role:task" or "role:project:task"
  const parts = taskName.split(':')
  
  // Skip known role prefixes to get the actual task
  const rolePrefixes = ['build', 'builder', 'reviewer', 'fixer', 'auditor', 'subagent', 'parallel', 'night']
  
  if (parts.length >= 2 && rolePrefixes.includes(parts[0].toLowerCase())) {
    // Return everything after the role prefix
    return parts.slice(1).join(':')
  }
  
  // If no known prefix, return as-is
  return taskName
})

function getStatusColor(status: string): string {
  switch (status) {
    case 'running': return '#10b981'
    case 'completed': return '#3b82f6'
    case 'idle': return '#f59e0b'
    case 'error': return '#ef4444'
    default: return 'var(--swarm-text-muted)'
  }
}

function getStatusBg(status: string): string {
  switch (status) {
    case 'running': return 'rgba(16, 185, 129, 0.1)'
    case 'completed': return 'rgba(59, 130, 246, 0.1)'
    case 'idle': return 'rgba(245, 158, 11, 0.1)'
    case 'error': return 'rgba(239, 68, 68, 0.1)'
    default: return 'var(--swarm-bg-hover)'
  }
}

function formatDuration(ms?: number): string {
  if (!ms) return '—'
  
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  }
  return `${seconds}s`
}

// Live duration counter
const liveDuration = ref(props.worker.duration || 0)
let intervalId: ReturnType<typeof setInterval> | null = null

function startDurationCounter() {
  if (props.worker.status === 'running' && props.worker.startedAt) {
    const startTime = new Date(props.worker.startedAt).getTime()
    intervalId = setInterval(() => {
      liveDuration.value = Date.now() - startTime
    }, 1000)
  }
}

function stopDurationCounter() {
  if (intervalId) {
    clearInterval(intervalId)
    intervalId = null
  }
}

onMounted(startDurationCounter)
onUnmounted(stopDurationCounter)

watch(() => props.worker.status, (newStatus) => {
  if (newStatus === 'running') {
    startDurationCounter()
  } else {
    stopDurationCounter()
    liveDuration.value = props.worker.duration || 0
  }
})

// Extract project name - use API value if available, otherwise parse from taskName
const projectName = computed(() => {
  // Use API-provided projectName if available
  if (props.worker.projectName) {
    return props.worker.projectName
  }
  
  // Otherwise try to parse from taskName (format: role:project-name or role:project-name:task-id)
  const task = props.worker.taskName
  if (!task) return null
  
  const parts = task.split(':')
  if (parts.length >= 2) {
    return parts[1] // project-name is the second part
  }
  return null
})
</script>

<template>
  <div 
    class="worker-card" 
    :class="{ 'is-running': worker.status === 'running' }"
    @click="emit('view-logs', worker)"
  >
    <div class="card-header">
      <div 
        class="status-indicator"
        :style="{ background: getStatusColor(worker.status) }"
      />
      <div class="worker-info">
        <h3 class="worker-role">{{ worker.roleName }}</h3>
        <p class="worker-id">{{ worker.id.slice(0, 8) }}</p>
      </div>
      <div 
        class="status-badge"
        :style="{ 
          color: getStatusColor(worker.status),
          background: getStatusBg(worker.status)
        }"
      >
        {{ worker.status }}
      </div>
    </div>

    <div class="card-body">
      <div v-if="projectName" class="info-row">
        <span class="info-label">Project</span>
        <span class="info-value project">{{ projectName }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Task</span>
        <span class="info-value task-name" :title="worker.taskId">{{ displayTaskName || 'None' }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Duration</span>
        <span class="info-value duration" :class="{ pulsing: worker.status === 'running' }">
          {{ formatDuration(worker.status === 'running' ? liveDuration : worker.duration) }}
        </span>
      </div>
    </div>

    <div class="card-actions">
      <button class="swarm-btn swarm-btn-ghost btn-sm" @click.stop="emit('view-logs', worker)">
        <UIcon name="i-heroicons-document-text" class="w-3.5 h-3.5" />
        Logs
      </button>
      <button 
        v-if="worker.status === 'running'"
        class="swarm-btn swarm-btn-danger btn-sm"
        @click.stop="emit('terminate', worker)"
      >
        <UIcon name="i-heroicons-stop" class="w-3.5 h-3.5" />
        Stop
      </button>
    </div>
  </div>
</template>

<style scoped>
.worker-card {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s;
  cursor: pointer;
}

.worker-card:hover {
  border-color: var(--swarm-accent);
}

.worker-card.is-running {
  border-color: rgba(16, 185, 129, 0.4);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--swarm-border);
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.worker-card.is-running .status-indicator {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.1); }
}

.worker-info {
  flex: 1;
  min-width: 0;
}

.worker-role {
  font-size: 14px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin: 0;
}

.worker-id {
  font-size: 11px;
  font-family: monospace;
  color: var(--swarm-text-muted);
  margin: 0;
}

.status-badge {
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 4px;
}

.card-body {
  padding: 14px 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-label {
  font-size: 12px;
  color: var(--swarm-text-muted);
}

.info-value {
  font-size: 12px;
  font-weight: 500;
  color: var(--swarm-text-secondary);
}

.info-value.duration.pulsing {
  color: #10b981;
}

.info-value.project {
  color: var(--swarm-accent, #8b5cf6);
  font-weight: 600;
}

.info-value.task-name {
  font-family: monospace;
  font-size: 11px;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-actions {
  display: flex;
  gap: 8px;
  padding: 10px 16px;
  background: var(--swarm-bg-hover);
  border-top: 1px solid var(--swarm-border);
}
.btn-sm {
  padding: 4px 10px !important;
  font-size: 12px !important;
}
</style>
