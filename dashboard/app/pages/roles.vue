<script setup lang="ts">
interface Role {
  id: string
  name: string
  model?: string
  thinking?: string
  instructions?: string
  promptFile?: string
  description?: string
  createdAt?: string
  updatedAt?: string
}

useHead({
  title: 'Roles - SwarmOps'
})

const { data: roles, pending, refresh } = useFetch<Role[]>('/api/orchestrator/roles', {
  default: () => [],
})

// Modal state
const showModal = ref(false)
const editingRole = ref<Role | null>(null)
const showDeleteConfirm = ref(false)
const roleToDelete = ref<Role | null>(null)

// Form state
const form = ref({
  name: '',
  model: 'anthropic/claude-opus-4-5',
  thinking: 'low',
  instructions: '',
  promptFile: '',
  description: '',
})

const modelOptions = [
  { label: 'Claude Opus 4.5', value: 'anthropic/claude-opus-4-5' },
  { label: 'Claude Sonnet 4', value: 'anthropic/claude-sonnet-4-20250514' },
  { label: 'Claude Haiku 3.5', value: 'anthropic/claude-3-5-haiku-20241022' },
]

const thinkingOptions = [
  { label: 'None', value: 'none' },
  { label: 'Low', value: 'low' },
  { label: 'Medium', value: 'medium' },
  { label: 'High', value: 'high' },
]

function openCreateModal() {
  editingRole.value = null
  form.value = {
    name: '',
    model: 'anthropic/claude-opus-4-5',
    thinking: 'low',
    instructions: '',
    promptFile: '',
    description: '',
  }
  showModal.value = true
}

function openEditModal(role: Role) {
  editingRole.value = role
  form.value = {
    name: role.name,
    model: role.model || 'anthropic/claude-sonnet-4-20250514',
    thinking: role.thinking || 'low',
    instructions: role.instructions || '',
    promptFile: role.promptFile || '',
    description: role.description || '',
  }
  showModal.value = true
}

function confirmDelete(role: Role) {
  roleToDelete.value = role
  showDeleteConfirm.value = true
}

const saving = ref(false)
const deleting = ref(false)

async function saveRole() {
  saving.value = true
  try {
    const method = editingRole.value ? 'PUT' : 'POST'
    const url = editingRole.value 
      ? `/api/orchestrator/roles/${editingRole.value.id}`
      : '/api/orchestrator/roles'
    
    await $fetch(url, {
      method,
      body: form.value,
    })
    
    showModal.value = false
    refresh()
  } catch (err) {
    console.error('Failed to save role:', err)
  } finally {
    saving.value = false
  }
}

