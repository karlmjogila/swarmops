/**
 * Merge Phase Endpoint
 * 
 * Triggers a phase merge after all workers in a phase have completed.
 * Automatically triggers a review after successful merge.
 * 
 * Call this when all workers in a phase have finished their work.
 */

import { mergePhaseWithReview } from '../../utils/phase-merger'
import { requireAuth } from '../../utils/security'

interface MergePhasePayload {
  runId: string
  phaseNumber: number
  phaseName?: string
  projectContext?: string
}

export default defineEventHandler(async (event) => {
  const body = await readBody<MergePhasePayload>(event)

  if (!body.runId) {
    throw createError({
      statusCode: 400,
      statusMessage: 'runId is required',
    })
  }

  if (body.phaseNumber === undefined || body.phaseNumber === null) {
    throw createError({
      statusCode: 400,
      statusMessage: 'phaseNumber is required',
    })
  }

  console.log(`[merge-phase] Starting merge for run ${body.runId}, phase ${body.phaseNumber}`)

  const result = await mergePhaseWithReview({
    runId: body.runId,
    phaseNumber: body.phaseNumber,
    phaseName: body.phaseName,
    projectContext: body.projectContext,
  })

  if (result.success) {
    console.log(`[merge-phase] Phase ${body.phaseNumber} merged successfully`)
    
    if (result.reviewerSession) {
      console.log(`[merge-phase] Review triggered: ${result.reviewerSession}`)
    }

    return {
      success: true,
      status: result.status,
      phaseBranch: result.phaseBranch,
      mergedBranches: result.mergedBranches,
      reviewTriggered: !!result.reviewerSession,
      reviewerSession: result.reviewerSession,
      message: result.status === 'no-changes' 
        ? 'No changes to merge in this phase'
        : `Merged ${result.mergedBranches.length} branches`,
    }
  }

  // Handle conflict case
  if (result.status === 'conflict') {
    console.log(`[merge-phase] Conflict detected in phase ${body.phaseNumber}`)
    return {
      success: false,
      status: 'conflict',
      phaseBranch: result.phaseBranch,
      mergedBranches: result.mergedBranches,
      conflictInfo: result.conflictInfo,
      resolverSpawned: !!result.resolverSession,
      resolverSession: result.resolverSession,
      message: `Conflict detected merging ${result.conflictInfo?.failedBranch}`,
    }
  }

  // Other failures
  console.log(`[merge-phase] Merge failed: ${result.error}`)
  return {
    success: false,
    status: result.status,
    error: result.error,
    mergedBranches: result.mergedBranches,
    message: `Merge failed: ${result.error}`,
  }
})
