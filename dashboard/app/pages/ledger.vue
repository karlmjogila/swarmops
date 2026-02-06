<script setup lang="ts">
import { groupEntriesByProject, type LedgerEntry, type ProjectGroup } from '~/composables/ledger-utils'

useHead({ title: 'Ledger - SwarmOps' })

// Filters
const searchQuery = ref('')
const expandedProjects = ref<Set<string>>(new Set())

function toggleProject(name: string) {
  const s = new Set(expandedProjects.value)
  if (s.has(name)) s.delete(name); else s.add(name)
  expandedProjects.value = s
}
function expandAll() {
  expandedProjects.value = new Set(projectGroups.value.map(g => g.projectName))
}
function collapseAll() {
  expandedProjects.value = new Set()
}

// Fetch aggregated activity from all projects
const { data: rawEntries, pending, refresh } = useFetch<LedgerEntry[]>('/api/orchestrator/ledger', {
  default: () => [],
})

const filteredEntries = computed(() => {
  let entries = rawEntries.value || []
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    entries = entries.filter(e =>
      e.message?.toLowerCase().includes(q) ||
      e.agent?.toLowerCase().includes(q) ||
      e.projectName?.toLowerCase().includes(q) ||
      e.taskId?.toLowerCase().includes(q)
    )
  }
  return entries
})

const projectGroups = computed<ProjectGroup[]>(() => groupEntriesByProject(filteredEntries.value))
const totalEvents = computed(() => filteredEntries.value.length)

function clearFilters() {
  searchQuery.value = ''
}
const hasFilters = computed(() => searchQuery.value !== '')

// Delete ledger
const deleting = ref(false)
async function confirmDelete() {
  if (!confirm('Delete all ledger entries? This cannot be undone.')) return
  deleting.value = true
  try {
    await $fetch('/api/orchestrator/ledger', { method: 'DELETE' })
    await refresh()
  } catch (e) {
    console.error('Failed to delete ledger:', e)
    alert('Failed to delete ledger')
  } finally {
    deleting.value = false
  }
}

// ── Modal state ──
const showModal = ref(false)

// Close modal on Escape
if (import.meta.client) {
  onMounted(() => {
    document.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showModal.value) {
        showModal.value = false
      }
    })
  })
}
const modalEvent = ref<LedgerEntry | null>(null)
const modalProject = ref<string>('')
const taskLifecycle = ref<LedgerEntry[]>([])
const loadingLifecycle = ref(false)

async function openEventModal(ev: LedgerEntry, projectName: string) {
  modalEvent.value = ev
  modalProject.value = projectName
  showModal.value = true
  taskLifecycle.value = []

  // If the event has a taskId or workerId, load all related events
  const matchId = ev.taskId || ev.workerId
  if (matchId && projectName) {
    loadingLifecycle.value = true
    try {
      const data = await $fetch<LedgerEntry[]>(`/api/projects/${projectName}/task-history`)
      if (data) {
        taskLifecycle.value = data.filter(e =>
          e.taskId === matchId || e.workerId === matchId
        )
      }
    } catch { /* ignore */ }
    loadingLifecycle.value = false
  }
}

