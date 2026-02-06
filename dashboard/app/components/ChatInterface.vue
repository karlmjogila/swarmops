<script setup lang="ts">
import type { ChatMessage } from '~/composables/useChatSession'

const props = withDefaults(defineProps<{
  messages?: ChatMessage[]
  isTyping?: boolean
  isConnected?: boolean
  disabled?: boolean
  error?: string | null
}>(), {
  messages: () => [],
  isTyping: false,
  isConnected: true,
  disabled: false,
  error: null
})

const emit = defineEmits<{
  send: [message: string, image?: string]
  retry: [messageId: string]
  clearError: []
}>()

const inputValue = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)
const pendingImage = ref<string | null>(null) // base64 data URL
const isDragging = ref(false)

// Focus input - called on mount and exposed for parent
function focusInput() {
  nextTick(() => inputRef.value?.focus())
}

// Expose focus method for parent components
defineExpose({ focusInput })

function handleSend() {
  const content = inputValue.value.trim()
  const image = pendingImage.value
  
  // Allow sending with just image, just text, or both
  if ((!content && !image) || props.disabled) return
  
  emit('send', content || '(image attached)', image || undefined)
  inputValue.value = ''
  pendingImage.value = null
  
  // Keep focus on input after sending
  focusInput()
}

function handlePaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      e.preventDefault()
      const file = item.getAsFile()
      if (file) {
        const reader = new FileReader()
        reader.onload = (ev) => {
          pendingImage.value = ev.target?.result as string
        }
        reader.readAsDataURL(file)
      }
      return
    }
  }
}

function handleImageSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  
  const reader = new FileReader()
  reader.onload = (ev) => {
    pendingImage.value = ev.target?.result as string
  }
  reader.readAsDataURL(file)
  input.value = '' // reset for re-select
}

function clearImage() {
  pendingImage.value = null
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  isDragging.value = true
}

function handleDragLeave(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
  
  const file = e.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('image/')) {
    const reader = new FileReader()
    reader.onload = (ev) => {
      pendingImage.value = ev.target?.result as string
    }
    reader.readAsDataURL(file)
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
  // Shift+Enter allows newline naturally in textarea
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(() => props.messages.length, scrollToBottom)
watch(() => props.isTyping, (typing, wasTyping) => {
  scrollToBottom()
  // Refocus input when response arrives
  if (!typing && wasTyping) {
    focusInput()
  }
})

onMounted(() => {
  scrollToBottom()
  focusInput()
})
</script>

<template>
  <div 
    class="chat-interface"
    :class="{ 'is-dragging': isDragging }"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
  >
    <!-- Disconnection banner -->
    <Transition name="banner">
      <div v-if="!isConnected" class="disconnection-banner">
        <UIcon name="i-heroicons-wifi" class="banner-icon" />
        <span>Connection lost. Messages will be sent when reconnected.</span>
      </div>
    </Transition>

    <!-- Error banner -->
    <Transition name="banner">
      <div v-if="error" class="error-banner">
        <UIcon name="i-heroicons-exclamation-triangle" class="banner-icon" />
        <span>{{ error }}</span>
        <button class="dismiss-btn" @click="emit('clearError')">
          <UIcon name="i-heroicons-x-mark" />
        </button>
      </div>
    </Transition>

    <div ref="messagesContainer" class="messages-container">
      <div v-if="props.messages.length === 0 && !isTyping" class="empty-state">
        <UIcon name="i-heroicons-chat-bubble-bottom-center-text" class="empty-icon" />
        <p class="empty-title">Start a conversation</p>
        <p class="empty-subtitle">Send a message to chat with SwarmOps</p>
      </div>

      <TransitionGroup name="message" tag="div" class="messages-list">
        <div
          v-for="message in props.messages"
          :key="message.id"
          class="message"
          :class="[`message--${message.role}`, message.status && `message--${message.status}`]"
        >
          <div class="message-avatar">
            <UIcon
              :name="message.role === 'assistant' ? 'i-heroicons-cpu-chip' : 'i-heroicons-user'"
              class="avatar-icon"
            />
          </div>
          <div class="message-content">
            <div class="message-header">
              <span class="message-sender">
                {{ message.role === 'assistant' ? 'SwarmOps' : 'You' }}
              </span>
              <span class="message-time">
                {{ message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}
              </span>
            </div>
            <div v-if="message.image" class="message-image">
              <img :src="message.image" alt="Attached image" />
            </div>
            <div class="message-body">
              {{ message.content }}
            </div>
            <div v-if="message.status === 'error'" class="message-error">
              <UIcon name="i-heroicons-exclamation-circle" />
              <span>Failed to send</span>
              <button 
                class="retry-btn"
                title="Retry sending"
                @click="emit('retry', message.id)"
              >
                <UIcon name="i-heroicons-arrow-path" />
                Retry
              </button>
            </div>
          </div>
        </div>
      </TransitionGroup>

      <Transition name="typing">
        <div v-if="isTyping" class="typing-indicator">
          <div class="message-avatar">
            <UIcon name="i-heroicons-cpu-chip" class="avatar-icon thinking-pulse" />
          </div>
          <div class="typing-content">
            <span class="thinking-text">Agent is thinking...</span>
            <span class="typing-dot" />
            <span class="typing-dot" />
            <span class="typing-dot" />
          </div>
        </div>
      </Transition>
    </div>

    <!-- Image preview -->
    <Transition name="preview">
      <div v-if="pendingImage" class="image-preview">
        <img :src="pendingImage" alt="Pending attachment" />
        <button class="remove-image-btn" @click="clearImage">
          <UIcon name="i-heroicons-x-mark" />
        </button>
      </div>
    </Transition>

    <div class="input-area">
      <label class="attach-btn" title="Attach image">
        <UIcon name="i-heroicons-photo" />
        <input 
          type="file" 
          accept="image/*" 
          class="sr-only"
          @change="handleImageSelect"
        />
      </label>
      <textarea
        ref="inputRef"
        v-model="inputValue"
        class="message-input"
        placeholder="Type a message... (Shift+Enter for new line)"
        :disabled="disabled"
        rows="1"
        @keydown="handleKeydown"
        @paste="handlePaste"
      />
      <button
        class="send-button"
        :disabled="!inputValue.trim() || disabled"
        @click="handleSend"
      >
        <UIcon name="i-heroicons-paper-airplane" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-interface {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.chat-interface.is-dragging::after {
  content: 'Drop image here';
  position: absolute;
  inset: 0;
  background: rgba(16, 185, 129, 0.1);
  border: 2px dashed var(--swarm-accent, #10b981);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 500;
  color: var(--swarm-accent, #10b981);
  z-index: 10;
  pointer-events: none;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--swarm-text-muted);
  gap: 8px;
  padding: 32px;
}

.empty-icon {
  width: 48px;
  height: 48px;
  opacity: 0.5;
  margin-bottom: 8px;
}

.empty-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--swarm-text-secondary);
}

.empty-subtitle {
  font-size: 13px;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  gap: 12px;
  animation: messageIn 0.2s ease-out;
}

.message--user {
  flex-direction: row-reverse;
}

.message--sending {
  opacity: 0.7;
}

.message-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--swarm-bg-tertiary);
  border: 1px solid var(--swarm-border-light);
}

