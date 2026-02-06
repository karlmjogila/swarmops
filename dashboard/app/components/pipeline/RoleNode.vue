<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
import type { ValidationIssue, ExecutionStatus } from '~/types/pipeline'
import { usePipelineExecutionContext } from '~/composables/usePipelineExecutionContext'

export interface RoleNodeData {
  roleId: string
  roleName: string
  model?: string
  action?: string
  status?: ExecutionStatus
  thinkingLevel?: 'none' | 'low' | 'medium' | 'high'
  sessionId?: string
}

const props = defineProps<{
  id: string
  data: RoleNodeData
  selected?: boolean
  connectable?: boolean
}>()

// Inject execution context (if available)
const executionContext = usePipelineExecutionContext()

// Inject validation functions from parent editor
const getNodeErrors = inject<(nodeId: string) => ValidationIssue[]>('getNodeErrors', () => [])

// Inject log viewing function
const viewNodeLogs = inject<(nodeId: string, nodeName: string, sessionId: string | undefined, status: ExecutionStatus) => void>('viewNodeLogs', () => {})

// Get status from execution context or from data props
const executionStatus = computed<ExecutionStatus>(() => {
  if (executionContext) {
    return executionContext.getNodeStatus(props.id)
  }
  return props.data.status || 'idle'
})

const isRunning = computed(() => executionStatus.value === 'running')
const isCompleted = computed(() => executionStatus.value === 'completed')
const isError = computed(() => executionStatus.value === 'error')
const isPending = computed(() => executionStatus.value === 'pending')
const isSkipped = computed(() => executionStatus.value === 'skipped')

// Validation state from injected function
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

// Model display names
function getModelName(model?: string): string {
  if (!model) return 'Default'
  const names: Record<string, string> = {
    'anthropic/claude-opus-4-5': 'Opus 4.5',
    'anthropic/claude-sonnet-4-20250514': 'Sonnet 4',
    'anthropic/claude-3-5-haiku-20241022': 'Haiku 3.5',
  }
  return names[model] || model.split('/').pop() || model
}

function getStatusColor(): string {
  switch (executionStatus.value) {
    case 'running': return '#3b82f6'
    case 'completed': return '#10b981'
    case 'error': return '#ef4444'
    case 'pending': return '#f59e0b'
    case 'skipped': return '#6c7086'
    default: return 'var(--swarm-accent)'
  }
}

function getThinkingIcon(level?: string): string {
  switch (level) {
    case 'high': return '🧠'
    case 'medium': return '💭'
    case 'low': return '💡'
    default: return ''
  }
}

// Can view logs if running, completed, or error
const canViewLogs = computed(() => 
  isRunning.value || isCompleted.value || isError.value
)

function handleViewLogs(event: MouseEvent) {
  event.stopPropagation()
  if (canViewLogs.value) {
    viewNodeLogs(props.id, props.data.roleName || 'Role', props.data.sessionId, executionStatus.value)
  }
}
</script>

