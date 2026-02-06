type ProjectUpdateCallback = (project: string, file: string) => void
type WorkerUpdateCallback = (worker: any) => void
type TaskUpdateCallback = (task: any) => void

interface WebSocketMessage {
  type: 'connected' | 'project-update' | 'worker-update' | 'task-update'
  message?: string
  project?: string
  file?: string
  worker?: any
  task?: any
}

// Singleton state for WebSocket connection
const connected = ref(false)
const ws = ref<WebSocket | null>(null)
const projectUpdateCallbacks = new Set<ProjectUpdateCallback>()
const workerUpdateCallbacks = new Set<WorkerUpdateCallback>()
const taskUpdateCallbacks = new Set<TaskUpdateCallback>()
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
let reconnectAttempts = 0
const MAX_RECONNECT_DELAY = 30000
const BASE_RECONNECT_DELAY = 1000

function getReconnectDelay(): number {
  // Exponential backoff: 1s, 2s, 4s, 8s, ... up to 30s
  const delay = Math.min(BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttempts), MAX_RECONNECT_DELAY)
  return delay
}

function connect() {
  // Don't connect on server side
  if (import.meta.server) return
  
  // Already connected or connecting
  if (ws.value?.readyState === WebSocket.OPEN || ws.value?.readyState === WebSocket.CONNECTING) {
    return
  }

  try {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/_ws`
    
    ws.value = new WebSocket(wsUrl)
    
    ws.value.onopen = () => {
      console.log('[WebSocket] Connected')
      connected.value = true
      reconnectAttempts = 0
    }
    
    ws.value.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        
        if (message.type === 'connected') {
          console.log('[WebSocket] Server says:', message.message)
        } else if (message.type === 'project-update' && message.project && message.file) {
          console.log('[WebSocket] Project update:', message.project, message.file)
          // Notify all registered callbacks
          projectUpdateCallbacks.forEach(callback => {
            callback(message.project!, message.file!)
          })
        } else if (message.type === 'worker-update' && message.worker) {
          console.log('[WebSocket] Worker update:', message.worker.id)
          workerUpdateCallbacks.forEach(callback => {
            callback(message.worker)
          })
        } else if (message.type === 'task-update' && message.task) {
          console.log('[WebSocket] Task update:', message.task.id)
          taskUpdateCallbacks.forEach(callback => {
            callback(message.task)
          })
        }
      } catch (err) {
        console.error('[WebSocket] Failed to parse message:', err)
      }
    }
    
    ws.value.onclose = (event) => {
      console.log('[WebSocket] Disconnected, code:', event.code)
      connected.value = false
      ws.value = null
      
      // Schedule reconnect
      scheduleReconnect()
    }
    
    ws.value.onerror = (error) => {
      console.error('[WebSocket] Error:', error)
      connected.value = false
    }
  } catch (err) {
    console.error('[WebSocket] Failed to connect:', err)
    connected.value = false
    scheduleReconnect()
  }
}

function scheduleReconnect() {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout)
  }
  
  const delay = getReconnectDelay()
  reconnectAttempts++
  
  console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`)
  
  reconnectTimeout = setTimeout(() => {
    connect()
  }, delay)
}

function disconnect() {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout)
    reconnectTimeout = null
  }
  
  if (ws.value) {
    ws.value.close()
    ws.value = null
  }
  
  connected.value = false
}

export function useWebSocket() {
  // Connect on first use (client-side only)
  if (import.meta.client && !ws.value) {
    connect()
  }

  /**
   * Register a callback to be called when a project is updated
   * Returns an unsubscribe function
   */
  const onProjectUpdate = (callback: ProjectUpdateCallback): (() => void) => {
    projectUpdateCallbacks.add(callback)
    
    // Return unsubscribe function
    return () => {
      projectUpdateCallbacks.delete(callback)
    }
  }

  /**
   * Register a callback to be called when a worker is updated
   * Returns an unsubscribe function
   */
  const onWorkerUpdate = (callback: WorkerUpdateCallback): (() => void) => {
    workerUpdateCallbacks.add(callback)
    return () => {
      workerUpdateCallbacks.delete(callback)
    }
  }

  /**
   * Register a callback to be called when a task is updated
   * Returns an unsubscribe function
   */
  const onTaskUpdate = (callback: TaskUpdateCallback): (() => void) => {
    taskUpdateCallbacks.add(callback)
    return () => {
      taskUpdateCallbacks.delete(callback)
    }
  }

  return {
    /** Reactive connection status */
    connected: readonly(connected),
    /** Register a project update listener */
    onProjectUpdate,
    /** Register a worker update listener */
    onWorkerUpdate,
    /** Register a task update listener */
    onTaskUpdate,
    /** Manually reconnect */
    reconnect: connect,
    /** Disconnect and stop reconnecting */
    disconnect,
  }
}
