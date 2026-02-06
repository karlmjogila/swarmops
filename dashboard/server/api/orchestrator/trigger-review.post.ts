/**
 * Trigger Review Endpoint
 * 
 * Manually trigger a review for a completed phase.
 * Use this after a successful phase merge, or to re-trigger review after fixes.
 */

import { triggerPhaseReview } from '../../utils/phase-merger'
import { requireAuth } from '../../utils/security'

interface TriggerReviewPayload {
  runId: string
  phaseNumber: number
  phaseName?: string
  projectContext?: string
}

export default defineEventHandler(async (event) => {
  requireAuth(event)
  const body = await readBody<TriggerReviewPayload>(event)

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

  console.log(`[trigger-review] Triggering review for run ${body.runId}, phase ${body.phaseNumber}`)

  const result = await triggerPhaseReview({
    runId: body.runId,
    phaseNumber: body.phaseNumber,
    phaseName: body.phaseName,
    projectContext: body.projectContext,
  })

  if (!result.ok) {
    console.log(`[trigger-review] Failed to trigger review: ${result.error}`)
    return {
      success: false,
      error: result.error,
    }
  }

  console.log(`[trigger-review] Review spawned: ${result.sessionKey}`)
  
  return {
    success: true,
    sessionKey: result.sessionKey,
    message: `Review triggered for phase ${body.phaseNumber}`,
  }
})
