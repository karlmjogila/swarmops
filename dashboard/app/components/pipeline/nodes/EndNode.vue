<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
import type { EndNodeData, ValidationIssue } from '~/types/pipeline'

interface Props {
  id: string
  data: EndNodeData
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
    class="end-node"
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

    <!-- Input handle only (left side) -->
    <Handle
      id="input"
      type="target"
      :position="Position.Left"
      class="handle handle-target"
    />
    
    <div class="node-content">
      <div class="node-icon">
        <UIcon name="i-heroicons-stop-circle-solid" class="w-6 h-6" />
      </div>
      <span class="node-label">{{ data.label || 'End' }}</span>
    </div>
  </div>
</template>

<style scoped>
.end-node {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  border-radius: 24px;
  background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
  border: 2px solid #f87171;
  min-width: 100px;
  cursor: grab;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.25);
}

.end-node:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(239, 68, 68, 0.35);
}

.end-node.selected {
  border-color: #fca5a5;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.3), 0 6px 16px rgba(239, 68, 68, 0.35);
}

.end-node.validation-error {
  border-color: #fbbf24 !important;
  background: linear-gradient(135deg, #b45309 0%, #d97706 100%) !important;
  box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.3), 0 4px 12px rgba(251, 191, 36, 0.3) !important;
  animation: validation-pulse 2s ease-in-out infinite;
}

.end-node.validation-warning {
  border-color: #fcd34d !important;
  box-shadow: 0 0 0 3px rgba(252, 211, 77, 0.25), 0 4px 12px rgba(252, 211, 77, 0.2) !important;
}

@keyframes validation-pulse {
  0%, 100% {
    box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.3), 0 4px 12px rgba(251, 191, 36, 0.3);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(251, 191, 36, 0.15), 0 4px 12px rgba(251, 191, 36, 0.3);
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
  border: 2px solid #f87171;
  transition: all 0.15s ease;
}

.handle:hover {
  transform: scale(1.2);
  background: #f87171;
  border-color: white;
}

.handle-target {
  left: -6px;
}

/* Vue Flow handle overrides */
:deep(.vue-flow__handle) {
  width: 12px;
  height: 12px;
}
</style>
