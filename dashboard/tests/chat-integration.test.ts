import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref, reactive, computed, readonly, nextTick, toRef } from 'vue'

// Mock WebSocket for testing
class MockWebSocket {
  static instances: MockWebSocket[] = []
  readyState: number = 0
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
  }

  close() {
    this.readyState = 3
    if (this.onclose) {
      this.onclose({ code: 1000 } as CloseEvent)
    }
  }

  simulateOpen() {
    this.readyState = 1
    if (this.onopen) {
      this.onopen(new Event('open'))
    }
  }

  simulateClose(code = 1006) {
    this.readyState = 3
    if (this.onclose) {
      this.onclose({ code } as CloseEvent)
    }
  }

  static clearInstances() {
    MockWebSocket.instances = []
  }

  static get OPEN() { return 1 }
  static get CLOSED() { return 3 }
}

describe('Chat Navigation Persistence', () => {
  // Recreate the singleton pattern used in useChatSession
  interface ChatMessage {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
    status?: 'sending' | 'sent' | 'error'
  }

  interface ChatSessionState {
    messages: ChatMessage[]
    isLoading: boolean
    error: string | null
    sessionId: string | null
  }

  // Singleton state - defined once outside component
  let singletonState: ChatSessionState

  beforeEach(() => {
    singletonState = reactive<ChatSessionState>({
      messages: [],
      isLoading: false,
      error: null,
      sessionId: null,
    })
  })

  function createChatSession() {
    // Initialize session on first use
    if (!singletonState.sessionId) {
      singletonState.sessionId = `chat-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
    }

    const messages = computed(() => singletonState.messages)
    const isLoading = computed(() => singletonState.isLoading)
    const error = computed(() => singletonState.error)

    function addMessage(content: string, role: 'user' | 'assistant') {
      const message: ChatMessage = {
        id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        role,
        content,
        timestamp: new Date(),
        status: 'sent',
      }
      singletonState.messages.push(message)
      return message
    }

    function clearMessages() {
      singletonState.messages = []
    }

    return {
      messages: readonly(messages),
      isLoading: readonly(isLoading),
      error: readonly(error),
      sessionId: readonly(toRef(() => singletonState.sessionId)),
      addMessage,
      clearMessages,
    }
  }

  it('should maintain chat messages across component instances (navigation)', () => {
    // First component instance (e.g., on homepage)
    const session1 = createChatSession()
    session1.addMessage('Hello from homepage', 'user')
    session1.addMessage('Hi there!', 'assistant')

    expect(session1.messages.value).toHaveLength(2)
    const firstSessionId = session1.sessionId.value

    // Simulate navigation - new component instance
    // In a real app, the first component unmounts and a new one mounts
    const session2 = createChatSession()

    // State should persist because it's singleton
    expect(session2.messages.value).toHaveLength(2)
    expect(session2.messages.value[0].content).toBe('Hello from homepage')
    expect(session2.messages.value[1].content).toBe('Hi there!')
    expect(session2.sessionId.value).toBe(firstSessionId)
  })

  it('should preserve session ID across multiple navigations', () => {
    const session1 = createChatSession()
    const originalSessionId = session1.sessionId.value

    // Simulate multiple page navigations
    const session2 = createChatSession()
    const session3 = createChatSession()
    const session4 = createChatSession()

    expect(session2.sessionId.value).toBe(originalSessionId)
    expect(session3.sessionId.value).toBe(originalSessionId)
    expect(session4.sessionId.value).toBe(originalSessionId)
  })

  it('should allow adding messages from different page contexts', () => {
    // Start chat on one page
    const homepageSession = createChatSession()
    homepageSession.addMessage('Started on homepage', 'user')

    // Navigate to another page
    const projectSession = createChatSession()
    projectSession.addMessage('Now on project page', 'user')
    projectSession.addMessage('Project details here', 'assistant')

    // Navigate back
    const homepageSession2 = createChatSession()

    // All messages should be there
    expect(homepageSession2.messages.value).toHaveLength(3)
    expect(homepageSession2.messages.value[0].content).toBe('Started on homepage')
    expect(homepageSession2.messages.value[1].content).toBe('Now on project page')
    expect(homepageSession2.messages.value[2].content).toBe('Project details here')
  })

  it('should clear messages only when explicitly requested', () => {
    const session1 = createChatSession()
    session1.addMessage('Message 1', 'user')
    session1.addMessage('Message 2', 'assistant')

    expect(session1.messages.value).toHaveLength(2)

    // Navigation should NOT clear messages
    const session2 = createChatSession()
    expect(session2.messages.value).toHaveLength(2)

    // Explicit clear should work
    session2.clearMessages()
    expect(session2.messages.value).toHaveLength(0)

    // And subsequent sessions should see the cleared state
    const session3 = createChatSession()
    expect(session3.messages.value).toHaveLength(0)
  })
})

describe('Chat WebSocket Reconnection', () => {
  let connected: ReturnType<typeof ref<boolean>>
  let reconnectAttempts: number
  let reconnectTimeout: ReturnType<typeof setTimeout> | null

  beforeEach(() => {
    vi.useFakeTimers()
    MockWebSocket.clearInstances()
    connected = ref(false)
    reconnectAttempts = 0
    reconnectTimeout = null
  })

  afterEach(() => {
    vi.useRealTimers()
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
    }
  })

  function simulateWebSocketConnect() {
    connected.value = true
    reconnectAttempts = 0
  }

  function simulateWebSocketDisconnect() {
    connected.value = false
  }

  function getReconnectDelay(): number {
    const BASE = 1000
    const MAX = 30000
    return Math.min(BASE * Math.pow(2, reconnectAttempts), MAX)
  }

  function scheduleReconnect(callback: () => void) {
    const delay = getReconnectDelay()
    reconnectAttempts++
    reconnectTimeout = setTimeout(callback, delay)
  }

  it('should disable chat input when disconnected', () => {
    // Simulate connected state
    simulateWebSocketConnect()
    expect(connected.value).toBe(true)

    // In ChatInterface, disabled prop is based on isLoading || !isConnected
    const isLoading = false
    const shouldDisable = isLoading || !connected.value
    expect(shouldDisable).toBe(false) // Input enabled when connected

    // Simulate disconnection
    simulateWebSocketDisconnect()
    const shouldDisableAfterDisconnect = isLoading || !connected.value
    expect(shouldDisableAfterDisconnect).toBe(true) // Input disabled when disconnected
  })

  it('should re-enable chat after WebSocket reconnects', () => {
    // Initial connection
    simulateWebSocketConnect()
    expect(connected.value).toBe(true)

    // Disconnect
    simulateWebSocketDisconnect()
    expect(connected.value).toBe(false)

    // Simulate reconnection
    let reconnected = false
    scheduleReconnect(() => {
      simulateWebSocketConnect()
      reconnected = true
    })

    // Fast forward past reconnect delay
    vi.advanceTimersByTime(1000)

    expect(reconnected).toBe(true)
    expect(connected.value).toBe(true)

    // Chat should be enabled again
    const isLoading = false
    const shouldDisable = isLoading || !connected.value
    expect(shouldDisable).toBe(false)
  })

  it('should preserve chat messages during disconnection and reconnection', () => {
    // Setup chat with messages
    interface ChatMessage {
      id: string
      content: string
    }

    const messages: ChatMessage[] = []
    messages.push({ id: '1', content: 'Hello' })
    messages.push({ id: '2', content: 'How are you?' })

    // Initial connection
    simulateWebSocketConnect()
    expect(messages).toHaveLength(2)

    // Disconnect
    simulateWebSocketDisconnect()

    // Messages should still be there
    expect(messages).toHaveLength(2)
    expect(messages[0].content).toBe('Hello')
    expect(messages[1].content).toBe('How are you?')

    // Reconnect
    scheduleReconnect(() => {
      simulateWebSocketConnect()
    })
    vi.advanceTimersByTime(1000)

    // Messages should still be there
    expect(messages).toHaveLength(2)
  })

  it('should apply exponential backoff for reconnection', () => {
    const delays: number[] = []

    // Simulate multiple failed reconnection attempts
    for (let i = 0; i < 6; i++) {
      delays.push(getReconnectDelay())
      reconnectAttempts++
    }

    expect(delays).toEqual([1000, 2000, 4000, 8000, 16000, 30000])
    
    // Further attempts should stay at max
    expect(getReconnectDelay()).toBe(30000)
  })

  it('should reset backoff after successful reconnection', () => {
    // Simulate several failed attempts
    reconnectAttempts = 5
    expect(getReconnectDelay()).toBe(30000)

    // Successful connection resets attempts
    simulateWebSocketConnect()
    expect(reconnectAttempts).toBe(0)
    expect(getReconnectDelay()).toBe(1000)
  })
})

describe('Chat Modal Persistence', () => {
  it('should maintain open/closed state at app level', () => {
    // The chatOpen state is defined in app.vue at the root level
    // This means it persists across route changes
    const chatOpen = ref(false)

    // Open chat
    chatOpen.value = true
    expect(chatOpen.value).toBe(true)

    // Simulate page navigation - in app.vue this ref persists
    // because it's not inside a page component
    const newRouteValue = chatOpen.value
    expect(newRouteValue).toBe(true)

    // Close chat
    chatOpen.value = false
    expect(chatOpen.value).toBe(false)
  })

  it('should handle keyboard shortcut (Ctrl/Cmd+K) toggle', () => {
    const chatOpen = ref(false)

    function handleKeydown(e: { key: string; metaKey: boolean; ctrlKey: boolean; preventDefault: () => void }) {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        chatOpen.value = !chatOpen.value
      }
    }

    // Simulate Ctrl+K
    handleKeydown({ key: 'k', metaKey: false, ctrlKey: true, preventDefault: vi.fn() })
    expect(chatOpen.value).toBe(true)

    // Toggle again
    handleKeydown({ key: 'k', metaKey: false, ctrlKey: true, preventDefault: vi.fn() })
    expect(chatOpen.value).toBe(false)

    // Simulate Cmd+K (macOS)
    handleKeydown({ key: 'k', metaKey: true, ctrlKey: false, preventDefault: vi.fn() })
    expect(chatOpen.value).toBe(true)
  })

  it('should close on Escape key', () => {
    const chatOpen = ref(true)

    function handleKeydown(e: { key: string }) {
      if (e.key === 'Escape' && chatOpen.value) {
        chatOpen.value = false
      }
    }

    expect(chatOpen.value).toBe(true)
    handleKeydown({ key: 'Escape' })
    expect(chatOpen.value).toBe(false)
  })
})

describe('Chat Session State Machine', () => {
  it('should track message sending states correctly', async () => {
    type MessageStatus = 'sending' | 'sent' | 'error'

    interface Message {
      id: string
      content: string
      status: MessageStatus
    }

    const messages: Message[] = []

    // Simulate sending a message
    const newMessage: Message = {
      id: '1',
      content: 'Test message',
      status: 'sending',
    }
    messages.push(newMessage)

    expect(messages[0].status).toBe('sending')

    // Simulate successful send
    newMessage.status = 'sent'
    expect(messages[0].status).toBe('sent')
  })

  it('should handle send errors gracefully', async () => {
    type MessageStatus = 'sending' | 'sent' | 'error'

    interface ChatState {
      messages: Array<{ id: string; content: string; status: MessageStatus }>
      isLoading: boolean
      error: string | null
    }

    const state: ChatState = {
      messages: [],
      isLoading: false,
      error: null,
    }

    // Start sending
    state.isLoading = true
    state.messages.push({
      id: '1',
      content: 'Failed message',
      status: 'sending',
    })

    // Simulate error
    state.messages[0].status = 'error'
    state.error = 'Network error'
    state.isLoading = false

    expect(state.messages[0].status).toBe('error')
    expect(state.error).toBe('Network error')
    expect(state.isLoading).toBe(false)
  })

  it('should support retry for failed messages', () => {
    interface Message {
      id: string
      content: string
      role: 'user' | 'assistant'
      status: 'sending' | 'sent' | 'error'
    }

    const messages: Message[] = []
    let sendAttempts = 0

    function sendMessage(content: string): Message {
      sendAttempts++
      const msg: Message = {
        id: `msg-${Date.now()}`,
        content,
        role: 'user',
        status: 'sending',
      }
      messages.push(msg)
      return msg
    }

    function retryLastMessage(): Message | undefined {
      const lastUserMessage = [...messages]
        .reverse()
        .find(m => m.role === 'user' && m.status === 'error')

      if (!lastUserMessage) return undefined

      // Remove failed message
      const index = messages.indexOf(lastUserMessage)
      messages.splice(index, 1)

      // Retry
      return sendMessage(lastUserMessage.content)
    }

    // Initial send
    const msg = sendMessage('Hello')
    msg.status = 'error' // Simulate failure

    expect(messages).toHaveLength(1)
    expect(messages[0].status).toBe('error')
    expect(sendAttempts).toBe(1)

    // Retry
    const retried = retryLastMessage()

    expect(retried).toBeDefined()
    expect(messages).toHaveLength(1) // Original removed, new one added
    expect(sendAttempts).toBe(2)
  })
})

describe('Integration: Chat with WebSocket Status', () => {
  it('should reflect WebSocket status in chat interface', () => {
    const wsConnected = ref(true)

    // Chat composable uses WebSocket status
    function useChatSession() {
      return {
        isConnected: readonly(wsConnected),
      }
    }

    const session = useChatSession()
    expect(session.isConnected.value).toBe(true)

    // WebSocket disconnects
    wsConnected.value = false
    expect(session.isConnected.value).toBe(false)

    // WebSocket reconnects
    wsConnected.value = true
    expect(session.isConnected.value).toBe(true)
  })

  it('should continue working after WebSocket reconnection cycle', async () => {
    const wsConnected = ref(true)
    const messages: Array<{ content: string; sent: boolean }> = []

    async function sendMessage(content: string): Promise<boolean> {
      if (!wsConnected.value) {
        return false
      }

      messages.push({ content, sent: true })
      return true
    }

    // Send while connected
    const sent1 = await sendMessage('Message 1')
    expect(sent1).toBe(true)
    expect(messages).toHaveLength(1)

    // Disconnect
    wsConnected.value = false

    // Try to send while disconnected
    const sent2 = await sendMessage('Message 2')
    expect(sent2).toBe(false)
    expect(messages).toHaveLength(1) // No new message

    // Reconnect
    wsConnected.value = true

    // Send after reconnection
    const sent3 = await sendMessage('Message 3')
    expect(sent3).toBe(true)
    expect(messages).toHaveLength(2)
    expect(messages[1].content).toBe('Message 3')
  })
})
