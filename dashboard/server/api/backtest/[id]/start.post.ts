/**
 * Start a backtest session
 * 
 * POST /api/backtest/:id/start
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

  try {
    await backtestManager.start(sessionId)
    
    return {
      success: true,
      sessionId,
      status: 'running',
    }
  } catch (err: any) {
    throw createError({
      statusCode: 500,
      message: err.message || 'Failed to start backtest',
    })
  }
})
