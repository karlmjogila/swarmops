import { appendFile, mkdir } from 'fs/promises'
import { join, dirname } from 'path'
import { existsSync } from 'fs'
import { randomUUID } from 'crypto'
import type { ActivityEvent } from './activity.get'
import { broadcastProjectUpdate } from '../../../plugins/websocket'
import { validateProjectName } from '../../../utils/security'

export default defineEventHandler(async (event): Promise<{ ok: true, event: ActivityEvent }> => {
  const name = validateProjectName(getRouterParam(event, 'name'))
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Project name required' })
  }

  const body = await readBody(event)
  
  if (!body.type || !body.message) {
    throw createError({ statusCode: 400, statusMessage: 'type and message required' })
  }

  const config = useRuntimeConfig(event)
  const projectDir = join(config.projectsDir, name)
  const activityFile = join(projectDir, 'activity.jsonl')

  // Ensure project directory exists
  if (!existsSync(projectDir)) {
    throw createError({ statusCode: 404, statusMessage: 'Project not found' })
  }

  const activityEvent: ActivityEvent = {
    id: randomUUID(),
    timestamp: new Date().toISOString(),
    type: body.type,
    sessionKey: body.sessionKey,
    agent: body.agent,
    task: body.task,
    message: body.message,
    details: body.details
  }

  try {
    await appendFile(activityFile, JSON.stringify(activityEvent) + '\n')
    
    // Broadcast update via WebSocket
    broadcastProjectUpdate(name, 'activity.jsonl')
    
    return { ok: true, event: activityEvent }
  } catch (err) {
    console.error('Failed to write activity:', err)
    throw createError({ statusCode: 500, statusMessage: 'Failed to write activity' })
  }
})
