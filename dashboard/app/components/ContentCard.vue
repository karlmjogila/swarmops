<script setup lang="ts">
const props = withDefaults(defineProps<{
  title: string
  summary?: string
  icon?: string
  iconColor?: string
  defaultOpen?: boolean
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info'
}>(), {
  icon: 'i-heroicons-document-text',
  iconColor: 'var(--swarm-text-muted)',
  defaultOpen: false,
  variant: 'default'
})

const isOpen = ref(props.defaultOpen)

const variantStyles = computed(() => {
  const styles: Record<string, { border: string; iconBg: string; iconColor: string }> = {
    default: {
      border: 'var(--swarm-border)',
      iconBg: 'var(--swarm-bg-hover)',
      iconColor: 'var(--swarm-text-muted)'
    },
    success: {
      border: 'rgba(16, 185, 129, 0.3)',
      iconBg: 'rgba(16, 185, 129, 0.1)',
      iconColor: '#10b981'
    },
    warning: {
      border: 'rgba(245, 158, 11, 0.3)',
      iconBg: 'rgba(245, 158, 11, 0.1)',
      iconColor: '#f59e0b'
    },
    error: {
      border: 'rgba(239, 68, 68, 0.3)',
      iconBg: 'rgba(239, 68, 68, 0.1)',
      iconColor: '#ef4444'
    },
    info: {
      border: 'rgba(59, 130, 246, 0.3)',
      iconBg: 'rgba(59, 130, 246, 0.1)',
      iconColor: '#3b82f6'
    }
  }
  return styles[props.variant] || styles.default
})
</script>

<template>
  <div class="content-card" :style="{ borderColor: variantStyles.border }">
    <div class="card-header" @click="isOpen = !isOpen">
      <div class="header-left">
        <div class="icon-wrapper" :style="{ background: variantStyles.iconBg }">
          <UIcon :name="icon" class="w-4 h-4" :style="{ color: variantStyles.iconColor }" />
        </div>
        <div class="header-text">
          <h3 class="card-title">{{ title }}</h3>
          <p v-if="summary && !isOpen" class="card-summary">{{ summary }}</p>
        </div>
      </div>
      <UIcon 
        :name="isOpen ? 'i-heroicons-chevron-up' : 'i-heroicons-chevron-down'" 
        class="w-4 h-4 toggle-icon"
      />
    </div>
    <div v-if="isOpen" class="card-content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.content-card {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border);
  border-radius: 10px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  cursor: pointer;
  transition: background 0.15s;
}

.card-header:hover {
  background: var(--swarm-bg-hover);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.icon-wrapper {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.header-text {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin: 0;
}

.card-summary {
  font-size: 12px;
  color: var(--swarm-text-muted);
  margin: 2px 0 0 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toggle-icon {
  color: var(--swarm-text-muted);
  flex-shrink: 0;
}

.card-content {
  padding: 0 16px 16px 16px;
  border-top: 1px solid var(--swarm-border);
  margin-top: 0;
  padding-top: 14px;
}

.card-content :deep(.swarm-pre) {
  margin: 0;
  max-height: 400px;
  overflow-y: auto;
}

.card-content :deep(ul) {
  margin: 0;
  padding-left: 20px;
}

.card-content :deep(li) {
  font-size: 13px;
  color: var(--swarm-text-secondary);
  margin-bottom: 6px;
}

.card-content :deep(li.done) {
  color: var(--swarm-text-muted);
  text-decoration: line-through;
}
</style>
