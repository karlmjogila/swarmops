/**
 * GET /api/watchdog/status
 * 
 * Get watchdog status and last run info
 */

export default defineEventHandler(async (event) => {
  return {
    enabled: true,
    interval: '5 minutes',
    stalledThreshold: '10 minutes',
    maxRetries: 3,
    endpoints: {
      run: 'POST /api/watchdog/run',
      status: 'GET /api/watchdog/status'
    }
  }
})
