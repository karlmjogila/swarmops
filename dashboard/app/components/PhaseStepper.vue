<script setup lang="ts">
const props = defineProps<{
  currentPhase: string
  status?: string
}>()

const phases = [
  { id: 'interview', label: 'Interview', icon: 'i-heroicons-chat-bubble-left-right' },
  { id: 'spec', label: 'Spec', icon: 'i-heroicons-clipboard-document-list' },
  { id: 'build', label: 'Build', icon: 'i-heroicons-wrench-screwdriver' },
  { id: 'review', label: 'Review', icon: 'i-heroicons-magnifying-glass' },
]

const isComplete = computed(() => props.status === 'completed' || props.currentPhase === 'complete')

function getPhaseIndex(phase: string): number {
  return phases.findIndex(p => p.id === phase)
}

function getPhaseStatus(phase: string): 'completed' | 'active' | 'pending' {
  if (isComplete.value) return 'completed'
  const currentIndex = getPhaseIndex(props.currentPhase)
  const phaseIndex = getPhaseIndex(phase)
  if (phaseIndex < currentIndex) return 'completed'
  if (phaseIndex === currentIndex) return 'active'
  return 'pending'
}
</script>

<template>
  <div class="phase-stepper">
    <div 
      v-for="(phase, index) in phases" 
      :key="phase.id"
      class="phase-step"
      :class="getPhaseStatus(phase.id)"
    >
      <div class="step-indicator">
        <div class="step-icon">
          <UIcon 
            v-if="getPhaseStatus(phase.id) === 'completed'" 
            name="i-heroicons-check" 
            class="w-4 h-4" 
          />
          <UIcon 
            v-else 
            :name="phase.icon" 
            class="w-4 h-4" 
          />
        </div>
        <div v-if="index < phases.length - 1" class="step-connector" />
      </div>
      <span class="step-label">{{ phase.label }}</span>
    </div>
  </div>
</template>

<style scoped>
.phase-stepper {
  display: flex;
  justify-content: space-between;
  padding: 14px 20px;
  background: var(--swarm-bg-secondary);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
}

.phase-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex: 1;
  position: relative;
}

.step-indicator {
  display: flex;
  align-items: center;
  width: 100%;
  position: relative;
}

.step-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin: 0 auto;
  position: relative;
  z-index: 1;
  transition: all 0.3s ease;
}

.step-connector {
  position: absolute;
  top: 50%;
  left: calc(50% + 20px);
  right: calc(-50% + 20px);
  height: 2px;
  background: var(--swarm-border);
  transform: translateY(-50%);
  transition: background 0.3s ease;
}

.step-label {
  font-size: 12px;
  font-weight: 500;
  text-align: center;
  transition: color 0.2s ease;
}

/* Pending state */
.phase-step.pending .step-icon {
  background: var(--swarm-bg-tertiary);
  border: 2px solid var(--swarm-border);
  color: var(--swarm-text-muted);
}
.phase-step.pending .step-label {
  color: var(--swarm-text-muted);
}

/* Active state */
.phase-step.active .step-icon {
  background: var(--swarm-accent);
  border: none;
  color: white;
  box-shadow: 0 4px 12px var(--swarm-accent-glow);
  animation: pulse-ring 2s ease-in-out infinite;
}
.phase-step.active .step-label {
  color: var(--swarm-accent);
  font-weight: 600;
}

/* Completed state */
.phase-step.completed .step-icon {
  background: var(--swarm-success);
  border: none;
  color: white;
}
.phase-step.completed .step-label {
  color: var(--swarm-success);
}
.phase-step.completed .step-connector {
  background: var(--swarm-success);
}

@keyframes pulse-ring {
  0%, 100% { box-shadow: 0 4px 12px var(--swarm-accent-glow); }
  50% { box-shadow: 0 4px 20px var(--swarm-accent-glow), 0 0 0 4px rgba(16, 185, 129, 0.1); }
}

@media (max-width: 480px) {
  .phase-stepper { padding: 12px 16px; }
  .step-icon { width: 28px; height: 28px; }
  .step-label { font-size: 10px; }
  .step-connector {
    left: calc(50% + 16px);
    right: calc(-50% + 16px);
  }
}
</style>
