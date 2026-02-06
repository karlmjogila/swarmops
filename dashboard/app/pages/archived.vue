<script setup lang="ts">
import type { ProjectListItem } from '~/types/project'

useHead({
  title: 'Archived Projects - SwarmOps'
})

const { data: projects, pending, refresh } = useFetch<ProjectListItem[]>('/api/projects?archived=true', {
  default: () => [],
})

const archiving = ref<string | null>(null)

async function unarchiveProject(projectName: string, e: Event) {
  e.preventDefault()
  e.stopPropagation()
  
  archiving.value = projectName
  try {
    await $fetch(`/api/projects/${projectName}/archive`, { method: 'POST' })
    refresh()
  } catch (err) {
    console.error('Failed to unarchive project:', err)
  } finally {
    archiving.value = null
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'running': return 'var(--swarm-accent)'
    case 'completed': return 'var(--swarm-info)'
    case 'paused': return 'var(--swarm-warning)'
    case 'error': return 'var(--swarm-error)'
    default: return 'var(--swarm-text-muted)'
  }
}

function getStatusBg(status: string): string {
  switch (status) {
    case 'running': return 'var(--swarm-accent-bg)'
    case 'completed': return 'var(--swarm-info-bg)'
    case 'paused': return 'var(--swarm-warning-bg)'
    case 'error': return 'var(--swarm-error-bg)'
    default: return 'var(--swarm-bg-hover)'
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
        <h1 class="overview-title">Archived Projects</h1>
        <p class="overview-subtitle">Projects that have been archived</p>
      </div>
      <button class="swarm-btn swarm-btn-ghost" @click="refresh">
        <UIcon name="i-heroicons-arrow-path" class="w-4 h-4" :class="{ 'animate-spin': pending }" />
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="pending && !projects?.length" class="loading-state">
      <UIcon name="i-heroicons-archive-box" class="w-8 h-8 animate-pulse" />
      <p>Loading archived projects...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!projects?.length" class="empty-state">
      <UIcon name="i-heroicons-archive-box" class="w-12 h-12" />
      <h2>No archived projects</h2>
      <p>Archive completed projects from the dashboard to move them here</p>
    </div>

    <!-- Project grid -->
    <div v-else class="projects-grid">
      <NuxtLink
        v-for="project in projects"
        :key="project.name"
        :to="`/project/${project.name}`"
        class="project-card archived"
      >
        <div class="card-header">
          <div class="project-name">{{ project.name }}</div>
          <div class="card-actions">
            <button
              class="unarchive-btn"
              :class="{ loading: archiving === project.name }"
              title="Restore from archive"
              @click="unarchiveProject(project.name, $event)"
            >
              <UIcon 
                :name="archiving === project.name ? 'i-heroicons-arrow-path' : 'i-heroicons-arrow-uturn-left'" 
                class="w-4 h-4"
                :class="{ 'animate-spin': archiving === project.name }"
              />
            </button>
            <div 
              class="status-badge"
              :style="{ 
                color: getStatusColor(project.status),
                background: getStatusBg(project.status)
              }"
            >
              {{ project.status }}
            </div>
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
            <span class="stat-label">Archived</span>
            <span class="stat-value">{{ formatDate(project.archivedAt || '') }}</span>
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

.project-card.archived {
  opacity: 0.8;
}

.project-card:hover {
  border-color: var(--swarm-accent);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  opacity: 1;
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

.unarchive-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  color: var(--swarm-text-muted);
  transition: all 0.15s;
}

.unarchive-btn:hover {
  background: var(--swarm-bg-hover);
  color: var(--swarm-accent);
}

.unarchive-btn.loading {
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
