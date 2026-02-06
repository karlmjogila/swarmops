import { readFile } from 'fs/promises'
import { join } from 'path'
import { validateProjectName } from '../../../utils/security'

interface ActivityEvent {
  id: string
  timestamp: string
  type: string
  message: string
  agent?: string
  taskId?: string
  workerId?: string
  phaseNumber?: number
  runId?: string
  workerBranch?: string
  worktreePath?: string
  success?: boolean
  mergeStatus?: string
  mergedBranches?: string[]
  phaseBranch?: string
  error?: string
  phaseComplete?: boolean
  allSucceeded?: boolean
  attemptNumber?: number
  maxAttempts?: number
  delayMs?: number
  escalationId?: string
  findings?: any
  [key: string]: any
}

export default defineEventHandler(async (event): Promise<ActivityEvent[]> => {
  const name = validateProjectName(getRouterParam(event, 'name'))
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Project name required' })
  }

  const config = useRuntimeConfig(event)
  const activityPath = join(config.projectsDir, name, 'activity.jsonl')

  try {
    const content = await readFile(activityPath, 'utf-8')
    const lines = content.trim().split('\n').filter(l => l.trim())
    const events: ActivityEvent[] = []

    for (const line of lines) {
      try {
        events.push(JSON.parse(line))
      } catch {
        // skip invalid lines
      }
    }

    // Return ALL events (not sliced) - the modal needs the full history
    return events
  } catch {
    return []
  }
})
