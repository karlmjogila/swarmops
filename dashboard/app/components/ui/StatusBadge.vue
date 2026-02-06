<script setup lang="ts">
export type BadgeVariant = 'success' | 'warning' | 'error' | 'neutral'
export type BadgeSize = 'sm' | 'md' | 'lg'

interface Props {
  variant?: BadgeVariant
  size?: BadgeSize
  label?: string
  dot?: boolean
  pulse?: boolean
  icon?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'neutral',
  size: 'md',
  dot: false,
  pulse: false
})

const variantStyles = {
  success: {
    bg: 'var(--swarm-success-bg)',
    border: 'rgba(16, 185, 129, 0.25)',
    color: 'var(--swarm-success)',
    glow: 'var(--swarm-success-glow)'
  },
  warning: {
    bg: 'var(--swarm-warning-bg)',
    border: 'rgba(245, 158, 11, 0.25)',
    color: 'var(--swarm-warning)',
    glow: 'var(--swarm-warning-glow)'
  },
  error: {
    bg: 'var(--swarm-error-bg)',
    border: 'rgba(239, 68, 68, 0.25)',
    color: 'var(--swarm-error)',
    glow: 'var(--swarm-error-glow)'
  },
  neutral: {
    bg: 'var(--swarm-neutral-bg)',
    border: 'rgba(100, 116, 139, 0.25)',
    color: 'var(--swarm-neutral)',
    glow: 'rgba(100, 116, 139, 0.3)'
  }
}

const sizeStyles = {
  sm: { padding: '2px 8px', fontSize: '11px', dotSize: '6px', iconSize: '12px', gap: '4px' },
  md: { padding: '4px 10px', fontSize: '12px', dotSize: '8px', iconSize: '14px', gap: '6px' },
  lg: { padding: '6px 14px', fontSize: '13px', dotSize: '10px', iconSize: '16px', gap: '8px' }
}

const currentVariant = computed(() => variantStyles[props.variant])
const currentSize = computed(() => sizeStyles[props.size])
</script>

<template>
  <span
    class="inline-flex items-center font-semibold tracking-wide uppercase rounded-full transition-all duration-200"
    :style="{
      padding: currentSize.padding,
      fontSize: currentSize.fontSize,
      gap: currentSize.gap,
      background: currentVariant.bg,
      border: `1px solid ${currentVariant.border}`,
      color: currentVariant.color,
      boxShadow: pulse ? `0 0 8px ${currentVariant.glow}` : 'none'
    }"
  >
    <span
      v-if="dot"
      class="relative flex shrink-0"
      :style="{ width: currentSize.dotSize, height: currentSize.dotSize }"
    >
      <span
        v-if="pulse"
        class="absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping"
        :style="{ background: currentVariant.color }"
      />
      <span
        class="relative inline-flex rounded-full h-full w-full"
        :style="{
          background: currentVariant.color,
          boxShadow: `0 0 6px ${currentVariant.glow}`
        }"
      />
    </span>
    <UIcon
      v-else-if="icon"
      :name="icon"
      class="shrink-0"
      :style="{ width: currentSize.iconSize, height: currentSize.iconSize }"
    />
    <span v-if="label">{{ label }}</span>
    <slot v-else />
  </span>
</template>
