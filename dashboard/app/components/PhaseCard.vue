<script setup lang="ts">
export interface PhaseTask {
  id: string
  title: string
  done: boolean
  working?: boolean
  activeAgent?: string
  completedAt?: string
}

export interface Phase {
  id: string
  number: number
  title: string
  status: 'done' | 'active' | 'next' | 'todo'
  tasks: PhaseTask[]
  summary?: string
}

const props = defineProps<{
  phase: Phase
}>()

const isExpanded = ref(props.phase.status === 'active' || props.phase.status === 'next')

const completedCount = computed(() => props.phase.tasks.filter(t => t.done).length)
const workingCount = computed(() => props.phase.tasks.filter(t => t.working).length)
const totalCount = computed(() => props.phase.tasks.length)
const progress = computed(() => totalCount.value > 0 ? (completedCount.value / totalCount.value) * 100 : 0)

const statusConfig = computed(() => {
  switch (props.phase.status) {
    case 'done':
      return { label: 'Complete', icon: 'i-heroicons-check-circle', color: 'var(--swarm-success)', bg: 'var(--swarm-success-bg)' }
    case 'active':
      return { label: 'In Progress', icon: 'i-heroicons-play-circle', color: 'var(--swarm-info)', bg: 'var(--swarm-info-bg)' }
    case 'next':
      return { label: 'Up Next', icon: 'i-heroicons-arrow-right-circle', color: 'var(--swarm-warning)', bg: 'var(--swarm-warning-bg)' }
    default:
      return { label: 'Planned', icon: 'i-heroicons-clock', color: 'var(--swarm-text-muted)', bg: 'var(--swarm-bg-hover)' }
  }
})

function formatRelativeTime(dateStr: string): string {
  const now = Date.now()
  const date = new Date(dateStr).getTime()
  const diff = now - date
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}
</script>

<template>
  <div
    class="phase-card"
    :class="[phase.status, { expanded: isExpanded }]"
  >
    <div class="card-header" @click="isExpanded = !isExpanded">
      <div class="phase-number" :style="{ background: statusConfig.bg, color: statusConfig.color }">
        {{ phase.number }}
      </div>

      <div class="phase-info">
        <div class="phase-title">{{ phase.title }}</div>
        <div class="phase-meta">
          <span class="task-count">{{ completedCount }}/{{ totalCount }} tasks</span>
          <span v-if="workingCount > 0" class="workers-badge">
            <span class="pulse-dot"></span>
            {{ workingCount }} active
          </span>
          <span v-else-if="phase.summary" class="phase-summary">&middot; {{ phase.summary }}</span>
        </div>
      </div>

      <div class="phase-status">
        <div
          class="status-badge"
          :style="{ background: statusConfig.bg, color: statusConfig.color }"
        >
          <UIcon :name="statusConfig.icon" class="w-4 h-4" />
          {{ statusConfig.label }}
        </div>
      </div>

      <UIcon
        :name="isExpanded ? 'i-heroicons-chevron-up' : 'i-heroicons-chevron-down'"
        class="w-5 h-5 expand-icon"
      />
    </div>

    <!-- Progress bar -->
    <div v-if="totalCount > 0" class="progress-bar">
      <div class="progress-fill" :style="{ width: `${progress}%` }" />
    </div>

    <!-- Expanded content -->
    <div v-if="isExpanded" class="card-content">
      <div class="task-list">
        <div
          v-for="task in phase.tasks"
          :key="task.id"
          class="task-item"
          :class="{ done: task.done, working: task.working }"
        >
          <span v-if="task.working" class="task-indicator">
            <span class="pulse-dot blue"></span>
          </span>
          <span v-else class="task-checkbox">{{ task.done ? '\u2713' : '\u25CB' }}</span>
          <span class="task-title">{{ task.title }}</span>
          <span v-if="task.working && task.activeAgent" class="agent-badge">
            <UIcon name="i-heroicons-cpu-chip" class="w-3 h-3" />
            {{ task.activeAgent }}
          </span>
          <span v-if="task.done && task.completedAt" class="completed-time">
            {{ formatRelativeTime(task.completedAt) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.phase-card {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s;
}
.phase-card.done { border-color: rgba(16, 185, 129, 0.3); }
.phase-card.active {
  border-color: rgba(59, 130, 246, 0.4);
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.1);
}
.phase-card.next { border-color: rgba(245, 158, 11, 0.3); }

.card-header {
  display: flex; align-items: center; gap: 14px;
  padding: 16px; cursor: pointer; transition: background 0.15s;
}
.card-header:hover { background: var(--swarm-bg-hover); }

.phase-number {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700; flex-shrink: 0;
}
.phase-info { flex: 1; min-width: 0; }
.phase-title {
  font-size: 15px; font-weight: 600;
  color: var(--swarm-text-primary); margin-bottom: 2px;
}
.phase-meta {
  font-size: 12px; color: var(--swarm-text-muted);
  display: flex; align-items: center; gap: 8px;
}
.task-count { font-weight: 500; }
.workers-badge {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; font-weight: 600; color: var(--swarm-info);
  background: var(--swarm-info-bg);
  padding: 2px 8px; border-radius: 10px;
}
.phase-summary { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.phase-status { flex-shrink: 0; }
.status-badge {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-radius: 8px;
  font-size: 12px; font-weight: 500;
}
.expand-icon { color: var(--swarm-text-muted); flex-shrink: 0; }

.progress-bar { height: 3px; background: var(--swarm-bg-hover); }
.progress-fill { height: 100%; background: var(--swarm-accent); transition: width 0.3s ease; }
.phase-card.done .progress-fill { background: #10b981; }
.phase-card.active .progress-fill { background: #3b82f6; }

.card-content { padding: 0 16px 16px; border-top: 1px solid var(--swarm-border); }
.task-list { padding-top: 12px; }
.task-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 0; font-size: 13px; color: var(--swarm-text-secondary);
}
.task-item + .task-item { border-top: 1px solid var(--swarm-border-light); }
.task-item.done { color: var(--swarm-text-muted); }
.task-item.done .task-title { text-decoration: line-through; }
.task-item.working { color: var(--swarm-text-primary); }
.task-checkbox { flex-shrink: 0; width: 18px; text-align: center; }
.task-item.done .task-checkbox { color: var(--swarm-success); }
.task-indicator {
  flex-shrink: 0; width: 18px;
  display: flex; align-items: center; justify-content: center;
}
.task-title {
  flex: 1; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.agent-badge {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; font-weight: 500; color: var(--swarm-info);
  background: var(--swarm-info-bg);
  padding: 2px 8px; border-radius: 6px; flex-shrink: 0;
}
.completed-time { font-size: 11px; color: var(--swarm-text-muted); flex-shrink: 0; }

/* Pulse animation */
.pulse-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #3b82f6; display: inline-block; position: relative;
}
.pulse-dot::before {
  content: ''; position: absolute; inset: -3px;
  border-radius: 50%; background: rgba(59, 130, 246, 0.4);
  animation: pulse-ring 1.5s ease-in-out infinite;
}
@keyframes pulse-ring {
  0% { transform: scale(0.8); opacity: 1; }
  100% { transform: scale(1.8); opacity: 0; }
}
</style>
