import { readFile, writeFile, appendFile } from 'fs/promises'
import { join } from 'path'
import { existsSync } from 'fs'
import { randomUUID } from 'crypto'
import { broadcastProjectUpdate } from '../../../plugins/websocket'
import { wakeAgent, buildPlannerPrompt } from '../../../utils/agent'
import { updateProjectPhase, triggerPhaseWork, logActivity } from '../../../utils/auto-advance'
import type { InterviewMessage, InterviewState } from './interview.get'
import { validateProjectName } from '../../../utils/security'

interface PostBody {
  role: 'user' | 'agent'
  content: string
  complete?: boolean
}

export default defineEventHandler(async (event): Promise<{ ok: true, message: InterviewMessage }> => {
  const name = validateProjectName(getRouterParam(event, 'name'))
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Project name required' })
  }

  const body = await readBody<PostBody>(event)
  
  if (!body.role || !body.content) {
    throw createError({ statusCode: 400, statusMessage: 'role and content required' })
  }

  if (body.role !== 'user' && body.role !== 'agent') {
    throw createError({ statusCode: 400, statusMessage: 'role must be "user" or "agent"' })
  }

  const config = useRuntimeConfig(event)
  const projectDir = join(config.projectsDir, name)
  const interviewFile = join(projectDir, 'interview.json')

  if (!existsSync(projectDir)) {
    throw createError({ statusCode: 404, statusMessage: 'Project not found' })
  }

  // Load existing state
  let state: InterviewState = { messages: [], complete: false }
  
  if (existsSync(interviewFile)) {
    try {
      const content = await readFile(interviewFile, 'utf-8')
      state = JSON.parse(content)
    } catch {
      // Use default state
    }
  }

  // Create new message
  const message: InterviewMessage = {
    id: randomUUID(),
    timestamp: new Date().toISOString(),
    role: body.role,
    content: body.content
  }

  // Append message
  state.messages.push(message)
  
  // Update complete status if provided
  if (typeof body.complete === 'boolean') {
    state.complete = body.complete
  }

  try {
    await writeFile(interviewFile, JSON.stringify(state, null, 2))
    
    // Broadcast update via WebSocket
    broadcastProjectUpdate(name, 'interview.json')
    
    // Log agent response as complete (not spawn waiting)
    if (body.role === 'agent') {
      await logActivity(projectDir, name, 'complete', 'Agent responded in interview')
    }
    
    // Auto-advance when interview completes
    if (body.complete && state.complete) {
      try {
        // Update phase to spec
        await updateProjectPhase(projectDir, name, 'spec')
        
        // Trigger spec generation work
        const triggerResult = await triggerPhaseWork(projectDir, name, 'spec')
        
        await logActivity(projectDir, name, 'progress', 
          `Interview complete → Auto-advanced to spec phase. ${triggerResult.message}`)
      } catch (err) {
        console.error('Failed to auto-advance from interview:', err)
        // Fallback: spawn planner directly
        try {
          const plannerPrompt = buildPlannerPrompt(name, state.messages)
          await wakeAgent(plannerPrompt)
          await logActivity(projectDir, name, 'spawn', 'Fallback: Planner agent spawned')
        } catch (fallbackErr) {
          console.error('Fallback planner spawn also failed:', fallbackErr)
        }
      }
    }
    
    return { ok: true, message }
  } catch (err) {
    console.error('Failed to write interview:', err)
    throw createError({ statusCode: 500, statusMessage: 'Failed to write interview' })
  }
})
