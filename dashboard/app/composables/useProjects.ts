import type { ProjectListItem } from '~/types/project'

export interface UseProjectsOptions {
  /** Auto-refresh interval in milliseconds (0 to disable) */
  refreshInterval?: number
  /** Whether to start fetching immediately */
  immediate?: boolean
  /** Enable real-time updates via WebSocket */
  realtime?: boolean
}

export function useProjects(options: UseProjectsOptions = {}) {
  const { refreshInterval = 0, immediate = true, realtime = true } = options

  const { data: projects, pending, error, refresh } = useFetch<ProjectListItem[]>('/api/projects', {
    key: 'projects-list',
    default: () => [],
    immediate,
  })

  // Auto-refresh interval
  let intervalId: ReturnType<typeof setInterval> | null = null

  const startAutoRefresh = () => {
    if (refreshInterval > 0 && !intervalId) {
      intervalId = setInterval(() => {
        refresh()
      }, refreshInterval)
    }
  }

  const stopAutoRefresh = () => {
    if (intervalId) {
      clearInterval(intervalId)
      intervalId = null
    }
  }

  // Start auto-refresh if enabled
  if (refreshInterval > 0) {
    onMounted(startAutoRefresh)
    onUnmounted(stopAutoRefresh)
  }

  // Real-time updates via WebSocket
  let unsubscribe: (() => void) | null = null
  
  if (realtime && import.meta.client) {
    onMounted(() => {
      const { onProjectUpdate } = useWebSocket()
      
      // Refresh project list when any project changes
      unsubscribe = onProjectUpdate((_project, file) => {
        // Only refresh on state.json changes to avoid too many refreshes
        if (file.includes('state.json')) {
          refresh()
        }
      })
    })
    
    onUnmounted(() => {
      if (unsubscribe) {
        unsubscribe()
        unsubscribe = null
      }
    })
  }

  return {
    projects,
    pending,
    error,
    refresh,
    startAutoRefresh,
    stopAutoRefresh,
  }
}
