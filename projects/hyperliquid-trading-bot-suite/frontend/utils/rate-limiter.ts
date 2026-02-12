/**
 * Rate Limiter Utility for API Calls
 * 
 * Implements sliding window rate limiting to prevent exceeding
 * exchange rate limits and avoid being banned.
 */

export interface RateLimiterConfig {
  maxRequests: number       // Maximum requests allowed in the window
  windowMs: number          // Window size in milliseconds
  retryAfterMs?: number     // How long to wait after hitting limit
  headroom?: number         // Percentage of limit to use (0.7 = 70%)
}

export interface RateLimitState {
  requests: number[]        // Timestamps of recent requests
  isLimited: boolean        // Currently rate limited
  retryAfter?: number       // When we can retry
}

/**
 * Sliding window rate limiter
 */
export class RateLimiter {
  private config: Required<RateLimiterConfig>
  private requests: number[] = []
  private isLimited: boolean = false
  private retryAfter: number = 0
  
  constructor(config: RateLimiterConfig) {
    this.config = {
      maxRequests: config.maxRequests,
      windowMs: config.windowMs,
      retryAfterMs: config.retryAfterMs ?? 1000,
      headroom: config.headroom ?? 0.8,
    }
  }
  
  /**
   * Clean up old requests outside the window
   */
  private cleanup(): void {
    const now = Date.now()
    const windowStart = now - this.config.windowMs
    this.requests = this.requests.filter(t => t > windowStart)
  }
  
  /**
   * Get current request count in window
   */
  public getRequestCount(): number {
    this.cleanup()
    return this.requests.length
  }
  
  /**
   * Check if we can make a request
   */
  public canRequest(): boolean {
    const now = Date.now()
    
    // Check if we're in a cooldown period
    if (this.isLimited && now < this.retryAfter) {
      return false
    }
    
    // Reset limited status if cooldown passed
    if (this.isLimited && now >= this.retryAfter) {
      this.isLimited = false
    }
    
    this.cleanup()
    
    const effectiveLimit = Math.floor(this.config.maxRequests * this.config.headroom)
    return this.requests.length < effectiveLimit
  }
  
  /**
   * Record a request
   */
  public recordRequest(): void {
    this.requests.push(Date.now())
  }
  
  /**
   * Mark as rate limited (call when receiving 429 response)
   */
  public markLimited(retryAfterMs?: number): void {
    this.isLimited = true
    this.retryAfter = Date.now() + (retryAfterMs ?? this.config.retryAfterMs)
  }
  
  /**
   * Get time until next request is allowed
   */
  public getWaitTime(): number {
    const now = Date.now()
    
    if (this.isLimited && now < this.retryAfter) {
      return this.retryAfter - now
    }
    
    this.cleanup()
    
    const effectiveLimit = Math.floor(this.config.maxRequests * this.config.headroom)
    
    if (this.requests.length < effectiveLimit) {
      return 0
    }
    
    // Calculate when the oldest request in the window will expire
    const oldestInWindow = this.requests[0]
    return (oldestInWindow + this.config.windowMs) - now
  }
  
  /**
   * Wait until we can make a request
   */
  public async waitForSlot(): Promise<void> {
    const waitTime = this.getWaitTime()
    if (waitTime > 0) {
      await new Promise(resolve => setTimeout(resolve, waitTime))
    }
  }
  
  /**
   * Acquire a slot (wait if necessary, then record request)
   */
  public async acquire(): Promise<void> {
    await this.waitForSlot()
    this.recordRequest()
  }
  
  /**
   * Get current state (for debugging/monitoring)
   */
  public getState(): RateLimitState {
    this.cleanup()
    return {
      requests: [...this.requests],
      isLimited: this.isLimited,
      retryAfter: this.isLimited ? this.retryAfter : undefined,
    }
  }
  
  /**
   * Reset the limiter
   */
  public reset(): void {
    this.requests = []
    this.isLimited = false
    this.retryAfter = 0
  }
}

/**
 * Debounce utility for input fields
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delayMs: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null
  
  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    timeoutId = setTimeout(() => {
      fn(...args)
      timeoutId = null
    }, delayMs)
  }
}

/**
 * Throttle utility for frequent events
 */
export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  limitMs: number
): (...args: Parameters<T>) => void {
  let lastRun = 0
  let timeoutId: ReturnType<typeof setTimeout> | null = null
  
  return (...args: Parameters<T>) => {
    const now = Date.now()
    const timeSinceLast = now - lastRun
    
    if (timeSinceLast >= limitMs) {
      lastRun = now
      fn(...args)
    } else if (!timeoutId) {
      timeoutId = setTimeout(() => {
        lastRun = Date.now()
        fn(...args)
        timeoutId = null
      }, limitMs - timeSinceLast)
    }
  }
}

/**
 * Default rate limiters for common use cases
 */
export const defaultLimiters = {
  // General API calls: 60 requests per minute
  api: new RateLimiter({
    maxRequests: 60,
    windowMs: 60000,
    headroom: 0.8,
  }),
  
  // Trade API calls: 30 requests per minute (more conservative)
  trades: new RateLimiter({
    maxRequests: 30,
    windowMs: 60000,
    headroom: 0.7,
  }),
  
  // WebSocket reconnections: 5 per minute
  websocket: new RateLimiter({
    maxRequests: 5,
    windowMs: 60000,
    retryAfterMs: 5000,
  }),
  
  // Market data: 120 requests per minute
  marketData: new RateLimiter({
    maxRequests: 120,
    windowMs: 60000,
    headroom: 0.8,
  }),
}
