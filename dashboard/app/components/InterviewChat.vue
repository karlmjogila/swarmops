<script setup lang="ts">
interface InterviewMessage {
  id: string
  timestamp: string
  role: 'user' | 'agent'
  content: string
  image?: string // base64 data URL
}

interface InterviewState {
  messages: InterviewMessage[]
  complete: boolean
}

const props = defineProps<{
  projectName: string
}>()

const emit = defineEmits<{
  (e: 'complete'): void
}>()

const { onProjectUpdate } = useWebSocket()

const interview = ref<InterviewState>({ messages: [], complete: false })
const userInput = ref('')
const isLoading = ref(false)
const isSending = ref(false)
const messagesContainer = ref<HTMLElement>()
const inputField = ref<HTMLTextAreaElement>()
const pendingImage = ref<string | null>(null) // base64 data URL
const isDragging = ref(false)

function focusInput() {
  nextTick(() => {
    inputField.value?.focus()
  })
}

// Image handling
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

const isWaitingForAgent = computed(() => {
  if (interview.value.complete) return false
  if (interview.value.messages.length === 0) return false
  const lastMsg = interview.value.messages[interview.value.messages.length - 1]
  return lastMsg.role === 'user'
})

async function spawnInterviewAgent(userMessage?: string, image?: string) {
  try {
    await $fetch(`/api/projects/${props.projectName}/interview-agent`, {
      method: 'POST',
      body: { userMessage, image }
    })
  } catch (err) {
    console.error('Failed to spawn/wake interview agent:', err)
  }
}

async function fetchInterview() {
  if (!props.projectName) return
  
  isLoading.value = true
  try {
    const data = await $fetch<InterviewState>(`/api/projects/${props.projectName}/interview`)
    interview.value = data
    
    if (data.messages.length === 0 && !data.complete) {
      await spawnInterviewAgent()
    }
    
    await nextTick()
    scrollToBottom()
    focusInput()
  } catch (err) {
    console.error('Failed to fetch interview:', err)
  } finally {
    isLoading.value = false
  }
}

async function sendMessage() {
  const content = userInput.value.trim()
  const image = pendingImage.value
  
  // Allow sending with just image, just text, or both
  if ((!content && !image) || isSending.value) return
  
  isSending.value = true
  userInput.value = ''
  pendingImage.value = null
  
  try {
    await spawnInterviewAgent(content || '(image attached)', image || undefined)
  } catch (err) {
    console.error('Failed to send message:', err)
    userInput.value = content
    pendingImage.value = image
  } finally {
    isSending.value = false
    focusInput()
  }
}

