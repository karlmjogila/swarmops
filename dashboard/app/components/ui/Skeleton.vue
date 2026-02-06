<script setup lang="ts">
type SkeletonVariant = 'rect' | 'circle' | 'text' | 'avatar' | 'badge' | 'button'

interface Props {
  variant?: SkeletonVariant
  width?: string
  height?: string
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'full'
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'rect',
  rounded: 'md',
})

const classes = computed(() => {
  const base = 'skeleton-element animate-pulse'
  const roundedMap = {
    none: 'rounded-none',
    sm: 'rounded',
    md: 'rounded-lg',
    lg: 'rounded-xl',
    full: 'rounded-full',
  }
  
  const variantDefaults = {
    rect: 'w-full h-4',
    circle: 'w-10 h-10 rounded-full',
    text: 'w-full h-4 rounded',
    avatar: 'w-10 h-10 rounded-full',
    badge: 'w-16 h-6 rounded-full',
    button: 'w-24 h-10 rounded-lg',
  }
  
  const rounded = props.variant === 'circle' || props.variant === 'avatar' || props.variant === 'badge'
    ? ''
    : roundedMap[props.rounded]
  
  return [base, variantDefaults[props.variant], rounded].filter(Boolean).join(' ')
})

const styles = computed(() => ({
  width: props.width,
  height: props.height,
  background: 'var(--swarm-bg-tertiary)',
}))
</script>

<template>
  <div :class="classes" :style="styles" />
</template>

<style scoped>
.skeleton-element {
  position: relative;
  overflow: hidden;
}

.skeleton-element::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(99, 102, 241, 0.05) 25%,
    rgba(255, 255, 255, 0.08) 50%,
    rgba(99, 102, 241, 0.05) 75%,
    transparent 100%
  );
  animation: shimmer 2s infinite ease-in-out;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}
</style>