// Compute extra metadata fields to display
function getMetadataFields(ev: LedgerEntry): Array<{ label: string; value: string }> {
  const fields: Array<{ label: string; value: string }> = []
  if (ev.agent) fields.push({ label: 'Agent', value: ev.agent })
  if (ev.taskId) fields.push({ label: 'Task', value: ev.taskId })
  if (ev.workerId && ev.workerId !== ev.taskId) fields.push({ label: 'Worker', value: ev.workerId })
  if (ev.phaseNumber != null) fields.push({ label: 'Phase', value: String(ev.phaseNumber) })
  if (ev.runId) fields.push({ label: 'Run', value: ev.runId })
  if (ev.workerBranch) fields.push({ label: 'Branch', value: ev.workerBranch })
  if (ev.worktreePath) fields.push({ label: 'Worktree', value: ev.worktreePath })
  if (ev.mergeStatus) fields.push({ label: 'Merge', value: ev.mergeStatus })
  if (ev.attemptNumber != null) fields.push({ label: 'Attempt', value: `${ev.attemptNumber}/${ev.maxAttempts || '?'}` })
  if (ev.success != null) fields.push({ label: 'Success', value: ev.success ? 'Yes' : 'No' })
  if (ev.phaseComplete != null) fields.push({ label: 'Phase Complete', value: ev.phaseComplete ? 'Yes' : 'No' })
  if (ev.allSucceeded != null) fields.push({ label: 'All Succeeded', value: ev.allSucceeded ? 'Yes' : 'No' })
  if (ev.escalationId) fields.push({ label: 'Escalation', value: ev.escalationId })
  return fields
}

// ── Formatting helpers ──
function formatRelative(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '\u2014'
  try {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit'
    })
  } catch { return dateStr }
}

function formatTime(dateStr?: string): string {
  if (!dateStr) return '\u2014'
  try {
    return new Date(dateStr).toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    })
  } catch { return dateStr }
}

type Severity = 'success' | 'info' | 'warning' | 'error'

function getSeverity(type: string): Severity {
  switch (type) {
    case 'complete': case 'phase-complete': case 'phase-merge': case 'worker-complete':
      return 'success'
    case 'spawn': case 'phase-change': case 'event': case 'progress':
      return 'info'
    case 'retry': case 'escalate': case 'spawn-retry-scheduled': case 'escalation-created':
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
    case 'progress': return 'i-heroicons-document-text'
    case 'spawn-retry-scheduled': case 'retry': return 'i-heroicons-arrow-path'
    case 'escalate': case 'escalation-created': return 'i-heroicons-arrow-up-circle'
    case 'error': case 'failed': return 'i-heroicons-x-circle'
    case 'event': return 'i-heroicons-bell'
    default: return 'i-heroicons-information-circle'
  }
}
</script>

