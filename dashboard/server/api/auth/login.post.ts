/**
 * Login endpoint - validates gateway token
 */

interface LoginRequest {
  token: string
}

export default defineEventHandler(async (event) => {
  const body = await readBody<LoginRequest>(event)

  if (!body.token?.trim()) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Token is required'
    })
  }

  const gatewayToken = process.env.OPENCLAW_GATEWAY_TOKEN || ''

  // If no gateway token is configured, auth is disabled
  if (!gatewayToken) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Authentication is not configured on this server'
    })
  }

  // Validate token
  if (body.token.trim() !== gatewayToken) {
    throw createError({
      statusCode: 401,
      statusMessage: 'Invalid token'
    })
  }

  // Set auth cookie (httpOnly for security, 7 day expiry)
  // Don't require secure for local/tailscale HTTP access
  const isHttps = getRequestURL(event).protocol === 'https:'
  setCookie(event, 'swarmops_auth', body.token.trim(), {
    httpOnly: true,
    secure: isHttps,
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 7, // 7 days
    path: '/'
  })

  return {
    success: true,
    message: 'Logged in successfully'
  }
})
