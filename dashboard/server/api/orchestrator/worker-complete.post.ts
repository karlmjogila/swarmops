/**
 * Worker Completion Webhook
 * 
 * Receives completion events from sub-agents and advances the pipeline.
 * Called when a step finishes (success or failure).
 * 
 * Also handles conflict resolver completion (stepOrder === -1):
 * When a conflict resolver completes, it resumes the merge process.
 */

import { PipelineRunner } from '../../utils/pipeline-runner'
import { 
  getResolverByRun, 
  completeResolver, 
  failResolver 
} from '../../utils/conflict-resolver-store'
import { resumeMergeWithReview } from '../../utils/phase-merger'
import { requireAuth } from '../../utils/security'

interface CompletionPayload {
  sessionKey?: string
  runId?: string
  stepOrder?: number
  status: 'completed' | 'failed'
  output?: string
  error?: string
}

export default defineEventHandler(async (event) => {
  const body = await readBody<CompletionPayload>(event)

  // Need either sessionKey or runId+stepOrder
  if (!body.sessionKey && !body.runId) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Missing sessionKey or runId',
    })
  }

  console.log(`[worker-complete] Received: runId=${body.runId}, stepOrder=${body.stepOrder}, status=${body.status}`)

  // Handle conflict resolver completion (stepOrder === -1)
  if (body.runId && body.stepOrder === -1) {
    console.log(`[worker-complete] Conflict resolver completed for run ${body.runId}`)
    
    // Find the active resolver for this run
    const resolver = await getResolverByRun(body.runId)
    
    if (!resolver) {
      console.log(`[worker-complete] No active conflict resolver found for run ${body.runId}`)
      return {
        success: false,
        error: `No active conflict resolver found for run ${body.runId}`,
      }
    }
    
    if (body.status === 'failed') {
      await failResolver(resolver.sessionKey, body.error || 'Conflict resolution failed')
      console.log(`[worker-complete] Conflict resolver failed: ${body.error}`)
      return {
        success: false,
        error: `Conflict resolver failed: ${body.error}`,
        phase: resolver.phaseNumber,
      }
    }
    
    // Mark resolver as completed
    await completeResolver(resolver.sessionKey, body.output)
    
    console.log(`[worker-complete] Conflict resolved, resuming merge for phase ${resolver.phaseNumber}`)
    console.log(`[worker-complete] Remaining branches to merge: ${resolver.remainingBranches.length}`)
    
    // Resume the merge process with remaining branches and trigger review on success
    const mergeResult = await resumeMergeWithReview({
      runId: body.runId,
      phaseNumber: resolver.phaseNumber,
      remainingBranches: resolver.remainingBranches,
      phaseName: `phase-${resolver.phaseNumber}`,
    })
    
    if (mergeResult.success) {
      console.log(`[worker-complete] Phase ${resolver.phaseNumber} merge completed after conflict resolution`)
      
      // Review was automatically triggered if merge succeeded
      if (mergeResult.reviewerSession) {
        console.log(`[worker-complete] Review triggered for phase ${resolver.phaseNumber}: ${mergeResult.reviewerSession}`)
      }
      
      return {
        success: true,
        conflictResolved: true,
        phaseCompleted: true,
        phaseBranch: mergeResult.phaseBranch,
        mergedBranches: mergeResult.mergedBranches,
        reviewTriggered: !!mergeResult.reviewerSession,
        reviewerSession: mergeResult.reviewerSession,
      }
    }
    
    if (mergeResult.status === 'conflict') {
      // Another conflict encountered - a new resolver was spawned
      console.log(`[worker-complete] Another conflict detected, new resolver spawned: ${mergeResult.resolverSession}`)
      return {
        success: true,
        conflictResolved: true,
        newConflict: true,
        resolverSession: mergeResult.resolverSession,
        conflictInfo: mergeResult.conflictInfo,
      }
    }
    
    // Merge failed for other reasons
    console.log(`[worker-complete] Merge failed after conflict resolution: ${mergeResult.error}`)
    return {
      success: false,
      conflictResolved: true,
      error: mergeResult.error,
    }
  }

  let result

  if (body.runId && body.stepOrder !== undefined) {
    // Lookup by runId and advance
    result = await PipelineRunner.onStepCompleteByRun(body.runId, body.stepOrder, {
      status: body.status || 'completed',
      output: body.output,
      error: body.error,
    })
  } else if (body.sessionKey) {
    // Lookup by session key (legacy/fallback)
    result = await PipelineRunner.onStepComplete(body.sessionKey, {
      status: body.status || 'completed',
      output: body.output,
      error: body.error,
    })
  } else {
    throw createError({
      statusCode: 400,
      statusMessage: 'Invalid payload',
    })
  }

  if (result.error) {
    // Check if this is a retry message (not a final failure)
    const isRetryScheduled = result.error.includes('retry') && result.error.includes('scheduled')
    
    if (isRetryScheduled) {
      console.log(`[worker-complete] ${result.error}`)
      return {
        success: true,
        retryScheduled: true,
        message: result.error,
      }
    }
    
    // Check if step was skipped with escalation
    if (result.skippedStep && result.escalationId) {
      console.log(`[worker-complete] Step ${result.skippedStep} skipped, escalation created: ${result.escalationId}`)
      return {
        success: true,
        skipped: true,
        skippedStep: result.skippedStep,
        escalationId: result.escalationId,
        nextStep: result.nextStep,
        pipelineCompleted: result.pipelineCompleted,
        message: `Step ${result.skippedStep} skipped after max retries, escalation created`,
      }
    }
    
    console.log(`[worker-complete] Error: ${result.error}`)
    return {
      success: false,
      error: result.error,
      retriesExhausted: result.retriesExhausted,
    }
  }

  // Check for skipped step even without error (can happen when skipping and continuing)
  if (result.skippedStep && result.escalationId) {
    console.log(`[worker-complete] Step ${result.skippedStep} skipped, continuing to step ${result.nextStep}`)
    return {
      success: true,
      skipped: true,
      skippedStep: result.skippedStep,
      escalationId: result.escalationId,
      nextStep: result.nextStep,
      pipelineCompleted: result.pipelineCompleted,
    }
  }

  if (result.pipelineCompleted) {
    console.log(`[worker-complete] Pipeline completed`)
    return {
      success: true,
      pipelineCompleted: true,
      retriesExhausted: result.retriesExhausted,
    }
  }

  if (result.nextStep) {
    console.log(`[worker-complete] Advanced to step ${result.nextStep}`)
    return {
      success: true,
      nextStep: result.nextStep,
    }
  }

  return { success: true }
})
