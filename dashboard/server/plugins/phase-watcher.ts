/**
 * Nitro plugin to start the phase watcher on server startup
 */

import { startPhaseWatcher } from '../utils/phase-watcher'

export default defineNitroPlugin((nitro) => {
  // Start phase watcher when server boots
  // Note: Nitro plugins run after server is ready
  nitro.hooks.hook('request', () => {
    // Only start once
    if (!(globalThis as any).__phaseWatcherStarted) {
      (globalThis as any).__phaseWatcherStarted = true
      console.log('[plugin:phase-watcher] Starting phase watcher service...')
      startPhaseWatcher()
    }
  })
})
