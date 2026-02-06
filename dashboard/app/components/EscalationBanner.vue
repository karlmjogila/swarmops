<script setup lang="ts">
interface Escalation {
  id: string
  runId: string
  pipelineId: string
  pipelineName: string
  stepOrder: number
  roleId: string
  roleName: string
  taskId?: string
  error: string
  attemptCount: number
  maxAttempts: number
  lastAttemptAt: string
  status: 'open' | 'resolved' | 'dismissed'
  severity: 'low' | 'medium' | 'high' | 'critical'
  createdAt: string
  resolvedAt?: string
  resolvedBy?: string
  resolution?: string
  projectDir?: string
  notes?: string
}

const props = defineProps<{
  projectName: string
  pipelineId?: string
  refreshInterval?: number
}>()

const emit = defineEmits<{
  'escalation-resolved': [escalation: Escalation]
  'escalation-dismissed': [escalation: Escalation]
}>()

const toast = useToast()
const escalations = ref<Escalation[]>([])
const loading = ref(false)
const actionLoading = ref<string | null>(null)
const expandedId = ref<string | null>(null)
const showResolveModal = ref(false)
const selectedEscalation = ref<Escalation | null>(null)
const resolutionText = ref('')

const severityConfig = {
  low: { color: '#6b7280', bg: 'rgba(107, 114, 128, 0.1)', icon: 'i-heroicons-information-circle' },
  medium: { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)', icon: 'i-heroicons-exclamation-triangle' },
  high: { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)', icon: 'i-heroicons-exclamation-circle' },
  critical: { color: '#dc2626', bg: 'rgba(220, 38, 38, 0.15)', icon: 'i-heroicons-fire' }
}

const openEscalations = computed(() => escalations.value.filter(e => e.status === 'open'))
const hasEscalations = computed(() => openEscalations.value.length > 0)
const highestSeverity = computed(() => {
  if (!hasEscalations.value) return 'low'
  const severities = ['critical', 'high', 'medium', 'low'] as const
  for (const sev of severities) {
    if (openEscalations.value.some(e => e.severity === sev)) return sev
  }
  return 'low'
})

async function fetchEscalations() {
  loading.value = true
  try {
    const params = new URLSearchParams({ status: 'open' })
    if (props.pipelineId) params.append('pipelineId', props.pipelineId)
    
    const response = await $fetch<{ escalations: Escalation[] }>(`/api/escalations?${params}`)
    escalations.value = response.escalations
  } catch (err) {
    console.error('Failed to fetch escalations:', err)
  } finally {
    loading.value = false
  }
}

function openResolveModal(escalation: Escalation) {
  selectedEscalation.value = escalation
  resolutionText.value = ''
  showResolveModal.value = true
}

async function resolveEscalation() {
  if (!selectedEscalation.value || !resolutionText.value.trim()) return
  
  actionLoading.value = selectedEscalation.value.id
  try {
    await $fetch(`/api/escalations/${selectedEscalation.value.id}/resolve`, {
      method: 'POST',
      body: { resolution: resolutionText.value.trim() }
    })
    
    toast.add({
      title: 'Escalation Resolved',
      description: `${selectedEscalation.value.roleName} issue marked as resolved`,
      icon: 'i-heroicons-check-circle',
      color: 'success',
      duration: 4000
    })
    
    emit('escalation-resolved', selectedEscalation.value)
    showResolveModal.value = false
    await fetchEscalations()
  } catch (err) {
    toast.add({
      title: 'Failed to resolve',
      description: err instanceof Error ? err.message : 'Unknown error',
      icon: 'i-heroicons-x-circle',
      color: 'error',
      duration: 5000
    })
  } finally {
    actionLoading.value = null
  }
}

async function dismissEscalation(escalation: Escalation) {
  actionLoading.value = escalation.id
  try {
    await $fetch(`/api/escalations/${escalation.id}/dismiss`, {
      method: 'POST',
      body: { reason: 'Dismissed from dashboard' }
    })
    
    toast.add({
      title: 'Escalation Dismissed',
      icon: 'i-heroicons-minus-circle',
      color: 'neutral',
      duration: 3000
    })
    
    emit('escalation-dismissed', escalation)
    await fetchEscalations()
  } catch (err) {
    toast.add({
      title: 'Failed to dismiss',
      description: err instanceof Error ? err.message : 'Unknown error',
      icon: 'i-heroicons-x-circle',
      color: 'error',
      duration: 5000
    })
  } finally {
    actionLoading.value = null
  }
}

