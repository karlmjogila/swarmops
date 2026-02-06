<script setup lang="ts">

interface ActivityEvent {
  id?: string
  timestamp: string
  type: string
  agent?: string
  taskId?: string
  message: string
  phaseNumber?: number
  workerId?: string
  workerBranch?: string
  success?: boolean
}

const props = defineProps<{
  events: ActivityEvent[]
}>()

const showAll = ref(false)
const COMPACT_COUNT = 10

const displayEvents = computed(() => {
  const sorted = [...props.events].reverse()
  return showAll.value ? sorted : sorted.slice(0, COMPACT_COUNT)
})

const hasMore = computed(() => props.events.length > COMPACT_COUNT)

type Severity = 'success' | 'info' | 'warning' | 'error'

function getSeverity(type: string): Severity {
  switch (type) {
    case 'complete': case 'phase-complete': case 'phase-merge': case 'worker-complete':
      return 'success'
    case 'spawn': case 'phase-change': case 'event':
      return 'info'
    case 'retry': case 'escalate':
      return 'warning'
    case 'error': case 'failed':
      return 'error'
    default: return 'info'
  }
}

function getColor(type: string): string {
  switch (getSeverity(type)) {
    case 'success': return 'var(--swarm-success)'
    case 'info': return 'var(--swarm-info)'
    case 'warning': return 'var(--swarm-warning)'
    case 'error': return 'var(--swarm-error)'
  }
}

function getBgColor(type: string): string {
  switch (getSeverity(type)) {
    case 'success': return 'var(--swarm-success-bg)'
    case 'info': return 'var(--swarm-info-bg)'
    case 'warning': return 'var(--swarm-warning-bg)'
    case 'error': return 'var(--swarm-error-bg)'
  }
}

function getIcon(type: string): string {
  switch (type) {
    case 'complete': case 'worker-complete': return 'i-heroicons-check-circle'
    case 'phase-complete': return 'i-heroicons-flag'
    case 'phase-merge': return 'i-heroicons-arrow-path-rounded-square'
    case 'spawn': return 'i-heroicons-sparkles'
    case 'phase-change': return 'i-heroicons-arrow-right-circle'
    case 'retry': return 'i-heroicons-arrow-path'
    case 'escalate': return 'i-heroicons-arrow-up-circle'
    case 'error': return 'i-heroicons-exclamation-circle'
    case 'failed': return 'i-heroicons-x-circle'
    case 'event': return 'i-heroicons-bell'
    default: return 'i-heroicons-information-circle'
  }
}

function getVerb(type: string): string {
  switch (type) {
    case 'spawn': return 'spawned'
    case 'complete': case 'worker-complete': return 'completed'
    case 'phase-complete': return 'finished phase'
    case 'phase-merge': return 'merged'
    case 'retry': return 'retrying'
    case 'escalate': return 'escalated'
    case 'error': case 'failed': return 'failed'
    default: return ''
  }
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now()
  const date = new Date(dateStr).getTime()
  const diff = now - date
  const secs = Math.floor(diff / 1000)
  if (secs < 60) return 'just now'
  const mins = Math.floor(secs / 60)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}
</script>

<template>
  <div class="activity-timeline">
    <div
      v-for="(event, index) in displayEvents"
      :key="event.id || index"
      class="timeline-entry"
    >
      <div class="timeline-rail">
        <div
          class="timeline-dot"
          :style="{ background: getColor(event.type), boxShadow: '0 0 0 3px ' + getBgColor(event.type) }"
        >
          <UIcon :name="getIcon(event.type)" class="w-3 h-3 text-white" />
        </div>
        <div v-if="index < displayEvents.length - 1" class="timeline-connector"></div>
      </div>

      <div class="timeline-body">
        <div class="timeline-header">
          <span v-if="event.agent" class="tl-agent">{{ event.agent }}</span>
          <span v-if="getVerb(event.type)" class="tl-verb">{{ getVerb(event.type) }}</span>
          <span v-if="event.taskId" class="tl-task">{{ event.taskId }}</span>
          <span class="tl-time">{{ formatRelativeTime(event.timestamp) }}</span>
        </div>
        <p class="tl-message">{{ event.message }}</p>
      </div>
    </div>

    <div v-if="displayEvents.length === 0" class="empty-state">
      <UIcon name="i-heroicons-clock" class="w-6 h-6" />
      <span>No activity yet</span>
    </div>

    <button
      v-if="hasMore"
      class="show-more-btn"
      @click="showAll = !showAll"
    >
      {{ showAll ? 'Show less' : `Show all ${events.length} events` }}
    </button>
  </div>
</template>

<style scoped>
.activity-timeline { position: relative; }
.timeline-entry { display: flex; gap: 14px; }
.timeline-rail {
  display: flex; flex-direction: column;
  align-items: center; flex-shrink: 0; width: 26px;
}
.timeline-dot {
  width: 26px; height: 26px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; z-index: 1;
}
.timeline-connector {
  width: 2px; flex: 1; min-height: 8px;
  background: var(--swarm-border-light);
}
.timeline-body { flex: 1; min-width: 0; padding-bottom: 18px; }
.timeline-header {
  display: flex; align-items: center; gap: 6px;
  flex-wrap: wrap; line-height: 1.5;
}
.tl-agent { font-size: 13px; font-weight: 600; color: var(--swarm-text-primary); }
.tl-verb { font-size: 13px; color: var(--swarm-text-muted); }
.tl-task {
  font-size: 11px; font-weight: 500;
  font-family: ui-monospace, SFMono-Regular, monospace;
  color: var(--swarm-accent);
  background: var(--swarm-accent-bg);
  padding: 1px 7px; border-radius: 4px;
}
.tl-time {
  font-size: 11px; color: var(--swarm-text-muted);
  opacity: 0.7; margin-left: auto; flex-shrink: 0;
}
.tl-message {
  font-size: 12px; color: var(--swarm-text-muted);
  margin: 2px 0 0; line-height: 1.4;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.empty-state {
  display: flex; align-items: center; justify-content: center;
  gap: 8px; padding: 32px; color: var(--swarm-text-muted); font-size: 14px;
}
.show-more-btn {
  display: block; width: 100%; padding: 10px;
  margin-top: 4px; font-size: 13px; font-weight: 500;
  color: var(--swarm-accent); background: var(--swarm-accent-bg);
  border: 1px solid var(--swarm-border-light);
  border-radius: 8px; cursor: pointer;
  transition: all 0.15s; text-align: center;
}
.show-more-btn:hover {
  background: var(--swarm-bg-hover); border-color: var(--swarm-accent);
}
</style>
