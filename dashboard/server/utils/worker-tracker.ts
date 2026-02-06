/**
 * Worker Tracker - Tracks spawned workers and logs their completion
 * 
 * Polls gateway for session status and logs worker_completed when sessions end.
 */

import { logWorkerCompleted } from './ledger-writer'

const GATEWAY_URL = process.env.OPENCLAW_GATEWAY_URL || 'http://127.0.0.1:18789'
const GATEWAY_TOKEN = process.env.OPENCLAW_GATEWAY_TOKEN || ''

const POLL_INTERVAL_MS = 10000  // Check every 10 seconds
const MAX_TRACK_TIME_MS = 30 * 60 * 1000  // Stop tracking after 30 minutes

interface TrackedWorker {
  sessionKey: string
  label: string
  startTime: number
  projectName?: string
}

// In-memory tracking (resets on server restart)
const trackedWorkers = new Map<string, TrackedWorker>()
let pollInterval: ReturnType<typeof setInterval> | null = null

/**
 * Start tracking a spawned worker
 */
export function trackWorker(sessionKey: string, label: string, projectName?: string): void {
  trackedWorkers.set(sessionKey, {
    sessionKey,
    label,
    startTime: Date.now(),
    projectName,
  })
  
  // Start polling if not already running
  if (!pollInterval && trackedWorkers.size > 0) {
    startPolling()
  }
  
  console.log(`[worker-tracker] Now tracking ${trackedWorkers.size} workers`)
}

/**
 * Check if a session is still active via gateway (using /tools/invoke API)
 */
async function isSessionActive(sessionKey: string): Promise<boolean> {
  try {
    const response = await fetch(`${GATEWAY_URL}/tools/invoke`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${GATEWAY_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        tool: 'sessions_list',
        parameters: { limit: 100, messageLimit: 1 }
      })
    })
    
    if (!response.ok) return true // Assume active if we can't check
    
    const data = await response.json()
    
    // Parse sessions from gateway response
    let sessions: any[] = []
    if (data.result?.details?.sessions) {
      sessions = data.result.details.sessions
    } else if (data.result?.content?.[0]?.text) {
      const parsed = JSON.parse(data.result.content[0].text)
      sessions = parsed.sessions || []
    } else if (data.sessions) {
      sessions = data.sessions
    }
    
    // Find the session and check if it's still running
    const session = sessions.find((s: any) => s.key === sessionKey || s.sessionKey === sessionKey)
    
    if (!session) {
      return false // Session not found = not active
    }
    
    // Check stopReason from last message to determine if finished
    const lastMessage = session.messages?.[0]
    if (lastMessage?.stopReason === 'stop') {
      return false // Session finished
    }
    
    return true // Session still active
  } catch (err) {
    console.error(`[worker-tracker] Failed to check session ${sessionKey}:`, err)
    return true // Assume active on error
  }
}

/**
 * Poll for worker completions
 */
async function pollWorkers(): Promise<void> {
  if (trackedWorkers.size === 0) {
    stopPolling()
    return
  }
  
  const now = Date.now()
  const toRemove: string[] = []
  
  for (const [sessionKey, worker] of trackedWorkers) {
    // Check if max track time exceeded
    if (now - worker.startTime > MAX_TRACK_TIME_MS) {
      console.log(`[worker-tracker] Worker ${sessionKey} exceeded max track time, stopping tracking`)
      toRemove.push(sessionKey)
      continue
    }
    
    // Check if session is still active
    const isActive = await isSessionActive(sessionKey)
    
    if (!isActive) {
      // Session completed!
      const duration = now - worker.startTime
      console.log(`[worker-tracker] Worker ${sessionKey} completed after ${Math.round(duration / 1000)}s`)
      
      try {
        await logWorkerCompleted({
          sessionKey,
          label: worker.label,
          duration,
        })
      } catch (err) {
        console.error(`[worker-tracker] Failed to log completion:`, err)
      }
      
      toRemove.push(sessionKey)
    }
  }
  
  // Remove completed workers
  for (const key of toRemove) {
    trackedWorkers.delete(key)
  }
  
  if (trackedWorkers.size === 0) {
    stopPolling()
  }
}

function startPolling(): void {
  if (pollInterval) return
  console.log('[worker-tracker] Starting completion polling')
  pollInterval = setInterval(pollWorkers, POLL_INTERVAL_MS)
}

function stopPolling(): void {
  if (pollInterval) {
    console.log('[worker-tracker] Stopping completion polling (no workers to track)')
    clearInterval(pollInterval)
    pollInterval = null
  }
}

/**
 * Get current tracker state (for debugging)
 */
export function getTrackerState(): { 
  workers: TrackedWorker[]
  isPolling: boolean 
} {
  return {
    workers: Array.from(trackedWorkers.values()),
    isPolling: pollInterval !== null,
  }
}

/**
 * Manually mark a worker as completed (if we know it finished)
 */
export function markWorkerCompleted(sessionKey: string, output?: string): void {
  const worker = trackedWorkers.get(sessionKey)
  if (!worker) return
  
  const duration = Date.now() - worker.startTime
  
  logWorkerCompleted({
    sessionKey,
    label: worker.label,
    duration,
    output,
  }).catch(err => console.error('[worker-tracker] Failed to log completion:', err))
  
  trackedWorkers.delete(sessionKey)
}
