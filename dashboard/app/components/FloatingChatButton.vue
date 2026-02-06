<script setup lang="ts">
defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  toggle: []
}>()
</script>

<template>
  <button
    class="floating-chat-btn"
    :class="{ 'is-open': open }"
    :aria-label="open ? 'Close chat' : 'Open chat'"
    :aria-expanded="open"
    @click="emit('toggle')"
  >
    <Transition name="icon-swap" mode="out-in">
      <UIcon
        v-if="!open"
        key="chat"
        name="i-heroicons-chat-bubble-left-ellipsis"
        class="icon"
      />
      <UIcon
        v-else
        key="close"
        name="i-heroicons-x-mark"
        class="icon"
      />
    </Transition>
    <span class="pulse-ring" />
  </button>
</template>

<style scoped>
.floating-chat-btn {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 50;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  box-shadow: 
    0 4px 20px rgba(16, 185, 129, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.1) inset;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.floating-chat-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.15) 0%, transparent 50%);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.floating-chat-btn:hover {
  transform: scale(1.08);
  box-shadow: 
    0 6px 28px rgba(16, 185, 129, 0.5),
    0 0 40px rgba(16, 185, 129, 0.3),
    0 0 0 1px rgba(255, 255, 255, 0.15) inset;
}

.floating-chat-btn:hover::before {
  opacity: 1;
}

.floating-chat-btn:active {
  transform: scale(0.95);
}

.floating-chat-btn.is-open {
  background: var(--swarm-bg-card, #ffffff);
  color: var(--swarm-text-secondary, #4a4a4a);
  box-shadow: 
    0 4px 16px rgba(0, 0, 0, 0.15),
    0 0 0 1px var(--swarm-border, #e0e0e0);
  /* Move left when panel is open (400px panel + 24px margin) */
  transform: translateX(-408px);
}

.floating-chat-btn.is-open:hover {
  background: var(--swarm-bg-hover, #f5f5f5);
  color: var(--swarm-text-primary, #1a1a1a);
  box-shadow: 
    0 6px 24px rgba(0, 0, 0, 0.2),
    0 0 0 1px var(--swarm-border, #e0e0e0);
  transform: translateX(-408px) scale(1.08);
}

.icon {
  width: 24px;
  height: 24px;
  position: relative;
  z-index: 1;
}

.pulse-ring {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid rgba(16, 185, 129, 0.6);
  opacity: 0;
  animation: pulse-ring 2s ease-out infinite;
}

.floating-chat-btn.is-open .pulse-ring {
  display: none;
}

@keyframes pulse-ring {
  0% {
    transform: scale(0.8);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.4);
    opacity: 0;
  }
}

/* Icon swap transitions */
.icon-swap-enter-active,
.icon-swap-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.icon-swap-enter-from {
  opacity: 0;
  transform: rotate(-90deg) scale(0.5);
}

.icon-swap-leave-to {
  opacity: 0;
  transform: rotate(90deg) scale(0.5);
}

/* Mobile adjustments */
@media (max-width: 768px) {
  .floating-chat-btn {
    right: 16px;
    bottom: 16px;
    width: 52px;
    height: 52px;
  }

  .icon {
    width: 22px;
    height: 22px;
  }
}

/* Reduce motion for accessibility */
@media (prefers-reduced-motion: reduce) {
  .floating-chat-btn {
    transition: none;
  }

  .pulse-ring {
    animation: none;
    display: none;
  }

  .icon-swap-enter-active,
  .icon-swap-leave-active {
    transition: opacity 0.1s ease;
  }

  .icon-swap-enter-from,
  .icon-swap-leave-to {
    transform: none;
  }
}
</style>