.message--assistant .message-avatar {
  background: linear-gradient(135deg, rgba(55, 65, 81, 0.15) 0%, rgba(75, 85, 99, 0.15) 100%);
  border-color: rgba(55, 65, 81, 0.3);
}

.message--user .message-avatar {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(20, 184, 166, 0.15) 100%);
  border-color: rgba(16, 185, 129, 0.3);
}

.avatar-icon {
  width: 16px;
  height: 16px;
  color: var(--swarm-text-secondary);
}

.message--assistant .avatar-icon {
  color: #374151;
}

.message--user .avatar-icon {
  color: var(--swarm-success);
}

.message-content {
  flex: 1;
  max-width: 280px;
}

.message--user .message-content {
  text-align: right;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.message--user .message-header {
  flex-direction: row-reverse;
}

.message-sender {
  font-size: 12px;
  font-weight: 600;
  color: var(--swarm-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.message-time {
  font-size: 11px;
  color: var(--swarm-text-muted);
}

.message-image {
  margin-bottom: 8px;
}

.message-image img {
  max-width: 200px;
  max-height: 150px;
  border-radius: 8px;
  border: 1px solid var(--swarm-border-light);
}

.message--user .message-image img {
  border-color: rgba(255, 255, 255, 0.2);
}

.message-body {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  word-wrap: break-word;
}

.message--assistant .message-body {
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border-light);
  color: var(--swarm-text-primary);
  border-bottom-left-radius: 4px;
}

.message--user .message-body {
  background: var(--swarm-gradient-primary);
  color: white;
  border-bottom-right-radius: 4px;
  box-shadow: 0 2px 8px var(--swarm-accent-glow);
}

.message-error {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  font-size: 11px;
  color: var(--swarm-error);
}

.message-error .u-icon {
  width: 12px;
  height: 12px;
}

.retry-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  margin-left: 8px;
  font-size: 11px;
  font-weight: 500;
  color: var(--swarm-error);
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.retry-btn:hover {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
}

.retry-btn .u-icon {
  width: 10px;
  height: 10px;
}

/* Disconnection & Error banners */
.disconnection-banner,
.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  font-size: 12px;
  font-weight: 500;
}

.disconnection-banner {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.1) 0%, rgba(245, 158, 11, 0.05) 100%);
  border-bottom: 1px solid rgba(251, 191, 36, 0.2);
  color: var(--swarm-warning);
}

.error-banner {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(220, 38, 38, 0.05) 100%);
  border-bottom: 1px solid rgba(239, 68, 68, 0.2);
  color: var(--swarm-error);
}

