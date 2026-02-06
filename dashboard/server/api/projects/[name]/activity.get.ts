import { readFile, stat } from 'fs/promises'
import { join } from 'path'
import { existsSync } from 'fs'
import { validateProjectName } from '../../../utils/security'

export interface ActivityEvent {
  id: string
  timestamp: string
  type: 'spawn' | 'progress' | 'output' | 'complete' | 'error'
  sessionKey?: string
  agent?: string
  task?: string
  message: string
  details?: string
}

export default defineEventHandler(async (event): Promise<{ events: ActivityEvent[], lastModified: string | null }> => {
  const name = validateProjectName(getRouterParam(event, 'name'))
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Project name required' })
  }

  const config = useRuntimeConfig(event)
  const projectDir = join(config.projectsDir, name)
  const activityFile = join(projectDir, 'activity.jsonl')

  if (!existsSync(activityFile)) {
    return { events: [], lastModified: null }
  }

  try {
    const [content, fileStat] = await Promise.all([
      readFile(activityFile, 'utf-8'),
      stat(activityFile)
    ])

    const events: ActivityEvent[] = content
      .split('\n')
      .filter(line => line.trim())
      .map(line => {
        try {
          return JSON.parse(line)
        } catch {
          return null
        }
      })
      .filter((e): e is ActivityEvent => e !== null)
      .slice(-50) // Last 50 events

    return {
      events,
      lastModified: fileStat.mtime.toISOString()
    }
  } catch (err) {
    console.error('Failed to read activity file:', err)
    return { events: [], lastModified: null }
  }
})
