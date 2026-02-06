<script setup lang="ts">
import type { ProjectState } from '~/types/project'

interface SpecFile {
  name: string
  content: string
}

interface ActivityEvent {
  id?: string
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

interface ProjectDetailData {
  name: string
  state: ProjectState | null
  progress: string | null
  plan: string | null
  specs: SpecFile[]
  activity?: ActivityEvent[]
}

const props = defineProps<{
  project: ProjectDetailData
  iterationCount?: number
  interviewMode?: boolean
}>()

const router = useRouter()

const confettiRef = ref<InstanceType<typeof import('./ConfettiCelebration.vue').default> | null>(null)
const showSuccessModal = ref(false)
const previousStatus = ref<string | undefined>(undefined)

watch(
  () => props.project.state?.status,
  (newStatus, oldStatus) => {
    if (newStatus === 'completed' && oldStatus !== 'completed' && oldStatus !== undefined) {
      confettiRef.value?.start()
      showSuccessModal.value = true
    }
    previousStatus.value = newStatus
  },
  { immediate: true }
)

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return 'N/A'
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

function getBadgeClass(status: string | undefined): string {
  switch (status) {
    case 'running': return 'ralph-badge ralph-badge-running'
    case 'completed': return 'ralph-badge ralph-badge-completed'
    case 'paused': return 'ralph-badge ralph-badge-paused'
    case 'error': return 'ralph-badge ralph-badge-error'
    default: return 'ralph-badge ralph-badge-pending'
  }
}

function statusIcon(status: string | undefined): string {
  switch (status) {
    case 'pending': return 'i-heroicons-clock'
    case 'running': return 'i-heroicons-play-circle'
    case 'paused': return 'i-heroicons-pause-circle'
    case 'completed': return 'i-heroicons-check-circle'
    case 'error': return 'i-heroicons-exclamation-circle'
    default: return 'i-heroicons-question-mark-circle'
  }
}
</script>

<template>
  <div class="project-page">
    <!-- Back nav -->
    <NuxtLink to="/" class="back-link">
      <UIcon name="i-heroicons-arrow-left" class="w-4 h-4" />
      Dashboard
    </NuxtLink>

    <!-- Header Card -->
    <div class="ralph-header-card header-card">
      <div class="header-inner">
        <!-- Top row: icon, name, status badge -->
        <div class="header-top">
          <div class="header-left">
            <div class="project-icon">
              <UIcon name="i-heroicons-rectangle-stack" class="w-6 h-6" />
            </div>
            <div>
              <h1 class="project-name">{{ project.name }}</h1>
              <div v-if="project.state?.startedAt" class="project-meta">
                <UIcon name="i-heroicons-clock" class="w-3.5 h-3.5" />
                <span>Started {{ formatDate(project.state.startedAt) }}</span>
              </div>
            </div>
          </div>
          <span
            v-if="project.state?.status"
            :class="getBadgeClass(project.state.status)"
            class="status-badge"
          >
            <UIcon :name="statusIcon(project.state.status)" class="w-4 h-4" />
            {{ project.state.status }}
          </span>
        </div>

        <!-- Phase stepper -->
        <PhaseStepper 
          v-if="project.state?.phase"
          :current-phase="project.state.phase"
          :status="project.state.status"
        />

        <!-- Controls (only for active/paused projects, not during interview) -->
        <div 
          v-if="project.state?.status && project.state.status !== 'completed' && !interviewMode"
          class="controls-row"
        >
          <slot name="controls" />
        </div>
      </div>
    </div>

    <!-- Interview slot - replaces main content during interview -->
    <template v-if="interviewMode">
      <slot name="interview" />
    </template>

    <!-- Normal project content -->
    <template v-else>
      <!-- Phase Cards -->
      <div class="ralph-section">
        <div class="ralph-section-header">
          <div class="ralph-section-icon" style="background: rgba(34, 197, 94, 0.15); color: var(--swarm-success);">
            <UIcon name="i-heroicons-queue-list" class="w-4 h-4" />
          </div>
          <h2 class="ralph-section-title">Phases</h2>
        </div>
        <PhaseList
          :project-name="project.name"
          :progress="project.progress"
          :activity="project.activity"
        />
      </div>

