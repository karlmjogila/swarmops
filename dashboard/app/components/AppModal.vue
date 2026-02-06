<script setup lang="ts">
const props = defineProps<{
  open?: boolean
  title?: string
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl'
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

const isOpen = computed({
  get: () => props.open ?? false,
  set: (value) => emit('update:open', value)
})

const sizeStyles = computed(() => {
  const sizes: Record<string, string> = {
    sm: '380px',
    md: '480px',
    lg: '560px',
    xl: '680px',
    '2xl': '800px'
  }
  return { maxWidth: sizes[props.size || 'md'] }
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click.self="isOpen = false">
        <div class="app-modal" :style="sizeStyles">
          <div class="modal-header" v-if="title">
            <h2>{{ title }}</h2>
            <button class="close-btn" @click="isOpen = false">
              <UIcon name="i-heroicons-x-mark" class="w-5 h-5" />
            </button>
          </div>
          
          <div class="modal-body">
            <slot />
          </div>
          
          <div class="modal-footer" v-if="$slots.footer">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  padding: 24px;
}

.app-modal {
  background: var(--swarm-bg-card, #1a1a1a);
  border: 1px solid var(--swarm-border, #333);
  border-radius: 12px;
  width: 100%;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--swarm-border, #333);
  flex-shrink: 0;
}

.modal-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--swarm-text-primary, #fff);
  margin: 0;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--swarm-text-muted, #888);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.close-btn:hover {
  background: var(--swarm-bg-hover, #333);
  color: var(--swarm-text-primary, #fff);
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 20px;
  border-top: 1px solid var(--swarm-border, #333);
  background: var(--swarm-bg-hover, #222);
  flex-shrink: 0;
}

/* Transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.15s ease;
}

.modal-enter-active .app-modal,
.modal-leave-active .app-modal {
  transition: transform 0.15s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .app-modal,
.modal-leave-to .app-modal {
  transform: scale(0.95) translateY(-10px);
}
</style>
