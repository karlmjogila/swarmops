export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  status?: 'sending' | 'sent' | 'error'
  image?: string  // base64 data URL for image attachments
}

interface ChatSessionState {
  messages: ChatMessage[]
  isLoading: boolean
  error: string | null
  sessionId: string | null
  agentSessionKey: string | null  // Persistent session for conversation continuity
}

const state = reactive<ChatSessionState>({
  messages: [],
  isLoading: false,
  error: null,
  sessionId: null,
  agentSessionKey: null,
})

function generateId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function generateSessionId(): string {
  return `chat-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export function useChatSession() {
  const { connected } = useWebSocket()

  // Initialize session on first use
  if (!state.sessionId && import.meta.client) {
    state.sessionId = generateSessionId()
  }

  const messages = computed(() => state.messages)
  const isLoading = computed(() => state.isLoading)
  const error = computed(() => state.error)
  const isConnected = connected

  async function sendMessage(content: string, image?: string): Promise<void> {
    const trimmed = content.trim()
    if (!trimmed && !image) return

    // Add user message optimistically
    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: trimmed || '(image attached)',
      timestamp: new Date(),
      status: 'sending',
      image,
    }
    state.messages.push(userMessage)
    state.error = null
    state.isLoading = true

    try {
      const response = await $fetch<{ content: string; sessionKey: string; timestamp: string }>('/api/chat/send', {
        method: 'POST',
        body: {
          message: trimmed,
          sessionKey: state.agentSessionKey,  // Reuse session for continuity
          image,
        },
      })
      
      // Store the session key for future messages
      if (response.sessionKey) {
        state.agentSessionKey = response.sessionKey
      }

      // Mark user message as sent
      userMessage.status = 'sent'

      // Update session ID if returned
      if (response.sessionId) {
        state.sessionId = response.sessionId
      }

      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: response.content,
        timestamp: new Date(),
        status: 'sent',
      }
      state.messages.push(assistantMessage)
    } catch (err) {
      userMessage.status = 'error'
      state.error = err instanceof Error ? err.message : 'Failed to send message'
      console.error('[useChatSession] Send error:', err)
    } finally {
      state.isLoading = false
    }
  }

  function clearMessages(): void {
    state.messages = []
    state.error = null
  }

  function reset(): void {
    state.messages = []
    state.isLoading = false
    state.error = null
    state.sessionId = generateSessionId()
    state.agentSessionKey = null  // Start fresh conversation
  }

  function clearError(): void {
    state.error = null
  }

  function retryMessage(messageId?: string): Promise<void> | undefined {
    // Find the message to retry - either by ID or the last failed message
    const targetMessage = messageId
      ? state.messages.find(m => m.id === messageId && m.status === 'error')
      : [...state.messages].reverse().find(m => m.role === 'user' && m.status === 'error')
    
    if (!targetMessage) return

    // Remove the failed message and retry
    state.messages = state.messages.filter(m => m.id !== targetMessage.id)
    return sendMessage(targetMessage.content)
  }

  // Alias for backward compatibility
  function retryLastMessage(): Promise<void> | undefined {
    return retryMessage()
  }

  return {
    // State
    messages: readonly(messages),
    isConnected: readonly(isConnected),
    isLoading: readonly(isLoading),
    error: readonly(error),
    sessionId: readonly(toRef(() => state.sessionId)),

    // Actions
    sendMessage,
    clearMessages,
    reset,
    clearError,
    retryMessage,
    retryLastMessage,
  }
}
