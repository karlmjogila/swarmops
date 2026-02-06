<script setup lang="ts">
import { useVueFlow } from '@vue-flow/core'
import { useAutoLayout } from '~/composables/useAutoLayout'
import type { ValidationIssue } from '~/types/pipeline'

const props = defineProps<{
  saving?: boolean
  running?: boolean
  disabled?: boolean
  isValid?: boolean
  errorCount?: number
  warningCount?: number
  validationErrors?: ValidationIssue[]
}>()

const emit = defineEmits<{
  save: []
  run: []
  'layout-complete': []
}>()

const showValidationPanel = ref(false)

const { fitView, zoomIn, zoomOut, setViewport } = useVueFlow()
const { layout, layouting } = useAutoLayout({
  direction: 'LR',
  nodeWidth: 200,
  nodeHeight: 80,
  nodeSpacing: 60,
  rankSpacing: 120,
  animate: true,
  animationDuration: 300,
})

function handleSave() {
  emit('save')
}

function handleRun() {
  emit('run')
}

function handleZoomIn() {
  zoomIn({ duration: 200 })
}

function handleZoomOut() {
  zoomOut({ duration: 200 })
}

function handleFitView() {
  fitView({ padding: 0.2, duration: 300 })
}

function handleResetView() {
  setViewport({ x: 0, y: 0, zoom: 1 }, { duration: 300 })
}

async function handleAutoLayout() {
  await layout()
  emit('layout-complete')
}
</script>

