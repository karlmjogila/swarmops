<script setup lang="ts">
import type { BadgeVariant } from '~/components/ui/StatusBadge.vue'

const { projects, pending, refresh } = useProjects()

useHead({
  title: 'SwarmOps'
})

const archiving = ref<string | null>(null)

async function archiveProject(projectName: string, e: Event) {
  e.preventDefault()
  e.stopPropagation()
  
  archiving.value = projectName
  try {
    await $fetch(`/api/projects/${projectName}/archive`, { method: 'POST' })
    refresh()
  } catch (err) {
    console.error('Failed to archive project:', err)
  } finally {
    archiving.value = null
  }
}

function getStatusVariant(status: string): BadgeVariant {
  switch (status) {
    case 'running': return 'success'
    case 'completed': return 'success'
    case 'paused': return 'warning'
    case 'error': return 'error'
    default: return 'neutral'
  }
}

function formatDate(dateStr: string): string {
  if (!dateStr) return 'N/A'
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}
</script>

<template>
  <div class="dashboard-overview">
    <div class="overview-header">
      <div class="header-content">
        <h1 class="overview-title">Projects</h1>
        <p class="overview-subtitle">Overview of all orchestration projects</p>
      </div>
      <button class="swarm-btn swarm-btn-ghost" @click="refresh">
        <UIcon name="i-heroicons-arrow-path" class="w-4 h-4" :class="{ 'animate-spin': pending }" />
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="pending && !projects?.length" class="loading-state">
      <UIcon name="i-heroicons-cube-transparent" class="w-8 h-8 animate-pulse" />
      <p>Loading projects...</p>
    </div>

    <!-- Empty state -->
    <UiEmptyState
      v-else-if="!projects?.length"
      icon="i-heroicons-folder-open"
      title="No projects yet"
      description="Create a new project to get started"
      action-label="New Project"
      @action="navigateTo('/projects/new')"
    />

    <!-- Project grid -->
    <div v-else class="projects-grid">
      <NuxtLink
        v-for="project in projects"
        :key="project.name"
        :to="`/project/${project.name}`"
        class="project-card"
      >
        <div class="card-header">
          <div class="project-name">{{ project.name }}</div>
          <div class="card-actions">
            <button
              class="archive-btn"
              :class="{ loading: archiving === project.name }"
              :title="project.archived ? 'Unarchive' : 'Archive'"
              @click="archiveProject(project.name, $event)"
            >
              <UIcon 
                :name="archiving === project.name ? 'i-heroicons-arrow-path' : 'i-heroicons-archive-box'" 
                class="w-4 h-4"
                :class="{ 'animate-spin': archiving === project.name }"
              />
            </button>
            <UiStatusBadge 
              :variant="getStatusVariant(project.status)"
              :label="project.status"
              size="sm"
            />
          </div>
        </div>
        
        <div class="card-body">
          <div class="stat-row">
            <span class="stat-label">Phase</span>
            <span class="stat-value">{{ project.phase }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Iterations</span>
            <span class="stat-value">{{ project.iterationCount || 0 }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Started</span>
            <span class="stat-value">{{ formatDate(project.startedAt) }}</span>
          </div>
        </div>

        <div class="card-footer">
          <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
          <span>View details</span>
        </div>
      </NuxtLink>
    </div>
  </div>
</template>

<style scoped>
.dashboard-overview {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.overview-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 32px;
}

.overview-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin-bottom: 4px;
}

.overview-subtitle {
  font-size: 14px;
  color: var(--swarm-text-muted);
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

.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.project-card {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
  padding: 20px;
  text-decoration: none;
  transition: all 0.2s;
}

.project-card:hover {
  border-color: var(--swarm-accent);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.project-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--swarm-text-primary);
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.archive-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  color: var(--swarm-text-muted);
  opacity: 0;
  transition: all 0.15s;
}

.project-card:hover .archive-btn {
  opacity: 1;
}

.archive-btn:hover {
  background: var(--swarm-bg-hover);
  color: var(--swarm-text-primary);
}

.archive-btn.loading {
  opacity: 1;
  pointer-events: none;
}

.status-badge {
  font-size: 11px;
  font-weight: 500;
  text-transform: capitalize;
  padding: 4px 10px;
  border-radius: 6px;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  font-size: 13px;
  color: var(--swarm-text-muted);
}

.stat-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--swarm-text-secondary);
  text-transform: capitalize;
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-top: 16px;
  border-top: 1px solid var(--swarm-border);
  font-size: 13px;
  color: var(--swarm-accent);
}

@media (max-width: 640px) {
  .dashboard-overview {
    padding: 16px;
  }
  
  .projects-grid {
    grid-template-columns: 1fr;
  }
}
</style>
