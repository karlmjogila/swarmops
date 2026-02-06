import { readFile, writeFile, appendFile } from 'fs/promises'
import { join } from 'path'
import { randomUUID } from 'crypto'
import { readdir } from 'fs/promises'
import type { ProjectState, ControlActionType, ProjectPhase } from '../../../types/project'
import { broadcastProjectUpdate } from '../../../plugins/websocket'
import { getGatewayUrl } from '../../../utils/agent'
import { triggerPhaseWork, triggerOrchestrator, checkAndAdvancePhase } from '../../../utils/auto-advance'
import { requireAuth, validateProjectName } from '../../../utils/security'

const VALID_ACTIONS: (ControlActionType | 'auto-start' | 'auto-continue')[] = ['kill', 'pause', 'resume', 'trigger', 'phase-change', 'auto-start', 'auto-continue']
const VALID_PHASES: ProjectPhase[] = ['interview', 'spec', 'build', 'review']

interface ControlRequest {
  action: ControlActionType | 'auto-start' | 'auto-continue'
  phase?: ProjectPhase
}

async function postActivity(projectPath: string, projectName: string, type: string, message: string, extra: Record<string, any> = {}) {
  const activityFile = join(projectPath, 'activity.jsonl')
  const event = {
    id: randomUUID(),
    timestamp: new Date().toISOString(),
    type,
    message,
    ...extra
  }
  await appendFile(activityFile, JSON.stringify(event) + '\n')
  broadcastProjectUpdate(projectName, 'activity.jsonl')
}

async function buildTaskPrompt(projectPath: string, projectName: string): Promise<string> {
  let progressContent = ''
  let specsContent = ''
  
  try {
    progressContent = await readFile(join(projectPath, 'progress.md'), 'utf-8')
  } catch {
    progressContent = 'No progress.md found'
  }
  
  try {
    const specsDir = join(projectPath, 'specs')
    const specFiles = await readdir(specsDir)
    const specContents = await Promise.all(
      specFiles
        .filter(f => f.endsWith('.md'))
        .map(async f => {
          const content = await readFile(join(specsDir, f), 'utf-8')
          return `### ${f}\n\n${content}`
        })
    )
    specsContent = specContents.join('\n\n')
  } catch {
    specsContent = 'No specs/ directory or files found'
  }
  
  return `You are a builder working on project "${projectName}".

## Current Progress
${progressContent}

## Specs
${specsContent}

## Task
Continue working on this project. Read progress.md, identify the next incomplete task, implement it, then update progress.md with what you completed.

When done, report your changes.`
}

