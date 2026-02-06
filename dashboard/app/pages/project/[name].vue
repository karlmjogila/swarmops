<script setup lang="ts">
import type { ProjectState, Iteration } from '~/types/project'

interface SpecFile {
  name: string
  content: string
}

interface InterviewState {
  messages: { id: string; timestamp: string; role: 'user' | 'agent'; content: string }[]
  complete: boolean
}

interface ActivityEvent {
  id: string
  timestamp: string
  type: string
  agent?: string
  taskId?: string
  message: string
  phaseNumber?: number
  workerId?: string
  workerBranch?: string
  success?: boolean
}

interface ActivityResponse {
  events: ActivityEvent[]
  lastModified: string | null
}

interface ProjectDetail {
  name: string
  state: ProjectState | null
  progress: string | null
  plan: string | null
  specs: SpecFile[]
  logs: Iteration[]
}

const route = useRoute()
const projectName = computed(() => route.params.name as string)

const { onProjectUpdate } = useWebSocket()

const { data: project, pending, error, refresh } = await useFetch<ProjectDetail>(
  () => `/api/projects/${projectName.value}`,
  { watch: [projectName] }
)

const { data: activityData, refresh: refreshActivity } = await useFetch<ActivityResponse>(
  () => `/api/projects/${projectName.value}/activity`,
  {
    watch: [projectName],
    default: () => ({ events: [], lastModified: null })
  }
)

const { data: interview, refresh: refreshInterview } = await useFetch<InterviewState>(
  () => `/api/projects/${projectName.value}/interview`,
  {
    watch: [projectName],
    default: () => ({ messages: [], complete: false })
  }
)

const projectWithActivity = computed(() => {
  if (!project.value) return null
  return {
    ...project.value,
    activity: activityData.value?.events || []
  }
})

const isInterviewPhase = computed(() => {
  return project.value?.state?.phase === 'interview' && !interview.value?.complete
})

async function handleInterviewComplete() {
  await Promise.all([refresh(), refreshInterview(), refreshActivity()])
}

let unsubscribe: (() => void) | null = null

onMounted(() => {
  unsubscribe = onProjectUpdate((updatedProject, file) => {
    if (updatedProject === projectName.value) {
      refresh()
      refreshActivity()
      if (file === 'interview.json') {
        refreshInterview()
      }
    }
  })
})

onUnmounted(() => {
  if (unsubscribe) {
    unsubscribe()
    unsubscribe = null
  }
})

useHead({
  title: computed(() => project.value?.name ? `${project.value.name} - SwarmOps` : 'SwarmOps')
})
</script>

<template>
  <div>
    <ProjectSkeleton v-if="pending && !project" />

    <div v-else-if="error" class="error-state">
      <div class="error-content">
        <UIcon name="i-heroicons-exclamation-triangle" class="error-icon" />
        <h2 class="error-title">Failed to load project</h2>
        <p class="error-message">{{ error.message || 'Unknown error occurred' }}</p>
        <button class="swarm-btn swarm-btn-primary" @click="() => refresh()">
          <UIcon name="i-heroicons-arrow-path" class="w-4 h-4" />
          Retry
        </button>
      </div>
    </div>

    <template v-else-if="projectWithActivity">
      <ProjectDetail 
        :project="projectWithActivity"
        :interview-mode="isInterviewPhase"
      >
        <!-- Controls for non-interview phases -->
        <template #controls>
          <ControlBar
            v-if="projectWithActivity.state"
            :project-name="projectWithActivity.name"
            :current-status="projectWithActivity.state.status"
            :current-phase="projectWithActivity.state.phase"
            @action-complete="refresh"
          />
          <button 
            class="swarm-btn swarm-btn-ghost"
            @click="() => { refresh(); refreshActivity() }"
            title="Refresh"
          >
            <UIcon name="i-heroicons-arrow-path" class="w-4 h-4" :class="{ 'animate-spin': pending }" />
            Refresh
          </button>
        </template>

        <!-- Interview chat embedded in the project page -->
        <template #interview>
          <InterviewChat
            :project-name="projectWithActivity.name"
            @complete="handleInterviewComplete"
          />
        </template>
      </ProjectDetail>

      <div v-if="!isInterviewPhase" class="p-4 sm:p-6 max-w-5xl mx-auto">
        <IterationList :logs="projectWithActivity.logs || []" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.error-state {
  display: flex; align-items: center; justify-content: center;
  min-height: 400px;
}
.error-content { text-align: center; }
.error-icon { width: 48px; height: 48px; margin: 0 auto 12px; color: var(--swarm-error); }
.error-title {
  font-size: 20px; font-weight: 600;
  color: var(--swarm-text-primary); margin-bottom: 8px;
}
.error-message {
  font-size: 14px; color: var(--swarm-text-muted); margin-bottom: 16px;
}
</style>
