/**
 * GET /api/orchestrator/phase-watcher - Get watcher status
 * POST /api/orchestrator/phase-watcher - Control watcher (start/stop/poll)
 */

import { 
  startPhaseWatcher, 
  stopPhaseWatcher, 
  triggerPoll, 
  getPhaseWatcherStatus 
} from '../../utils/phase-watcher'
import { requireAuth } from '../../utils/security'

export default defineEventHandler(async (event) => {
  requireAuth(event)
  
  const method = event.method
  
  if (method === 'GET') {
    return getPhaseWatcherStatus()
  }
  
  if (method === 'POST') {
    const body = await readBody<{ action: 'start' | 'stop' | 'poll' }>(event)
    
    switch (body?.action) {
      case 'start':
        startPhaseWatcher()
        return { ok: true, message: 'Phase watcher started', status: getPhaseWatcherStatus() }
        
      case 'stop':
        stopPhaseWatcher()
        return { ok: true, message: 'Phase watcher stopped', status: getPhaseWatcherStatus() }
        
      case 'poll':
        await triggerPoll()
        return { ok: true, message: 'Manual poll triggered', status: getPhaseWatcherStatus() }
        
      default:
        throw createError({ statusCode: 400, statusMessage: 'Invalid action. Use: start, stop, poll' })
    }
  }
  
  throw createError({ statusCode: 405, statusMessage: 'Method not allowed' })
})
