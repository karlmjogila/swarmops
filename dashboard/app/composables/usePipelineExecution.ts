import type { 
  ExecutionStatus, 
  NodeExecutionState, 
  PipelineExecution,
  PipelineNode,
} from '../types/pipeline'

interface RunData {
  runId: string
  pipelineId: string
  pipelineName: string
  status: 'running' | 'completed' | 'failed'
  currentStep: number
  totalSteps: number
  completedSteps: number
  activeSessionKey?: string
  startedAt: string
}

interface StepResult {
  stepId: string
  stepOrder: number
  status: 'completed' | 'failed' | 'skipped'
  output?: string
  error?: string
  completedAt: string
}

interface DetailedRunState {
  runId: string
  pipelineId: string
  pipelineName: string
  status: 'running' | 'completed' | 'failed'
  currentStepIndex: number
  totalSteps: number
  stepResults: StepResult[]
  startedAt: string
  completedAt?: string
}

export interface UsePipelineExecutionOptions {
  pipelineId: string
  pollInterval?: number // ms, default 2000
}

export function usePipelineExecution(options: UsePipelineExecutionOptions) {
  const { pipelineId, pollInterval = 2000 } = options
  
  // Core state
  const executionState = ref<PipelineExecution | null>(null)
  const nodeStatuses = ref<Map<string, ExecutionStatus>>(new Map())
  const nodeSessions = ref<Map<string, string>>(new Map()) // nodeId -> sessionId
  const isRunning = ref(false)
  const isStarting = ref(false)
  const isStopping = ref(false)
  const error = ref<string | null>(null)
  const currentRunId = ref<string | null>(null)
  
  // Polling interval reference
  let pollTimer: ReturnType<typeof setInterval> | null = null

  // Map step order to node IDs (will be set from pipeline graph)
  const stepToNodeMap = ref<Map<number, string>>(new Map())
  
  // Lock to prevent mapping changes during execution
  const isMappingLocked = ref(false)

  /**
   * Initialize step-to-node mapping from pipeline nodes
   * Should be called when pipeline graph is loaded
   * Mapping is locked during execution to prevent race conditions
   */
  function setNodeMapping(nodes: PipelineNode[]) {
    // Don't update mapping while execution is running
    // This prevents race conditions when nodes are moved during execution
    if (isMappingLocked.value) {
      return
    }
    
    const map = new Map<number, string>()
    
    // Find role nodes and map their order (position-based) to their IDs
    const roleNodes = nodes
      .filter(n => n.type === 'role')
      .sort((a, b) => a.position.y - b.position.y) // Sort by vertical position
    
    roleNodes.forEach((node, index) => {
      map.set(index + 1, node.id) // Steps are 1-indexed
    })
    
    stepToNodeMap.value = map
  }

  /**
   * Update node statuses based on run state
   */
  function updateNodeStatuses(run: DetailedRunState) {
    const statuses = new Map<string, ExecutionStatus>()
    
    // Mark completed/failed steps
    for (const result of run.stepResults) {
      const nodeId = stepToNodeMap.value.get(result.stepOrder)
      if (nodeId) {
        statuses.set(nodeId, result.status === 'completed' ? 'completed' : 'error')
      }
    }
    
    // Mark current step as running
    if (run.status === 'running') {
      const currentStepOrder = run.currentStepIndex + 1
      const currentNodeId = stepToNodeMap.value.get(currentStepOrder)
      if (currentNodeId && !statuses.has(currentNodeId)) {
        statuses.set(currentNodeId, 'running')
      }
    }
    
    // Mark remaining steps as idle/pending
    for (const [stepOrder, nodeId] of stepToNodeMap.value) {
      if (!statuses.has(nodeId)) {
        if (run.status === 'running' && stepOrder > run.currentStepIndex + 1) {
          statuses.set(nodeId, 'pending')
        } else {
          statuses.set(nodeId, 'idle')
        }
      }
    }
    
    nodeStatuses.value = statuses
    
    // Build execution state
    const nodeStates: Record<string, NodeExecutionState> = {}
    for (const [nodeId, status] of statuses) {
      const result = run.stepResults.find(r => {
        const mappedNodeId = stepToNodeMap.value.get(r.stepOrder)
        return mappedNodeId === nodeId
      })
      
      nodeStates[nodeId] = {
        nodeId,
        status,
        startedAt: result?.completedAt, // We don't have start time, use completed as approximation
        completedAt: result?.completedAt,
        error: result?.error,
      }
    }
    
    executionState.value = {
      id: run.runId,
      pipelineId: run.pipelineId,
      status: run.status === 'running' ? 'running' 
            : run.status === 'completed' ? 'completed' 
            : 'error',
      startedAt: run.startedAt,
      completedAt: run.completedAt,
      nodeStates,
      error: run.status === 'failed' 
        ? run.stepResults.find(r => r.status === 'failed')?.error 
        : undefined,
    }
  }

  /**
   * Poll for execution updates
   */
  async function pollExecution() {
    if (!currentRunId.value) {
      // Check if pipeline has an active run
      try {
        const runs = await $fetch<RunData[]>('/api/orchestrator/runs')
        const activeRun = runs.find(r => r.pipelineId === pipelineId && r.status === 'running')
        
        if (activeRun) {
          currentRunId.value = activeRun.runId
          isRunning.value = true
        }
      } catch (e) {
        // Ignore polling errors
      }
      return
    }
    
    // Get detailed run state from runs directory
    try {
      const runs = await $fetch<DetailedRunState[]>(`/api/orchestrator/pipelines/${pipelineId}/runs`, {
        query: { limit: 1 }
      })
      
      // Find our current run in the general runs list for real-time status
      const activeRuns = await $fetch<RunData[]>('/api/orchestrator/runs')
      const activeRun = activeRuns.find(r => r.runId === currentRunId.value)
      
      if (activeRun) {
        // Run is still active, construct state from active run data
        const run: DetailedRunState = {
          runId: activeRun.runId,
          pipelineId: activeRun.pipelineId,
          pipelineName: activeRun.pipelineName,
          status: activeRun.status,
          currentStepIndex: activeRun.currentStep - 1,
          totalSteps: activeRun.totalSteps,
          stepResults: [], // Active runs don't have step results yet
          startedAt: activeRun.startedAt,
        }
        
        // Get step results from stored run file if available
        if (runs.length > 0 && runs[0].runId === currentRunId.value) {
          run.stepResults = runs[0].stepResults
        }
        
        updateNodeStatuses(run)
        isRunning.value = true
      } else {
        // Run completed or was not found
        if (runs.length > 0 && runs[0].runId === currentRunId.value) {
          updateNodeStatuses(runs[0])
          isRunning.value = runs[0].status === 'running'
          
          if (runs[0].status !== 'running') {
            stopPolling()
            isMappingLocked.value = false
          }
        } else {
          // Run not found anywhere, stop polling
          isRunning.value = false
          isMappingLocked.value = false
          stopPolling()
        }
      }
    } catch (e) {
      // Ignore polling errors
    }
  }

  /**
   * Start polling for updates
   */
  function startPolling() {
    if (pollTimer) return
    
    // Initial poll
    pollExecution()
    
    // Set up interval
    pollTimer = setInterval(pollExecution, pollInterval)
  }

  /**
   * Stop polling
   */
  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  /**
   * Start pipeline execution
   */
  async function start(context?: { projectContext?: string; projectDir?: string }) {
    if (isStarting.value || isRunning.value) return
    
    isStarting.value = true
    error.value = null
    
    try {
      const result = await $fetch<{
        success: boolean
        runId?: string
        error?: string
      }>(`/api/orchestrator/pipelines/${pipelineId}/run`, {
        method: 'POST',
        body: context || {},
      })
      
      if (!result.success) {
        error.value = result.error || 'Failed to start pipeline'
        return false
      }
      
      currentRunId.value = result.runId || null
      isRunning.value = true
      
      // Lock mapping to prevent race conditions during execution
      isMappingLocked.value = true
      
      // Reset all node statuses to pending
      for (const nodeId of stepToNodeMap.value.values()) {
        nodeStatuses.value.set(nodeId, 'pending')
      }
      
      // Start polling for updates
      startPolling()
      
      return true
    } catch (e: any) {
      error.value = e.message || 'Failed to start pipeline'
      return false
    } finally {
      isStarting.value = false
    }
  }

  /**
   * Stop pipeline execution
   * Note: Backend may not support graceful stop yet
   */
  async function stop() {
    if (isStopping.value || !isRunning.value) return
    
    isStopping.value = true
    
    try {
      // TODO: Implement stop endpoint when backend supports it
      // For now, just stop polling and mark as stopped
      stopPolling()
      isRunning.value = false
      currentRunId.value = null
      
      // Unlock mapping now that execution has stopped
      isMappingLocked.value = false
      
      // Reset statuses
      for (const nodeId of stepToNodeMap.value.values()) {
        const currentStatus = nodeStatuses.value.get(nodeId)
        if (currentStatus === 'running' || currentStatus === 'pending') {
          nodeStatuses.value.set(nodeId, 'idle')
        }
      }
      
      return true
    } finally {
      isStopping.value = false
    }
  }

  /**
   * Reset execution state
   */
  function reset() {
    stopPolling()
    executionState.value = null
    nodeStatuses.value = new Map()
    nodeSessions.value = new Map()
    isRunning.value = false
    currentRunId.value = null
    error.value = null
    
    // Unlock mapping when resetting
    isMappingLocked.value = false
    
    // Set all mapped nodes to idle
    for (const nodeId of stepToNodeMap.value.values()) {
      nodeStatuses.value.set(nodeId, 'idle')
    }
  }

  /**
   * Get status for a specific node
   */
  function getNodeStatus(nodeId: string): ExecutionStatus {
    return nodeStatuses.value.get(nodeId) || 'idle'
  }

  /**
   * Get session ID for a node
   */
  function getNodeSessionId(nodeId: string): string | undefined {
    return nodeSessions.value.get(nodeId)
  }

  /**
   * Fetch active workers and map them to nodes
   */
  async function refreshWorkerSessions() {
    try {
      const workers = await $fetch<{
        id: string
        roleId: string
        roleName: string
        taskId?: string
        status: string
      }[]>('/api/orchestrator/workers')
      
      // Clear existing mappings
      nodeSessions.value.clear()
      
      // Map workers to nodes by matching role information
      for (const [stepOrder, nodeId] of stepToNodeMap.value) {
        // Find a worker that might match this node
        // This is heuristic - in production, the backend should provide explicit mapping
        const worker = workers.find(w => {
          // Check if taskId contains step order or node-related info
          return w.taskId?.includes(`step${stepOrder}`) || 
                 w.taskId?.includes(`node-${nodeId}`)
        })
        
        if (worker) {
          nodeSessions.value.set(nodeId, worker.id)
        }
      }
    } catch (e) {
      console.error('Failed to fetch workers:', e)
    }
  }

  /**
   * Check if any node has an error
   */
  const hasError = computed(() => {
    for (const status of nodeStatuses.value.values()) {
      if (status === 'error') return true
    }
    return false
  })

  /**
   * Get completion percentage
   */
  const completionPercent = computed(() => {
    const total = stepToNodeMap.value.size
    if (total === 0) return 0
    
    let completed = 0
    for (const status of nodeStatuses.value.values()) {
      if (status === 'completed') completed++
    }
    
    return Math.round((completed / total) * 100)
  })

  // Cleanup on unmount
  onUnmounted(() => {
    stopPolling()
  })

  // Start checking for existing runs on mount
  onMounted(() => {
    pollExecution()
  })

  return {
    // State
    executionState: readonly(executionState),
    nodeStatuses: readonly(nodeStatuses),
    nodeSessions: readonly(nodeSessions),
    isRunning: readonly(isRunning),
    isStarting: readonly(isStarting),
    isStopping: readonly(isStopping),
    error: readonly(error),
    currentRunId: readonly(currentRunId),
    
    // Computed
    hasError,
    completionPercent,
    
    // Actions
    start,
    stop,
    reset,
    setNodeMapping,
    getNodeStatus,
    getNodeSessionId,
    refreshWorkerSessions,
    startPolling,
    stopPolling,
  }
}
