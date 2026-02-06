/**
 * GET /api/orchestrator/spawn-guard
 * 
 * Returns current spawn guard state for monitoring
 */

import { getSpawnGuardState } from '../../utils/gateway-client'

export default defineEventHandler(async () => {
  return getSpawnGuardState()
})
