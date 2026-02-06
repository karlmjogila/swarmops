<script setup lang="ts">
import type { Iteration } from '~/types/project'

const props = defineProps<{
  iteration: Iteration
}>()

const toast = useToast()
const expanded = ref(false)

// Format timestamp for display
function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return timestamp
  }
}

// Format duration in seconds
function formatDuration(duration: number | undefined): string {
  if (!duration) return '-'
  if (duration < 60) return `${duration}s`
  const mins = Math.floor(duration / 60)
  const secs = duration % 60
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`
}

// Copy output to clipboard
async function copyOutput() {
  if (props.iteration.output) {
    try {
      await navigator.clipboard.writeText(props.iteration.output)
      toast.add({
        title: 'Copied to clipboard',
        icon: 'i-heroicons-clipboard-document-check',
        color: 'success',
        duration: 2000
      })
    } catch {
      toast.add({
        title: 'Failed to copy',
        icon: 'i-heroicons-exclamation-triangle',
        color: 'error',
        duration: 2000
      })
    }
  }
}

function toggleExpand() {
  expanded.value = !expanded.value
}
</script>

<template>
  <div class="iteration-item" :class="{ expanded, success: iteration.success, failed: !iteration.success }">
    <!-- Summary Row -->
    <div class="item-header" @click="toggleExpand">
      <div class="item-info">
        <!-- Iteration Number -->
        <span class="iteration-num">#{{ iteration.iteration }}</span>

        <!-- Status Badge -->
        <span class="status-badge" :class="iteration.success ? 'success' : 'error'">
          <UIcon
            :name="iteration.success ? 'i-heroicons-check-circle' : 'i-heroicons-x-circle'"
            class="w-3.5 h-3.5"
          />
          {{ iteration.success ? 'Passed' : 'Failed' }}
        </span>

        <!-- Timestamp -->
        <span class="meta-item">
          <UIcon name="i-heroicons-clock" class="w-3.5 h-3.5" />
          {{ formatTime(iteration.timestamp) }}
        </span>

        <!-- Duration -->
        <span class="meta-item">
          {{ formatDuration(iteration.duration) }}
        </span>

        <!-- DONE Badge -->
        <span v-if="iteration.done" class="done-badge">
          <UIcon name="i-heroicons-check-badge" class="w-3.5 h-3.5" />
          Done
        </span>
      </div>

      <!-- Expand Toggle -->
      <UIcon
        :name="expanded ? 'i-heroicons-chevron-up' : 'i-heroicons-chevron-down'"
        class="w-4 h-4 toggle-icon"
      />
    </div>

    <!-- Expanded Content -->
    <div v-if="expanded" class="item-content">
      <!-- Output -->
      <div v-if="iteration.output" class="output-section">
        <pre class="ralph-pre">{{ iteration.output }}</pre>
        <button class="copy-btn" @click.stop="copyOutput">
          <UIcon name="i-heroicons-clipboard-document" class="w-4 h-4" />
          Copy
        </button>
      </div>
      <div v-else class="no-output">
        <UIcon name="i-heroicons-document" class="w-4 h-4" />
        No output recorded
      </div>

      <!-- Files Changed -->
      <div v-if="iteration.filesChanged?.length" class="files-section">
        <div class="files-label">Files Changed</div>
        <div class="files-list">
          <span v-for="file in iteration.filesChanged" :key="file" class="file-tag">
            {{ file }}
          </span>
        </div>
      </div>

      <!-- Tokens -->
      <div v-if="iteration.tokensUsed" class="tokens-info">
        <UIcon name="i-heroicons-cpu-chip" class="w-3.5 h-3.5" />
        Tokens: {{ iteration.tokensUsed.toLocaleString() }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.iteration-item {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 8px;
  overflow: hidden;
}

.iteration-item.failed {
  border-color: rgba(239, 68, 68, 0.3);
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.15s;
}

.item-header:hover {
  background: var(--swarm-bg-hover);
}

.item-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.iteration-num {
  font-family: 'SF Mono', monospace;
  font-weight: 600;
  font-size: 14px;
  color: var(--swarm-text-primary);
  min-width: 40px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.status-badge.success {
  background: #ecfdf5;
  color: #059669;
}

.status-badge.error {
  background: #fef2f2;
  color: #dc2626;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--swarm-text-muted);
}

.done-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--swarm-accent);
  color: white;
  font-size: 11px;
  font-weight: 500;
}

.toggle-icon {
  color: var(--swarm-text-muted);
  flex-shrink: 0;
}

.item-content {
  padding: 16px;
  border-top: 1px solid var(--swarm-border);
  background: var(--swarm-bg-hover);
}

.output-section {
  position: relative;
}

.output-section .swarm-pre {
  max-height: 300px;
  overflow-y: auto;
}

.copy-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 6px;
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  font-size: 12px;
  color: var(--swarm-text-secondary);
  cursor: pointer;
}

.copy-btn:hover {
  background: var(--swarm-bg-hover);
}

.no-output {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--swarm-text-muted);
  font-style: italic;
}

.files-section {
  margin-top: 16px;
}

.files-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--swarm-text-muted);
  margin-bottom: 8px;
}

.files-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.file-tag {
  font-family: 'SF Mono', monospace;
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  color: var(--swarm-text-secondary);
}

.tokens-info {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  font-size: 12px;
  color: var(--swarm-text-muted);
}
</style>
