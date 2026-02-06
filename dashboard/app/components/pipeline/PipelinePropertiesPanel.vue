<script setup lang="ts">
import type { PipelineNode, RoleNodeData } from '~/types/pipeline'

interface Role {
  id: string
  name: string
  model?: string
  thinking?: string
  description?: string
}

const props = defineProps<{
  node: PipelineNode | null
}>()

const emit = defineEmits<{
  'update:node': [node: PipelineNode]
  'close': []
}>()

// Fetch available roles
const { data: roles } = useFetch<Role[]>('/api/orchestrator/roles', {
  default: () => [],
})

// Available models
const models = [
  { value: '', label: 'Default (from role)' },
  { value: 'anthropic/claude-opus-4-5', label: 'Claude Opus 4.5' },
  { value: 'anthropic/claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
  { value: 'anthropic/claude-3-5-haiku-20241022', label: 'Claude Haiku 3.5' },
]

// Thinking levels
const thinkingLevels = [
  { value: 'none', label: 'None', icon: '—' },
  { value: 'low', label: 'Low', icon: '💡' },
  { value: 'medium', label: 'Medium', icon: '💭' },
  { value: 'high', label: 'High', icon: '🧠' },
]

// Local editable state
const localLabel = ref('')
const localRoleId = ref('')
const localModel = ref('')
const localThinking = ref('none')
const localAction = ref('')

// Watch for node changes and sync local state
watch(() => props.node, (newNode) => {
  if (!newNode) return
  
  localLabel.value = newNode.data.label || ''
  
  if (newNode.type === 'role') {
    const roleData = newNode.data as RoleNodeData
    localRoleId.value = roleData.roleId || ''
    localModel.value = (roleData.config?.model as string) || ''
    localThinking.value = (roleData.config?.thinkingLevel as string) || 'none'
    localAction.value = (roleData.config?.action as string) || ''
  }
}, { immediate: true })

// Computed: selected role details
const selectedRole = computed(() => {
  if (!localRoleId.value) return null
  return roles.value?.find(r => r.id === localRoleId.value)
})

// Update node when local values change
function updateNode() {
  if (!props.node) return
  
  const updatedNode = { ...props.node }
  updatedNode.data = { ...updatedNode.data, label: localLabel.value }
  
  if (updatedNode.type === 'role') {
    const roleData = updatedNode.data as RoleNodeData
    roleData.roleId = localRoleId.value
    
    // Update roleName from selected role
    if (selectedRole.value) {
      roleData.label = localLabel.value || selectedRole.value.name
    }
    
    // Store overrides in config
    roleData.config = {
      ...roleData.config,
      model: localModel.value || undefined,
      thinkingLevel: localThinking.value !== 'none' ? localThinking.value : undefined,
      action: localAction.value || undefined,
    }
  }
  
  emit('update:node', updatedNode)
}

// Watch for changes and update
watch([localLabel, localRoleId, localModel, localThinking, localAction], updateNode)

// When role changes, update label if it was empty or matched old role name
watch(localRoleId, (newRoleId, oldRoleId) => {
  const newRole = roles.value?.find(r => r.id === newRoleId)
  const oldRole = roles.value?.find(r => r.id === oldRoleId)
  
  if (newRole && (!localLabel.value || localLabel.value === oldRole?.name)) {
    localLabel.value = newRole.name
  }
})

// Node type display
const nodeTypeDisplay = computed(() => {
  if (!props.node) return ''
  switch (props.node.type) {
    case 'start': return 'Start Node'
    case 'end': return 'End Node'
    case 'role': return 'Role Node'
    default: return 'Node'
  }
})

const nodeTypeIcon = computed(() => {
  if (!props.node) return 'i-heroicons-cube'
  switch (props.node.type) {
    case 'start': return 'i-heroicons-play-circle'
    case 'end': return 'i-heroicons-stop-circle'
    case 'role': return 'i-heroicons-user-circle'
    default: return 'i-heroicons-cube'
  }
})
</script>

<template>
  <aside v-if="node" class="properties-panel">
    <!-- Header -->
    <div class="panel-header">
      <div class="header-title">
        <UIcon :name="nodeTypeIcon" class="w-5 h-5" />
        <span>{{ nodeTypeDisplay }}</span>
      </div>
      <UButton
        variant="ghost"
        size="xs"
        square
        @click="emit('close')"
      >
        <UIcon name="i-heroicons-x-mark" class="w-4 h-4" />
      </UButton>
    </div>

    <!-- Content -->
    <div class="panel-content">
      <!-- Common: Label -->
      <div class="field-group">
        <label class="field-label">Label</label>
        <UInput
          v-model="localLabel"
          placeholder="Node label..."
          size="sm"
        />
      </div>

      <!-- Role Node specific fields -->
      <template v-if="node.type === 'role'">
        <!-- Role Selector -->
        <div class="field-group">
          <label class="field-label">Role</label>
          <USelect
            v-model="localRoleId"
            :options="roles?.map(r => ({ value: r.id, label: r.name })) || []"
            placeholder="Select role..."
            size="sm"
          />
          <p v-if="selectedRole?.description" class="field-hint">
            {{ selectedRole.description }}
          </p>
        </div>

        <!-- Model Override -->
        <div class="field-group">
          <label class="field-label">Model Override</label>
          <USelect
            v-model="localModel"
            :options="models"
            size="sm"
          />
          <p v-if="selectedRole?.model && !localModel" class="field-hint">
            Using role default: {{ selectedRole.model.split('/').pop() }}
          </p>
        </div>

        <!-- Thinking Level -->
        <div class="field-group">
          <label class="field-label">Thinking Level</label>
          <div class="thinking-options">
            <button
              v-for="level in thinkingLevels"
              :key="level.value"
              class="thinking-option"
              :class="{ active: localThinking === level.value }"
              @click="localThinking = level.value"
            >
              <span class="thinking-icon">{{ level.icon }}</span>
              <span class="thinking-label">{{ level.label }}</span>
            </button>
          </div>
          <p v-if="selectedRole?.thinking && localThinking === 'none'" class="field-hint">
            Role default: {{ selectedRole.thinking }}
          </p>
        </div>

        <!-- Action Field -->
        <div class="field-group">
          <label class="field-label">Action</label>
          <UInput
            v-model="localAction"
            placeholder="e.g., review, implement, test..."
            size="sm"
          />
          <p class="field-hint">
            Optional action context passed to the agent
          </p>
        </div>

        <!-- Role Info Card -->
        <div v-if="selectedRole" class="role-info-card">
          <div class="role-info-header">
            <UIcon name="i-heroicons-information-circle" class="w-4 h-4" />
            <span>Role Configuration</span>
          </div>
          <div class="role-info-row">
            <span class="info-label">Base Model</span>
            <span class="info-value">{{ selectedRole.model?.split('/').pop() || 'Not set' }}</span>
          </div>
          <div class="role-info-row">
            <span class="info-label">Thinking</span>
            <span class="info-value">{{ selectedRole.thinking || 'None' }}</span>
          </div>
        </div>
      </template>

      <!-- Start/End node info -->
      <template v-else>
        <div class="node-info-box">
          <UIcon 
            :name="node.type === 'start' ? 'i-heroicons-play-circle' : 'i-heroicons-stop-circle'" 
            class="w-8 h-8"
          />
          <p>
            {{ node.type === 'start' 
              ? 'Pipeline entry point. Execution begins here.' 
              : 'Pipeline exit point. Execution ends here.' 
            }}
          </p>
        </div>
      </template>
    </div>

    <!-- Footer with node ID -->
    <div class="panel-footer">
      <span class="node-id">ID: {{ node.id }}</span>
    </div>
  </aside>
</template>

<style scoped>
.properties-panel {
  width: 280px;
  background: var(--swarm-bg-card, #1e1e2e);
  border-left: 1px solid var(--swarm-border, #313244);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--swarm-border, #313244);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--swarm-text-primary, #cdd6f4);
}

.header-title .w-5 {
  color: var(--swarm-accent, #89b4fa);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--swarm-text-muted, #6c7086);
}

.field-hint {
  font-size: 11px;
  color: var(--swarm-text-muted, #6c7086);
  margin: 0;
  line-height: 1.4;
}

/* Thinking Level Options */
.thinking-options {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}

.thinking-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 4px;
  border-radius: 8px;
  background: var(--swarm-bg-hover, #181825);
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.15s ease;
}

.thinking-option:hover {
  border-color: var(--swarm-border, #313244);
}

.thinking-option.active {
  border-color: var(--swarm-accent, #89b4fa);
  background: var(--swarm-accent-bg, rgba(137, 180, 250, 0.1));
}

.thinking-icon {
  font-size: 14px;
  line-height: 1;
}

.thinking-label {
  font-size: 9px;
  font-weight: 500;
  color: var(--swarm-text-secondary, #a6adc8);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.thinking-option.active .thinking-label {
  color: var(--swarm-accent, #89b4fa);
}

/* Role Info Card */
.role-info-card {
  background: var(--swarm-bg-hover, #181825);
  border-radius: 8px;
  padding: 12px;
  margin-top: 8px;
}

.role-info-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--swarm-text-muted, #6c7086);
  margin-bottom: 10px;
}

.role-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.role-info-row:not(:last-child) {
  border-bottom: 1px solid var(--swarm-border, #313244);
}

.info-label {
  font-size: 11px;
  color: var(--swarm-text-muted, #6c7086);
}

.info-value {
  font-size: 11px;
  font-weight: 500;
  color: var(--swarm-text-primary, #cdd6f4);
  font-family: monospace;
}

/* Node Info Box (for Start/End) */
.node-info-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
  padding: 24px 16px;
  color: var(--swarm-text-muted, #6c7086);
}

.node-info-box p {
  font-size: 12px;
  line-height: 1.5;
  margin: 0;
}

/* Footer */
.panel-footer {
  padding: 8px 16px;
  border-top: 1px solid var(--swarm-border, #313244);
}

.node-id {
  font-size: 10px;
  font-family: monospace;
  color: var(--swarm-text-muted, #6c7086);
}

/* Custom scrollbar */
.panel-content::-webkit-scrollbar {
  width: 4px;
}

.panel-content::-webkit-scrollbar-track {
  background: transparent;
}

.panel-content::-webkit-scrollbar-thumb {
  background: var(--swarm-border, #313244);
  border-radius: 2px;
}

.panel-content::-webkit-scrollbar-thumb:hover {
  background: var(--swarm-text-muted, #6c7086);
}
</style>
