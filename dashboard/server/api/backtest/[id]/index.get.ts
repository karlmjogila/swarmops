/**
 * Get backtest session state
 * 
 * GET /api/backtest/:id
 */

import { requireAuth, validateId } from '../../../utils/security'
import { backtestManager } from '../../../utils/backtest-manager'

export default defineEventHandler(async (event) => {
  // Require authentication
  requireAuth(event)

  const sessionId = validateId(getRouterParam(event, 'id'), 'Session ID')

  const session = backtestManager.getSession(sessionId)
  
  if (!session) {
    throw createError({
      statusCode: 404,
      message: `Session not found: ${sessionId}`,
    })
  }

  return {
    sessionId: session.id,
    config: session.config,
    state: session.state,
    createdAt: session.createdAt,
    isRunning: session.process !== null && !session.process.killed,
  }
})