async function spawnSubAgent(task: string, label: string): Promise<any> {
  // Use the proper gateway-client spawnSession function
  const { spawnSession } = await import('../../../utils/gateway-client')
  const sessionLabel = `swarm:${label}`
  
  const result = await spawnSession({
    task: `[SWARM TASK] ${sessionLabel}\n\n${task}`,
    label: sessionLabel,
    runTimeoutSeconds: 600,
    cleanup: 'keep'
  })
  
  if (!result.ok) {
    throw new Error(`Gateway spawn failed: ${result.error?.message || 'Unknown error'}`)
  }
  
  return {
    success: true,
    method: 'sessions_spawn',
    label: sessionLabel,
    sessionKey: result.result?.childSessionKey,
    message: 'Session spawned',
    result: result.result
  }
}

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const name = validateProjectName(getRouterParam(event, 'name'))
  
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Project name required' })
  }

  const body = await readBody<ControlRequest>(event)
  
  if (!body?.action || !VALID_ACTIONS.includes(body.action)) {
    throw createError({ 
      statusCode: 400, 
      statusMessage: `Invalid action. Must be one of: ${VALID_ACTIONS.join(', ')}` 
    })
  }

  if (body.action === 'phase-change' && (!body.phase || !VALID_PHASES.includes(body.phase))) {
    throw createError({ 
      statusCode: 400, 
      statusMessage: `phase-change requires valid phase. Must be one of: ${VALID_PHASES.join(', ')}` 
    })
  }

  const projectPath = join(config.projectsDir, name)
  const statePath = join(projectPath, 'state.json')
  
  let state: ProjectState
  try {
    const stateRaw = await readFile(statePath, 'utf-8')
    state = JSON.parse(stateRaw)
  } catch {
    throw createError({ statusCode: 404, statusMessage: 'Project not found' })
  }

  switch (body.action) {
    case 'kill':
      state.status = 'error'
      state.completedAt = new Date().toISOString()
      await postActivity(projectPath, name, 'error', 'Project killed by user', { agent: 'dashboard' })
      break
    
    case 'pause':
      state.status = 'paused'
      await postActivity(projectPath, name, 'progress', 'Project paused', { agent: 'dashboard' })
      break
    
    case 'resume':
      state.status = 'running'
      try {
        const taskPrompt = await buildTaskPrompt(projectPath, name)
        const spawnResult = await spawnSubAgent(taskPrompt, `builder:${name}:resume`)
        
        await postActivity(projectPath, name, 'spawn', 'Resume - sub-agent spawned', {
          agent: 'dashboard',
          requestType: 'resume',
          requestId: randomUUID(),
          sessionId: spawnResult.sessionId,
          spawnResult
        })
      } catch (error) {
        await postActivity(projectPath, name, 'error', `Resume spawn failed: ${error.message}`, {
          agent: 'dashboard',
          requestType: 'resume',
          error: error.message
        })
      }
      break
    
    case 'trigger':
      state.status = 'running'
      try {
        const taskPrompt = await buildTaskPrompt(projectPath, name)
        const spawnResult = await spawnSubAgent(taskPrompt, `builder:${name}:trigger`)
        
        await postActivity(projectPath, name, 'spawn', 'Trigger - sub-agent spawned', {
          agent: 'dashboard',
          requestType: 'trigger',
          requestId: randomUUID(),
          sessionId: spawnResult.sessionId,
          spawnResult
        })
      } catch (error) {
        await postActivity(projectPath, name, 'error', `Trigger spawn failed: ${error.message}`, {
          agent: 'dashboard',
          requestType: 'trigger',
          error: error.message
        })
      }
      break
    
    case 'phase-change':
      state.phase = body.phase!
      state.iteration = 0
      state.history = state.history || []
      state.history.push({
        iteration: 0,
        timestamp: new Date().toISOString()
      })
      await postActivity(projectPath, name, 'progress', `Phase changed to: ${body.phase}`, { agent: 'dashboard' })
      break
    
    case 'auto-start': {
      // Start the auto-continue pipeline from current phase
      state.status = 'running'
      const triggerResult = await triggerPhaseWork(projectPath, name, state.phase)
      await postActivity(projectPath, name, 'spawn', 
        `Auto-start: triggered ${state.phase} phase. ${triggerResult.message}`, { 
          agent: 'dashboard',
          triggerResult 
        })
      break
    }
    
    case 'auto-continue': {
      // Check if phase should advance, then trigger work for current/new phase
      state.status = 'running'
      const advanceResult = await checkAndAdvancePhase(projectPath, name, config)
      
      if (advanceResult.advanced && advanceResult.newPhase) {
        state.phase = advanceResult.newPhase
        const triggerResult = await triggerPhaseWork(projectPath, name, advanceResult.newPhase)
        await postActivity(projectPath, name, 'progress', 
          `Auto-continue: ${advanceResult.message}. ${triggerResult.message}`, { 
            agent: 'dashboard',
            advanceResult,
            triggerResult 
          })
      } else if (state.phase === 'build') {
        // In build phase, trigger orchestrator for ready tasks
        const orchestratorResult = await triggerOrchestrator(projectPath, name)
        await postActivity(projectPath, name, 'spawn', 
          `Auto-continue (build): ${orchestratorResult.message}`, { 
            agent: 'dashboard',
            orchestratorResult 
          })
      } else {
        await postActivity(projectPath, name, 'progress', 
          `Auto-continue: ${advanceResult.message}`, { agent: 'dashboard' })
      }
      break
    }
  }

  await writeFile(statePath, JSON.stringify(state, null, 2))
  
  // Broadcast state update
  broadcastProjectUpdate(name, 'state.json')
  
  return { success: true, state }
})
