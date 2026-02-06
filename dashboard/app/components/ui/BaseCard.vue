<script setup lang="ts">
interface Props {
  /** Whether the card is clickable (enables hover effects) */
  clickable?: boolean
  /** Remove default padding */
  noPadding?: boolean
  /** Elevated style with stronger shadow */
  elevated?: boolean
  /** Compact padding */
  compact?: boolean
  /** Disable hover effects */
  noHover?: boolean
  /** Custom border color variant */
  variant?: 'default' | 'success' | 'warning' | 'error' | 'accent'
  /** Loading state */
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  clickable: false,
  noPadding: false,
  elevated: false,
  compact: false,
  noHover: false,
  variant: 'default',
  loading: false,
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

function handleClick(e: MouseEvent) {
  if (props.clickable && !props.loading) {
    emit('click', e)
  }
}
</script>

<template>
  <div
    class="base-card"
    :class="{
      'base-card--clickable': clickable && !loading,
      'base-card--no-padding': noPadding,
      'base-card--elevated': elevated,
      'base-card--compact': compact,
      'base-card--no-hover': noHover || loading,
      'base-card--loading': loading,
      [`base-card--${variant}`]: variant !== 'default',
    }"
    :role="clickable ? 'button' : undefined"
    :tabindex="clickable ? 0 : undefined"
    @click="handleClick"
    @keydown.enter="clickable ? handleClick($event as unknown as MouseEvent) : undefined"
  >
    <!-- Loading overlay -->
    <div v-if="loading" class="base-card__loading">
      <div class="base-card__spinner" />
    </div>

    <!-- Header slot -->
    <div v-if="$slots.header" class="base-card__header">
      <slot name="header" />
    </div>

    <!-- Default content slot -->
    <div class="base-card__content">
      <slot />
    </div>

    <!-- Footer slot -->
    <div v-if="$slots.footer" class="base-card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<style scoped>
.base-card {
  background: var(--swarm-bg-card);
  background-image: var(--swarm-gradient-card);
  border: 1px solid var(--swarm-border-light);
  border-radius: 16px;
  padding: 20px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(10px);
}

.base-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--swarm-gradient-surface);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

/* Hover states */
.base-card:not(.base-card--no-hover):hover {
  background: var(--swarm-bg-card-hover);
  border-color: var(--swarm-border);
  transform: translateY(-2px);
  box-shadow: 
    0 8px 24px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(99, 102, 241, 0.1);
}

.base-card:not(.base-card--no-hover):hover::before {
  opacity: 1;
}

/* Clickable variant */
.base-card--clickable {
  cursor: pointer;
}

.base-card--clickable:focus-visible {
  outline: 2px solid var(--swarm-accent);
  outline-offset: 2px;
}

.base-card--clickable:active {
  transform: translateY(0);
  transition-duration: 0.1s;
}

/* Padding variants */
.base-card--no-padding {
  padding: 0;
}

.base-card--no-padding .base-card__content {
  padding: 0;
}

.base-card--compact {
  padding: 12px;
}

/* Elevated variant */
.base-card--elevated {
  background: var(--swarm-bg-elevated);
  box-shadow: 
    0 4px 16px rgba(0, 0, 0, 0.3),
    0 0 0 1px var(--swarm-border-light);
}

.base-card--elevated:not(.base-card--no-hover):hover {
  box-shadow: 
    0 12px 32px rgba(0, 0, 0, 0.5),
    0 0 0 1px var(--swarm-border),
    0 0 24px var(--swarm-accent-glow);
}

/* Color variants */
.base-card--success {
  border-color: rgba(16, 185, 129, 0.3);
}

.base-card--success:not(.base-card--no-hover):hover {
  border-color: rgba(16, 185, 129, 0.5);
  box-shadow: 
    0 8px 24px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(16, 185, 129, 0.2),
    0 0 16px var(--swarm-success-glow);
}

.base-card--warning {
  border-color: rgba(245, 158, 11, 0.3);
}

.base-card--warning:not(.base-card--no-hover):hover {
  border-color: rgba(245, 158, 11, 0.5);
  box-shadow: 
    0 8px 24px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(245, 158, 11, 0.2),
    0 0 16px var(--swarm-warning-glow);
}

.base-card--error {
  border-color: rgba(239, 68, 68, 0.3);
}

.base-card--error:not(.base-card--no-hover):hover {
  border-color: rgba(239, 68, 68, 0.5);
  box-shadow: 
    0 8px 24px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(239, 68, 68, 0.2),
    0 0 16px var(--swarm-error-glow);
}

.base-card--accent {
  border-color: rgba(99, 102, 241, 0.3);
}

.base-card--accent:not(.base-card--no-hover):hover {
  border-color: rgba(99, 102, 241, 0.5);
  box-shadow: 
    0 8px 24px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(99, 102, 241, 0.2),
    0 0 16px var(--swarm-accent-glow);
}

/* Loading state */
.base-card--loading {
  pointer-events: none;
}

.base-card__loading {
  position: absolute;
  inset: 0;
  background: rgba(8, 11, 20, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  backdrop-filter: blur(2px);
}

.base-card__spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--swarm-border-light);
  border-top-color: var(--swarm-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Header styles */
.base-card__header {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--swarm-border-light);
}

.base-card--compact .base-card__header {
  margin-bottom: 12px;
  padding-bottom: 12px;
}

.base-card--no-padding .base-card__header {
  padding: 20px 20px 16px;
  margin: 0;
}

/* Content styles */
.base-card__content {
  position: relative;
  z-index: 1;
}

/* Footer styles */
.base-card__footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--swarm-border-light);
}

.base-card--compact .base-card__footer {
  margin-top: 12px;
  padding-top: 12px;
}

.base-card--no-padding .base-card__footer {
  padding: 16px 20px 20px;
  margin: 0;
}
</style>
