/**
 * Resume a paused backtest session
 * 
 * POST /api/backtest/:id/resume
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
    await backtestManager.resume(sessionId)
    
    return {
      success: true,
      sessionId,
      status: 'running',
    }
  } catch (err: any) {
    // Distinguish between "session not found" and other errors
    if (err.message?.includes('not found')) {
      throw createError({
        statusCode: 404,
        message: err.message,
      })
    }
    throw createError({
      statusCode: 500,
      message: err.message || 'Failed to resume backtest',
    })
  }
})