async function continueToPlanning() {
  try {
    await $fetch(`/api/projects/${props.projectName}/interview`, {
      method: 'POST',
      body: {
        role: 'agent',
        content: 'Thanks for the details! I have everything I need. Let me put together an implementation plan...',
        complete: true
      }
    })
    emit('complete')
  } catch (err) {
    console.error('Failed to complete interview:', err)
  }
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function formatTime(timestamp: string): string {
  try {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return ''
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

onMounted(() => {
  fetchInterview()
})

let unsubscribe: (() => void) | null = null

onMounted(() => {
  unsubscribe = onProjectUpdate((project, file) => {
    if (project === props.projectName && file === 'interview.json') {
      fetchInterview()
    }
  })
})

onUnmounted(() => {
  if (unsubscribe) {
    unsubscribe()
    unsubscribe = null
  }
})

watch(() => props.projectName, () => {
  fetchInterview()
})
</script>

<template>
  <div 
    class="ralph-section interview-section"
    :class="{ 'is-dragging': isDragging }"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
  >
    <!-- Section header matching other ralph-sections -->
    <div class="ralph-section-header">
      <div class="ralph-section-icon" style="background: var(--swarm-accent-bg); color: var(--swarm-accent);">
        <UIcon name="i-heroicons-chat-bubble-left-right" class="w-4 h-4" />
      </div>
      <div>
        <h2 class="ralph-section-title">Project Interview</h2>
        <p class="interview-subtitle">Answer questions to help SwarmOps understand your project</p>
      </div>
    </div>

    <!-- Messages -->
    <div ref="messagesContainer" class="messages-area">
      <!-- Loading state -->
      <div v-if="isLoading && interview.messages.length === 0" class="chat-empty-state">
        <div class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
        <p>Loading conversation...</p>
      </div>

      <!-- Waiting for agent to start -->
      <div v-else-if="interview.messages.length === 0" class="chat-empty-state">
        <div class="empty-icon">
          <UIcon name="i-heroicons-chat-bubble-oval-left-ellipsis" class="w-8 h-8" />
        </div>
        <p>Waiting for SwarmOps to start the interview...</p>
        <p class="hint">Questions will appear here</p>
      </div>

      <!-- Message list -->
      <template v-else>
        <div
          v-for="msg in interview.messages"
          :key="msg.id"
          class="message"
          :class="msg.role"
        >
          <div class="message-avatar">
            <UIcon
              :name="msg.role === 'agent' ? 'i-heroicons-cpu-chip' : 'i-heroicons-user'"
              class="w-4 h-4"
            />
          </div>
          <div class="message-bubble">
            <div class="message-header">
              <span class="message-sender">{{ msg.role === 'agent' ? 'SwarmOps' : 'You' }}</span>
              <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
            </div>
            <div v-if="msg.image" class="message-image">
              <img :src="msg.image" alt="Attached image" />
            </div>
            <div class="message-text">{{ msg.content }}</div>
          </div>
        </div>
        
        <!-- Typing indicator -->
        <div v-if="isWaitingForAgent" class="message agent typing-msg">
          <div class="message-avatar">
            <UIcon name="i-heroicons-cpu-chip" class="w-4 h-4" />
          </div>
          <div class="message-bubble typing-bubble">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
            <div class="typing-label">Agent is thinking...</div>
          </div>
        </div>
      </template>
    </div>

    <!-- Image preview -->
    <Transition name="preview">
      <div v-if="pendingImage" class="image-preview">
        <img :src="pendingImage" alt="Pending attachment" />
        <button class="remove-image-btn" @click="clearImage">
          <UIcon name="i-heroicons-x-mark" class="w-4 h-4" />
        </button>
      </div>
    </Transition>

    <!-- Input area -->
    <div class="input-area">
      <div v-if="interview.complete" class="complete-banner">
        <UIcon name="i-heroicons-check-circle" class="w-5 h-5" />
        <span>Interview complete -- generating plan...</span>
        <button class="swarm-btn swarm-btn-success" @click="continueToPlanning">
          Continue to Planning
          <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
        </button>
      </div>
      
      <template v-else>
        <div class="input-row">
          <label class="attach-btn" title="Attach image (or paste/drag)">
            <UIcon name="i-heroicons-photo" class="w-5 h-5" />
            <input 
              type="file" 
              accept="image/*" 
              class="sr-only"
              @change="handleImageSelect"
            />
          </label>
          <textarea
            ref="inputField"
            v-model="userInput"
            class="chat-input"
            placeholder="Type your response..."
            rows="2"
            :disabled="isSending"
            autofocus
            @keydown="handleKeydown"
            @paste="handlePaste"
          />
          <button
            class="send-btn"
            :disabled="(!userInput.trim() && !pendingImage) || isSending"
            @click="sendMessage"
          >
            <UIcon v-if="isSending" name="i-heroicons-arrow-path" class="w-5 h-5 animate-spin" />
            <UIcon v-else name="i-heroicons-paper-airplane" class="w-5 h-5" />
          </button>
        </div>
        <p class="input-hint">Press Enter to send • Paste or drag images • Shift+Enter for new line</p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.interview-section {
  padding: 0 !important;
  overflow: hidden;
  position: relative;
}

.interview-section.is-dragging::after {
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

.interview-section :deep(.ralph-section-header) {
  padding: 20px 20px 0;
  margin-bottom: 0;
}

.interview-subtitle {
  font-size: 13px;
  color: var(--swarm-text-muted);
  margin: 2px 0 0;
}

.messages-area {
  min-height: 300px;
  max-height: calc(100vh - 420px);
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--swarm-text-muted);
  text-align: center;
  gap: 8px;
  padding: 48px 20px;
}

.empty-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: var(--swarm-accent-bg);
  color: var(--swarm-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
}

.chat-empty-state .hint {
  font-size: 12px;
  opacity: 0.6;
}

/* Messages */
.message {
  display: flex;
  gap: 10px;
  max-width: 85%;
  animation: fadeIn 0.2s ease;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message.agent {
  align-self: flex-start;
}

.message-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message.agent .message-avatar {
  background: var(--swarm-accent-bg);
  color: var(--swarm-accent);
}

.message.user .message-avatar {
  background: rgba(59, 130, 246, 0.12);
  color: #3b82f6;
}

.message-bubble {
  background: var(--swarm-bg-secondary);
  border: 1px solid var(--swarm-border);
  border-radius: 12px;
  padding: 10px 14px;
}

.message.user .message-bubble {
  background: rgba(59, 130, 246, 0.06);
  border-color: rgba(59, 130, 246, 0.12);
}

.typing-bubble {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 3px;
}

.message-sender {
  font-size: 12px;
  font-weight: 600;
  color: var(--swarm-text-primary);
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
  border: 1px solid var(--swarm-border);
}

.message-text {
  font-size: 14px;
  line-height: 1.5;
  color: var(--swarm-text-secondary);
  white-space: pre-wrap;
}

.typing-label {
  font-size: 13px;
  color: var(--swarm-text-muted);
  font-style: italic;
}

/* Typing indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--swarm-accent);
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Image preview */
.image-preview {
  position: relative;
  padding: 12px 20px;
  border-top: 1px solid var(--swarm-border);
  background: var(--swarm-bg-hover);
}

.image-preview img {
  max-height: 100px;
  max-width: 180px;
  border-radius: 8px;
  border: 1px solid var(--swarm-border);
}

.remove-image-btn {
  position: absolute;
  top: 8px;
  left: calc(20px + 180px - 24px);
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

/* Input area */
.input-area {
  padding: 14px 20px 16px;
  border-top: 1px solid var(--swarm-border);
  background: var(--swarm-bg-secondary);
}

.complete-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: var(--swarm-success-bg);
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 10px;
  color: var(--swarm-success);
}

.complete-banner span {
  flex: 1;
  font-weight: 500;
  font-size: 14px;
}

.input-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.attach-btn {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid var(--swarm-border);
  background: var(--swarm-bg-card);
  color: var(--swarm-text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.attach-btn:hover {
  background: var(--swarm-bg-hover);
  color: var(--swarm-text-primary);
  border-color: var(--swarm-accent);
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

.chat-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid var(--swarm-border);
  border-radius: 10px;
  background: var(--swarm-bg-card);
  color: var(--swarm-text-primary);
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  transition: border-color 0.15s;
  font-family: inherit;
}

.chat-input:focus {
  outline: none;
  border-color: var(--swarm-accent);
}

.chat-input::placeholder {
  color: var(--swarm-text-muted);
}

.chat-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: none;
  background: var(--swarm-accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: var(--swarm-accent-dark);
}

.send-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.input-hint {
  font-size: 11px;
  color: var(--swarm-text-muted);
  margin-top: 6px;
  opacity: 0.7;
}

@media (max-width: 640px) {
  .messages-area {
    max-height: calc(100vh - 360px);
    padding: 12px 14px;
  }
  
  .message {
    max-width: 92%;
  }
  
  .input-area {
    padding: 10px 14px 12px;
  }
}
</style>
