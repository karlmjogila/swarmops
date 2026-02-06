<script setup lang="ts">
import type { ProjectPhase, ProjectStatus } from '~/types/project'

const props = defineProps<{
  projectName: string
  phase: ProjectPhase
  status: ProjectStatus
  iteration: number
}>()

const emit = defineEmits<{
  'approve': []
  'action-complete': []
}>()

const loading = ref(false)
const toast = useToast()

const defaultConfig = {
  title: 'Unknown',
  description: 'Unknown phase',
  icon: 'i-heroicons-question-mark-circle',
  color: '#6b7280',
  nextAction: '',
  nextPhase: null as ProjectPhase | null
}

const phaseConfig: Record<string, { 
  title: string
  description: string
  icon: string
  color: string
  nextAction: string
  nextPhase: ProjectPhase | null
}> = {
  interview: {
    title: 'Interview',
    description: 'Gathering requirements and clarifying goals',
    icon: 'i-heroicons-chat-bubble-left-right',
    color: '#8b5cf6',
    nextAction: 'Complete Interview',
    nextPhase: 'spec'
  },
  spec: {
    title: 'Planning',
    description: 'Creating specifications and implementation plan',
    icon: 'i-heroicons-clipboard-document-list',
    color: '#3b82f6',
    nextAction: 'Approve Plan',
    nextPhase: 'build'
  },
  planning: {
    title: 'Planning',
    description: 'Creating specifications and implementation plan',
    icon: 'i-heroicons-clipboard-document-list',
    color: '#3b82f6',
    nextAction: 'Approve Plan',
    nextPhase: 'build'
  },
  build: {
    title: 'Building',
    description: 'Executing tasks and building the project',
    icon: 'i-heroicons-wrench-screwdriver',
    color: '#10b981',
    nextAction: '', // Auto-advances when all tasks complete
    nextPhase: 'review'
  },
  review: {
    title: 'Review',
    description: 'Reviewing completed work for approval',
    icon: 'i-heroicons-magnifying-glass',
    color: '#f59e0b',
    nextAction: 'Approve & Complete',
    nextPhase: 'complete'
  },
  complete: {
    title: 'Complete',
    description: 'Project successfully completed',
    icon: 'i-heroicons-check-circle',
    color: '#10b981',
    nextAction: '',
    nextPhase: null
  }
}

const currentConfig = computed(() => phaseConfig[props.phase] || defaultConfig)

const isRunning = computed(() => props.status === 'running')
const isPaused = computed(() => props.status === 'paused')
const isCompleted = computed(() => props.status === 'completed')
const canApprove = computed(() => !isRunning.value && !isCompleted.value)

async function handleApprove() {
  loading.value = true
  try {
    // Post approval to control endpoint
    await $fetch(`/api/projects/${props.projectName}/control`, {
      method: 'POST',
      body: { 
        action: 'trigger',
        phase: currentConfig.value.nextPhase
      }
    })
    
    toast.add({
      title: currentConfig.value.nextPhase 
        ? `Moving to ${phaseConfig[currentConfig.value.nextPhase].title}` 
        : 'Project completed',
      icon: 'i-heroicons-check-circle',
      color: 'success'
    })
    
    emit('approve')
    emit('action-complete')
  } catch (err) {
    toast.add({
      title: 'Action failed',
      description: err instanceof Error ? err.message : 'Unknown error',
      icon: 'i-heroicons-exclamation-triangle',
      color: 'error'
    })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="phase-gate" :class="{ running: isRunning, completed: isCompleted }">
    <div class="phase-indicator">
      <div 
        class="phase-icon"
        :style="{ background: `${currentConfig.color}15`, color: currentConfig.color }"
      >
        <UIcon :name="currentConfig.icon" class="w-6 h-6" />
      </div>
      <div class="phase-info">
        <div class="phase-label">Current Phase</div>
        <div class="phase-title">{{ currentConfig.title }}</div>
        <div class="phase-description">{{ currentConfig.description }}</div>
      </div>
    </div>

    <div class="phase-status">
      <div v-if="isRunning" class="status-running">
        <div class="pulse-dot" />
        <span>In Progress</span>
      </div>
      <div v-else-if="isCompleted" class="status-completed">
        <UIcon name="i-heroicons-check-circle" class="w-5 h-5" />
        <span>Completed</span>
      </div>
      <div v-else-if="isPaused" class="status-paused">
        <UIcon name="i-heroicons-pause-circle" class="w-5 h-5" />
        <span>Awaiting Approval</span>
      </div>
    </div>

    <div v-if="canApprove && currentConfig.nextAction" class="phase-action">
      <button 
        class="approve-btn"
        :disabled="loading"
        @click="handleApprove"
      >
        <UIcon v-if="loading" name="i-heroicons-arrow-path" class="w-5 h-5 animate-spin" />
        <UIcon v-else name="i-heroicons-arrow-right-circle" class="w-5 h-5" />
        {{ currentConfig.nextAction }}
      </button>
    </div>

    <!-- Phase progress dots -->
    <div class="phase-dots">
      <div 
        v-for="(config, key) in phaseConfig" 
        :key="key"
        class="phase-dot"
        :class="{ 
          active: key === phase,
          completed: getPhaseIndex(key as ProjectPhase) < getPhaseIndex(phase)
        }"
        :title="config.title"
      />
    </div>
  </div>
</template>

<script lang="ts">
function getPhaseIndex(phase: string): number {
  const order = ['interview', 'spec', 'planning', 'build', 'review', 'complete']
  const idx = order.indexOf(phase)
  // Map planning to same index as spec
  if (phase === 'planning') return order.indexOf('spec')
  return idx >= 0 ? idx : -1
}
</script>

<style scoped>
.phase-gate {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.phase-gate.running {
  border-color: rgba(16, 185, 129, 0.4);
}

.phase-gate.completed {
  border-color: rgba(59, 130, 246, 0.4);
}

.phase-indicator {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.phase-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.phase-info {
  flex: 1;
}

.phase-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--swarm-text-muted);
  margin-bottom: 4px;
}

.phase-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin-bottom: 4px;
}

.phase-description {
  font-size: 13px;
  color: var(--swarm-text-muted);
}

.phase-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 14px;
  border-radius: 8px;
  background: var(--swarm-bg-hover);
}

.status-running {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #10b981;
  font-size: 13px;
  font-weight: 500;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
}

.status-completed {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #3b82f6;
  font-size: 13px;
  font-weight: 500;
}

.status-paused {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f59e0b;
  font-size: 13px;
  font-weight: 500;
}

.phase-action {
  margin-bottom: 16px;
}

.approve-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 12px 20px;
  border-radius: 8px;
  background: var(--swarm-accent);
  color: white;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
  justify-content: center;
}

.approve-btn:hover:not(:disabled) {
  filter: brightness(1.1);
}

.approve-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.phase-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--swarm-border);
}

.phase-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--swarm-border);
  transition: all 0.2s;
}

.phase-dot.active {
  background: var(--swarm-accent);
  transform: scale(1.25);
}

.phase-dot.completed {
  background: #3b82f6;
}
</style>