function toggleExpand(id: string) {
  expandedId.value = expandedId.value === id ? null : id
}

function formatTime(isoString: string): string {
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}

// Fetch on mount
onMounted(fetchEscalations)

// Auto-refresh if interval provided
let refreshTimer: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  if (props.refreshInterval && props.refreshInterval > 0) {
    refreshTimer = setInterval(fetchEscalations, props.refreshInterval)
  }
})
onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})

// Refetch when projectName changes
watch(() => props.projectName, fetchEscalations)
watch(() => props.pipelineId, fetchEscalations)
</script>

<template>
  <div v-if="hasEscalations" class="escalation-banner" :class="[highestSeverity]">
    <!-- Header -->
    <div class="banner-header">
      <div class="header-icon" :style="{ background: severityConfig[highestSeverity].bg }">
        <UIcon 
          :name="severityConfig[highestSeverity].icon" 
          class="w-5 h-5"
          :style="{ color: severityConfig[highestSeverity].color }"
        />
      </div>
      <div class="header-content">
        <div class="header-title">
          {{ openEscalations.length }} Open Escalation{{ openEscalations.length > 1 ? 's' : '' }}
        </div>
        <div class="header-subtitle">
          Tasks failed after max retries and need attention
        </div>
      </div>
    </div>

    <!-- Escalation List -->
    <div class="escalation-list">
      <div 
        v-for="esc in openEscalations"
        :key="esc.id"
        class="escalation-item"
        :class="{ expanded: expandedId === esc.id }"
      >
        <div class="item-header" @click="toggleExpand(esc.id)">
          <div class="item-severity">
            <div 
              class="severity-dot"
              :style="{ background: severityConfig[esc.severity].color }"
            />
          </div>
          <div class="item-info">
            <div class="item-role">{{ esc.roleName }}</div>
            <div class="item-meta">
              Step {{ esc.stepOrder }} · {{ esc.attemptCount }}/{{ esc.maxAttempts }} attempts · {{ formatTime(esc.createdAt) }}
            </div>
          </div>
          <UIcon 
            name="i-heroicons-chevron-down" 
            class="expand-icon w-4 h-4"
            :class="{ rotated: expandedId === esc.id }"
          />
        </div>

        <div v-if="expandedId === esc.id" class="item-details">
          <div class="error-box">
            <div class="error-label">Error</div>
            <pre class="error-text">{{ esc.error }}</pre>
          </div>

          <div v-if="esc.taskId" class="detail-row">
            <span class="detail-label">Task ID:</span>
            <code class="detail-value">{{ esc.taskId }}</code>
          </div>

          <div class="item-actions">
            <button
              class="action-btn resolve"
              :disabled="actionLoading === esc.id"
              @click.stop="openResolveModal(esc)"
            >
              <UIcon 
                v-if="actionLoading === esc.id" 
                name="i-heroicons-arrow-path" 
                class="w-4 h-4 animate-spin" 
              />
              <UIcon v-else name="i-heroicons-check" class="w-4 h-4" />
              Resolve
            </button>
            <button
              class="action-btn dismiss"
              :disabled="actionLoading === esc.id"
              @click.stop="dismissEscalation(esc)"
            >
              <UIcon name="i-heroicons-x-mark" class="w-4 h-4" />
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Resolve Modal -->
    <AppModal v-model:open="showResolveModal" title="Resolve Escalation" size="md">
      <div v-if="selectedEscalation" class="resolve-modal-content">
        <div class="modal-info">
          <div class="info-row">
            <span class="info-label">Role:</span>
            <span class="info-value">{{ selectedEscalation.roleName }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Error:</span>
            <code class="info-value error">{{ selectedEscalation.error.slice(0, 100) }}{{ selectedEscalation.error.length > 100 ? '...' : '' }}</code>
          </div>
        </div>

        <div class="resolution-input">
          <label for="resolution" class="input-label">Resolution Notes</label>
          <textarea
            id="resolution"
            v-model="resolutionText"
            class="swarm-textarea"
            placeholder="Describe how this was resolved..."
            rows="3"
          />
        </div>
      </div>

      <template #footer>
        <button class="swarm-btn swarm-btn-ghost" @click="showResolveModal = false">
          Cancel
        </button>
        <button
          class="swarm-btn swarm-btn-success"
          :disabled="!resolutionText.trim() || actionLoading !== null"
          @click="resolveEscalation"
        >
          <UIcon v-if="actionLoading" name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
          <UIcon v-else name="i-heroicons-check" class="w-4 h-4" />
          Mark Resolved
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.escalation-banner {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
  margin-bottom: 24px;
  overflow: hidden;
}

.escalation-banner.critical,
.escalation-banner.high {
  border-color: rgba(239, 68, 68, 0.4);
  background: linear-gradient(to bottom, rgba(239, 68, 68, 0.03), var(--swarm-bg-card));
}

.escalation-banner.medium {
  border-color: rgba(245, 158, 11, 0.4);
  background: linear-gradient(to bottom, rgba(245, 158, 11, 0.03), var(--swarm-bg-card));
}

.banner-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--swarm-border);
}

