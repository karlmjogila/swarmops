<script setup lang="ts">
import type { ProjectStatus, ProjectPhase } from '~/types/project'

const props = defineProps<{
  projectName: string
  currentStatus: ProjectStatus
  currentPhase: ProjectPhase
}>()

const emit = defineEmits<{
  'action-complete': []
}>()

const toast = useToast()
const loading = ref<string | null>(null)
const showKillModal = ref(false)

const phases: { label: string; value: ProjectPhase }[] = [
  { label: 'Interview', value: 'interview' },
  { label: 'Spec', value: 'spec' },
  { label: 'Build', value: 'build' },
  { label: 'Review', value: 'review' }
]

const isRunning = computed(() => props.currentStatus === 'running')
const isPaused = computed(() => props.currentStatus === 'paused')
const canTrigger = computed(() => !isRunning.value && props.currentStatus !== 'completed')

const phaseItems = computed(() => 
  phases.map(p => ({
    label: p.label,
    icon: p.value === props.currentPhase ? 'i-heroicons-check' : undefined,
    click: () => handlePhaseChange(p.value),
    disabled: p.value === props.currentPhase
  }))
)

async function controlAction(action: string, phase?: ProjectPhase) {
  loading.value = action
  try {
    const body: Record<string, string> = { action }
    if (phase) body.phase = phase
    
    await $fetch(`/api/projects/${props.projectName}/control`, {
      method: 'POST',
      body
    })
    
    toast.add({
      title: action === 'kill' ? 'Project killed' : 
             action === 'pause' ? 'Project paused' :
             action === 'resume' ? 'Project resumed' :
             action === 'trigger' ? 'Iteration triggered' : 'Phase changed',
      icon: 'i-heroicons-check-circle',
      color: 'success',
      duration: 3000
    })
    
    emit('action-complete')
  } catch (error) {
    toast.add({
      title: 'Action failed',
      description: error instanceof Error ? error.message : 'Unknown error',
      icon: 'i-heroicons-exclamation-triangle',
      color: 'error',
      duration: 5000
    })
  } finally {
    loading.value = null
  }
}

function handleKillClick() {
  showKillModal.value = true
}

async function confirmKill() {
  showKillModal.value = false
  await controlAction('kill')
}

async function handlePauseResume() {
  await controlAction(isPaused.value ? 'resume' : 'pause')
}

async function handleTrigger() {
  await controlAction('trigger')
}

async function handlePhaseChange(phase: ProjectPhase) {
  await controlAction('phase-change', phase)
}

const currentPhaseLabel = computed(() => 
  phases.find(p => p.value === props.currentPhase)?.label ?? props.currentPhase
)
</script>

<template>
  <div class="flex items-center gap-2 flex-wrap">
    <!-- Kill -->
    <button
      class="swarm-btn swarm-btn-danger"
      :disabled="loading === 'kill'"
      @click="handleKillClick"
    >
      <UIcon v-if="loading === 'kill'" name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
      <UIcon v-else name="i-heroicons-x-circle" class="w-4 h-4" />
      Kill
    </button>

    <!-- Pause/Resume -->
    <button
      v-if="isRunning"
      class="swarm-btn swarm-btn-warning"
      :disabled="loading === 'pause'"
      @click="handlePauseResume"
    >
      <UIcon v-if="loading === 'pause'" name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
      <UIcon v-else name="i-heroicons-pause" class="w-4 h-4" />
      Pause
    </button>
    <button
      v-else-if="isPaused"
      class="swarm-btn swarm-btn-success"
      :disabled="loading === 'resume'"
      @click="handlePauseResume"
    >
      <UIcon v-if="loading === 'resume'" name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
      <UIcon v-else name="i-heroicons-play" class="w-4 h-4" />
      Resume
    </button>

    <!-- Trigger -->
    <button
      v-if="canTrigger"
      class="swarm-btn swarm-btn-primary"
      :disabled="loading === 'trigger'"
      @click="handleTrigger"
    >
      <UIcon v-if="loading === 'trigger'" name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
      <UIcon v-else name="i-heroicons-forward" class="w-4 h-4" />
      Trigger
    </button>

    <!-- Phase (hide when completed) -->
    <UDropdownMenu v-if="currentStatus !== 'completed'" :items="phaseItems">
      <button class="swarm-btn swarm-btn-ghost" :disabled="loading === 'phase-change'">
        <UIcon v-if="loading === 'phase-change'" name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
        Phase: {{ currentPhaseLabel }}
        <UIcon name="i-heroicons-chevron-down" class="w-4 h-4" />
      </button>
    </UDropdownMenu>

    <!-- Kill Modal -->
    <AppModal v-model:open="showKillModal" title="Kill Project" size="sm">
      <div class="flex items-center gap-3 mb-4">
        <div 
          class="w-10 h-10 rounded-full flex items-center justify-center"
          style="background: var(--swarm-error-bg);"
        >
          <UIcon name="i-heroicons-exclamation-triangle" class="w-5 h-5" style="color: var(--swarm-error);" />
        </div>
        <p class="text-sm font-mono" style="color: var(--swarm-text-muted);">{{ projectName }}</p>
      </div>
      
      <p class="text-sm" style="color: var(--swarm-text-secondary);">
        This will stop all processing. Are you sure?
      </p>
      
      <template #footer>
        <button class="swarm-btn swarm-btn-ghost" @click="showKillModal = false">
          Cancel
        </button>
        <button class="swarm-btn swarm-btn-danger" @click="confirmKill">
          <UIcon name="i-heroicons-x-circle" class="w-4 h-4" />
          Kill
        </button>
      </template>
    </AppModal>
  </div>
</template>
