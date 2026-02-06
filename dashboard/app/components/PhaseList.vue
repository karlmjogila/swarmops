<script setup lang="ts">
import type { Phase, PhaseTask } from './PhaseCard.vue'

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

const props = defineProps<{
  projectName: string
  progress: string | null
  activity?: ActivityEvent[]
}>()

const emit = defineEmits<{
  'start-phase': [phaseId: string]
}>()

/** Parse phases from progress.md markdown */
const parsedPhases = computed((): Phase[] => {
  if (!props.progress) return []

  const result: Phase[] = []
  const lines = props.progress.split('\n')
  let currentPhase: Phase | null = null

  for (const line of lines) {
    // Match "## Phase 1: Title" or "### Phase 1: Title"
    const phaseMatch = line.match(/^#{2,3}\s*Phase\s*(\d+)[:\s]+(.+)/i)
    if (phaseMatch && phaseMatch[1] && phaseMatch[2]) {
      if (currentPhase) result.push(currentPhase)
      const num = parseInt(phaseMatch[1])
      currentPhase = {
        id: `phase-${num}`, number: num,
        title: phaseMatch[2].trim(), status: 'todo',
        tasks: [], summary: ''
      }
      continue
    }

    // Fallback: "**Phase 1: Title**"
    const altMatch = line.match(/^\*?\*?Phase\s*(\d+)[:\s]+(.+?)\*?\*?$/i)
    if (altMatch && altMatch[1] && altMatch[2] && !currentPhase) {
      const num = parseInt(altMatch[1])
      currentPhase = {
        id: `phase-${num}`, number: num,
        title: altMatch[2].trim().replace(/\*+/g, ''), status: 'todo',
        tasks: [], summary: ''
      }
      continue
    }

    // Match tasks within current phase
    if (currentPhase) {
      const taskMatch = line.match(/^-\s*\[([ xX])\]\s*(.+)/)
      if (taskMatch && taskMatch[1] !== undefined && taskMatch[2]) {
        const rawTitle = taskMatch[2].trim()
        const idAnnotation = rawTitle.match(/@id\(([^)]+)\)/)
        const taskId = idAnnotation && idAnnotation[1] ? idAnnotation[1] : `${currentPhase.id}-task-${currentPhase.tasks.length}`
        const cleanTitle = rawTitle
          .replace(/@id\([^)]+\)/g, '')
          .replace(/@depends\([^)]+\)/g, '')
          .replace(/@role\([^)]+\)/g, '')
          .trim()

        currentPhase.tasks.push({
          id: taskId,
          title: cleanTitle,
          done: taskMatch[1].toLowerCase() === 'x'
        })
      }
    }
  }
  if (currentPhase) result.push(currentPhase)

  // Fallback: "Planned Features" / "Planned Phases"
  if (result.length === 0) {
    let inPlanned = false
    currentPhase = null
    for (const line of lines) {
      if (line.includes('Planned Features') || line.includes('Planned Phases')) {
        inPlanned = true; continue
      }
      if (!inPlanned) continue
      const match = line.match(/(?:###?\s*|\*\*)?\s*Phase\s*(\d+)[:\s]+([^*]+)/i)
      if (match && match[1] && match[2]) {
        if (currentPhase) result.push(currentPhase)
        const num = parseInt(match[1])
        currentPhase = {
          id: `phase-${num}`, number: num,
          title: match[2].trim(), status: 'todo', tasks: [], summary: ''
        }
        continue
      }
      if (currentPhase) {
        const taskMatch = line.match(/^-\s*\[([ xX])\]\s*(.+)/)
        if (taskMatch && taskMatch[1] !== undefined && taskMatch[2]) {
          currentPhase.tasks.push({
            id: `${currentPhase.id}-task-${currentPhase.tasks.length}`,
            title: taskMatch[2].trim(),
            done: taskMatch[1].toLowerCase() === 'x'
          })
        }
      }
      if (line.match(/^##[^#]/) && !line.toLowerCase().includes('phase')) break
    }
    if (currentPhase) result.push(currentPhase)
  }

  // Determine phase status
  let foundActive = false
  for (let i = 0; i < result.length; i++) {
    const phase = result[i]!
    const done = phase.tasks.filter(t => t.done).length
    const total = phase.tasks.length

    if (total > 0 && done === total) {
      phase.status = 'done'
    } else if (done > 0) {
      phase.status = 'active'
      foundActive = true
    } else if (!foundActive && i > 0 && result[i - 1]!.status === 'done') {
      phase.status = 'next'
      foundActive = true
    } else if (!foundActive && i === 0) {
      phase.status = 'next'
      foundActive = true
    }

    if (phase.tasks.length > 0) {
      const titles = phase.tasks.slice(0, 3).map(t => {
        const short = t.title.split(':')[0]!.split('\u2014')[0]!.trim()
        return short.length > 40 ? short.slice(0, 37) + '...' : short
      })
      phase.summary = titles.join(', ') + (phase.tasks.length > 3 ? '...' : '')
    }
  }

  return result
})

/** Enrich parsed phases with live activity data */
const phases = computed((): Phase[] => {
  const base = parsedPhases.value
  if (!props.activity || props.activity.length === 0) return base

  const spawned = new Map<string, { agent: string; timestamp: string }>()
  const completed = new Map<string, { timestamp: string; success: boolean }>()

  for (const ev of props.activity) {
    if (!ev.taskId) continue
    if (ev.type === 'spawn') {
      spawned.set(ev.taskId, { agent: ev.agent || 'agent', timestamp: ev.timestamp })
    }
    if (ev.type === 'complete' || ev.type === 'worker-complete') {
      completed.set(ev.taskId, { timestamp: ev.timestamp, success: ev.success !== false })
    }
  }

  // First pass: enrich tasks with activity data
  const enriched = base.map(phase => ({
    ...phase,
    tasks: phase.tasks.map(task => {
      const sp = spawned.get(task.id)
      const cp = completed.get(task.id)
      return {
        ...task,
        working: !!sp && !cp && !task.done,
        activeAgent: sp && !cp && !task.done ? sp.agent : undefined,
        completedAt: cp ? cp.timestamp : undefined
      }
    })
  }))

  // Second pass: fix status for phases with active workers
  // If any task in a phase is working, it should be 'active' not 'next'
  for (const phase of enriched) {
    const hasActiveWorkers = phase.tasks.some(t => t.working)
    if (hasActiveWorkers && phase.status === 'next') {
      phase.status = 'active'
    }
  }

  return enriched
})

const hasPhases = computed(() => phases.value.length > 0)
</script>

<template>
  <div class="phase-list">
    <div v-if="hasPhases" class="phases">
      <PhaseCard
        v-for="phase in phases"
        :key="phase.id"
        :phase="phase"
      />
    </div>

    <div v-else class="no-phases">
      <UIcon name="i-heroicons-clipboard-document-list" class="w-8 h-8" />
      <p>No phases defined yet</p>
    </div>
  </div>
</template>

<style scoped>
.phase-list { margin-bottom: 0; }
.phases { display: flex; flex-direction: column; gap: 12px; }
.no-phases {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 40px; color: var(--swarm-text-muted);
  text-align: center; gap: 12px;
}
.no-phases p { margin: 0; font-size: 14px; }
</style>