<template>
  <div class="ledger-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Ledger</h1>
        <p class="page-subtitle">Cross-project activity log</p>
      </div>
      <div class="header-actions">
        <UButton variant="ghost" size="sm" @click="() => refresh()" :loading="pending" title="Refresh">
          <UIcon name="i-heroicons-arrow-path" class="w-4 h-4" />
        </UButton>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-bar">
      <UInput
        v-model="searchQuery"
        placeholder="Search messages, agents, projects, tasks..."
        icon="i-heroicons-magnifying-glass"
        size="sm"
        class="search-input"
      />
      <UButton v-if="hasFilters" variant="ghost" size="sm" @click="clearFilters">
        <UIcon name="i-heroicons-x-mark" class="w-4 h-4" /> Clear
      </UButton>
      <div class="spacer" />
      <UButton
        variant="soft"
        color="red"
        size="sm"
        :loading="deleting"
        @click="confirmDelete"
      >
        <UIcon name="i-heroicons-trash" class="w-4 h-4" />
        Delete Ledger
      </UButton>
    </div>

    <!-- Summary bar -->
    <div class="summary-bar">
      <span class="summary-text" v-if="projectGroups.length">
        {{ projectGroups.length }} project{{ projectGroups.length !== 1 ? 's' : '' }} &middot;
        {{ totalEvents }} events
      </span>
      <span class="summary-text" v-else-if="!pending">No events match filters</span>
      <div v-if="projectGroups.length > 1" class="summary-actions">
        <button class="link-btn" @click="expandAll">Expand all</button>
        <button class="link-btn" @click="collapseAll">Collapse all</button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="pending && !rawEntries?.length" class="empty-card">
      <UIcon name="i-heroicons-arrow-path" class="w-5 h-5 animate-spin" />
      <span>Loading activity...</span>
    </div>

    <!-- Empty state -->
    <div v-else-if="!projectGroups.length" class="empty-card">
      <UIcon name="i-heroicons-document-text" class="w-8 h-8" />
      <span>No activity found</span>
    </div>

    <!-- Project groups -->
    <div v-else class="project-groups">
      <div
        v-for="group in projectGroups"
        :key="group.projectName"
        class="project-card"
        :class="{ expanded: expandedProjects.has(group.projectName) }"
      >
        <!-- Project header -->
        <div class="project-header" @click="toggleProject(group.projectName)">
          <div class="project-icon">
            <UIcon name="i-heroicons-folder" class="w-4 h-4" />
          </div>
          <div class="project-info">
            <span class="project-name">{{ group.projectName }}</span>
            <span class="project-meta">
              {{ group.entries.length }} events &middot; {{ formatRelative(group.latestTimestamp) }}
            </span>
          </div>
          <div class="stat-pills">
            <span v-if="group.stats.spawns" class="pill info">
              <UIcon name="i-heroicons-sparkles" class="w-3 h-3" />
              {{ group.stats.spawns }}
            </span>
            <span v-if="group.stats.completions" class="pill success">
              <UIcon name="i-heroicons-check" class="w-3 h-3" />
              {{ group.stats.completions }}
            </span>
            <span v-if="group.stats.errors" class="pill error">
              <UIcon name="i-heroicons-exclamation-triangle" class="w-3 h-3" />
              {{ group.stats.errors }}
            </span>
          </div>
          <UIcon
            :name="expandedProjects.has(group.projectName) ? 'i-heroicons-chevron-up' : 'i-heroicons-chevron-down'"
            class="w-5 h-5 chevron"
          />
        </div>

        <!-- Expanded event list -->
        <div v-if="expandedProjects.has(group.projectName)" class="event-list">
          <div
            v-for="ev in group.entries"
            :key="ev.id"
            class="event-row"
            @click="openEventModal(ev, group.projectName)"
          >
            <div
              class="event-dot"
              :style="{ background: getColor(ev.type), boxShadow: '0 0 0 3px ' + getBgColor(ev.type) }"
            >
              <UIcon :name="getIcon(ev.type)" class="w-3 h-3 dot-icon" />
            </div>
            <div class="event-body">
              <div class="event-top">
                <span v-if="ev.agent" class="ev-agent">{{ ev.agent }}</span>
                <span class="ev-type" :style="{ color: getColor(ev.type) }">{{ ev.type }}</span>
                <span v-if="ev.taskId" class="ev-task">{{ ev.taskId }}</span>
                <span class="ev-time">{{ formatDate(ev.timestamp) }}</span>
              </div>
              <p class="ev-msg">{{ ev.message }}</p>
            </div>
            <UIcon name="i-heroicons-chevron-right" class="w-4 h-4 row-arrow" />
          </div>
        </div>
      </div>
    </div>

    <!-- ════════ Event Detail Modal ════════ -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="showModal && modalEvent" class="modal-overlay" @click.self="showModal = false">
          <div class="modal-inner">
          <!-- Modal header -->
          <div class="modal-head">
            <div class="modal-head-left">
              <div
                class="modal-icon"
                :style="{ background: getBgColor(modalEvent.type), color: getColor(modalEvent.type) }"
              >
                <UIcon :name="getIcon(modalEvent.type)" class="w-5 h-5" />
              </div>
              <div>
                <h2 class="modal-title">{{ modalEvent.type }}</h2>
                <p class="modal-sub">{{ modalProject }} &middot; {{ formatDate(modalEvent.timestamp) }}</p>
              </div>
            </div>
            <UButton variant="ghost" size="sm" icon="i-heroicons-x-mark" @click="showModal = false" />
          </div>

          <!-- Message -->
          <div class="modal-section">
            <p class="modal-message">{{ modalEvent.message }}</p>
          </div>

          <!-- Metadata grid -->
          <div v-if="getMetadataFields(modalEvent).length" class="modal-section">
            <h3 class="section-title">Details</h3>
            <div class="meta-grid">
              <div v-for="field in getMetadataFields(modalEvent)" :key="field.label" class="meta-item">
                <span class="meta-label">{{ field.label }}</span>
                <span class="meta-value" :class="{ mono: ['Run','Branch','Worktree','Task','Worker','Escalation'].includes(field.label) }">
                  {{ field.value }}
                </span>
              </div>
            </div>
          </div>

          <!-- Error block -->
          <div v-if="modalEvent.error" class="modal-section">
            <h3 class="section-title error-title">Error</h3>
            <pre class="error-block">{{ modalEvent.error }}</pre>
          </div>

          <!-- Findings (from escalation events) -->
          <div v-if="modalEvent.findings" class="modal-section">
            <h3 class="section-title">Findings</h3>
            <pre class="json-block">{{ JSON.stringify(modalEvent.findings, null, 2) }}</pre>
          </div>

          <!-- Task Lifecycle Timeline -->
          <div v-if="taskLifecycle.length > 1 || loadingLifecycle" class="modal-section">
            <h3 class="section-title">
              Task Lifecycle
              <span v-if="taskLifecycle.length" class="lifecycle-count">{{ taskLifecycle.length }} events</span>
            </h3>

            <div v-if="loadingLifecycle" class="lifecycle-loading">
              <UIcon name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
              Loading history...
            </div>

            <div v-else class="lifecycle-timeline">
              <div
                v-for="(step, idx) in taskLifecycle"
                :key="step.id"
                class="lc-step"
                :class="{ active: step.id === modalEvent.id }"
              >
                <div class="lc-rail">
                  <div
                    class="lc-dot"
                    :style="{ background: getColor(step.type) }"
                  ></div>
                  <div v-if="idx < taskLifecycle.length - 1" class="lc-line"></div>
                </div>
                <div class="lc-content">
                  <div class="lc-header">
                    <span class="lc-type" :style="{ color: getColor(step.type) }">{{ step.type }}</span>
                    <span v-if="step.agent" class="lc-agent">{{ step.agent }}</span>
                    <span class="lc-time">{{ formatTime(step.timestamp) }}</span>
                  </div>
                  <p class="lc-msg">{{ step.message }}</p>
                  <p v-if="step.error" class="lc-error">{{ step.error.substring(0, 120) }}{{ step.error.length > 120 ? '...' : '' }}</p>
                  <div v-if="step.runId && step.runId !== modalEvent.runId" class="lc-run">
                    run: {{ step.runId }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Raw JSON toggle -->
          <details class="modal-section raw-section">
            <summary class="raw-toggle">Raw event data</summary>
            <pre class="json-block">{{ JSON.stringify(modalEvent, null, 2) }}</pre>
          </details>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.ledger-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--swarm-text-primary);
  margin-bottom: 2px;
}
.page-subtitle {
  font-size: 13px;
  color: var(--swarm-text-muted);
}
.header-actions { display: flex; gap: 8px; }