<template>
  <div class="pipeline-toolbar">
    <!-- Validation Summary -->
    <div class="toolbar-group validation-summary">
      <button
        v-if="errorCount || warningCount"
        class="toolbar-btn validation-btn"
        :class="{
          'validation-btn-error': errorCount,
          'validation-btn-warning': !errorCount && warningCount
        }"
        :title="isValid ? 'Pipeline is valid' : `${errorCount} errors, ${warningCount} warnings`"
        @click="showValidationPanel = !showValidationPanel"
      >
        <UIcon
          :name="errorCount ? 'i-heroicons-exclamation-circle' : 'i-heroicons-exclamation-triangle'"
          class="w-4 h-4"
        />
        <span v-if="errorCount">{{ errorCount }} error{{ errorCount > 1 ? 's' : '' }}</span>
        <span v-else-if="warningCount">{{ warningCount }} warning{{ warningCount > 1 ? 's' : '' }}</span>
        <UIcon name="i-heroicons-chevron-down" class="w-3 h-3 expand-icon" :class="{ 'expanded': showValidationPanel }" />
      </button>
      <div v-else-if="isValid !== undefined" class="validation-status validation-ok">
        <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
        <span>Valid</span>
      </div>
      
      <!-- Validation Panel Dropdown -->
      <Transition name="panel-slide">
        <div v-if="showValidationPanel && validationErrors?.length" class="validation-panel">
          <div class="panel-header">
            <span class="panel-title">Validation Issues</span>
            <button class="panel-close" @click="showValidationPanel = false">
              <UIcon name="i-heroicons-x-mark" class="w-4 h-4" />
            </button>
          </div>
          <div class="panel-content">
            <div
              v-for="(error, idx) in validationErrors"
              :key="idx"
              class="validation-item"
              :class="{ 'item-error': error.type === 'error', 'item-warning': error.type === 'warning' }"
            >
              <UIcon
                :name="error.type === 'error' ? 'i-heroicons-exclamation-circle' : 'i-heroicons-exclamation-triangle'"
                class="w-4 h-4 item-icon"
              />
              <div class="item-content">
                <span class="item-code">{{ error.code }}</span>
                <span class="item-message">{{ error.message }}</span>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <div class="toolbar-divider" />

    <div class="toolbar-group">
      <button
        class="toolbar-btn toolbar-btn-primary"
        :disabled="saving || disabled || !isValid"
        :title="!isValid ? 'Fix validation errors before saving' : 'Save pipeline (Ctrl+S)'"
        @click="handleSave"
      >
        <UIcon
          v-if="saving"
          name="i-heroicons-arrow-path"
          class="w-4 h-4 animate-spin"
        />
        <UIcon v-else name="i-heroicons-cloud-arrow-up" class="w-4 h-4" />
        <span>Save</span>
      </button>

      <button
        class="toolbar-btn toolbar-btn-success"
        :disabled="running || disabled || !isValid"
        :title="!isValid ? 'Fix validation errors before running' : 'Run pipeline'"
        @click="handleRun"
      >
        <UIcon
          v-if="running"
          name="i-heroicons-arrow-path"
          class="w-4 h-4 animate-spin"
        />
        <UIcon v-else name="i-heroicons-play" class="w-4 h-4" />
        <span>Run</span>
      </button>
    </div>

    <div class="toolbar-divider" />

    <div class="toolbar-group">
      <button
        class="toolbar-btn"
        :disabled="layouting || disabled"
        title="Auto-layout nodes"
        @click="handleAutoLayout"
      >
        <UIcon
          v-if="layouting"
          name="i-heroicons-arrow-path"
          class="w-4 h-4 animate-spin"
        />
        <UIcon v-else name="i-heroicons-squares-2x2" class="w-4 h-4" />
        <span>Auto Layout</span>
      </button>
    </div>

    <div class="toolbar-divider" />

    <div class="toolbar-group zoom-controls">
      <button
        class="toolbar-btn toolbar-btn-icon"
        :disabled="disabled"
        title="Zoom in"
        @click="handleZoomIn"
      >
        <UIcon name="i-heroicons-plus" class="w-4 h-4" />
      </button>

      <button
        class="toolbar-btn toolbar-btn-icon"
        :disabled="disabled"
        title="Zoom out"
        @click="handleZoomOut"
      >
        <UIcon name="i-heroicons-minus" class="w-4 h-4" />
      </button>

      <button
        class="toolbar-btn toolbar-btn-icon"
        :disabled="disabled"
        title="Fit to view"
        @click="handleFitView"
      >
        <UIcon name="i-heroicons-arrows-pointing-out" class="w-4 h-4" />
      </button>

      <button
        class="toolbar-btn toolbar-btn-icon"
        :disabled="disabled"
        title="Reset view"
        @click="handleResetView"
      >
        <UIcon name="i-heroicons-viewfinder-circle" class="w-4 h-4" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.pipeline-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--swarm-bg-card, #1e1e2e);
  border: 1px solid var(--swarm-border, #313244);
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.toolbar-divider {
  width: 1px;
  height: 24px;
  background: var(--swarm-border, #313244);
  margin: 0 4px;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--swarm-text-secondary, #a6adc8);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.toolbar-btn:hover:not(:disabled) {
  background: var(--swarm-bg-hover, #181825);
  color: var(--swarm-text-primary, #cdd6f4);
}

.toolbar-btn:active:not(:disabled) {
  transform: scale(0.98);
}

.toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.toolbar-btn-icon {
  padding: 6px;
}

.toolbar-btn-icon span {
  display: none;
}

.toolbar-btn-primary {
  background: var(--swarm-accent, #89b4fa);
  color: var(--swarm-bg, #11111b);
  border-color: var(--swarm-accent, #89b4fa);
}

.toolbar-btn-primary:hover:not(:disabled) {
  background: #9fc5fb;
  border-color: #9fc5fb;
  color: var(--swarm-bg, #11111b);
}

.toolbar-btn-success {
  background: var(--swarm-success, #a6e3a1);
  color: var(--swarm-bg, #11111b);
  border-color: var(--swarm-success, #a6e3a1);
}

.toolbar-btn-success:hover:not(:disabled) {
  background: #b8eab4;
  border-color: #b8eab4;
  color: var(--swarm-bg, #11111b);
}

.zoom-controls {
  gap: 2px;
}

.zoom-controls .toolbar-btn-icon {
  padding: 6px 8px;
  border-radius: 4px;
}

/* Validation Summary Styles */
.validation-summary {
  position: relative;
}

.validation-btn {
  gap: 4px;
}

.validation-btn-error {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
}

.validation-btn-error:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.validation-btn-warning {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.3);
}

.validation-btn-warning:hover:not(:disabled) {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.expand-icon {
  transition: transform 0.2s ease;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.validation-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 6px;
}

.validation-ok {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}

/* Validation Panel Dropdown */
.validation-panel {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  min-width: 320px;
  max-width: 400px;
  background: var(--swarm-bg-card, #1e1e2e);
  border: 1px solid var(--swarm-border, #313244);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  z-index: 100;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--swarm-border, #313244);
  background: var(--swarm-bg-hover, #181825);
}

.panel-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--swarm-text-primary, #cdd6f4);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.panel-close {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  border-radius: 4px;
  color: var(--swarm-text-muted, #6c7086);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
}

.panel-close:hover {
  background: var(--swarm-bg-card, #1e1e2e);
  color: var(--swarm-text-primary, #cdd6f4);
}

.panel-content {
  max-height: 300px;
  overflow-y: auto;
}

.validation-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--swarm-border, #313244);
}

.validation-item:last-child {
  border-bottom: none;
}

.validation-item:hover {
  background: var(--swarm-bg-hover, #181825);
}

.item-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.item-error .item-icon {
  color: #ef4444;
}

.item-warning .item-icon {
  color: #f59e0b;
}

.item-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.item-code {
  font-size: 10px;
  font-weight: 600;
  font-family: monospace;
  color: var(--swarm-text-muted, #6c7086);
  text-transform: uppercase;
}

.item-message {
  font-size: 12px;
  color: var(--swarm-text-secondary, #a6adc8);
  line-height: 1.4;
}

/* Panel animations */
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Responsive: hide text on smaller screens */
@media (max-width: 640px) {
  .toolbar-btn span {
    display: none;
  }
  
  .toolbar-btn {
    padding: 6px 8px;
  }
  
  .validation-panel {
    min-width: 280px;
    right: 0;
    left: auto;
  }
}
</style>