.header-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.header-content {
  flex: 1;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--swarm-text-primary);
}

.header-subtitle {
  font-size: 12px;
  color: var(--swarm-text-muted);
  margin-top: 2px;
}

.escalation-list {
  padding: 8px;
}

.escalation-item {
  background: var(--swarm-bg-hover);
  border-radius: 8px;
  margin-bottom: 6px;
  overflow: hidden;
}

.escalation-item:last-child {
  margin-bottom: 0;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  cursor: pointer;
  transition: background 0.15s;
}

.item-header:hover {
  background: rgba(0, 0, 0, 0.02);
}

.item-severity {
  flex-shrink: 0;
}

.severity-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-role {
  font-size: 14px;
  font-weight: 500;
  color: var(--swarm-text-primary);
}

.item-meta {
  font-size: 12px;
  color: var(--swarm-text-muted);
  margin-top: 2px;
}

.expand-icon {
  color: var(--swarm-text-muted);
  transition: transform 0.2s;
}

.expand-icon.rotated {
  transform: rotate(180deg);
}

.item-details {
  padding: 0 14px 14px;
  border-top: 1px solid var(--swarm-border);
  margin-top: 0;
}

.error-box {
  margin-top: 12px;
  padding: 10px 12px;
  background: rgba(239, 68, 68, 0.05);
  border-radius: 6px;
  border: 1px solid rgba(239, 68, 68, 0.15);
}

.error-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #ef4444;
  margin-bottom: 6px;
}

.error-text {
  font-family: 'SF Mono', ui-monospace, monospace;
  font-size: 12px;
  line-height: 1.5;
  color: var(--swarm-text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  font-size: 12px;
}

.detail-label {
  color: var(--swarm-text-muted);
}

.detail-value {
  font-family: 'SF Mono', ui-monospace, monospace;
  padding: 2px 6px;
  background: var(--swarm-bg-card);
  border-radius: 4px;
  color: var(--swarm-text-secondary);
}

.item-actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.action-btn.resolve {
  background: var(--swarm-accent);
  color: white;
}

.action-btn.resolve:hover:not(:disabled) {
  filter: brightness(1.1);
}

.action-btn.dismiss {
  background: var(--swarm-bg-card);
  color: var(--swarm-text-secondary);
  border: 1px solid var(--swarm-border);
}

.action-btn.dismiss:hover:not(:disabled) {
  background: var(--swarm-bg-hover);
  color: var(--swarm-text-primary);
}

/* Modal styles */
.resolve-modal-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.modal-info {
  padding: 12px;
  background: var(--swarm-bg-hover);
  border-radius: 8px;
}

.info-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-label {
  color: var(--swarm-text-muted);
  flex-shrink: 0;
  min-width: 50px;
}

.info-value {
  color: var(--swarm-text-primary);
}

.info-value.error {
  font-family: 'SF Mono', ui-monospace, monospace;
  font-size: 11px;
  color: #ef4444;
  word-break: break-word;
}

.resolution-input {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--swarm-text-secondary);
}

.swarm-textarea {
  width: 100%;
  padding: 10px 12px;
  font-size: 14px;
  font-family: inherit;
  border: 1px solid var(--swarm-border);
  border-radius: 8px;
  background: var(--swarm-bg-card);
  color: var(--swarm-text-primary);
  resize: vertical;
  min-height: 80px;
}

.swarm-textarea:focus {
  outline: none;
  border-color: var(--swarm-accent);
}

.swarm-textarea::placeholder {
  color: var(--swarm-text-muted);
}
</style>
