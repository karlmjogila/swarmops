/**
 * WebSocket Composable with Security and Reconnection
 * 
 * SECURITY: Enforces wss:// in production environments.
 * Includes automatic reconnection with exponential backoff.
 */

import { RateLimiter } from '~/utils/rate-limiter'

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

export interface WebSocketOptions {
  /** Automatically reconnect on disconnect */
  autoReconnect?: boolean
  /** Maximum reconnection attempts (0 = unlimited) */
  maxReconnectAttempts?: number
  /** Initial reconnection delay in ms */
  reconnectDelay?: number
  /** Maximum reconnection delay in ms */
  maxReconnectDelay?: number
  /** Heartbeat interval in ms (0 = disabled) */
  heartbeatInterval?: number
  /** Custom protocols */
  protocols?: string | string[]
}

const defaultOptions: Required<WebSocketOptions> = {
  autoReconnect: true,
  maxReconnectAttempts: 10,
  reconnectDelay: 1000,
  maxReconnectDelay: 30000,
  heartbeatInterval: 30000,
  protocols: [],
}

// Rate limiter for reconnection attempts - 5 per minute
const reconnectRateLimiter = new RateLimiter({
  maxRequests: 5,
  windowMs: 60000,
  retryAfterMs: 10000,
})

export const useWebSocket = (
  url?: string,
  options: WebSocketOptions = {}
) => {
  const config = useRuntimeConfig()
  const notifications = useNotifications()
  
  const opts = { ...defaultOptions, ...options }
  
  // Resolve WebSocket URL
  const resolveUrl = (inputUrl?: string): string => {
    let wsUrl = inputUrl || config.public.wsUrl
    
    // SECURITY: Enforce wss:// in production
    if (config.public.enforceSecureWs && wsUrl.startsWith('ws://')) {
      console.warn('SECURITY WARNING: Upgrading insecure ws:// to wss:// in production')
      wsUrl = wsUrl.replace('ws://', 'wss://')
    }
    
    // Validate URL
    if (!wsUrl.startsWith('ws://') && !wsUrl.startsWith('wss://')) {
      throw new Error(`Invalid WebSocket URL: ${wsUrl}. Must start with ws:// or wss://`)
    }
    
    return wsUrl
  }
  
  // State
  const socket = ref<WebSocket | null>(null)
  const status = ref<WebSocketStatus>('disconnected')
  const error = ref<Error | null>(null)
  const lastMessage = ref<any>(null)
  const reconnectAttempts = ref(0)
  
  // Internal state
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  
  /**
   * Calculate reconnection delay with exponential backoff
   */
  const getReconnectDelay = (): number => {
    const delay = Math.min(
      opts.reconnectDelay * Math.pow(2, reconnectAttempts.value),
      opts.maxReconnectDelay
    )
    // Add jitter (±10%)
    return delay * (0.9 + Math.random() * 0.2)
  }
  
  /**
   * Start heartbeat
   */
  const startHeartbeat = (): void => {
    if (opts.heartbeatInterval > 0 && socket.value) {
      stopHeartbeat()
      heartbeatTimer = setInterval(() => {
        if (socket.value?.readyState === WebSocket.OPEN) {
          socket.value.send(JSON.stringify({ type: 'ping' }))
        }
      }, opts.heartbeatInterval)
    }
  }
  
  /**
   * Stop heartbeat
   */
  const stopHeartbeat = (): void => {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }
  
  /**
   * Connect to WebSocket
   */
  const connect = async (inputUrl?: string): Promise<void> => {
    // Clean up existing connection
    disconnect()
    
    try {
      const wsUrl = resolveUrl(inputUrl)
      
      status.value = 'connecting'
      error.value = null
      
      socket.value = new WebSocket(wsUrl, opts.protocols)
      
      socket.value.onopen = () => {
        status.value = 'connected'
        reconnectAttempts.value = 0
        startHeartbeat()
        console.log(`WebSocket connected to ${wsUrl}`)
      }
      
      socket.value.onclose = (event) => {
        status.value = 'disconnected'
        stopHeartbeat()
        
        if (event.code !== 1000 && opts.autoReconnect) {
          // Abnormal close - attempt reconnect
          scheduleReconnect()
        }
      }
      
      socket.value.onerror = (event) => {
        status.value = 'error'
        error.value = new Error('WebSocket connection error')
        console.error('WebSocket error:', event)
      }
      
      socket.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          // Handle pong (heartbeat response)
          if (data.type === 'pong') {
            return
          }
          
          lastMessage.value = data
        } catch {
          // Non-JSON message
          lastMessage.value = event.data
        }
      }
      
    } catch (err) {
      status.value = 'error'
      error.value = err instanceof Error ? err : new Error(String(err))
      
      if (opts.autoReconnect) {
        scheduleReconnect()
      }
    }
  }
  
  /**
   * Schedule reconnection with exponential backoff
   */
  const scheduleReconnect = async (): Promise<void> => {
    // Check max attempts
    if (opts.maxReconnectAttempts > 0 && reconnectAttempts.value >= opts.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      notifications.connectionError('WebSocket')
      return
    }
    
    // Check rate limit
    if (!reconnectRateLimiter.canRequest()) {
      console.warn('Reconnection rate limited')
      await reconnectRateLimiter.waitForSlot()
    }
    
    reconnectRateLimiter.recordRequest()
    
    const delay = getReconnectDelay()
    reconnectAttempts.value++
    
    console.log(`Scheduling WebSocket reconnect in ${Math.round(delay)}ms (attempt ${reconnectAttempts.value})`)
    
    reconnectTimer = setTimeout(() => {
      connect()
    }, delay)
  }
  
  /**
   * Disconnect WebSocket
   */
  const disconnect = (): void => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    
    stopHeartbeat()
    
    if (socket.value) {
      socket.value.onclose = null // Prevent reconnect on intentional close
      socket.value.close(1000, 'Client disconnect')
      socket.value = null
    }
    
    status.value = 'disconnected'
  }
  
  /**
   * Send message via WebSocket
   */
  const send = (data: any): boolean => {
    if (socket.value?.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected, cannot send message')
      return false
    }
    
    try {
      const message = typeof data === 'string' ? data : JSON.stringify(data)
      socket.value.send(message)
      return true
    } catch (err) {
      console.error('Failed to send WebSocket message:', err)
      return false
    }
  }
  
  /**
   * Subscribe to a channel/topic
   */
  const subscribe = (channel: string, params?: Record<string, any>): boolean => {
    return send({
      type: 'subscribe',
      channel,
      ...params,
    })
  }
  
  /**
   * Unsubscribe from a channel/topic
   */
  const unsubscribe = (channel: string): boolean => {
    return send({
      type: 'unsubscribe',
      channel,
    })
  }
  
  // Cleanup on unmount
  onUnmounted(() => {
    disconnect()
  })
  
  return {
    // State
    socket: readonly(socket),
    status: readonly(status),
    error: readonly(error),
    lastMessage: readonly(lastMessage),
    reconnectAttempts: readonly(reconnectAttempts),
    
    // Methods
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
  }
}
