/**
 * Logout endpoint - clears auth cookie
 */

export default defineEventHandler(async (event) => {
  // Clear auth cookie
  deleteCookie(event, 'swarmops_auth', {
    path: '/'
  })

  return {
    success: true,
    message: 'Logged out successfully'
  }
})