.banner-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.dismiss-btn {
  margin-left: auto;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: inherit;
  opacity: 0.7;
  cursor: pointer;
  transition: all 0.15s ease;
}

.dismiss-btn:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.1);
}

/* Banner transitions */
.banner-enter-active,
.banner-leave-active {
  transition: all 0.2s ease;
}

.banner-enter-from,
.banner-leave-to {
  opacity: 0;
  transform: translateY(-100%);
}

.typing-indicator {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.typing-content {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 16px;
  background: var(--swarm-bg-card);
  border: 1px solid var(--swarm-border-light);
  border-radius: 12px;
  border-bottom-left-radius: 4px;
}

.thinking-text {
  font-size: 13px;
  color: var(--swarm-text-muted);
  margin-right: 4px;
}

.thinking-pulse {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--swarm-text-muted);
  animation: typingBounce 1.4s infinite ease-in-out;
}

.typing-dot:nth-child(1) {
  animation-delay: 0s;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

/* Image preview */
.image-preview {
  position: relative;
  padding: 12px 16px;
  border-top: 1px solid var(--swarm-border-light);
  background: var(--swarm-bg-tertiary);
}

.image-preview img {
  max-height: 120px;
  max-width: 200px;
  border-radius: 8px;
  border: 1px solid var(--swarm-border-light);
}

.remove-image-btn {
  position: absolute;
  top: 8px;
  right: 12px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  cursor: pointer;
  transition: background 0.15s ease;
}

.remove-image-btn:hover {
  background: rgba(0, 0, 0, 0.8);
}

.preview-enter-active,
.preview-leave-active {
  transition: all 0.2s ease;
}

.preview-enter-from,
.preview-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.input-area {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 16px;
  border-top: 1px solid var(--swarm-border-light);
  background: var(--swarm-bg-card);
}

.attach-btn {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid var(--swarm-border-light);
  background: var(--swarm-bg-tertiary);
  color: var(--swarm-text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.attach-btn:hover {
  background: var(--swarm-bg-card-hover);
  color: var(--swarm-text-primary);
  border-color: var(--swarm-border);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.message-input {
  flex: 1;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid var(--swarm-border-light);
  background: var(--swarm-bg-tertiary);
  color: var(--swarm-text-primary);
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: all 0.15s ease;
  resize: none;
  min-height: 40px;
  max-height: 120px;
  line-height: 1.4;
  field-sizing: content;
}

.message-input:focus {
  border-color: var(--swarm-success);
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
}

.message-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.message-input::placeholder {
  color: var(--swarm-text-muted);
}

.send-button {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: none;
  background: var(--swarm-gradient-primary);
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px var(--swarm-accent-glow);
}

.send-button:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 16px var(--swarm-accent-glow);
}

.send-button:active:not(:disabled) {
  transform: scale(0.95);
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

@keyframes messageIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes typingBounce {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-4px);
  }
}

/* Transition group animations */
.message-enter-active {
  transition: all 0.2s ease-out;
}

.message-leave-active {
  transition: all 0.15s ease-in;
}

.message-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.message-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Typing indicator transition */
.typing-enter-active,
.typing-leave-active {
  transition: all 0.2s ease;
}

.typing-enter-from,
.typing-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

/* Mobile responsive */
@media (max-width: 640px) {
  .messages-container {
    padding: 12px;
  }

  .message-content {
    max-width: 240px;
  }

  .input-area {
    padding: 12px;
  }
}

/* Banner styles */
.disconnection-banner,
.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  font-size: 13px;
  border-bottom: 1px solid var(--swarm-border-light);
}

.disconnection-banner {
  background: rgba(251, 191, 36, 0.1);
  color: var(--swarm-warning);
}

.error-banner {
  background: rgba(239, 68, 68, 0.1);
  color: var(--swarm-error);
}

.banner-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.dismiss-btn {
  margin-left: auto;
  padding: 4px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: inherit;
  opacity: 0.7;
  transition: opacity 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dismiss-btn:hover {
  opacity: 1;
}

.dismiss-btn .u-icon {
  width: 14px;
  height: 14px;
}

.retry-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 500;
  background: transparent;
  border: 1px solid var(--swarm-error);
  border-radius: 4px;
  color: var(--swarm-error);
  cursor: pointer;
  transition: all 0.15s ease;
}

.retry-btn:hover {
  background: rgba(239, 68, 68, 0.1);
}

.retry-btn .u-icon {
  width: 12px;
  height: 12px;
}

/* Banner transitions */
.banner-enter-active,
.banner-leave-active {
  transition: all 0.2s ease;
}

.banner-enter-from,
.banner-leave-to {
  opacity: 0;
  transform: translateY(-100%);
}

/* Reduce motion */
@media (prefers-reduced-motion: reduce) {
  .message,
  .message-enter-active,
  .message-leave-active,
  .typing-enter-active,
  .typing-leave-active,
  .banner-enter-active,
  .banner-leave-active {
    animation: none;
    transition: opacity 0.1s ease;
  }

  .typing-dot {
    animation: none;
  }
}
</style>
