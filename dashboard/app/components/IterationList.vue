<script setup lang="ts">
import type { Iteration } from '~/types/project'

const props = defineProps<{
  logs: Iteration[]
}>()

// Sort iterations newest first
const sortedIterations = computed(() => {
  return [...props.logs].sort((a, b) => b.iteration - a.iteration)
})

// Stats summary
const stats = computed(() => {
  const total = props.logs.length
  const successful = props.logs.filter(l => l.success).length
  const failed = total - successful
  const done = props.logs.some(l => l.done)
  return { total, successful, failed, done }
})
</script>

<template>
  <div class="section">
    <!-- Section Header -->
    <div class="section-header">
      <UIcon name="i-heroicons-queue-list" class="w-4 h-4" style="color: var(--swarm-accent);" />
      <h2 class="section-title">Recent Iterations</h2>
      <span class="section-badge">{{ stats.total }}</span>
      <span class="view-all">View all</span>
    </div>

    <!-- Content -->
    <div class="section-body">
      <!-- Quick Stats Bar -->
      <div class="stats-bar" v-if="stats.total > 0">
        <span class="stat success">
          <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
          <span class="stat-num">{{ stats.successful }}</span>
          <span class="stat-label">passed</span>
        </span>
        <span v-if="stats.failed > 0" class="stat error">
          <UIcon name="i-heroicons-x-circle" class="w-4 h-4" />
          <span class="stat-num">{{ stats.failed }}</span>
          <span class="stat-label">failed</span>
        </span>
        <span v-if="stats.done" class="done-badge">
          <UIcon name="i-heroicons-check-badge" class="w-4 h-4" />
          Completed
        </span>
      </div>

      <!-- Empty State -->
      <div v-if="sortedIterations.length === 0" class="empty-state">
        <UIcon name="i-heroicons-inbox" class="w-12 h-12 mx-auto mb-3" style="color: var(--swarm-text-muted);" />
        <p class="empty-title">No iterations yet</p>
        <p class="empty-text">Iterations will appear here as the build progresses</p>
      </div>

      <!-- Iteration List -->
      <div v-else class="iteration-list">
        <IterationItem
          v-for="iteration in sortedIterations"
          :key="iteration.iteration"
          :iteration="iteration"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.section {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  background: var(--swarm-bg-hover);
  border-bottom: 1px solid var(--swarm-border);
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  flex: 1;
}

.section-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--swarm-border);
  color: var(--swarm-text-muted);
}

.view-all {
  font-size: 13px;
  color: var(--swarm-accent);
  cursor: pointer;
}

.view-all:hover {
  text-decoration: underline;
}

.section-body {
  padding: 16px 20px;
}

.stats-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: var(--swarm-bg-hover);
  border-radius: 8px;
  margin-bottom: 16px;
}

.stat {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.stat.success {
  color: var(--swarm-success);
}

.stat.error {
  color: var(--swarm-error);
}

.stat-num {
  font-weight: 600;
}

.stat-label {
  color: var(--swarm-text-muted);
}

.done-badge {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  background: var(--swarm-accent);
  color: white;
  font-size: 12px;
  font-weight: 500;
}

.empty-state {
  text-align: center;
  padding: 32px;
}

.empty-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--swarm-text-secondary);
  margin-bottom: 4px;
}

.empty-text {
  font-size: 13px;
  color: var(--swarm-text-muted);
}

.iteration-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
