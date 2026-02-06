<script setup lang="ts">
interface PipelineStep {
  id: string
  order: number
  roleId: string
  roleName?: string
  action: string
  convergence?: {
    maxIterations?: number
    targetScore?: number
  }
}

interface Role {
  id: string
  name: string
}

const props = defineProps<{
  steps: PipelineStep[]
  roles: Role[]
}>()

const emit = defineEmits<{
  'update:steps': [steps: PipelineStep[]]
  'add-step': []
  'remove-step': [stepId: string]
  'update-step': [step: PipelineStep]
}>()

const draggedIndex = ref<number | null>(null)
const dropTargetIndex = ref<number | null>(null)

// Delete confirmation
const stepToDelete = ref<string | null>(null)
const showDeleteConfirm = ref(false)

function confirmDeleteStep(stepId: string) {
  stepToDelete.value = stepId
  showDeleteConfirm.value = true
}

function executeDelete() {
  if (stepToDelete.value) {
    emit('remove-step', stepToDelete.value)
  }
  showDeleteConfirm.value = false
  stepToDelete.value = null
}

function onDragStart(index: number) {
  draggedIndex.value = index
}

function onDragOver(e: DragEvent, index: number) {
  e.preventDefault()
  dropTargetIndex.value = index
}

function onDragLeave() {
  dropTargetIndex.value = null
}

function onDrop(targetIndex: number) {
  if (draggedIndex.value === null) return
  
  const newSteps = [...props.steps]
  const [draggedStep] = newSteps.splice(draggedIndex.value, 1)
  newSteps.splice(targetIndex, 0, draggedStep)
  
  // Update order numbers
  newSteps.forEach((step, idx) => {
    step.order = idx + 1
  })
  
  emit('update:steps', newSteps)
  draggedIndex.value = null
  dropTargetIndex.value = null
}

function onDragEnd() {
  draggedIndex.value = null
  dropTargetIndex.value = null
}

function updateStepRole(step: PipelineStep, roleId: string) {
  const role = props.roles.find(r => r.id === roleId)
  emit('update-step', { 
    ...step, 
    roleId, 
    roleName: role?.name 
  })
}

function updateStepAction(step: PipelineStep, action: string) {
  emit('update-step', { ...step, action })
}

function updateConvergence(step: PipelineStep, field: 'maxIterations' | 'targetScore', value: string) {
  const numValue = parseInt(value) || undefined
  emit('update-step', {
    ...step,
    convergence: {
      ...step.convergence,
      [field]: numValue
    }
  })
}

const actionOptions = [
  { label: 'Execute', value: 'execute' },
  { label: 'Review', value: 'review' },
  { label: 'Validate', value: 'validate' },
  { label: 'Transform', value: 'transform' },
  { label: 'Aggregate', value: 'aggregate' },
]
</script>

