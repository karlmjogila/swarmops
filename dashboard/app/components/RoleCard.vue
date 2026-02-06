<script setup lang="ts">
interface Role {
  id: string
  name: string
  model?: string
  thinking?: string
  thinkingLevel?: 'none' | 'low' | 'medium' | 'high'
  instructions?: string
  systemPrompt?: string
  description?: string
  createdAt?: string
}

const props = defineProps<{
  role: Role
}>()

const emit = defineEmits<{
  edit: [role: Role]
  delete: [role: Role]
}>()

// Friendly model names
function getModelName(model?: string): string {
  if (!model) return 'Default'
  const names: Record<string, string> = {
    'anthropic/claude-opus-4-5': 'Opus 4.5',
    'anthropic/claude-sonnet-4-20250514': 'Sonnet 4',
    'anthropic/claude-3-5-haiku-20241022': 'Haiku 3.5',
  }
  return names[model] || model.split('/').pop() || model
}

function getThinkingLevel(role: Role): string {
  return role.thinking || role.thinkingLevel || 'none'
}

function getThinkingColor(level?: string): string {
  switch (level) {
    case 'high': return 'var(--swarm-success)'
    case 'medium': return 'var(--swarm-info)'
    case 'low': return 'var(--swarm-warning)'
    default: return 'var(--swarm-text-muted)'
  }
}

function getThinkingBg(level?: string): string {
  switch (level) {
    case 'high': return 'var(--swarm-success-bg)'
    case 'medium': return 'var(--swarm-info-bg)'
    case 'low': return 'var(--swarm-warning-bg)'
    default: return 'var(--swarm-bg-hover)'
  }
}
</script>

<template>
  <div class="role-card">
    <div class="card-header">
      <div class="role-icon">
        <UIcon name="i-heroicons-user-circle" class="w-5 h-5" />
      </div>
      <div class="role-info">
        <h3 class="role-name">{{ role.name }}</h3>
        <p class="role-model">{{ getModelName(role.model) }}</p>
      </div>
      <div class="card-actions">
        <button class="icon-btn" @click="emit('edit', role)" title="Edit">
          <UIcon name="i-heroicons-pencil-square" class="w-4 h-4" />
        </button>
        <button class="icon-btn icon-btn-danger" @click="emit('delete', role)" title="Delete">
          <UIcon name="i-heroicons-trash" class="w-4 h-4" />
        </button>
      </div>
    </div>

    <div class="card-body">
      <div v-if="role.description" class="role-description">
        {{ role.description }}
      </div>
      
      <div class="role-meta">
        <div 
          class="thinking-badge"
          :style="{ 
            color: getThinkingColor(getThinkingLevel(role)),
            background: getThinkingBg(getThinkingLevel(role))
          }"
        >
          <UIcon name="i-heroicons-light-bulb" class="w-3 h-3" />
          <span>{{ getThinkingLevel(role) }}</span>
        </div>
      </div>
    </div>

    <div v-if="role.systemPrompt" class="card-footer">
      <div class="prompt-preview">
        <span class="prompt-label">System Prompt:</span>
        <span class="prompt-text">{{ role.systemPrompt.slice(0, 100) }}{{ role.systemPrompt.length > 100 ? '...' : '' }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.role-card {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s;
}

.role-card:hover {
  border-color: var(--swarm-accent);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--swarm-border);
}

.role-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--swarm-accent-bg);
  color: var(--swarm-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.role-info {
  flex: 1;
  min-width: 0;
}

.role-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin: 0 0 2px 0;
}

.role-model {
  font-size: 12px;
  color: var(--swarm-text-muted);
  margin: 0;
  font-family: monospace;
}

.card-actions {
  display: flex;
  gap: 2px;
}

.icon-btn {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--swarm-text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}
.icon-btn:hover {
  background: var(--swarm-bg-hover);
  color: var(--swarm-text-primary);
}
.icon-btn-danger:hover {
  background: var(--swarm-error-bg);
  color: var(--swarm-error);
}

.card-body {
  padding: 16px;
}

.role-description {
  font-size: 13px;
  color: var(--swarm-text-secondary);
  line-height: 1.5;
  margin-bottom: 12px;
}

.role-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.thinking-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  text-transform: capitalize;
  padding: 4px 10px;
  border-radius: 6px;
}

.card-footer {
  padding: 12px 16px;
  background: var(--swarm-bg-hover);
  border-top: 1px solid var(--swarm-border);
}

.prompt-preview {
  font-size: 12px;
  line-height: 1.4;
}

.prompt-label {
  color: var(--swarm-text-muted);
  margin-right: 4px;
}

.prompt-text {
  color: var(--swarm-text-secondary);
}
</style>