<template>
  <div
    class="role-node"
    :class="{
      'role-node--selected': selected,
      'role-node--running': isRunning,
      'role-node--completed': isCompleted,
      'role-node--error': isError,
      'role-node--pending': isPending,
      'role-node--skipped': isSkipped,
      'role-node--validation-error': hasErrors,
      'role-node--validation-warning': hasWarnings && !hasErrors
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

    <!-- Target Handle (input) -->
    <Handle
      id="target"
      type="target"
      :position="Position.Top"
      class="role-handle role-handle--target"
      :connectable="connectable"
    />

    <!-- Node Content -->
    <div class="role-node__content">
      <div class="role-node__icon" :style="{ borderColor: getStatusColor() }">
        <!-- Default icon when idle -->
        <svg
          v-if="!isRunning && !isCompleted && !isError"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          class="role-node__icon-svg"
        >
          <path
            fill-rule="evenodd"
            d="M18.685 19.097A9.723 9.723 0 0 0 21.75 12c0-5.385-4.365-9.75-9.75-9.75S2.25 6.615 2.25 12a9.723 9.723 0 0 0 3.065 7.097A9.716 9.716 0 0 0 12 21.75a9.716 9.716 0 0 0 6.685-2.653Zm-12.54-1.285A7.486 7.486 0 0 1 12 15a7.486 7.486 0 0 1 5.855 2.812A8.224 8.224 0 0 1 12 20.25a8.224 8.224 0 0 1-5.855-2.438ZM15.75 9a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z"
            clip-rule="evenodd"
          />
        </svg>

        <!-- Spinner when running -->
        <svg
          v-if="isRunning"
          class="role-node__spinner"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            class="spinner-track"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="3"
          />
          <path
            class="spinner-head"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>

        <!-- Checkmark when completed -->
        <svg
          v-if="isCompleted"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          class="role-node__icon-svg role-node__icon-svg--completed"
        >
          <path
            fill-rule="evenodd"
            d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm13.36-1.814a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z"
            clip-rule="evenodd"
          />
        </svg>

        <!-- Error icon when error -->
        <svg
          v-if="isError"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          class="role-node__icon-svg role-node__icon-svg--error"
        >
          <path
            fill-rule="evenodd"
            d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25zm-1.72 6.97a.75.75 0 10-1.06 1.06L10.94 12l-1.72 1.72a.75.75 0 101.06 1.06L12 13.06l1.72 1.72a.75.75 0 101.06-1.06L13.06 12l1.72-1.72a.75.75 0 10-1.06-1.06L12 10.94l-1.72-1.72z"
            clip-rule="evenodd"
          />
        </svg>

        <!-- Running pulse effect -->
        <div v-if="isRunning" class="role-node__pulse" />
      </div>

      <div class="role-node__info">
        <div class="role-node__name">
          {{ data.roleName || 'Unnamed Role' }}
          <span v-if="data.thinkingLevel && data.thinkingLevel !== 'none'" class="role-node__thinking">
            {{ getThinkingIcon(data.thinkingLevel) }}
          </span>
        </div>
        <div class="role-node__meta">
          <span v-if="data.action" class="role-node__action">{{ data.action }}</span>
          <span v-if="data.model" class="role-node__model">{{ getModelName(data.model) }}</span>
        </div>
      </div>

      <!-- Status and logs section -->
      <div class="role-node__actions">
        <!-- View logs button -->
        <button
          v-if="canViewLogs"
          class="role-node__logs-btn"
          :class="{
            'role-node__logs-btn--running': isRunning,
            'role-node__logs-btn--completed': isCompleted,
            'role-node__logs-btn--error': isError
          }"
          title="View logs"
          @click="handleViewLogs"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5">
            <path fill-rule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm2.25 8.5a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zm0 3a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5z" clip-rule="evenodd" />
          </svg>
        </button>

        <!-- Status badge -->
        <div v-if="isRunning" class="role-node__status-badge role-node__status-badge--running">
          Running
        </div>
        <div v-else-if="isCompleted" class="role-node__status-badge role-node__status-badge--completed">
          Done
        </div>
        <div v-else-if="isError" class="role-node__status-badge role-node__status-badge--error">
          Error
        </div>
        <div v-else-if="isPending" class="role-node__status-badge role-node__status-badge--pending">
          Queued
        </div>
      </div>
    </div>

    <!-- Source Handle (output) -->
    <Handle
      id="source"
      type="source"
      :position="Position.Bottom"
      class="role-handle role-handle--source"
      :connectable="connectable"
    />
  </div>
</template>

<style scoped>
.role-node {
  position: relative;
  background: var(--swarm-bg-card, #1e1e2e);
  border: 2px solid var(--swarm-border, #313244);
  border-radius: 12px;
  min-width: 180px;
  max-width: 240px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transition: all 0.2s ease;
}

.role-node:hover {
  border-color: var(--swarm-accent, #89b4fa);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
  transform: translateY(-1px);
}

.role-node--selected {
  border-color: var(--swarm-accent, #89b4fa);
  box-shadow: 0 0 0 3px rgba(137, 180, 250, 0.2), 0 6px 20px rgba(0, 0, 0, 0.3);
}

/* Execution states */
.role-node--running {
  border-color: #3b82f6;
  animation: node-glow-pulse 2s ease-in-out infinite;
}

.role-node--completed {
  border-color: #10b981;
}

.role-node--error {
  border-color: #ef4444;
  animation: node-error-shake 0.4s ease-in-out;
}

.role-node--pending {
  border-color: #f59e0b;
  opacity: 0.8;
}

.role-node--skipped {
  border-color: #6c7086;
  opacity: 0.6;
}

/* Validation states */
.role-node--validation-error {
  border-color: #ef4444 !important;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.25), 0 4px 12px rgba(239, 68, 68, 0.3);
  animation: validation-error-pulse 2s ease-in-out infinite;
}

.role-node--validation-warning {
  border-color: #f59e0b !important;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2), 0 4px 12px rgba(245, 158, 11, 0.2);
}

/* Animations */
@keyframes node-glow-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4), 0 4px 12px rgba(0, 0, 0, 0.2);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(59, 130, 246, 0), 0 4px 12px rgba(0, 0, 0, 0.2);
  }
}

@keyframes node-error-shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-4px); }
  40% { transform: translateX(4px); }
  60% { transform: translateX(-4px); }
  80% { transform: translateX(4px); }
}

