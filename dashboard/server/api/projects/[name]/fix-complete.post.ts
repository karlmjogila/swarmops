import { join } from 'path'
import { logActivity, triggerPhaseWork } from '../../../utils/auto-advance'
import { handleFixComplete } from '../../../utils/review-handler'
import { triggerPhaseReview } from '../../../utils/phase-merger'
import { requireAuth, validateProjectName } from '../../../utils/security'

interface FixCompleteRequest {
  issuesFixed: number
  message?: string
  runId?: string
  phaseNumber?: number
  status?: 'completed' | 'failed'
}

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const name = validateProjectName(getRouterParam(event, 'name'))
  
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Project name required' })
  }

  const body = await readBody<FixCompleteRequest>(event)
  const projectPath = join(config.projectsDir, name)
  
  // Log fix completion
  await logActivity(projectPath, name, 'complete', 
    `Fixer completed: ${body.issuesFixed} issues addressed`, { 
      issuesFixed: body.issuesFixed,
      message: body.message,
      runId: body.runId,
      phaseNumber: body.phaseNumber,
    })
  
  // If runId and phaseNumber provided, use the new pipeline flow
  if (body.runId && body.phaseNumber !== undefined) {
    console.log(`[fix-complete] Using pipeline flow for run ${body.runId}, phase ${body.phaseNumber}`)
    
    const fixResult = await handleFixComplete({
      runId: body.runId,
      phaseNumber: body.phaseNumber,
      status: body.status || 'completed',
      summary: body.message || `Fixed ${body.issuesFixed} issues`,
      error: body.status === 'failed' ? body.message : undefined,
    })
    
    if (fixResult.escalated) {
      await logActivity(projectPath, name, 'escalated',
        `Phase ${body.phaseNumber} escalated after fix failure`,
        { runId: body.runId, phaseNumber: body.phaseNumber, escalationId: fixResult.escalationId })
      
      return {
        status: 'escalated',
        issuesFixed: body.issuesFixed,
        message: fixResult.message,
        escalationId: fixResult.escalationId,
        runId: body.runId,
        phaseNumber: body.phaseNumber,
      }
    }
    
    if (fixResult.reviewTriggered) {
      await logActivity(projectPath, name, 'progress', 
        `Fixes complete → Re-review triggered (pipeline flow)`,
        { runId: body.runId, phaseNumber: body.phaseNumber, reviewerSession: fixResult.reviewerSession })
      
      return {
        status: 'review-triggered',
        issuesFixed: body.issuesFixed,
        message: fixResult.message,
        reviewerSession: fixResult.reviewerSession,
        runId: body.runId,
        phaseNumber: body.phaseNumber,
      }
    }
    
    // Review not triggered - maybe failed to spawn reviewer
    // Fall back to legacy re-review trigger
    console.warn(`[fix-complete] Pipeline review trigger failed, falling back to legacy`)
    const triggerResult = await triggerPhaseWork(projectPath, name, 'review')
    
    return {
      status: 'review-triggered',
      issuesFixed: body.issuesFixed,
      message: 'Fixes applied, re-review spawned (fallback)',
      triggerResult,
      runId: body.runId,
      phaseNumber: body.phaseNumber,
    }
  }
  
  // Legacy flow (no runId/phaseNumber)
  console.log(`[fix-complete] Using legacy flow (no runId/phaseNumber)`)
  
  const triggerResult = await triggerPhaseWork(projectPath, name, 'review')
  
  await logActivity(projectPath, name, 'progress', 
    `Fixes complete → Re-review triggered. ${triggerResult.message}`)
  
  return {
    status: 'review-triggered',
    issuesFixed: body.issuesFixed,
    message: 'Fixes applied, re-review spawned',
    triggerResult
  }
})
