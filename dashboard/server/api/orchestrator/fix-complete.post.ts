/**
 * Fix Complete Endpoint
 * 
 * Called by fixer agents when they complete their work.
 * Triggers re-review of the phase to verify fixes.
 * 
 * Flow:
 * 1. Fixer completes and calls this endpoint
 * 2. Update review state
 * 3. Spawn a new reviewer to verify the fixes
 */

import { spawnPhaseReviewer } from '../../utils/phase-reviewer'
import { getPhaseState } from '../../utils/phase-collector'
import {
  onFixerComplete,
  getReviewState,
  startReview,
} from '../../utils/review-state'
import { createEscalation } from '../../utils/escalation-store'
import { requireAuth } from '../../utils/security'

interface FixCompletePayload {
  runId: string
  phaseNumber: number
  status: 'completed' | 'failed'
  summary?: string
  error?: string
}

export default defineEventHandler(async (event) => {
  requireAuth(event)
  const body = await readBody<FixCompletePayload>(event)

  if (!body.runId) {
    throw createError({
      statusCode: 400,
      statusMessage: 'runId is required',
    })
  }

  if (body.phaseNumber === undefined) {
    throw createError({
      statusCode: 400,
      statusMessage: 'phaseNumber is required',
    })
  }

  if (!body.status || !['completed', 'failed'].includes(body.status)) {
    throw createError({
      statusCode: 400,
      statusMessage: 'status must be "completed" or "failed"',
    })
  }

  console.log(`[fix-complete] Run ${body.runId}, Phase ${body.phaseNumber}: ${body.status}`)

  // Get phase state
  const phaseState = await getPhaseState(body.runId, body.phaseNumber)
  if (!phaseState) {
    return {
      success: false,
      error: `Phase ${body.phaseNumber} not found for run ${body.runId}`,
    }
  }

  // Update review state
  const reviewState = await onFixerComplete({
    runId: body.runId,
    phaseNumber: body.phaseNumber,
    success: body.status === 'completed',
    summary: body.summary,
    error: body.error,
  })

  if (body.status === 'failed') {
    console.log(`[fix-complete] Fixer failed for phase ${body.phaseNumber}, escalating`)

    // Create escalation for failed fix
    const escalation = await createEscalation({
      runId: body.runId,
      pipelineId: body.runId,
      pipelineName: `phase-${body.phaseNumber}`,
      stepOrder: body.phaseNumber,
      roleId: 'fixer',
      roleName: 'AI Fixer',
      error: body.error || 'Fixer agent failed',
      attemptCount: reviewState.attempts.length,
      maxAttempts: 3,
      projectDir: phaseState.repoDir,
      severity: 'medium',
    })

    return {
      success: false,
      status: 'escalated',
      escalationId: escalation.id,
      message: 'Fixer failed, escalated for human review',
    }
  }

  // Success - trigger re-review
  console.log(`[fix-complete] Fixer completed, triggering re-review for phase ${body.phaseNumber}`)

  const phaseBranch = phaseState.phaseBranch || `swarmops/${body.runId}/phase-${body.phaseNumber}`
  const phaseName = `Phase ${body.phaseNumber}`

  // Get previous review context for the re-review prompt
  const previousAttempts = reviewState.attempts
    .filter(a => a.decision === 'fix')
    .map((a, i) => `Fix attempt ${i + 1}: ${a.fixInstructions || 'Unknown issues'}`)
    .join('\n')

  const projectContext = previousAttempts
    ? `## Previous Fix Attempts\n${previousAttempts}\n\n## Fixer Summary\n${body.summary || 'No summary provided'}`
    : undefined

  // Spawn a new reviewer
  const reviewResult = await spawnPhaseReviewer({
    runId: body.runId,
    phaseName,
    phaseNumber: body.phaseNumber,
    projectDir: phaseState.repoDir,
    phaseBranch,
    targetBranch: phaseState.baseBranch || 'main',
    projectContext,
  })

  if (!reviewResult.ok) {
    console.error(`[fix-complete] Failed to spawn reviewer: ${reviewResult.error}`)

    // If we can't spawn a reviewer, escalate
    const escalation = await createEscalation({
      runId: body.runId,
      pipelineId: body.runId,
      pipelineName: `phase-${body.phaseNumber}`,
      stepOrder: body.phaseNumber,
      roleId: 'reviewer',
      roleName: 'AI Reviewer',
      error: `Failed to spawn re-reviewer after fix: ${reviewResult.error}`,
      attemptCount: reviewState.attempts.length,
      maxAttempts: 3,
      projectDir: phaseState.repoDir,
      severity: 'medium',
    })

    return {
      success: false,
      status: 'escalated',
      error: reviewResult.error,
      escalationId: escalation.id,
      message: 'Failed to spawn re-reviewer, escalated',
    }
  }

  // Update review state with new reviewer
  await startReview({
    runId: body.runId,
    phaseNumber: body.phaseNumber,
    phaseName,
    phaseBranch,
    targetBranch: phaseState.baseBranch || 'main',
    projectDir: phaseState.repoDir,
    reviewerSession: reviewResult.sessionKey,
  })

  console.log(`[fix-complete] Re-reviewer spawned: ${reviewResult.sessionKey}`)

  return {
    success: true,
    status: 're-review-triggered',
    reviewerSession: reviewResult.sessionKey,
    attemptNumber: reviewState.attempts.length + 1,
    message: 'Fixes applied, re-review triggered',
    nextStep: 'await-review-decision',
  }
})
