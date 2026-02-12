/**
 * List all backtest sessions
 * 
 * GET /api/backtest
 */

import { requireAuth } from '../../utils/security'
import { backtestManager } from '../../utils/backtest-manager'

export default defineEventHandler(async (event) => {
  // Require authentication
  requireAuth(event)

  const sessions = backtestManager.getAllSessions()

  return {
    sessions: sessions.map(session => ({
      sessionId: session.id,
      config: session.config,
      status: session.state.status,
      progress: session.state.progressPercent,
      createdAt: session.createdAt,
      isRunning: session.process !== null && !session.process.killed,
    })),
    total: sessions.length,
  }
})
