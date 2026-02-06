/**
 * POST /api/watchdog/run
 * 
 * Manually trigger the progress watchdog
 */

import { runWatchdog } from '../../utils/progress-watchdog'
import { requireAuth } from '../../utils/security'

export default defineEventHandler(async (event) => {
  requireAuth(event)
  const results = await runWatchdog()
  
  return {
    success: true,
    timestamp: new Date().toISOString(),
    results
  }
})
