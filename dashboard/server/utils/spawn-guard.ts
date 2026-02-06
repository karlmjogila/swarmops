/**
 * Spawn Guard - Prevents runaway session storms
 * 
 * Implements:
 * - Circuit breaker: stops spawns after consecutive failures
 * - Exponential backoff: delays retries progressively
 * - Unique labels: prevents label collisions
 * - Rate limiting: max concurrent spawns
 */

interface CircuitState {
  failures: number
  lastFailure: number
  openUntil: number  // Circuit is "open" (blocking) until this time
  lastSuccess: number
}

interface SpawnAttempt {
  timestamp: number
  label: string
  success: boolean
  error?: string
}

// Global state
const circuitState: CircuitState = {
  failures: 0,
  lastFailure: 0,
  openUntil: 0,
  lastSuccess: Date.now(),
}

const recentAttempts: SpawnAttempt[] = []
const MAX_RECENT_ATTEMPTS = 100

// Configuration
const CONFIG = {
  maxConsecutiveFailures: 5,      // Open circuit after this many failures
  circuitOpenDurationMs: 60_000,  // Keep circuit open for 1 minute
  maxConcurrentSpawns: 5,         // Allow up to 5 spawns per window (staggered in orchestrator)
  spawnWindowMs: 20_000,          // Window for spawn rate limit (20s)
  backoffBaseMs: 2000,            // Base delay for exponential backoff
  backoffMaxMs: 60_000,           // Max delay cap
  backoffMultiplier: 2,           // Exponential multiplier
}

/**
 * Generate a unique label suffix
 */
export function uniqueLabel(baseLabel: string): string {
  const timestamp = Date.now()
  const random = Math.random().toString(36).slice(2, 6)
  const full = `${baseLabel}:${timestamp}-${random}`
  
  // Gateway requires label <= 64 characters
  if (full.length <= 64) {
    return full
  }
  
  // Truncate base to fit: timestamp-random is ~18 chars, add colon = 19
  const maxBaseLen = 64 - 19
  const truncatedBase = baseLabel.slice(0, maxBaseLen)
  return `${truncatedBase}:${timestamp}-${random}`
}

/**
 * Check if spawning is allowed
 */
export function canSpawn(): { allowed: boolean; reason?: string; waitMs?: number } {
  const now = Date.now()
  
  // Check circuit breaker
  if (now < circuitState.openUntil) {
    const waitMs = circuitState.openUntil - now
    return {
      allowed: false,
      reason: `Circuit breaker open (${circuitState.failures} consecutive failures). Retry in ${Math.ceil(waitMs / 1000)}s`,
      waitMs,
    }
  }
  
  // Check rate limit
  const windowStart = now - CONFIG.spawnWindowMs
  const recentSpawns = recentAttempts.filter(a => a.timestamp > windowStart)
  
  if (recentSpawns.length >= CONFIG.maxConcurrentSpawns) {
    const oldestInWindow = Math.min(...recentSpawns.map(a => a.timestamp))
    const waitMs = oldestInWindow + CONFIG.spawnWindowMs - now
    return {
      allowed: false,
      reason: `Rate limit: ${CONFIG.maxConcurrentSpawns} spawns per ${CONFIG.spawnWindowMs / 1000}s window`,
      waitMs: Math.max(waitMs, 1000),
    }
  }
  
  return { allowed: true }
}

/**
 * Calculate exponential backoff delay
 */
export function getBackoffDelay(): number {
  if (circuitState.failures === 0) return 0
  
  const delay = Math.min(
    CONFIG.backoffBaseMs * Math.pow(CONFIG.backoffMultiplier, circuitState.failures - 1),
    CONFIG.backoffMaxMs
  )
  
  return delay
}

/**
 * Record a spawn attempt
 */
export function recordSpawn(label: string, success: boolean, error?: string): void {
  const now = Date.now()
  
  // Record attempt
  recentAttempts.push({ timestamp: now, label, success, error })
  
  // Trim old attempts
  while (recentAttempts.length > MAX_RECENT_ATTEMPTS) {
    recentAttempts.shift()
  }
  
  if (success) {
    // Reset circuit on success
    circuitState.failures = 0
    circuitState.lastSuccess = now
    circuitState.openUntil = 0
  } else {
    // Track failure
    circuitState.failures++
    circuitState.lastFailure = now
    
    // Open circuit if too many failures
    if (circuitState.failures >= CONFIG.maxConsecutiveFailures) {
      circuitState.openUntil = now + CONFIG.circuitOpenDurationMs
      console.warn(`[spawn-guard] Circuit breaker OPEN after ${circuitState.failures} failures. Blocking spawns for ${CONFIG.circuitOpenDurationMs / 1000}s`)
    }
  }
}

/**
 * Get current guard state (for debugging/monitoring)
 */
export function getGuardState() {
  const now = Date.now()
  const windowStart = now - CONFIG.spawnWindowMs
  
  return {
    circuitOpen: now < circuitState.openUntil,
    circuitOpensIn: circuitState.openUntil > now ? circuitState.openUntil - now : 0,
    consecutiveFailures: circuitState.failures,
    recentSpawnsInWindow: recentAttempts.filter(a => a.timestamp > windowStart).length,
    maxConcurrentSpawns: CONFIG.maxConcurrentSpawns,
    lastSuccess: circuitState.lastSuccess,
    lastFailure: circuitState.lastFailure,
    config: CONFIG,
  }
}

/**
 * Reset guard state (for testing/admin)
 */
export function resetGuard(): void {
  circuitState.failures = 0
  circuitState.lastFailure = 0
  circuitState.openUntil = 0
  circuitState.lastSuccess = Date.now()
  recentAttempts.length = 0
  console.log('[spawn-guard] Guard state reset')
}

/**
 * Sleep utility
 */
export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}