/* Filters */
.filters-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.search-input {
  flex: 1;
  min-width: 200px;
  max-width: 320px;
}
.spacer { flex: 1; }

.summary-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--swarm-text-muted);
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--swarm-border);
}
.summary-actions { display: flex; gap: 12px; }
.link-btn {
  background: none; border: none;
  font-size: 12px; font-weight: 500;
  color: var(--swarm-accent);
  cursor: pointer; padding: 0;
}
.link-btn:hover { text-decoration: underline; }

.empty-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 64px 24px;
  color: var(--swarm-text-muted);
  font-size: 14px;
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
}

/* Project groups */
.project-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.project-card {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.2s;
}
.project-card.expanded { border-color: var(--swarm-accent); }

.project-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  cursor: pointer;
  transition: background 0.15s;
}
.project-header:hover { background: var(--swarm-bg-hover); }

.project-icon {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  background: var(--swarm-accent-bg);
  color: var(--swarm-accent);
  flex-shrink: 0;
}
.project-info {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 2px;
}
.project-name {
  font-size: 15px; font-weight: 600;
  color: var(--swarm-text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.project-meta { font-size: 12px; color: var(--swarm-text-muted); }

.stat-pills { display: flex; gap: 6px; flex-shrink: 0; }
.pill {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 2px 8px; border-radius: 10px;
  font-size: 11px; font-weight: 600;
}
.pill.success { background: rgba(16,185,129,0.1); color: var(--swarm-success); }
.pill.info { background: rgba(59,130,246,0.1); color: var(--swarm-info); }
.pill.error { background: rgba(239,68,68,0.1); color: var(--swarm-error); }

.chevron { color: var(--swarm-text-muted); flex-shrink: 0; }

/* Event list */
.event-list {
  border-top: 1px solid var(--swarm-border);
  max-height: 500px;
  overflow-y: auto;
}
.event-row {
  display: flex;
  gap: 12px;
  padding: 10px 20px;
  border-bottom: 1px solid var(--swarm-border);
  cursor: pointer;
  transition: background 0.1s;
  align-items: flex-start;
}
.event-row:last-child { border-bottom: none; }
.event-row:hover { background: var(--swarm-bg-hover); }

.event-dot {
  width: 24px; height: 24px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; margin-top: 2px;
}
.dot-icon { color: white; }

.event-body { flex: 1; min-width: 0; }
.event-top {
  display: flex; align-items: center;
  gap: 6px; flex-wrap: wrap; margin-bottom: 2px;
}
.ev-agent { font-size: 13px; font-weight: 600; color: var(--swarm-text-primary); }
.ev-type { font-size: 11px; font-weight: 500; }
.ev-task {
  font-size: 11px; font-weight: 500;
  font-family: ui-monospace, monospace;
  color: var(--swarm-accent);
  background: var(--swarm-accent-bg);
  padding: 1px 6px; border-radius: 4px;
}
.ev-time {
  font-size: 11px; color: var(--swarm-text-muted);
  opacity: 0.7; margin-left: auto; flex-shrink: 0;
}
.ev-msg {
  font-size: 12px; color: var(--swarm-text-muted);
  margin: 0; line-height: 1.4;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.row-arrow {
  color: var(--swarm-text-muted);
  opacity: 0;
  transition: opacity 0.15s;
  flex-shrink: 0;
  margin-top: 6px;
}
.event-row:hover .row-arrow { opacity: 0.6; }

/* ════════ Modal ════════ */



/* Error & JSON blocks */

/* Modal overlay & transitions */

@media (max-width: 768px) {
  .ledger-page { padding: 16px; }
  .filters-bar { flex-direction: column; align-items: stretch; }
  .search-input { max-width: none; }
  .stat-pills { display: none; }
  .event-row { padding: 10px 14px; }
}
</style>

<style>
/* Modal styles (unscoped for Teleport) */
.modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}
.modal-head-left {
  display: flex; align-items: center; gap: 14px;
}
.modal-icon {
  width: 40px; height: 40px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.modal-title {
  font-size: 18px; font-weight: 700;
  color: var(--swarm-text-primary);
  text-transform: capitalize;
  margin: 0;
}
.modal-sub {
  font-size: 12px; color: var(--swarm-text-muted);
  margin: 2px 0 0 0;
}
.modal-section {
  margin-bottom: 20px;
}
.modal-message {
  font-size: 14px;
  color: var(--swarm-text-secondary);
  line-height: 1.5;
  margin: 0;
  padding: 12px 16px;
  background: var(--swarm-bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--swarm-border);
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--swarm-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0 0 10px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.error-title { color: var(--swarm-error); }
.lifecycle-count {
  font-size: 11px;
  font-weight: 500;
  color: var(--swarm-text-muted);
  background: var(--swarm-bg-hover);
  padding: 1px 8px;
  border-radius: 10px;
  text-transform: none;
  letter-spacing: 0;
}

/* Metadata grid */
.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.meta-item {
  display: flex; flex-direction: column; gap: 2px;
  padding: 8px 12px;
  background: var(--swarm-bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--swarm-border);
}
.meta-label {
  font-size: 10px; font-weight: 600;
  color: var(--swarm-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.meta-value {
  font-size: 13px;
  color: var(--swarm-text-secondary);
  word-break: break-all;
}
.meta-value.mono {
  font-family: ui-monospace, monospace;
  font-size: 11px;
}
.error-block {
  background: rgba(239,68,68,0.08);
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: 8px;
  padding: 12px;
  margin: 0;
  font-size: 12px;
  font-family: ui-monospace, monospace;
  color: var(--swarm-error);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
}
.json-block {
  background: var(--swarm-bg-secondary);
  border: 1px solid var(--swarm-border);
  border-radius: 8px;
  padding: 12px;
  margin: 0;
  font-size: 11px;
  font-family: ui-monospace, monospace;
  color: var(--swarm-text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
}

/* Lifecycle timeline */
.lifecycle-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 0;
  font-size: 13px;
  color: var(--swarm-text-muted);
}

.lifecycle-timeline {
  display: flex;
  flex-direction: column;
}
.lc-step {
  display: flex;
  gap: 12px;
  position: relative;
}
.lc-step.active .lc-content {
  background: var(--swarm-bg-hover);
  border-radius: 8px;
}
.lc-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 14px;
  flex-shrink: 0;
  padding-top: 6px;
}
.lc-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  z-index: 1;
}
.lc-line {
  width: 2px;
  flex: 1;
  background: var(--swarm-border);
  margin-top: 2px;
}
.lc-content {
  flex: 1;
  padding: 4px 10px 12px;
  min-width: 0;
}
.lc-header {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 2px;
}
.lc-type {
  font-size: 12px;
  font-weight: 600;
}
.lc-agent {
  font-size: 11px;
  color: var(--swarm-text-muted);
}
.lc-time {
  font-size: 11px;
  color: var(--swarm-text-muted);
  opacity: 0.6;
  margin-left: auto;
  font-family: ui-monospace, monospace;
}
.lc-msg {
  font-size: 12px;
  color: var(--swarm-text-muted);
  margin: 0;
  line-height: 1.4;
}
.lc-error {
  font-size: 11px;
  color: var(--swarm-error);
  margin: 4px 0 0;
  font-family: ui-monospace, monospace;
  line-height: 1.3;
}
.lc-run {
  font-size: 10px;
  color: var(--swarm-text-muted);
  font-family: ui-monospace, monospace;
  opacity: 0.5;
  margin-top: 2px;
}

/* Raw JSON toggle */
.raw-section {
  border-top: 1px solid var(--swarm-border);
  padding-top: 16px;
}
.raw-toggle {
  font-size: 12px;
  font-weight: 500;
  color: var(--swarm-text-muted);
  cursor: pointer;
  margin-bottom: 8px;
}
.raw-toggle:hover { color: var(--swarm-text-secondary); }
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 2rem;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  overflow-y: auto;
}
.modal-inner {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 16px;
  width: 100%;
  max-width: 640px;
  max-height: calc(100vh - 4rem);
  overflow-y: auto;
  padding: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-active .modal-inner,
.modal-fade-leave-active .modal-inner {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-from .modal-inner,
.modal-fade-leave-to .modal-inner {
  transform: scale(0.95);
  opacity: 0;
}
@media (max-width: 768px) {
  .modal-inner { padding: 16px; }
  .meta-grid { grid-template-columns: 1fr; }
}
</style>
