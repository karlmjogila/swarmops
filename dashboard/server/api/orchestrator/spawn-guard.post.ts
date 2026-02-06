/**
 * POST /api/orchestrator/spawn-guard
 * 
 * Reset spawn guard state (admin action)
 * Body: { "action": "reset" }
 */

import { resetGuard, getGuardState } from '../../utils/spawn-guard'
import { requireAuth } from '../../utils/security'

export default defineEventHandler(async (event) => {
  requireAuth(event)
  const body = await readBody<{ action: string }>(event)
  
  if (body?.action === 'reset') {
    resetGuard()
    return { 
      success: true, 
      message: 'Spawn guard reset',
      state: getGuardState()
    }
  }
  
  throw createError({
    statusCode: 400,
    statusMessage: 'Invalid action. Use { "action": "reset" }',
  })
})
