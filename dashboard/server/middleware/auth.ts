/**
 * Auth middleware for SwarmOps Dashboard
 * Uses OpenClaw gateway token for authentication
 */

// Routes that don't require auth
const publicRoutes = [
  '/api/auth/login',
  '/api/auth/verify',
  '/api/auth/status',
  '/_ws', // WebSocket might handle its own auth
]

// API routes that agents/internal services call (allow without auth from localhost)
const agentApiPatterns = [
  /^\/api\/projects\/[^/]+\/task-complete$/,
  /^\/api\/projects\/[^/]+\/review-result$/,
  /^\/api\/projects\/[^/]+\/spec-complete$/,
  /^\/api\/projects\/[^/]+\/fix-complete$/,
  /^\/api\/projects\/[^/]+\/interview$/,
  /^\/api\/projects\/[^/]+\/orchestrate$/,
  /^\/api\/orchestrator\/review-result$/,
  /^\/api\/orchestrator\/worker-complete$/,
  /^\/api\/orchestrator\/merge-phase$/,
]

// Static assets and internal routes
const ignoredPrefixes = [
  '/_nuxt',
  '/__nuxt',
  '/favicon.ico',
  '/robots.txt',
]

function isPublicRoute(path: string): boolean {
  // Check exact matches
  if (publicRoutes.includes(path)) return true
  
  // Check prefixes for static assets
  for (const prefix of ignoredPrefixes) {
    if (path.startsWith(prefix)) return true
  }
  
  // Login page is public
  if (path === '/login') return true
  
  return false
}

function isAgentApiRoute(path: string): boolean {
  return agentApiPatterns.some(pattern => pattern.test(path))
}

function isLocalhostRequest(event: any): boolean {
  const host = getHeader(event, 'host') || ''
  const forwardedFor = getHeader(event, 'x-forwarded-for') || ''
  const remoteAddr = event.node?.req?.socket?.remoteAddress || ''
  
  // Check if request is from localhost
  return (
    host.startsWith('localhost') ||
    host.startsWith('127.0.0.1') ||
    remoteAddr === '127.0.0.1' ||
    remoteAddr === '::1' ||
    remoteAddr === '::ffff:127.0.0.1' ||
    forwardedFor === '' // No forwarded-for means direct local connection
  )
}

export default defineEventHandler(async (event) => {
  const path = getRequestURL(event).pathname
  
  // Skip auth for public routes
  if (isPublicRoute(path)) return
  
  // Allow agent API calls from localhost without auth
  // This lets spawned agents call back to report task completion
  if (isAgentApiRoute(path) && isLocalhostRequest(event)) {
    return
  }

  // Check if auth is enabled (only when OPENCLAW_GATEWAY_TOKEN is set)
  const gatewayToken = process.env.OPENCLAW_GATEWAY_TOKEN || ''
  if (!gatewayToken) {
    // No token configured = auth disabled (dev mode)
    return
  }

  // Check for auth cookie or header
  const authToken = getCookie(event, 'swarmops_auth') ||
                    getHeader(event, 'x-swarmops-token')

  if (!authToken) {
    // No auth token - redirect to login for pages, 401 for API
    if (path.startsWith('/api/')) {
      throw createError({
        statusCode: 401,
        statusMessage: 'Authentication required'
      })
    }
    // Redirect to login
    return sendRedirect(event, '/login')
  }

  // Validate token matches gateway token
  if (authToken !== gatewayToken) {
    // Invalid token
    deleteCookie(event, 'swarmops_auth')
    
    if (path.startsWith('/api/')) {
      throw createError({
        statusCode: 401,
        statusMessage: 'Invalid authentication token'
      })
    }
    return sendRedirect(event, '/login')
  }

  // Token is valid, continue
})
