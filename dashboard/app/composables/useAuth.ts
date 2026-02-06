/**
 * Auth composable for SwarmOps Dashboard
 */

interface AuthStatus {
  authEnabled: boolean
  authenticated: boolean
  message?: string
}

const authState = reactive({
  checked: false,
  authEnabled: false,
  authenticated: false,
})

export function useAuth() {
  const router = useRouter()

  async function checkAuth(): Promise<AuthStatus> {
    try {
      const status = await $fetch<AuthStatus>('/api/auth/status')
      authState.checked = true
      authState.authEnabled = status.authEnabled
      authState.authenticated = status.authenticated
      return status
    } catch {
      authState.checked = true
      authState.authEnabled = false
      authState.authenticated = true // Assume authenticated if check fails
      return { authEnabled: false, authenticated: true }
    }
  }

  async function logout(): Promise<void> {
    try {
      await $fetch('/api/auth/logout', { method: 'POST' })
    } finally {
      authState.authenticated = false
      router.push('/login')
    }
  }

  const isAuthenticated = computed(() => authState.authenticated)
  const isAuthEnabled = computed(() => authState.authEnabled)
  const isChecked = computed(() => authState.checked)

  return {
    isAuthenticated: readonly(isAuthenticated),
    isAuthEnabled: readonly(isAuthEnabled),
    isChecked: readonly(isChecked),
    checkAuth,
    logout,
  }
}
