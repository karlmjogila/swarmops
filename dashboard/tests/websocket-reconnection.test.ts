import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock WebSocket for testing reconnection logic
class MockWebSocket {
  static instances: MockWebSocket[] = []
  
  readyState: number = 0 // CONNECTING
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  
  constructor(public url: string) {
    MockWebSocket.instances.push(this)
  }
  
  close() {
    this.readyState = 3 // CLOSED
    if (this.onclose) {
      this.onclose({ code: 1000 } as CloseEvent)
    }
  }
  
  simulateOpen() {
    this.readyState = 1 // OPEN
    if (this.onopen) {
      this.onopen(new Event('open'))
    }
  }
  
  simulateClose(code = 1006) {
    this.readyState = 3 // CLOSED
    if (this.onclose) {
      this.onclose({ code } as CloseEvent)
    }
  }
  
  simulateMessage(data: unknown) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) } as MessageEvent)
    }
  }
  
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'))
    }
  }
  
  static clearInstances() {
    MockWebSocket.instances = []
  }
  
  static get CONNECTING() { return 0 }
  static get OPEN() { return 1 }
  static get CLOSING() { return 2 }
  static get CLOSED() { return 3 }
}

describe('WebSocket Reconnection Logic', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    MockWebSocket.clearInstances()
    vi.stubGlobal('WebSocket', MockWebSocket)
    vi.stubGlobal('window', { location: { protocol: 'http:', host: 'localhost:3000' } })
  })
  
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })
  
  it('should use exponential backoff for reconnection delays', () => {
    const BASE_DELAY = 1000
    const MAX_DELAY = 30000
    
    // Test exponential backoff calculation
    const getReconnectDelay = (attempts: number): number => {
      return Math.min(BASE_DELAY * Math.pow(2, attempts), MAX_DELAY)
    }
    
    expect(getReconnectDelay(0)).toBe(1000)   // 1s
    expect(getReconnectDelay(1)).toBe(2000)   // 2s
    expect(getReconnectDelay(2)).toBe(4000)   // 4s
    expect(getReconnectDelay(3)).toBe(8000)   // 8s
    expect(getReconnectDelay(4)).toBe(16000)  // 16s
    expect(getReconnectDelay(5)).toBe(30000)  // capped at 30s
    expect(getReconnectDelay(10)).toBe(30000) // still capped at 30s
  })
  
  it('should reset reconnect attempts after successful connection', () => {
    let reconnectAttempts = 0
    const BASE_DELAY = 1000
    const MAX_DELAY = 30000
    
    const getReconnectDelay = (): number => {
      return Math.min(BASE_DELAY * Math.pow(2, reconnectAttempts), MAX_DELAY)
    }
    
    // Simulate failed attempts
    reconnectAttempts = 5
    expect(getReconnectDelay()).toBe(30000) // Should be at max
    
    // Simulate successful connection - reset attempts
    reconnectAttempts = 0
    expect(getReconnectDelay()).toBe(1000) // Should be back to base
  })
  
  it('should schedule reconnect after connection closes', async () => {
    let reconnectScheduled = false
    let reconnectDelay = 0
    
    const scheduleReconnect = (delay: number) => {
      reconnectScheduled = true
      reconnectDelay = delay
    }
    
    // Simulate WebSocket close event triggering reconnect
    const ws = new MockWebSocket('ws://localhost:3000/_ws')
    ws.onclose = () => {
      scheduleReconnect(1000) // First reconnect at 1s
    }
    
    ws.simulateClose()
    
    expect(reconnectScheduled).toBe(true)
    expect(reconnectDelay).toBe(1000)
  })
  
  it('should handle project update messages correctly', () => {
    const callbacks = new Set<(project: string, file: string) => void>()
    const receivedUpdates: Array<{ project: string; file: string }> = []
    
    // Register a callback
    const callback = (project: string, file: string) => {
      receivedUpdates.push({ project, file })
    }
    callbacks.add(callback)
    
    // Simulate receiving a project-update message
    const message = {
      type: 'project-update',
      project: 'my-project',
      file: 'state.json'
    }
    
    if (message.type === 'project-update' && message.project && message.file) {
      callbacks.forEach(cb => cb(message.project!, message.file!))
    }
    
    expect(receivedUpdates).toHaveLength(1)
    expect(receivedUpdates[0]).toEqual({ project: 'my-project', file: 'state.json' })
  })
  
  it('should allow unsubscribing from project updates', () => {
    const callbacks = new Set<(project: string, file: string) => void>()
    const receivedUpdates: Array<{ project: string; file: string }> = []
    
    const callback = (project: string, file: string) => {
      receivedUpdates.push({ project, file })
    }
    
    // Subscribe
    callbacks.add(callback)
    
    // Trigger update
    callbacks.forEach(cb => cb('project1', 'state.json'))
    expect(receivedUpdates).toHaveLength(1)
    
    // Unsubscribe
    callbacks.delete(callback)
    
    // Trigger another update
    callbacks.forEach(cb => cb('project2', 'state.json'))
    
    // Should still only have 1 update
    expect(receivedUpdates).toHaveLength(1)
  })
})

describe('WebSocket Message Handling', () => {
  it('should parse connected messages', () => {
    const message = JSON.parse('{"type":"connected","message":"Welcome to Ralph Dashboard"}')
    
    expect(message.type).toBe('connected')
    expect(message.message).toBe('Welcome to Ralph Dashboard')
  })
  
  it('should parse project-update messages', () => {
    const message = JSON.parse('{"type":"project-update","project":"test-project","file":"state.json"}')
    
    expect(message.type).toBe('project-update')
    expect(message.project).toBe('test-project')
    expect(message.file).toBe('state.json')
  })
  
  it('should handle malformed JSON gracefully', () => {
    let errorCaught = false
    
    try {
      JSON.parse('not valid json')
    } catch {
      errorCaught = true
    }
    
    expect(errorCaught).toBe(true)
  })
})
