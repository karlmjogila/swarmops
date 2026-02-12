<template>
  <Teleport to="body">
    <div class="notification-container" aria-live="polite" aria-atomic="true">
      <TransitionGroup name="notification">
        <div
          v-for="notification in notifications"
          :key="notification.id"
          class="notification"
          :class="[notification.type, { dismissible: notification.dismissible }]"
          role="alert"
        >
          <div class="notification-icon">
            <svg v-if="notification.type === 'success'" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
            </svg>
            <svg v-else-if="notification.type === 'error'" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd" />
            </svg>
            <svg v-else-if="notification.type === 'warning'" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
            </svg>
            <svg v-else viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clip-rule="evenodd" />
            </svg>
          </div>
          
          <div class="notification-content">
            <div class="notification-title">{{ notification.title }}</div>
            <div v-if="notification.message" class="notification-message">
              {{ notification.message }}
            </div>
          </div>
          
          <button
            v-if="notification.dismissible"
            class="notification-dismiss"
            @click="dismiss(notification.id)"
            aria-label="Dismiss notification"
          >
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const { notifications, removeNotification } = useNotifications()

const dismiss = (id: string): void => {
  removeNotification(id)
}
</script>

<style scoped>
.notification-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-width: 420px;
  width: 100%;
  pointer-events: none;
}

.notification {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-radius: 12px;
  background: var(--color-surface-elevated, hsl(0, 0%, 100%));
  border: 1px solid var(--color-border, hsl(210, 20%, 90%));
  box-shadow: 
    0 4px 6px hsl(210 20% 20% / 0.04),
    0 8px 20px hsl(210 20% 20% / 0.08),
    0 0 0 1px hsl(210 20% 20% / 0.02);
  pointer-events: auto;
  font-family: var(--font-body, 'Inter', sans-serif);
}

.notification-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  margin-top: 1px;
}

.notification-icon svg {
  width: 100%;
  height: 100%;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text-primary, hsl(210, 25%, 8%));
  line-height: 1.4;
}

.notification-message {
  font-size: 0.85rem;
  color: var(--color-text-secondary, hsl(210, 15%, 45%));
  margin-top: 0.25rem;
  line-height: 1.4;
}

.notification-dismiss {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--color-text-tertiary, hsl(210, 12%, 65%));
  cursor: pointer;
  transition: all 0.15s ease;
  margin: -0.25rem -0.25rem -0.25rem 0;
}

.notification-dismiss:hover {
  background: var(--color-surface-deep, hsl(210, 20%, 96%));
  color: var(--color-text-secondary, hsl(210, 15%, 45%));
}

.notification-dismiss svg {
  width: 16px;
  height: 16px;
}

/* Type-specific styles */
.notification.success {
  border-left: 3px solid hsl(142, 76%, 36%);
}

.notification.success .notification-icon {
  color: hsl(142, 76%, 36%);
}

.notification.error {
  border-left: 3px solid hsl(0, 84%, 60%);
}

.notification.error .notification-icon {
  color: hsl(0, 84%, 60%);
}

.notification.warning {
  border-left: 3px solid hsl(38, 92%, 50%);
}

.notification.warning .notification-icon {
  color: hsl(38, 92%, 50%);
}

.notification.info {
  border-left: 3px solid hsl(190, 85%, 45%);
}

.notification.info .notification-icon {
  color: hsl(190, 85%, 45%);
}

/* Animations */
.notification-enter-active {
  animation: notification-in 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.notification-leave-active {
  animation: notification-out 0.2s ease-out forwards;
}

.notification-move {
  transition: transform 0.3s ease;
}

@keyframes notification-in {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes notification-out {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(100%);
  }
}

/* Dark mode */
:root[data-theme="dark"] .notification,
.dark .notification {
  background: hsl(220, 18%, 12%);
  border-color: hsl(220, 15%, 22%);
}

:root[data-theme="dark"] .notification-title,
.dark .notification-title {
  color: hsl(220, 15%, 92%);
}

:root[data-theme="dark"] .notification-message,
.dark .notification-message {
  color: hsl(220, 10%, 65%);
}

/* Responsive */
@media (max-width: 480px) {
  .notification-container {
    right: 0.5rem;
    left: 0.5rem;
    max-width: none;
  }
  
  .notification {
    padding: 0.875rem 1rem;
  }
}
</style>
