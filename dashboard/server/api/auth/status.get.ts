/**
 * Auth status endpoint - check if user is authenticated
 */

export default defineEventHandler(async (event) => {
  const gatewayToken = process.env.OPENCLAW_GATEWAY_TOKEN || ''

  // Check if auth is enabled
  const authEnabled = !!gatewayToken

  if (!authEnabled) {
    return {
      authEnabled: false,
      authenticated: true, // No auth = always authenticated
      message: 'Authentication is disabled'
    }
  }

  // Check for auth cookie
  const authToken = getCookie(event, 'swarmops_auth')

  if (!authToken) {
    return {
      authEnabled: true,
      authenticated: false,
      message: 'Not authenticated'
    }
  }

  // Validate token
  const isValid = authToken === gatewayToken
  
  return {
    authEnabled: true,
    authenticated: isValid,
    message: isValid ? 'Authenticated' : 'Invalid token'
  }
})
