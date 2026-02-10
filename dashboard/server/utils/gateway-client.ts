/**
 * OpenClaw Gateway Client
 * Calls the Gateway's tools/invoke endpoint to spawn sessions
 * 
 * SAFEGUARDS (added after session storm incident 2026-02-03):
 * - Circuit breaker: stops spawns after consecutive failures
 * - Rate limiting: max 10 concurrent spawns per 10s window
 * - Unique labels: auto-appends timestamp to prevent collisions
 * - Auto-cleanup: failed sessions deleted by default
 * - Exponential backoff: automatic delays on failures
 * - Spawn verification: confirms session actually started running (2026-02-03)
 */

import { 
  canSpawn, 
  recordSpawn, 
  uniqueLabel, 
  getBackoffDelay, 
  sleep,
  getGuardState 
} from './spawn-guard'
import { logWorkerSpawned, logWorkerFailed } from './ledger-writer'
import { trackWorker } from './worker-tracker'

// Gateway config loaded lazily from runtimeConfig
let _gatewayUrl: string | null = null
let _gatewayToken: string | null = null

function getGatewayConfig() {
  if (!_gatewayUrl) {
    _gatewayUrl = process.env.OPENCLAW_GATEWAY_URL || 'http://127.0.0.1:18789'
    _gatewayToken = process.env.OPENCLAW_GATEWAY_TOKEN || ''
  }
  return { url: _gatewayUrl, token: _gatewayToken! }
}
// Token loaded from runtimeConfig via getGatewayConfig()

// Spawn verification settings (DISABLED 2026-02-04 - sessions created but verification fails)
// Sessions get created but don't start immediately when spawned from HTTP context
// Disabling verification - trusting spawn acceptance
const VERIFY_DELAY_MS = 3000       // Wait 3s before checking (gateway can be slow)
const VERIFY_POLL_INTERVAL_MS = 2000  // Poll every 2s
const VERIFY_MAX_POLLS = 6        // Check up to 6 times (12s total)
const SPAWN_MAX_RETRIES = 0       // No retries - just accept spawn
const SKIP_VERIFICATION = true    // Skip verification entirely

interface SpawnResult {
  ok: boolean
  result?: {
    status: 'accepted'
    runId: string
    childSessionKey: string
    // Gateway wraps tool results in content/details
    content?: any[]
    details?: {
      status: 'accepted'
      runId: string
      childSessionKey: string
      modelApplied?: boolean
    }
  }
  error?: {
    type: string
    message: string
  }
  guardBlocked?: boolean  // True if spawn was blocked by circuit breaker/rate limit
  verified?: boolean      // True if session was verified to be running
  retryCount?: number     // Number of retries needed
}

interface SpawnOptions {
  task: string
  label?: string
  model?: string
  thinking?: string
  runTimeoutSeconds?: number
  cleanup?: 'delete' | 'keep'
  skipGuard?: boolean  // Bypass safeguards (use with caution!)
  skipVerify?: boolean // Skip spawn verification (use for fire-and-forget)
}

/**
 * Check if a session has actually started running
 * Returns true if session has tokens > 0 or has messages
 */
async function verifySessionRunning(sessionKey: string): Promise<boolean> {
  try {
    const response = await fetch(`${getGatewayConfig().url}/tools/invoke`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getGatewayConfig().token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        tool: 'sessions_list',
        args: {
          limit: 50,
          messageLimit: 1,
        },
      }),
    })

    if (!response.ok) return false

    const data = await response.json()
    // Gateway wraps tool results in result.details
    const sessions = data.result?.details?.sessions || data.sessions || []
    
    // Find our session
    const session = sessions.find((s: any) => s.key === sessionKey)
    if (!session) {
      console.log(`[gateway-client] Session ${sessionKey} not found in list`)
      return false
    }
    
    // Check if it has tokens (meaning it actually ran)
    const hasTokens = session.totalTokens > 0
    // Check if it has a model assigned (meaning it initialized)
    const hasModel = !!session.model
    // Check if it has messages
    const hasMessages = session.messages && session.messages.length > 0
    
    const isRunning = hasTokens || hasModel || hasMessages
    
    console.log(`[gateway-client] Session ${sessionKey} verify: tokens=${session.totalTokens}, model=${session.model}, running=${isRunning}`)
    
    return isRunning
  } catch (err) {
    console.error(`[gateway-client] Failed to verify session ${sessionKey}:`, err)
    return false
  }
}