@keyframes validation-error-pulse {
  0%, 100% {
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.25), 0 4px 12px rgba(239, 68, 68, 0.3);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(239, 68, 68, 0.1), 0 4px 12px rgba(239, 68, 68, 0.3);
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
  min-width: 200px;
  max-width: 300px;
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

/* Node content */
.role-node__content {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
}

/* Icon container */
.role-node__icon {
  position: relative;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--swarm-accent-bg, rgba(137, 180, 250, 0.1));
  color: var(--swarm-accent, #89b4fa);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 2px solid transparent;
  transition: border-color 0.2s, background 0.2s;
}

.role-node--running .role-node__icon {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.role-node--completed .role-node__icon {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.role-node--error .role-node__icon {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.role-node__icon-svg {
  width: 20px;
  height: 20px;
}

.role-node__icon-svg--completed {
  animation: scale-in 0.3s ease-out;
}

.role-node__icon-svg--error {
  animation: scale-in 0.3s ease-out;
}

@keyframes scale-in {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  50% {
    transform: scale(1.2);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Spinner */
.role-node__spinner {
  width: 20px;
  height: 20px;
  animation: spin 1s linear infinite;
}

.spinner-track {
  opacity: 0.25;
}

.spinner-head {
  opacity: 0.85;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Pulse effect for running state */
.role-node__pulse {
  position: absolute;
  inset: -4px;
  border-radius: 14px;
  border: 2px solid #3b82f6;
  animation: icon-pulse 1.5s ease-in-out infinite;
}

@keyframes icon-pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0;
    transform: scale(1.3);
  }
}

/* Node info */
.role-node__info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.role-node__name {
  font-size: 13px;
  font-weight: 600;
  color: var(--swarm-text-primary, #cdd6f4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 4px;
}

.role-node__thinking {
  font-size: 12px;
}

.role-node__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.role-node__action {
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--swarm-accent, #89b4fa);
  background: var(--swarm-accent-bg, rgba(137, 180, 250, 0.1));
  padding: 2px 6px;
  border-radius: 4px;
}

.role-node__model {
  font-size: 11px;
  color: var(--swarm-text-muted, #6c7086);
  font-family: monospace;
}

/* Actions container */
.role-node__actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

/* Logs button */
.role-node__logs-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
  background: var(--swarm-bg-hover, #181825);
  color: var(--swarm-text-muted, #6c7086);
}

.role-node__logs-btn:hover {
  transform: scale(1.1);
}

.role-node__logs-btn--running {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.role-node__logs-btn--running:hover {
  background: rgba(59, 130, 246, 0.25);
}

.role-node__logs-btn--completed {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.role-node__logs-btn--completed:hover {
  background: rgba(16, 185, 129, 0.25);
}

.role-node__logs-btn--error {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.role-node__logs-btn--error:hover {
  background: rgba(239, 68, 68, 0.25);
}

/* Status badge */
.role-node__status-badge {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 3px 6px;
  border-radius: 4px;
  flex-shrink: 0;
  animation: badge-slide-in 0.2s ease-out;
}

@keyframes badge-slide-in {
  from {
    opacity: 0;
    transform: translateX(8px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.role-node__status-badge--running {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
}

.role-node__status-badge--completed {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.role-node__status-badge--error {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.role-node__status-badge--pending {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

/* Vue Flow Handle Styles */
.role-handle {
  width: 12px !important;
  height: 12px !important;
  border-radius: 50% !important;
  background: var(--swarm-bg-card, #1e1e2e) !important;
  border: 2px solid var(--swarm-border, #313244) !important;
  transition: all 0.15s ease !important;
}

.role-handle:hover {
  background: var(--swarm-accent, #89b4fa) !important;
  border-color: var(--swarm-accent, #89b4fa) !important;
  transform: scale(1.2);
}

.role-handle--target {
  top: -6px !important;
}

.role-handle--source {
  bottom: -6px !important;
}

/* Connected state */
.role-handle.connected {
  background: var(--swarm-accent, #89b4fa) !important;
  border-color: var(--swarm-accent, #89b4fa) !important;
}

/* Connectable hint */
.role-handle.connectable {
  cursor: crosshair;
}

.role-handle.valid {
  background: #10b981 !important;
  border-color: #10b981 !important;
}

.role-handle.invalid {
  background: #ef4444 !important;
  border-color: #ef4444 !important;
}
</style>
