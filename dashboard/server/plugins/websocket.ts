import { projectWatcher, type FileChangeEvent } from '../utils/watcher'

const clients = new Set<any>()

export default defineNitroPlugin((nitro) => {
  // Global error handlers - only catch connection errors
  // Use error codes (not message strings) for reliable matching
  const CONNECTION_ERROR_CODES = new Set(['ECONNRESET', 'EPIPE', 'ETIMEDOUT', 'ECONNABORTED'])

  process.on('unhandledRejection', (reason: any) => {
    const code = reason?.code || ''
    if (CONNECTION_ERROR_CODES.has(code)) {
      console.log(`[server] Ignored connection error: ${code}`)
      return
    }
    // Log all other unhandled rejections with full context
    console.error('[server] Unhandled rejection:', reason)
  })

  process.on('uncaughtException', (err: any) => {
    const code = err?.code || ''
    if (CONNECTION_ERROR_CODES.has(code)) {
      console.log(`[server] Ignored uncaught connection error: ${code}`)
      return
    }
    console.error('[server] Uncaught exception:', err)
    process.exit(1)
  })

  projectWatcher.init()

  projectWatcher.subscribe((event: FileChangeEvent) => {
    broadcast(event)
  })

  console.log('[websocket] Plugin initialized')
})

export function addClient(peer: any) {
  clients.add(peer)
  console.log(`[websocket] Client connected (${clients.size} total)`)
  peer.send(JSON.stringify({ type: 'connected', message: 'SwarmOps Dashboard WebSocket connected' }))
}

export function removeClient(peer: any) {
  clients.delete(peer)
  console.log(`[websocket] Client disconnected (${clients.size} total)`)
}

export function broadcast(data: FileChangeEvent) {
  const message = JSON.stringify(data)
  for (const client of clients) {
    try {
      client.send(message)
    } catch {}
  }
}

export function broadcastProjectUpdate(project: string, file: string) {
  broadcast({
    type: 'project-update',
    project,
    file
  })
}
