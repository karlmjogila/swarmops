export interface PipelineStep {
  id: string
  order: number
  roleId: string
  roleName?: string
  action: string
  convergence?: {
    maxIterations?: number
    targetScore?: number
  }
}

export interface Pipeline {
  id: string
  name: string
  description?: string
  status: 'idle' | 'running' | 'paused' | 'completed' | 'error'
  steps: PipelineStep[]
  createdAt?: string
  lastRunAt?: string
  currentStep?: number
  completedSteps?: number[]
}

export interface UsePipelineOptions {
  immediate?: boolean
}

export function usePipeline(options: UsePipelineOptions = {}) {
  const { immediate = true } = options

  const { data: pipelines, pending, error, refresh } = useFetch<Pipeline[]>('/api/orchestrator/pipelines', {
    key: 'pipelines-list',
    default: () => [],
    immediate,
  })

  const deleting = ref<string | null>(null)
  const running = ref<string | null>(null)

  async function deletePipeline(id: string) {
    deleting.value = id
    try {
      await $fetch(`/api/orchestrator/pipelines/${id}`, { method: 'DELETE' })
      await refresh()
    } finally {
      deleting.value = null
    }
  }

  async function runPipeline(id: string) {
    running.value = id
    try {
      await $fetch(`/api/orchestrator/pipelines/${id}/run`, { method: 'POST' })
      await refresh()
    } finally {
      running.value = null
    }
  }

  async function createPipeline(data: { name: string; description?: string; steps?: PipelineStep[] }) {
    const result = await $fetch<Pipeline>('/api/orchestrator/pipelines', {
      method: 'POST',
      body: data,
    })
    await refresh()
    return result
  }

  async function updatePipeline(id: string, data: { name?: string; description?: string; steps?: PipelineStep[] }) {
    const result = await $fetch<Pipeline>(`/api/orchestrator/pipelines/${id}`, {
      method: 'PUT',
      body: data,
    })
    await refresh()
    return result
  }

  return {
    pipelines,
    pending,
    error,
    refresh,
    deletePipeline,
    runPipeline,
    createPipeline,
    updatePipeline,
    deleting,
    running,
  }
}
