/**
 * Watchdog Plugin
 * 
 * Runs the progress watchdog every 5 minutes to detect and recover stalled projects.
 */

import { runWatchdog } from '../utils/progress-watchdog'

const WATCHDOG_INTERVAL_MS = 5 * 60 * 1000  // 5 minutes

let watchdogInterval: ReturnType<typeof setInterval> | null = null

export default defineNitroPlugin((nitroApp) => {
  console.log('[watchdog] Plugin initialized')
  
  // Start watchdog on server ready
  nitroApp.hooks.hook('ready', () => {
    console.log(`[watchdog] Starting watchdog (interval: ${WATCHDOG_INTERVAL_MS / 1000}s)`)
    
    // Run immediately on startup (after 30s delay to let things settle)
    setTimeout(async () => {
      try {
        console.log('[watchdog] Running initial check...')
        const results = await runWatchdog()
        console.log(`[watchdog] Initial check complete: ${results.length} projects checked`)
      } catch (err) {
        console.error('[watchdog] Initial check failed:', err)
      }
    }, 30000)
    
    // Then run every 5 minutes
    watchdogInterval = setInterval(async () => {
      try {
        const results = await runWatchdog()
        const issues = results.filter(r => r.status !== 'healthy')
        if (issues.length > 0) {
          console.log(`[watchdog] Found ${issues.length} issues:`, issues)
        }
      } catch (err) {
        console.error('[watchdog] Check failed:', err)
      }
    }, WATCHDOG_INTERVAL_MS)
  })
  
  // Clean up on shutdown
  nitroApp.hooks.hook('close', () => {
    if (watchdogInterval) {
      clearInterval(watchdogInterval)
      watchdogInterval = null
      console.log('[watchdog] Plugin stopped')
    }
  })
})
