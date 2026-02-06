<script setup lang="ts">
interface Props {
  icon?: string
  title: string
  description?: string
  ctaText?: string
  ctaIcon?: string
  size?: 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  icon: 'i-heroicons-inbox',
  size: 'md',
})

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <div class="empty-state" :class="`empty-${size}`">
    <div class="empty-icon-wrap">
      <UIcon :name="icon" class="empty-icon" />
    </div>

    <h3 class="empty-title">{{ title }}</h3>

    <p v-if="description" class="empty-description">{{ description }}</p>

    <slot />

    <button
      v-if="ctaText"
      class="swarm-btn swarm-btn-primary empty-cta"
      @click="emit('action')"
    >
      <UIcon v-if="ctaIcon" :name="ctaIcon" class="w-4 h-4" />
      {{ ctaText }}
    </button>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.empty-sm { padding: 24px 16px; }
.empty-md { padding: 48px 24px; }
.empty-lg { padding: 64px 32px; }

.empty-icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: var(--swarm-bg-secondary);
  border: 1px solid var(--swarm-border);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.empty-sm .empty-icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  margin-bottom: 12px;
}

.empty-lg .empty-icon-wrap {
  width: 72px;
  height: 72px;
  border-radius: 18px;
  margin-bottom: 20px;
}

.empty-icon {
  width: 24px;
  height: 24px;
  color: var(--swarm-text-muted);
}

.empty-sm .empty-icon { width: 18px; height: 18px; }
.empty-lg .empty-icon { width: 32px; height: 32px; }

.empty-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin: 0 0 4px;
}

.empty-sm .empty-title { font-size: 13px; }
.empty-lg .empty-title { font-size: 18px; }

.empty-description {
  font-size: 13px;
  color: var(--swarm-text-muted);
  margin: 0;
  max-width: 280px;
  line-height: 1.5;
}

.empty-sm .empty-description { font-size: 12px; }
.empty-lg .empty-description { font-size: 14px; max-width: 360px; }

.empty-cta {
  margin-top: 16px;
}
</style>
