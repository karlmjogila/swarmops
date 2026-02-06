<script setup lang="ts">
const props = defineProps<{
  open: boolean
  connected?: boolean
}>()

const emit = defineEmits<{
  close: []
  reconnect: []
}>()

const panelRef = ref<HTMLElement | null>(null)

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.open) {
    emit('close')
  }
}

function handleBackdropClick(e: MouseEvent) {
  if (e.target === e.currentTarget) {
    emit('close')
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

// Panel focus removed - let ChatInterface handle input focus
// The panel has tabindex="-1" for accessibility but shouldn't steal focus
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="open"
        class="modal-backdrop"
        @click="handleBackdropClick"
      >
        <div
          ref="panelRef"
          class="modal-panel"
          role="dialog"
          aria-modal="true"
          aria-label="Chat with SwarmOps"
          tabindex="-1"
        >
          <header class="modal-header">
            <div class="header-title">
              <UIcon name="i-heroicons-chat-bubble-left-ellipsis" class="header-icon" />
              <span>SwarmOps Chat</span>
            </div>
            <div class="header-actions">
              <ChatConnectionStatus
                :connected="connected ?? true"
                @reconnect="emit('reconnect')"
              />
              <button
                class="close-btn"
                aria-label="Close chat"
                @click="emit('close')"
              >
                <UIcon name="i-heroicons-x-mark" />
              </button>
            </div>
          </header>

          <main class="modal-content">
            <slot />
          </main>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal-panel {
  position: absolute;
  right: 0;
  top: 0;
  height: 100vh;
  width: 400px;
  max-width: calc(100vw - 16px);
  background: var(--swarm-bg-secondary);
  border-left: 1px solid var(--swarm-border);
  display: flex;
  flex-direction: column;
  box-shadow: 
    -8px 0 32px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(16, 185, 129, 0.05);
  outline: none;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--swarm-border-light);
  background: var(--swarm-bg-card);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 15px;
  color: var(--swarm-text-primary);
}

.header-icon {
  width: 20px;
  height: 20px;
  color: var(--swarm-accent-light);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid var(--swarm-border, #e0e0e0);
  background: var(--swarm-bg-hover, #f5f5f5);
  color: var(--swarm-text-secondary, #4a4a4a);
  cursor: pointer;
  transition: all 0.15s ease;
}

.close-btn:hover {
  background: var(--swarm-bg-tertiary, #e8e8e8);
  border-color: var(--swarm-border, #d0d0d0);
  color: var(--swarm-text-primary, #1a1a1a);
}

.close-btn:active {
  transform: scale(0.95);
}

.modal-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Transitions */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.modal-enter-active .modal-panel,
.modal-leave-active .modal-panel {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.modal-enter-from,
.modal-leave-to {
  background: rgba(0, 0, 0, 0);
  backdrop-filter: blur(0);
}

.modal-enter-from .modal-panel,
.modal-leave-to .modal-panel {
  transform: translateX(100%);
}

/* Mobile responsive */
@media (max-width: 640px) {
  .modal-panel {
    width: calc(100vw - 16px);
  }
  
  .modal-header {
    padding: 14px 16px;
  }
}
</style>
