<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
import type { StartNodeData, ValidationIssue } from '~/types/pipeline'

interface Props {
  id: string
  data: StartNodeData
  selected?: boolean
}

const props = defineProps<Props>()

// Inject validation functions from parent editor
const getNodeErrors = inject<(nodeId: string) => ValidationIssue[]>('getNodeErrors', () => [])

const validationErrors = computed(() => getNodeErrors(props.id))
const hasErrors = computed(() => validationErrors.value?.some(e => e.type === 'error'))
const hasWarnings = computed(() => validationErrors.value?.some(e => e.type === 'warning'))
const showTooltip = ref(false)

const tooltipMessages = computed(() => {
  if (!validationErrors.value?.length) return []
  return validationErrors.value.map(e => ({
    type: e.type,
    message: e.message
  }))
})
</script>

<template>
  <div
    class="start-node"
    :class="{ 
      selected,
      'validation-error': hasErrors,
      'validation-warning': hasWarnings && !hasErrors
    }"
    @mouseenter="showTooltip = true"
    @mouseleave="showTooltip = false"
  >
    <!-- Validation Error Tooltip -->
    <Transition name="tooltip-fade">
      <div v-if="showTooltip && tooltipMessages.length > 0" class="validation-tooltip">
        <div
          v-for="(msg, idx) in tooltipMessages"
          :key="idx"
          class="tooltip-item"
          :class="{ 'tooltip-error': msg.type === 'error', 'tooltip-warning': msg.type === 'warning' }"
        >
          <UIcon
            :name="msg.type === 'error' ? 'i-heroicons-exclamation-circle' : 'i-heroicons-exclamation-triangle'"
            class="w-3 h-3"
          />
          <span>{{ msg.message }}</span>
        </div>
      </div>
    </Transition>

    <div class="node-content">
      <div class="node-icon">
        <UIcon name="i-heroicons-play-circle-solid" class="w-6 h-6" />
      </div>
      <span class="node-label">{{ data.label || 'Start' }}</span>
    </div>
    
    <!-- Output handle only (right side) -->
    <Handle
      id="output"
      type="source"
      :position="Position.Right"
      class="handle handle-source"
    />
  </div>
</template>

<style scoped>
.start-node {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  border-radius: 24px;
  background: linear-gradient(135deg, #059669 0%, #10b981 100%);
  border: 2px solid #34d399;
  min-width: 100px;
  cursor: grab;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
}

.start-node:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(16, 185, 129, 0.35);
}

.start-node.selected {
  border-color: #6ee7b7;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.3), 0 6px 16px rgba(16, 185, 129, 0.35);
}

.start-node.validation-error {
  border-color: #ef4444 !important;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.3), 0 4px 12px rgba(239, 68, 68, 0.3) !important;
  animation: validation-pulse 2s ease-in-out infinite;
}

.start-node.validation-warning {
  border-color: #f59e0b !important;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.25), 0 4px 12px rgba(245, 158, 11, 0.2) !important;
}

@keyframes validation-pulse {
  0%, 100% {
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.3), 0 4px 12px rgba(239, 68, 68, 0.3);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(239, 68, 68, 0.15), 0 4px 12px rgba(239, 68, 68, 0.3);
  }
}

/* Validation Tooltip */
.validation-tooltip {
  position: absolute;
  bottom: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--swarm-bg-card, #1e1e2e);
  border: 1px solid var(--swarm-border, #313244);
  border-radius: 8px;
  padding: 8px;
  min-width: 180px;
  max-width: 280px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.validation-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: var(--swarm-border, #313244);
}

.tooltip-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 11px;
  line-height: 1.4;
}

.tooltip-error {
  color: #ef4444;
}

.tooltip-warning {
  color: #f59e0b;
}

.tooltip-fade-enter-active,
.tooltip-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.tooltip-fade-enter-from,
.tooltip-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(4px);
}

.node-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.node-label {
  font-size: 14px;
  font-weight: 600;
  color: white;
  white-space: nowrap;
}

/* Handle styling */
.handle {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: white;
  border: 2px solid #34d399;
  transition: all 0.15s ease;
}

.handle:hover {
  transform: scale(1.2);
  background: #34d399;
  border-color: white;
}

.handle-source {
  right: -6px;
}

/* Vue Flow handle overrides */
:deep(.vue-flow__handle) {
  width: 12px;
  height: 12px;
}
</style>
