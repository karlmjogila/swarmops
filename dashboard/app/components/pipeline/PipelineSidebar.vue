<script setup lang="ts">
interface Role {
  id: string
  name: string
  model?: string
  thinking?: string
  description?: string
}

// Emit drag data for the canvas to handle drops
const emit = defineEmits<{
  'drag-start': [event: DragEvent, nodeType: string, data?: Record<string, unknown>]
}>()

// Fetch roles from API
const { data: roles, pending } = useFetch<Role[]>('/api/orchestrator/roles', {
  default: () => [],
})

function onDragStart(event: DragEvent, nodeType: string, data?: Record<string, unknown>) {
  if (!event.dataTransfer) return
  
  // Set the data that will be used when dropped on the canvas
  const transferData = JSON.stringify({
    type: nodeType,
    ...data,
  })
  
  event.dataTransfer.setData('application/vueflow', transferData)
  event.dataTransfer.effectAllowed = 'move'
  
  emit('drag-start', event, nodeType, data)
}

function getThinkingBadge(thinking?: string): string {
  switch (thinking) {
    case 'high': return '🧠'
    case 'medium': return '💭'
    case 'low': return '💡'
    default: return ''
  }
}

function getModelShort(model?: string): string {
  if (!model) return ''
  const names: Record<string, string> = {
    'anthropic/claude-opus-4-5': 'Opus',
    'anthropic/claude-sonnet-4-20250514': 'Sonnet',
    'anthropic/claude-3-5-haiku-20241022': 'Haiku',
  }
  return names[model] || model.split('/').pop() || ''
}
</script>

<template>
  <aside class="pipeline-sidebar">
    <div class="sidebar-header">
      <h3>Node Palette</h3>
      <p class="sidebar-hint">Drag nodes to canvas</p>
    </div>

    <!-- Boundary Nodes Section -->
    <div class="sidebar-section">
      <div class="section-title">Flow Control</div>
      
      <div 
        class="node-item node-item--start"
        draggable="true"
        @dragstart="(e) => onDragStart(e, 'start', { label: 'Start' })"
      >
        <div class="node-preview node-preview--start">
          <UIcon name="i-heroicons-play-circle-solid" class="w-4 h-4" />
        </div>
        <div class="node-info">
          <span class="node-name">Start</span>
          <span class="node-desc">Entry point</span>
        </div>
      </div>

      <div 
        class="node-item node-item--end"
        draggable="true"
        @dragstart="(e) => onDragStart(e, 'end', { label: 'End' })"
      >
        <div class="node-preview node-preview--end">
          <UIcon name="i-heroicons-stop-circle-solid" class="w-4 h-4" />
        </div>
        <div class="node-info">
          <span class="node-name">End</span>
          <span class="node-desc">Exit point</span>
        </div>
      </div>
    </div>

    <!-- Roles Section -->
    <div class="sidebar-section">
      <div class="section-title">
        Agent Roles
        <span v-if="pending" class="loading-indicator">
          <UIcon name="i-heroicons-arrow-path" class="w-3 h-3 animate-spin" />
        </span>
      </div>

      <div v-if="!roles?.length && !pending" class="empty-roles">
        <UIcon name="i-heroicons-user-group" class="w-6 h-6" />
        <span>No roles defined</span>
        <NuxtLink to="/roles" class="create-link">
          Create role →
        </NuxtLink>
      </div>

      <div 
        v-for="role in roles"
        :key="role.id"
        class="node-item node-item--role"
        draggable="true"
        @dragstart="(e) => onDragStart(e, 'role', { 
          roleId: role.id, 
          roleName: role.name,
          model: role.model,
          thinkingLevel: role.thinking
        })"
      >
        <div class="node-preview node-preview--role">
          <UIcon name="i-heroicons-user-circle-solid" class="w-4 h-4" />
        </div>
        <div class="node-info">
          <span class="node-name">
            {{ role.name }}
            <span v-if="role.thinking && role.thinking !== 'none'" class="thinking-badge">
              {{ getThinkingBadge(role.thinking) }}
            </span>
          </span>
          <span class="node-desc">
            <template v-if="role.description">{{ role.description }}</template>
            <template v-else-if="role.model">{{ getModelShort(role.model) }}</template>
            <template v-else>Agent role</template>
          </span>
        </div>
      </div>
    </div>

    <!-- Help Section -->
    <div class="sidebar-footer">
      <div class="help-tip">
        <UIcon name="i-heroicons-light-bulb" class="w-4 h-4" />
        <span>Connect nodes by dragging from handles</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.pipeline-sidebar {
  width: 240px;
  background: var(--swarm-bg-card, #1e1e2e);
  border-right: 1px solid var(--swarm-border, #313244);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--swarm-border, #313244);
}

.sidebar-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--swarm-text-primary, #cdd6f4);
  margin: 0 0 4px 0;
}

.sidebar-hint {
  font-size: 11px;
  color: var(--swarm-text-muted, #6c7086);
  margin: 0;
}

.sidebar-section {
  padding: 12px;
  border-bottom: 1px solid var(--swarm-border, #313244);
}

.section-title {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--swarm-text-muted, #6c7086);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.loading-indicator {
  color: var(--swarm-accent, #89b4fa);
}

/* Node Items */
.node-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  margin-bottom: 6px;
  border-radius: 8px;
  background: var(--swarm-bg-hover, #181825);
  border: 1px solid transparent;
  cursor: grab;
  transition: all 0.15s ease;
}

.node-item:last-child {
  margin-bottom: 0;
}

.node-item:hover {
  border-color: var(--swarm-border, #313244);
  transform: translateX(2px);
}

.node-item:active {
  cursor: grabbing;
  opacity: 0.8;
}

/* Node Previews */
.node-preview {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.node-preview--start {
  background: linear-gradient(135deg, #059669 0%, #10b981 100%);
  color: white;
}

.node-preview--end {
  background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
  color: white;
}

.node-preview--role {
  background: var(--swarm-accent-bg, rgba(137, 180, 250, 0.1));
  color: var(--swarm-accent, #89b4fa);
}

/* Node Info */
.node-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.node-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--swarm-text-primary, #cdd6f4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 4px;
}

.thinking-badge {
  font-size: 10px;
}

.node-desc {
  font-size: 10px;
  color: var(--swarm-text-muted, #6c7086);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Empty State */
.empty-roles {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 8px;
  text-align: center;
  color: var(--swarm-text-muted, #6c7086);
  gap: 6px;
}

.empty-roles span {
  font-size: 11px;
}

.create-link {
  font-size: 11px;
  color: var(--swarm-accent, #89b4fa);
  text-decoration: none;
  margin-top: 4px;
}

.create-link:hover {
  text-decoration: underline;
}

/* Footer */
.sidebar-footer {
  margin-top: auto;
  padding: 12px;
  border-top: 1px solid var(--swarm-border, #313244);
}

.help-tip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 11px;
  color: var(--swarm-text-muted, #6c7086);
  line-height: 1.4;
}

.help-tip .w-4 {
  flex-shrink: 0;
  margin-top: 1px;
  color: var(--swarm-accent, #89b4fa);
  opacity: 0.7;
}

/* Scrollable roles section */
.sidebar-section:nth-child(3) {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

/* Custom scrollbar */
.sidebar-section::-webkit-scrollbar {
  width: 4px;
}

.sidebar-section::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-section::-webkit-scrollbar-thumb {
  background: var(--swarm-border, #313244);
  border-radius: 2px;
}

.sidebar-section::-webkit-scrollbar-thumb:hover {
  background: var(--swarm-text-muted, #6c7086);
}
</style>
