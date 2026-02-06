<script setup lang="ts">
import type { ProjectState } from '~/types/ralph'

interface Props {
  modelValue: boolean
  project: ProjectState | null
  iterationCount: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

function formatDuration(startedAt: string, completedAt?: string): string {
  if (!startedAt) return 'Unknown'
  
  const start = new Date(startedAt)
  const end = completedAt ? new Date(completedAt) : new Date()
  const diffMs = end.getTime() - start.getTime()
  
  if (diffMs < 0) return 'Unknown'
  
  const seconds = Math.floor(diffMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 0) {
    const remainingHours = hours % 24
    return remainingHours > 0 ? `${days}d ${remainingHours}h` : `${days}d`
  }
  if (hours > 0) {
    const remainingMins = minutes % 60
    return remainingMins > 0 ? `${hours}h ${remainingMins}m` : `${hours}h`
  }
  if (minutes > 0) {
    const remainingSecs = seconds % 60
    return remainingSecs > 0 ? `${minutes}m ${remainingSecs}s` : `${minutes}m`
  }
  return `${seconds}s`
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return 'N/A'
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

const phases = ['interview', 'spec', 'build', 'review'] as const

function getPhaseIcon(phase: string): string {
  switch (phase) {
    case 'interview': return 'i-heroicons-chat-bubble-left-right'
    case 'spec': return 'i-heroicons-document-text'
    case 'build': return 'i-heroicons-wrench-screwdriver'
    case 'review': return 'i-heroicons-magnifying-glass'
    default: return 'i-heroicons-question-mark-circle'
  }
}

function getPhaseStatus(phase: string): 'completed' | 'current' | 'pending' {
  if (!props.project) return 'pending'
  
  const currentIndex = phases.indexOf(props.project.phase as typeof phases[number])
  const phaseIndex = phases.indexOf(phase as typeof phases[number])
  
  if (props.project.status === 'completed') return 'completed'
  if (phaseIndex < currentIndex) return 'completed'
  if (phaseIndex === currentIndex) return 'current'
  return 'pending'
}
</script>

<template>
  <UModal v-model:open="isOpen">
    <template #content>
      <div 
        class="relative overflow-hidden"
        style="background: var(--swarm-bg-secondary); border-radius: 20px;"
      >
        <!-- Success Glow Effect -->
        <div 
          class="absolute inset-0 pointer-events-none"
          style="background: radial-gradient(ellipse at top center, rgba(16, 185, 129, 0.15) 0%, transparent 60%);"
        />
        
        <!-- Content -->
        <div class="relative z-10 p-6 sm:p-8">
          <!-- Header with Trophy -->
          <div class="text-center mb-8">
            <div 
              class="w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-5 relative"
              style="background: linear-gradient(135deg, var(--swarm-success) 0%, #059669 100%); box-shadow: 0 8px 32px var(--swarm-success-glow), inset 0 1px 0 rgba(255,255,255,0.2);"
            >
              <UIcon name="i-heroicons-trophy" class="w-10 h-10 text-white" />
              <div class="absolute inset-0 rounded-2xl" style="background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.3) 0%, transparent 60%);"></div>
            </div>
            <h2 
              class="text-2xl sm:text-3xl font-extrabold tracking-tight mb-2"
              style="color: var(--swarm-text-bright);"
            >
              Project Complete!
            </h2>
            <p class="text-sm" style="color: var(--swarm-text-muted);">
              {{ project?.project ?? 'Project' }} has been successfully completed
            </p>
          </div>

          <!-- Stats Grid -->
          <div class="grid grid-cols-3 gap-3 sm:gap-4 mb-8">
            <!-- Duration -->
            <div class="ralph-stat-card text-center">
              <div class="ralph-stat-label justify-center">
                <UIcon name="i-heroicons-clock" class="w-3.5 h-3.5" style="color: var(--swarm-accent-light);" />
                Duration
              </div>
              <div class="ralph-stat-value text-lg sm:text-xl">
                {{ project ? formatDuration(project.startedAt, project.completedAt) : '-' }}
              </div>
            </div>

            <!-- Phases -->
            <div class="ralph-stat-card text-center">
              <div class="ralph-stat-label justify-center">
                <UIcon name="i-heroicons-flag" class="w-3.5 h-3.5" style="color: var(--swarm-warning);" />
                Phases
              </div>
              <div class="ralph-stat-value text-lg sm:text-xl text-gradient">
                {{ phases.length }}
              </div>
            </div>

            <!-- Iterations -->
            <div class="ralph-stat-card text-center">
              <div class="ralph-stat-label justify-center">
                <UIcon name="i-heroicons-arrow-path" class="w-3.5 h-3.5" style="color: var(--swarm-success);" />
                Iterations
              </div>
              <div class="ralph-stat-value text-lg sm:text-xl">
                {{ iterationCount }}
              </div>
            </div>
          </div>

          <!-- Phase Timeline -->
          <div 
            class="mb-8 p-4 sm:p-5 rounded-xl"
            style="background: var(--swarm-bg-primary); border: 1px solid var(--swarm-border-light);"
          >
            <div 
              class="text-xs uppercase tracking-[0.1em] font-bold mb-4 flex items-center gap-2"
              style="color: var(--swarm-text-muted);"
            >
              <UIcon name="i-heroicons-queue-list" class="w-3.5 h-3.5" />
              Phases Completed
            </div>
            <div class="flex items-center justify-between gap-2">
              <template v-for="(phase, index) in phases" :key="phase">
                <div class="flex flex-col items-center gap-2 flex-1">
                  <div 
                    class="w-10 h-10 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center transition-all"
                    :style="{
                      background: getPhaseStatus(phase) === 'completed' 
                        ? 'linear-gradient(135deg, var(--swarm-success) 0%, #059669 100%)'
                        : 'var(--swarm-bg-tertiary)',
                      boxShadow: getPhaseStatus(phase) === 'completed' 
                        ? '0 4px 16px var(--swarm-success-glow)' 
                        : 'none',
                      border: getPhaseStatus(phase) === 'completed' 
                        ? 'none' 
                        : '1px solid var(--swarm-border-light)'
                    }"
                  >
                    <UIcon 
                      :name="getPhaseStatus(phase) === 'completed' ? 'i-heroicons-check' : getPhaseIcon(phase)" 
                      class="w-5 h-5 sm:w-6 sm:h-6"
                      :style="{ 
                        color: getPhaseStatus(phase) === 'completed' 
                          ? 'white' 
                          : 'var(--swarm-text-muted)' 
                      }"
                    />
                  </div>
                  <span 
                    class="text-[10px] sm:text-xs font-semibold uppercase tracking-wide"
                    :style="{ 
                      color: getPhaseStatus(phase) === 'completed' 
                        ? 'var(--swarm-success)' 
                        : 'var(--swarm-text-muted)' 
                    }"
                  >
                    {{ phase }}
                  </span>
                </div>
                <!-- Connector Line -->
                <div 
                  v-if="index < phases.length - 1"
                  class="flex-shrink-0 h-0.5 w-4 sm:w-8 -mt-6"
                  :style="{ 
                    background: getPhaseStatus(phases[index + 1]) === 'completed' || getPhaseStatus(phase) === 'completed'
                      ? 'var(--swarm-success)' 
                      : 'var(--swarm-border-light)' 
                  }"
                />
              </template>
            </div>
          </div>

          <!-- Timestamps -->
          <div 
            class="flex flex-col sm:flex-row justify-between gap-3 text-xs mb-6 px-2"
            style="color: var(--swarm-text-muted);"
          >
            <div class="flex items-center gap-2">
              <UIcon name="i-heroicons-play" class="w-3.5 h-3.5" />
              <span>Started: {{ formatDate(project?.startedAt) }}</span>
            </div>
            <div class="flex items-center gap-2">
              <UIcon name="i-heroicons-flag" class="w-3.5 h-3.5" style="color: var(--swarm-success);" />
              <span>Completed: {{ formatDate(project?.completedAt) }}</span>
            </div>
          </div>

          <!-- Close Button -->
          <button
            class="swarm-btn swarm-btn-success"
            style="width: 100%; justify-content: center; padding: 12px 20px; font-size: 15px;"
            @click="isOpen = false"
          >
            <UIcon name="i-heroicons-check-circle" class="w-5 h-5" />
            Awesome!
          </button>
        </div>
      </div>
    </template>
  </UModal>
</template>