<template>
  <div class="pipeline-editor">
    <div class="editor-header">
      <h3>Pipeline Steps</h3>
      <UButton size="xs" variant="soft" @click="emit('add-step')">
        <UIcon name="i-heroicons-plus" class="w-4 h-4" />
        Add Step
      </UButton>
    </div>

    <div v-if="!steps.length" class="empty-steps">
      <UIcon name="i-heroicons-queue-list" class="w-8 h-8" />
      <p>No steps defined. Add your first step to build the pipeline.</p>
    </div>

    <TransitionGroup v-else name="step-list" tag="div" class="steps-list">
      <div
        v-for="(step, index) in steps"
        :key="step.id"
        class="step-item"
        :class="{ 
          'dragging': draggedIndex === index,
          'drop-target': dropTargetIndex === index 
        }"
        draggable="true"
        @dragstart="onDragStart(index)"
        @dragover="onDragOver($event, index)"
        @dragleave="onDragLeave"
        @drop="onDrop(index)"
        @dragend="onDragEnd"
      >
        <div class="step-handle">
          <UIcon name="i-heroicons-bars-3" class="w-4 h-4" />
        </div>
        
        <div class="step-number">{{ step.order }}</div>
        
        <div class="step-config">
          <div class="config-row">
            <div class="config-field">
              <label>Role</label>
              <USelect
                :model-value="step.roleId"
                :items="roles.map(r => ({ label: r.name, value: r.id }))"
                placeholder="Select role"
                @update:model-value="updateStepRole(step, $event)"
              />
            </div>
            
            <div class="config-field">
              <label>Action</label>
              <USelect
                :model-value="step.action"
                :items="actionOptions"
                @update:model-value="updateStepAction(step, $event)"
              />
            </div>
          </div>
          
          <div class="config-row convergence-row">
            <div class="config-field small">
              <label>Max iterations</label>
              <UInput
                type="number"
                :model-value="step.convergence?.maxIterations"
                placeholder="No limit"
                min="1"
                @update:model-value="updateConvergence(step, 'maxIterations', $event)"
              />
            </div>
            
            <div class="config-field small">
              <label>Target score</label>
              <UInput
                type="number"
                :model-value="step.convergence?.targetScore"
                placeholder="Optional"
                min="0"
                max="100"
                @update:model-value="updateConvergence(step, 'targetScore', $event)"
              />
            </div>
          </div>
        </div>
        
        <UButton
          variant="ghost"
          size="xs"
          icon="i-heroicons-trash"
          color="error"
          class="remove-btn"
          @click="confirmDeleteStep(step.id)"
        />
      </div>
    </TransitionGroup>

    <!-- Delete Confirmation -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showDeleteConfirm" class="delete-overlay" @click.self="showDeleteConfirm = false">
          <div class="delete-dialog">
            <UIcon name="i-heroicons-exclamation-triangle" class="w-10 h-10 text-amber-500" />
            <h4>Remove step?</h4>
            <p>This step will be removed from the pipeline.</p>
            <div class="delete-actions">
              <UButton variant="outline" size="sm" @click="showDeleteConfirm = false">Cancel</UButton>
              <UButton color="error" size="sm" @click="executeDelete">Remove</UButton>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.pipeline-editor {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
  overflow: hidden;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--swarm-border);
  background: var(--swarm-bg-hover);
}

.editor-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin: 0;
}

.empty-steps {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
  color: var(--swarm-text-muted);
  gap: 12px;
}

.empty-steps p {
  font-size: 13px;
  margin: 0;
}

.steps-list {
  display: flex;
  flex-direction: column;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--swarm-border);
  background: var(--swarm-bg-card);
  transition: all 0.2s;
}

.step-item:last-child {
  border-bottom: none;
}

.step-item.dragging {
  opacity: 0.5;
  background: var(--swarm-bg-hover);
}

.step-item.drop-target {
  border-top: 2px solid var(--swarm-accent);
}

.step-handle {
  cursor: grab;
  color: var(--swarm-text-muted);
  padding: 8px 4px;
}

.step-handle:active {
  cursor: grabbing;
}

.step-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--swarm-accent-bg);
  color: var(--swarm-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.step-config {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.config-row {
  display: flex;
  gap: 12px;
}

.convergence-row {
  padding-top: 8px;
  border-top: 1px dashed var(--swarm-border);
}

.config-field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-field.small {
  max-width: 120px;
}

.config-field label {
  font-size: 13px;
  font-weight: 500;
  color: var(--swarm-text-secondary);
}

.remove-btn {
  flex-shrink: 0;
}

/* Delete confirmation dialog */
.delete-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(2px);
}

.delete-dialog {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  max-width: 320px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.delete-dialog h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin: 12px 0 4px;
}

.delete-dialog p {
  font-size: 13px;
  color: var(--swarm-text-muted);
  margin: 0 0 16px;
}

.delete-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}

/* Modal transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.15s ease;
}

.modal-enter-active .delete-dialog,
.modal-leave-active .delete-dialog {
  transition: transform 0.15s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .delete-dialog,
.modal-leave-to .delete-dialog {
  transform: scale(0.95);
}

/* Transition animations */
.step-list-enter-active,
.step-list-leave-active {
  transition: all 0.3s ease;
}

.step-list-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.step-list-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.step-list-move {
  transition: transform 0.3s ease;
}

@media (max-width: 640px) {
  .config-row {
    flex-direction: column;
  }
  
  .config-field.small {
    max-width: none;
  }
}
</style>
