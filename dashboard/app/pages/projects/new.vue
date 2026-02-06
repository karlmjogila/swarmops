<script setup lang="ts">
useHead({
  title: 'New Project - SwarmOps'
})

const router = useRouter()

const form = reactive({
  name: '',
  description: '',
  phase: 'interview'
})

const phases = [
  { label: 'Interview', value: 'interview' },
  { label: 'Spec', value: 'spec' },
  { label: 'Build', value: 'build' },
  { label: 'Review', value: 'review' }
]

const creating = ref(false)
const error = ref('')

const createProject = async () => {
  if (!form.name.match(/^[a-z0-9-]+$/)) {
    error.value = 'Project name must be lowercase letters, numbers, and hyphens only'
    return
  }
  
  creating.value = true
  error.value = ''
  
  try {
    await $fetch('/api/projects', {
      method: 'POST',
      body: {
        name: form.name,
        description: form.description,
        phase: form.phase
      }
    })
    router.push(`/project/${form.name}`)
  } catch (e: any) {
    error.value = e.data?.message || e.message || 'Failed to create project'
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="new-project-page">
    <div class="page-header">
      <NuxtLink to="/" class="back-link">
        <UIcon name="i-heroicons-arrow-left" class="w-4 h-4" />
        Back to Dashboard
      </NuxtLink>
    </div>
    
    <div class="form-container">
      <h1 class="page-title">Create New Project</h1>
      
      <form @submit.prevent="createProject" class="project-form">
        <div class="form-group">
          <label class="form-label">Project Name *</label>
          <input 
            v-model="form.name" 
            type="text"
            class="form-input"
            placeholder="my-project"
            :disabled="creating"
          />
          <span class="form-hint">Lowercase letters, numbers, and hyphens only</span>
        </div>
        
        <div class="form-group">
          <label class="form-label">Description</label>
          <textarea 
            v-model="form.description"
            class="form-input form-textarea"
            placeholder="What does this project do?"
            :disabled="creating"
            rows="3"
          />
        </div>
        
        <div class="form-group">
          <label class="form-label">Initial Phase</label>
          <select v-model="form.phase" class="form-input form-select" :disabled="creating">
            <option v-for="p in phases" :key="p.value" :value="p.value">
              {{ p.label }}
            </option>
          </select>
        </div>
        
        <div v-if="error" class="error-message">
          {{ error }}
        </div>
        
        <div class="form-actions">
          <button type="submit" class="swarm-btn swarm-btn-primary" :disabled="creating">
            <UIcon v-if="creating" name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
            {{ creating ? 'Creating...' : 'Create Project' }}
          </button>
          <NuxtLink to="/" class="swarm-btn swarm-btn-ghost">
            Cancel
          </NuxtLink>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.new-project-page {
  padding: 24px;
  max-width: 600px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 32px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--swarm-text-muted);
  text-decoration: none;
  transition: color 0.2s;
}

.back-link:hover {
  color: var(--swarm-accent);
}

.form-container {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
  padding: 32px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin-bottom: 32px;
}

.project-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--swarm-text-secondary);
}

.form-input {
  background: var(--swarm-bg-page);
  border: 1px solid var(--swarm-border);
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 14px;
  color: var(--swarm-text-primary);
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: var(--swarm-accent);
}

.form-input::placeholder {
  color: var(--swarm-text-muted);
}

.form-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-select {
  cursor: pointer;
}

.form-hint {
  font-size: 12px;
  color: var(--swarm-text-muted);
}

.error-message {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 14px;
  color: #ef4444;
}

.form-actions {
  display: flex;
  gap: 12px;
  padding-top: 8px;
}









.btn-ghost:hover {
  border-color: var(--swarm-text-muted);
  color: var(--swarm-text-primary);
}

@media (max-width: 640px) {
  .new-project-page {
    padding: 16px;
  }
  
  .form-container {
    padding: 20px;
  }
}
</style>
