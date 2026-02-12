/**
 * Delete a backtest session
 * 
 * DELETE /api/backtest/:id
 */

import { requireAuth, validateId } from '../../../utils/security'
import { backtestManager } from '../../../utils/backtest-manager'

export default defineEventHandler(async (event) => {
  // Require authentication
  requireAuth(event)

  const sessionId = validateId(getRouterParam(event, 'id'), 'Session ID')

  const deleted = backtestManager.deleteSession(sessionId)

  if (!deleted) {
    throw createError({
      statusCode: 404,
      message: `Session not found: ${sessionId}`,
    })
  }

  return {
    success: true,
    sessionId,
  }
})