      <!-- Activity Timeline -->
      <div class="ralph-section">
        <div class="ralph-section-header">
          <div class="ralph-section-icon" style="background: var(--swarm-info-bg); color: var(--swarm-info);">
            <UIcon name="i-heroicons-bell-alert" class="w-4 h-4" />
          </div>
          <h2 class="ralph-section-title">Activity</h2>
          <span
            v-if="project.activity?.length"
            class="count-pill"
          >{{ project.activity.length }}</span>
        </div>
        <ActivityTimeline :events="project.activity || []" />
      </div>

      <!-- Implementation Plan -->
      <div v-if="project.plan" class="ralph-section">
        <div class="ralph-section-header">
          <div class="ralph-section-icon">
            <UIcon name="i-heroicons-clipboard-document-list" class="w-4 h-4" />
          </div>
          <h2 class="ralph-section-title">Implementation Plan</h2>
        </div>
        <pre class="ralph-pre">{{ project.plan }}</pre>
      </div>

      <!-- Specs -->
      <div v-if="project.specs?.length" class="ralph-section">
        <div class="ralph-section-header">
          <div class="ralph-section-icon" style="background: var(--swarm-warning-bg); color: var(--swarm-warning);">
            <UIcon name="i-heroicons-document-magnifying-glass" class="w-4 h-4" />
          </div>
          <h2 class="ralph-section-title">Specifications</h2>
          <span class="count-pill">{{ project.specs.length }}</span>
        </div>
        <div class="specs-list">
          <details v-for="spec in project.specs" :key="spec.name" class="spec-details">
            <summary class="spec-summary">
              <UIcon name="i-heroicons-document-text" class="w-4 h-4" style="color: var(--swarm-text-muted);" />
              <span>{{ spec.name }}</span>
            </summary>
            <pre class="ralph-pre spec-pre">{{ spec.content }}</pre>
          </details>
        </div>
      </div>
    </template>

    <!-- Confetti & Success Modal -->
    <ConfettiCelebration ref="confettiRef" />
    <ProjectSuccessModal
      v-model="showSuccessModal"
      :project="project.state"
      :iteration-count="iterationCount ?? 0"
    />
  </div>
</template>

<style scoped>
.project-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 20px 24px 32px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--swarm-text-muted);
  text-decoration: none;
  margin-bottom: 16px;
  padding: 4px 0;
  transition: color 0.15s;
}
.back-link:hover {
  color: var(--swarm-accent);
}

.header-card {
  margin-bottom: 24px;
}

.header-inner {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  z-index: 1;
}

.header-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.project-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--swarm-accent-bg);
  color: var(--swarm-accent);
  border: 1px solid rgba(16, 185, 129, 0.15);
}

.project-name {
  font-size: 22px;
  font-weight: 700;
  color: var(--swarm-text-primary);
  letter-spacing: -0.02em;
  line-height: 1.2;
  word-break: break-all;
  margin: 0;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--swarm-text-muted);
  margin-top: 4px;
}

.status-badge {
  font-size: 13px;
  padding: 5px 12px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.controls-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 12px;
  border-top: 1px solid var(--swarm-border);
}

.count-pill {
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 10px;
  background: var(--swarm-bg-tertiary);
  color: var(--swarm-text-muted);
}

.specs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.spec-details {
  border: 1px solid var(--swarm-border);
  border-radius: 8px;
  overflow: hidden;
}

.spec-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--swarm-text-primary);
}
.spec-summary:hover {
  background: var(--swarm-bg-hover);
}

.spec-pre {
  margin: 0;
  border-radius: 0;
  border-top: 1px solid var(--swarm-border);
  border-left: none;
  border-right: none;
  border-bottom: none;
}

@media (max-width: 640px) {
  .project-page {
    padding: 16px;
  }
}
</style>