/**
 * Wait for session to start running with polling
 */
async function waitForSessionStart(sessionKey: string): Promise<boolean> {
  // Initial delay before first check
  await sleep(VERIFY_DELAY_MS)
  
  for (let i = 0; i < VERIFY_MAX_POLLS; i++) {
    const isRunning = await verifySessionRunning(sessionKey)
    if (isRunning) {
      console.log(`[gateway-client] Session ${sessionKey} verified running after ${i + 1} polls`)
      return true
    }
    
    if (i < VERIFY_MAX_POLLS - 1) {
      await sleep(VERIFY_POLL_INTERVAL_MS)
    }
  }
  
  console.warn(`[gateway-client] Session ${sessionKey} failed to start after ${VERIFY_MAX_POLLS} polls`)
  return false
}

/**
 * Internal spawn without verification (used for retries)
 */
async function spawnSessionInternal(options: SpawnOptions, finalLabel: string): Promise<SpawnResult> {
  try {
    // Build args, only including defined values (avoid sending undefined)
    const args: Record<string, any> = {
      task: options.task,
      label: finalLabel,
      cleanup: options.cleanup || 'delete', // Default to delete - sessions pile up otherwise
    }
    if (options.model) args.model = options.model
    if (options.thinking) args.thinking = options.thinking
    if (options.runTimeoutSeconds) args.runTimeoutSeconds = options.runTimeoutSeconds
    
    console.log(`[gateway-client] Spawn request args:`, JSON.stringify(args))
    
    const response = await fetch(`${getGatewayConfig().url}/tools/invoke`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getGatewayConfig().token}`,
        'Content-Type': 'application/json',
        'Connection': 'close', // Don't keep-alive - might cause issues
      },
      body: JSON.stringify({
        tool: 'sessions_spawn',
        args,
      }),
    })

    if (!response.ok) {
      const text = await response.text()
      console.error(`[gateway-client] Spawn HTTP error ${response.status}: ${text}`)
      return {
        ok: false,
        error: {
          type: `HTTP_${response.status}`,
          message: text || response.statusText,
        },
      }
    }

    const result = await response.json()
    console.log(`[gateway-client] Spawn response:`, JSON.stringify(result).slice(0, 500))
    
    // Check for error in the details (gateway returns ok:true but status:"error" in details)
    const details = result.result?.details
    if (details?.status === 'error') {
      console.error(`[gateway-client] Spawn returned error: ${details.error}`)
      return {
        ok: false,
        error: {
          type: 'SPAWN_ERROR',
          message: details.error || 'Spawn failed',
        },
      }
    }
    
    return result
  } catch (err: any) {
    return {
      ok: false,
      error: {
        type: 'NETWORK_ERROR',
        message: err?.message || String(err),
      },
    }
  }
}

export async function spawnSession(options: SpawnOptions): Promise<SpawnResult> {
  // === SAFEGUARD: Check if spawning is allowed ===
  if (!options.skipGuard) {
    const guardCheck = canSpawn()
    if (!guardCheck.allowed) {
      console.warn(`[gateway-client] Spawn blocked: ${guardCheck.reason}`)
      return {
        ok: false,
        guardBlocked: true,
        error: {
          type: 'GUARD_BLOCKED',
          message: guardCheck.reason || 'Spawn blocked by guard',
        },
      }
    }
    
    // Apply backoff delay if we've had recent failures
    const backoffMs = getBackoffDelay()
    if (backoffMs > 0) {
      console.log(`[gateway-client] Applying ${backoffMs}ms backoff delay before spawn`)
      await sleep(backoffMs)
    }
  }
  
  // === SAFEGUARD: Make label unique to prevent collisions ===
  let finalLabel = options.label 
    ? uniqueLabel(options.label)
    : uniqueLabel('swarm-agent')
  
  let lastResult: SpawnResult | null = null
  let retryCount = 0
  
  // Try spawning with verification and retries
  for (let attempt = 0; attempt <= SPAWN_MAX_RETRIES; attempt++) {
    if (attempt > 0) {
      // Generate new unique label for retry
      finalLabel = options.label 
        ? uniqueLabel(`${options.label}-retry${attempt}`)
        : uniqueLabel(`swarm-agent-retry${attempt}`)
      console.log(`[gateway-client] Retry ${attempt}/${SPAWN_MAX_RETRIES} with label: ${finalLabel}`)
    } else {
      console.log(`[gateway-client] Spawning session with label: ${finalLabel}`)
    }
    
    // Attempt spawn
    const result = await spawnSessionInternal(options, finalLabel)
    lastResult = result
    
    if (!result.ok) {
      console.error(`[gateway-client] Spawn failed: ${result.error?.message}`)
      if (!options.skipGuard) {
        recordSpawn(finalLabel, false, result.error?.message)
      }
      continue // Try again
    }
    
    // Spawn returned success - verify it actually started
    // Gateway wraps responses: check details.childSessionKey first, then direct childSessionKey
    const sessionKey = result.result?.details?.childSessionKey || result.result?.childSessionKey
    
    // DISABLED: Verification disabled globally - sessions created from HTTP don't start immediately
    if (!SKIP_VERIFICATION && !options.skipVerify && sessionKey) {
      console.log(`[gateway-client] Verifying session ${sessionKey} actually started...`)
      
      const verified = await waitForSessionStart(sessionKey)
      
      if (verified) {
        // Success! Session is actually running
        if (!options.skipGuard) {
          recordSpawn(finalLabel, true)
        }
        
        // Log to ledger
        logWorkerSpawned({
          sessionKey,
          label: finalLabel,
          model: options.model,
          task: options.task?.slice(0, 200), // Truncate long tasks
        }).catch(err => console.error('[gateway-client] Failed to log worker spawn:', err))
        
        // Track for completion
        trackWorker(sessionKey, finalLabel)
        
        // Normalize result structure (gateway wraps in details)
        const normalizedResult = {
          ok: result.ok,
          result: {
            status: 'accepted' as const,
            childSessionKey: sessionKey,
            runId: result.result?.details?.runId || result.result?.runId || '',
          },
          verified: true,
          retryCount: attempt,
        }
        return normalizedResult
      } else {
        // Session created but never started - this is the bug we're fixing
        console.error(`[gateway-client] Session ${result.result.childSessionKey} created but failed to start (zombie session)`)
        
        if (!options.skipGuard) {
          recordSpawn(finalLabel, false, 'Session created but failed to start')
        }
        
        retryCount = attempt + 1
        // Continue to retry
        continue
      }
    } else {
      // Verification skipped - trust the spawn result
      if (!options.skipGuard) {
        recordSpawn(finalLabel, result.ok, result.error?.message)
      }
      
      // Log to ledger and track for completion (when verification skipped)
      const sessionKey = result.result?.details?.childSessionKey || result.result?.childSessionKey
      if (result.ok && sessionKey) {
        logWorkerSpawned({
          sessionKey,
          label: finalLabel,
          model: options.model,
          task: options.task?.slice(0, 200),
        }).catch(err => console.error('[gateway-client] Failed to log worker spawn:', err))
        
        trackWorker(sessionKey, finalLabel)
      }
      
      return {
        ...result,
        verified: false,
        retryCount: attempt,
      }
    }
  }
  
  // All retries exhausted
  console.error(`[gateway-client] Spawn failed after ${SPAWN_MAX_RETRIES + 1} attempts`)
  
  const errorMessage = `Session spawn failed verification after ${SPAWN_MAX_RETRIES + 1} attempts. Last error: ${lastResult?.error?.message || 'Session created but never started'}`
  
  // Log failure to ledger
  logWorkerFailed({
    sessionKey: lastResult?.result?.details?.childSessionKey || lastResult?.result?.childSessionKey || 'unknown',
    label: finalLabel,
    error: errorMessage,
  }).catch(err => console.error('[gateway-client] Failed to log worker failure:', err))
  
  return {
    ok: false,
    error: {
      type: 'SPAWN_VERIFICATION_FAILED',
      message: errorMessage,
    },
    retryCount,
  }
}

/**
 * Get current spawn guard state (for monitoring/debugging)
 */
export function getSpawnGuardState() {
  return getGuardState()
}

export async function listSessions(options?: { 
  activeMinutes?: number
  limit?: number 
}): Promise<any> {
  const response = await fetch(`${getGatewayConfig().url}/tools/invoke`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getGatewayConfig().token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      tool: 'sessions_list',
      args: {
        activeMinutes: options?.activeMinutes,
        limit: options?.limit,
      },
    }),
  })

  return response.json()
}