async function deleteRole() {
  if (!roleToDelete.value) return
  
  deleting.value = true
  try {
    await $fetch(`/api/orchestrator/roles/${roleToDelete.value.id}`, {
      method: 'DELETE',
    })
    showDeleteConfirm.value = false
    roleToDelete.value = null
    refresh()
  } catch (err) {
    console.error('Failed to delete role:', err)
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="roles-page">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">Roles</h1>
        <p class="page-subtitle">Define agent personas and behaviors</p>
      </div>
      <div class="header-actions">
        <button class="swarm-btn swarm-btn-ghost" @click="refresh">
          <UIcon name="i-heroicons-arrow-path" class="w-4 h-4" :class="{ 'animate-spin': pending }" />
        </button>
        <button class="swarm-btn swarm-btn-primary" @click="openCreateModal">
          <UIcon name="i-heroicons-plus" class="w-4 h-4" />
          New Role
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="pending && !roles?.length" class="loading-state">
      <UIcon name="i-heroicons-user-circle" class="w-8 h-8 animate-pulse" />
      <p>Loading roles...</p>
    </div>

    <!-- Empty state -->
    <UiEmptyState
      v-else-if="!roles?.length"
      icon="i-heroicons-user-group"
      title="No roles defined"
      description="Create your first role to define agent behaviors"
      action-label="Create Role"
      @action="openCreateModal"
    />

    <!-- Roles grid -->
    <div v-else class="roles-grid">
      <RoleCard
        v-for="role in roles"
        :key="role.id"
        :role="role"
        @edit="openEditModal"
        @delete="confirmDelete"
      />
    </div>

    <!-- Create/Edit Modal -->
    <AppModal 
      v-model:open="showModal" 
      :title="editingRole ? 'Edit Role' : 'Create Role'"
      size="md"
    >
      <form @submit.prevent="saveRole" class="role-form">
        <!-- Identity Section -->
        <div class="form-section">
          <div class="form-row">
            <div class="form-group flex-1">
              <label>Name</label>
              <UInput 
                v-model="form.name" 
                placeholder="e.g., reviewer" 
                required 
              />
            </div>
          </div>
          
          <div class="form-group">
            <label>Description</label>
            <UInput 
              v-model="form.description" 
              placeholder="Brief description of what this role does"
            />
          </div>
        </div>

        <!-- Model Settings -->
        <div class="form-section">
          <div class="section-label">Model Settings</div>
          <div class="form-row">
            <div class="form-group flex-2">
              <label>Model</label>
              <select v-model="form.model" class="native-select">
                <option v-for="opt in modelOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>
            <div class="form-group flex-1">
              <label>Thinking</label>
              <select v-model="form.thinking" class="native-select">
                <option v-for="opt in thinkingOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>
          </div>
        </div>

        <!-- Instructions -->
        <div class="form-section">
          <div class="form-group">
            <label>Prompt File</label>
            <span class="label-hint">Path to .md file with detailed instructions (optional, overrides inline)</span>
            <UInput 
              v-model="form.promptFile" 
              placeholder="e.g., reviewer.md or /full/path/to/prompt.md"
            />
          </div>
          <div class="form-group">
            <label>Instructions</label>
            <span class="label-hint">Fallback if no prompt file, or inline instructions</span>
            <UTextarea 
              v-model="form.instructions" 
              placeholder="You are a code reviewer. Focus on finding bugs, security issues, and suggesting improvements..."
              :rows="6"
              class="instructions-textarea"
            />
          </div>
        </div>
        
        <div class="form-actions">
          <button type="button" class="swarm-btn swarm-btn-ghost" @click="showModal = false">Cancel</button>
          <button type="submit" class="swarm-btn swarm-btn-primary" :disabled="saving">
            <UIcon v-if="saving" name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
            {{ editingRole ? 'Save Changes' : 'Create Role' }}
          </button>
        </div>
      </form>
    </AppModal>

    <!-- Delete Confirmation Modal -->
    <AppModal v-model:open="showDeleteConfirm" title="Delete Role" size="sm">
      <div class="delete-confirm">
        <UIcon name="i-heroicons-exclamation-triangle" class="delete-icon" />
        <p>Delete <strong>{{ roleToDelete?.name }}</strong>?</p>
        <p class="delete-hint">This cannot be undone.</p>
      </div>
      
      <template #footer>
        <button class="swarm-btn swarm-btn-ghost" @click="showDeleteConfirm = false">Cancel</button>
        <button class="swarm-btn swarm-btn-danger" :disabled="deleting" @click="deleteRole">
          <UIcon v-if="deleting" name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
          Delete
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.roles-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 32px;
  gap: 16px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--swarm-text-muted);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  text-align: center;
  color: var(--swarm-text-muted);
  gap: 12px;
}

.empty-state h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin: 0;
}

.empty-state p {
  font-size: 14px;
  margin: 0;
}

.roles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

/* Form Styles */
.role-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--swarm-text-muted);
  margin-top: 4px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
}

.form-group.flex-1 { flex: 1; }
.form-group.flex-2 { flex: 2; }

.form-group label {
  font-size: 13px;
  font-weight: 500;
  color: var(--swarm-text-secondary);
}

.label-hint {
  font-size: 11px;
  color: var(--swarm-text-muted);
}

.role-form :deep(input),
.role-form :deep(select),
.role-form :deep(textarea) {
  width: 100% !important;
}

.role-form :deep(textarea) {
  font-family: 'SF Mono', ui-monospace, monospace;
  font-size: 13px;
  min-height: 120px;
}

.native-select {
  width: 100%;
  padding: 8px 12px;
  font-size: 14px;
  background: var(--swarm-bg-card, #1a1a1a);
  border: 1px solid var(--swarm-border, #333);
  border-radius: 8px;
  color: var(--swarm-text-primary, #fff);
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23888'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  background-size: 16px;
  padding-right: 36px;
}

.native-select:focus {
  outline: none;
  border-color: var(--swarm-accent, #8b5cf6);
}

.native-select option {
  background: var(--swarm-bg-card, #1a1a1a);
  color: var(--swarm-text-primary, #fff);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--swarm-border);
}

/* Delete Confirmation */
.delete-confirm {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 16px 0;
  gap: 8px;
}

.delete-icon {
  width: 40px;
  height: 40px;
  color: #f59e0b;
  margin-bottom: 8px;
}

.delete-confirm p {
  margin: 0;
  color: var(--swarm-text-secondary);
}

.delete-hint {
  font-size: 13px;
  color: var(--swarm-text-muted);
}

@media (max-width: 640px) {
  .roles-page {
    padding: 16px;
  }
  
  .roles-grid {
    grid-template-columns: 1fr;
  }
  
  .form-row {
    flex-direction: column;
  }
}
</style>
