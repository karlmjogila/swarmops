/**
 * POST /api/projects/:name/spec-complete
 * 
 * Called when spec generation is complete. Triggers automatic advancement to build phase.
 * This provides a reliable handover point instead of relying on agent instructions.
 */

import { join } from 'path'
import { readFile, writeFile } from 'fs/promises'
import { existsSync } from 'fs'
import { 
  updateProjectPhase, 
  triggerPhaseWork, 
  logActivity,
  checkAndAdvancePhase 
} from '../../../utils/auto-advance'
import { broadcastProjectUpdate } from '../../../plugins/websocket'
import { requireAuth, validateProjectName } from '../../../utils/security'

interface SpecCompleteRequest {
  summary?: string  // Optional summary of the spec
  taskCount?: number  // Number of tasks created
}

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const name = validateProjectName(getRouterParam(event, 'name'))
  
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Project name required' })
  }

  const body = await readBody<SpecCompleteRequest>(event) || {}
  const projectPath = join(config.projectsDir, name)
  
  if (!existsSync(projectPath)) {
    throw createError({ statusCode: 404, statusMessage: 'Project not found' })
  }

  // Verify spec file exists
  const specPath = join(projectPath, 'specs', 'IMPLEMENTATION_PLAN.md')
  const progressPath = join(projectPath, 'progress.md')
  
  let hasSpec = false
  let hasProgress = false
  
  try {
    await readFile(specPath, 'utf-8')
    hasSpec = true
  } catch {}
  
  try {
    await readFile(progressPath, 'utf-8')
    hasProgress = true
  } catch {}
  
  if (!hasSpec && !hasProgress) {
    throw createError({ 
      statusCode: 400, 
      statusMessage: 'No spec or progress file found. Generate the plan first.' 
    })
  }

  // Log spec completion
  await logActivity(projectPath, name, 'spec-complete', 
    `Spec generation complete${body.taskCount ? ` (${body.taskCount} tasks)` : ''}. Advancing to build phase.`,
    { summary: body.summary, taskCount: body.taskCount })

  // Update phase to build
  await updateProjectPhase(projectPath, name, 'build', 'ready')
  
  // Trigger build phase (starts the orchestrator)
  const triggerResult = await triggerPhaseWork(projectPath, name, 'build')
  
  // Broadcast update
  broadcastProjectUpdate(name, 'state.json')

  return {
    ok: true,
    message: 'Spec complete, build phase started',
    phase: 'build',
    triggerResult
  }
})
