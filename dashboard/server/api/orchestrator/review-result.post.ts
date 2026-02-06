/**
 * Review Result Endpoint
 * 
 * Receives review decisions from AI reviewers.
 * Handles approve/fix/escalate decisions and triggers appropriate follow-up actions.
 * 
 * Flow:
 * - approve → merge phase branch to target (usually main), advance pipeline
 * - fix → spawn fixer agent, wait for fix-complete callback, then re-review
 * - escalate → create escalation for human review, pause pipeline
 */

import { 
  spawnFixer,
  spawnPhaseReviewer,
  advanceReviewChain,
  resetReviewChain,
  getReviewChainState,
  type ReviewResult 
} from '../../utils/phase-reviewer'
import { createEscalation } from '../../utils/escalation-store'
import { getPhaseState } from '../../utils/phase-collector'
import {
  recordReviewDecision,
  recordFixerSpawned,
  getReviewState,
  markMerged,
  getFixAttemptCount,
} from '../../utils/review-state'
import {
  advanceToNextPhase,
  getProjectInfoFromRun,
} from '../../utils/phase-advancer'
import { exec as execCallback } from 'child_process'
import { promisify } from 'util'
import { requireAuth } from '../../utils/security'

const exec = promisify(execCallback)

const MAX_FIX_ATTEMPTS = 3

interface ReviewResultPayload {
  runId: string
  phaseNumber: number
  decision: 'approve' | 'fix' | 'escalate'
  comments?: string
  fixInstructions?: string
  escalationReason?: string
}

export default defineEventHandler(async (event) => {
  const body = await readBody<ReviewResultPayload>(event)

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

  if (!body.decision || !['approve', 'fix', 'escalate'].includes(body.decision)) {
    throw createError({
      statusCode: 400,
      statusMessage: 'decision must be one of: approve, fix, escalate',
    })
  }

  console.log(`[review-result] Run ${body.runId}, Phase ${body.phaseNumber}: ${body.decision}`)

  // Get phase state for context
  const phaseState = await getPhaseState(body.runId, body.phaseNumber)
  if (!phaseState) {
    return {
      success: false,
      decision: body.decision,
      error: `Phase ${body.phaseNumber} not found for run ${body.runId}`,
    }
  }

  // Handle based on decision
  switch (body.decision) {
    case 'approve': {
      return await handleApprove(body, phaseState)
    }

    case 'fix': {
      return await handleFix(body, phaseState)
    }

    case 'escalate': {
      return await handleEscalate(body, phaseState)
    }
  }
})

/**
 * Handle APPROVE decision - merge phase branch to target
 */
async function handleApprove(
  body: ReviewResultPayload,
  phaseState: any
): Promise<any> {
  console.log(`[review-result] Phase ${body.phaseNumber} APPROVED`)

  // Record the decision
  await recordReviewDecision({
    runId: body.runId,
    phaseNumber: body.phaseNumber,
    decision: 'approve',
    comments: body.comments,
  })

  // Check if there are more reviewers in the chain
  const chainState = getReviewChainState(body.runId, body.phaseNumber)
  if (chainState && chainState.remaining.length > 1) {
    // More reviewers to go - advance the chain
    const currentRole = chainState.currentRole
    console.log(`[review-result] ${currentRole} approved, advancing review chain...`)

    const nextResult = await advanceReviewChain(
      body.runId,
      body.phaseNumber,
      currentRole,
      {
        runId: body.runId,
        phaseName: `phase-${body.phaseNumber}`,
        phaseNumber: body.phaseNumber,
        projectDir: phaseState.repoDir,
        phaseBranch: phaseState.phaseBranch,
        targetBranch: phaseState.baseBranch || 'main',
        reviewChain: chainState.chain,
        currentReviewerIndex: chainState.currentIndex,
      }
    )

    if (nextResult) {
      // Next reviewer spawned
      const nextChainState = getReviewChainState(body.runId, body.phaseNumber)
      return {
        success: true,
        decision: 'approve',
        chainAdvanced: true,
        previousReviewer: currentRole,
        nextReviewer: nextChainState?.currentRole,
        chainProgress: `${chainState.approvals.length + 1}/${chainState.chain.length}`,
        message: `${currentRole} approved. Next: ${nextChainState?.currentRole}`,
        nextStep: 'await-next-reviewer',
      }
    }
    // nextResult is null = chain complete, fall through to merge
    console.log(`[review-result] All reviewers in chain approved, proceeding to merge`)
  } else if (chainState) {
    // Last reviewer in chain - advance to mark complete
    advanceReviewChain(body.runId, body.phaseNumber, chainState.currentRole, {
      runId: body.runId,
      phaseName: `phase-${body.phaseNumber}`,
      phaseNumber: body.phaseNumber,
      projectDir: phaseState.repoDir,
      phaseBranch: phaseState.phaseBranch,
    })
    console.log(`[review-result] Final reviewer approved, proceeding to merge`)
  }

  const phaseBranch = phaseState.phaseBranch
  const targetBranch = phaseState.baseBranch || 'main'
  const repoDir = phaseState.repoDir

  if (!phaseBranch) {
    return {
      success: false,
      decision: 'approve',
      error: 'No phase branch to merge',
    }
  }

  // Merge phase branch to target
  const mergeResult = await mergeToTarget(repoDir, phaseBranch, targetBranch)

  if (!mergeResult.success) {
    console.error(`[review-result] Merge failed: ${mergeResult.error}`)
    
    // If merge fails, escalate for human review
    const escalation = await createEscalation({
      runId: body.runId,
      pipelineId: body.runId,
      pipelineName: `phase-${body.phaseNumber}`,
      stepOrder: body.phaseNumber,
      roleId: 'reviewer',
      roleName: 'AI Reviewer',
      error: `Merge to ${targetBranch} failed after approval: ${mergeResult.error}`,
      attemptCount: 1,
      maxAttempts: 1,
      projectDir: repoDir,
      severity: 'high',
    })

    return {
      success: false,
      decision: 'approve',
      error: mergeResult.error,
      escalationId: escalation.id,
      message: 'Merge failed, escalated for human review',
    }
  }

  // Mark as merged
  await markMerged({
    runId: body.runId,
    phaseNumber: body.phaseNumber,
  })

  console.log(`[review-result] Phase ${body.phaseNumber} merged to ${targetBranch}`)

  // Advance to the next phase
  const projectInfo = await getProjectInfoFromRun(body.runId)
  let advanceResult: any = null
  
  if (projectInfo) {
    console.log(`[review-result] Advancing pipeline for project: ${projectInfo.projectName}`)
    
    advanceResult = await advanceToNextPhase({
      runId: body.runId,
      completedPhaseNumber: body.phaseNumber,
      projectPath: projectInfo.projectPath,
      projectName: projectInfo.projectName,
    })

    if (advanceResult.pipelineComplete) {
      console.log(`[review-result] Pipeline complete!`)
    } else if (advanceResult.advanced) {
      console.log(`[review-result] Advanced to phase ${advanceResult.nextPhase}`)
    }
  } else {
    console.log(`[review-result] Could not find project info for run ${body.runId}, skipping auto-advance`)
  }

  return {
    success: true,
    decision: 'approve',
    message: `Phase branch ${phaseBranch} merged to ${targetBranch}`,
    mergedBranch: phaseBranch,
    targetBranch,
    nextStep: advanceResult?.pipelineComplete ? 'complete' : 'pipeline-advance',
    pipelineComplete: advanceResult?.pipelineComplete || false,
    advanceResult: advanceResult ? {
      advanced: advanceResult.advanced,
      nextPhase: advanceResult.nextPhase,
      spawnedWorkers: advanceResult.spawnedWorkers,
      message: advanceResult.message,
    } : null,
  }
}

/**
 * Handle FIX decision - spawn fixer agent
 */
async function handleFix(
  body: ReviewResultPayload,
  phaseState: any
): Promise<any> {
  if (!body.fixInstructions) {
    throw createError({
      statusCode: 400,
      statusMessage: 'fixInstructions required for fix decision',
    })
  }

  // Check fix attempt count
  const fixAttempts = await getFixAttemptCount(body.runId, body.phaseNumber)
  
  if (fixAttempts >= MAX_FIX_ATTEMPTS) {
    console.log(`[review-result] Phase ${body.phaseNumber} exceeded max fix attempts (${MAX_FIX_ATTEMPTS}), escalating`)
    
    // Auto-escalate after too many fix attempts
    return await handleEscalate({
      ...body,
      decision: 'escalate',
      escalationReason: `Exceeded maximum fix attempts (${MAX_FIX_ATTEMPTS}). Original issues: ${body.fixInstructions}`,
    }, phaseState)
  }

  console.log(`[review-result] Phase ${body.phaseNumber} needs fixes (attempt ${fixAttempts + 1}/${MAX_FIX_ATTEMPTS})`)

  // Reset the review chain so fixes get re-reviewed from the start
  resetReviewChain(body.runId, body.phaseNumber)

  // Record the decision
  await recordReviewDecision({
    runId: body.runId,
    phaseNumber: body.phaseNumber,
    decision: 'fix',
    comments: body.comments,
    fixInstructions: body.fixInstructions,
  })

  // Spawn a fixer agent
  const phaseBranch = phaseState.phaseBranch || `swarmops/${body.runId}/phase-${body.phaseNumber}`

  const fixerResult = await spawnFixer({
    runId: body.runId,
    phaseName: `phase-${body.phaseNumber}`,
    phaseNumber: body.phaseNumber,
    projectDir: phaseState.repoDir,
    phaseBranch,
    fixInstructions: body.fixInstructions,
    reviewComments: body.comments,
  })

  if (!fixerResult.ok) {
    console.error(`[review-result] Failed to spawn fixer: ${fixerResult.error}`)
    
    // If we can't spawn a fixer, escalate
    const escalation = await createEscalation({
      runId: body.runId,
      pipelineId: body.runId,
      pipelineName: `phase-${body.phaseNumber}`,
      stepOrder: body.phaseNumber,
      roleId: 'fixer',
      roleName: 'AI Fixer',
      error: `Failed to spawn fixer: ${fixerResult.error}. Issues: ${body.fixInstructions}`,
      attemptCount: fixAttempts + 1,
      maxAttempts: MAX_FIX_ATTEMPTS,
      projectDir: phaseState.repoDir,
      severity: 'medium',
    })

    return {
      success: false,
      decision: 'fix',
      error: fixerResult.error,
      escalationId: escalation.id,
      message: 'Failed to spawn fixer agent, escalated',
    }
  }

  // Record the fixer session
  await recordFixerSpawned({
    runId: body.runId,
    phaseNumber: body.phaseNumber,
    fixerSession: fixerResult.sessionKey!,
  })

  console.log(`[review-result] Fixer spawned: ${fixerResult.sessionKey}`)

  return {
    success: true,
    decision: 'fix',
    fixerSpawned: true,
    fixerSession: fixerResult.sessionKey,
    fixAttempt: fixAttempts + 1,
    maxAttempts: MAX_FIX_ATTEMPTS,
    message: `Fixer agent spawned (attempt ${fixAttempts + 1}/${MAX_FIX_ATTEMPTS})`,
    nextStep: 'await-fix-complete',
  }
}

/**
 * Handle ESCALATE decision - create escalation for human review
 */
async function handleEscalate(
  body: ReviewResultPayload,
  phaseState: any
): Promise<any> {
  console.log(`[review-result] Phase ${body.phaseNumber} ESCALATED for human review`)

  // Create an escalation for human review
  const escalation = await createEscalation({
    runId: body.runId,
    pipelineId: body.runId,
    pipelineName: `phase-${body.phaseNumber}`,
    stepOrder: body.phaseNumber,
    roleId: 'reviewer',
    roleName: 'AI Reviewer',
    error: body.escalationReason || body.comments || 'Review escalated for human decision',
    attemptCount: 1,
    maxAttempts: 1,
    projectDir: phaseState?.repoDir || '',
    severity: 'medium',
  })

  // Record the decision
  await recordReviewDecision({
    runId: body.runId,
    phaseNumber: body.phaseNumber,
    decision: 'escalate',
    comments: body.comments,
    escalationReason: body.escalationReason,
    escalationId: escalation.id,
  })

  console.log(`[review-result] Escalation created: ${escalation.id}`)
  
  return {
    success: true,
    decision: 'escalate',
    escalationId: escalation.id,
    message: 'Review escalated for human decision',
    reason: body.escalationReason || body.comments,
    nextStep: 'human-review',
  }
}

/**
 * Merge a branch to target branch
 */
async function mergeToTarget(
  repoDir: string,
  sourceBranch: string,
  targetBranch: string
): Promise<{ success: boolean; error?: string }> {
  try {
    // Checkout target branch
    await exec(`git checkout "${targetBranch}"`, { cwd: repoDir })

    // Merge the source branch
    const { stdout, stderr } = await exec(
      `git merge "${sourceBranch}" --no-ff -m "Merge phase branch ${sourceBranch}"`,
      { cwd: repoDir }
    )

    console.log(`[review-result] Merge output: ${stdout}`)
    
    return { success: true }
  } catch (err: any) {
    // Check if it's a merge conflict
    if (err.message?.includes('CONFLICT') || err.stderr?.includes('CONFLICT')) {
      // Abort the failed merge
      try {
        await exec('git merge --abort', { cwd: repoDir })
      } catch {
        // Ignore abort errors
      }
      return {
        success: false,
        error: 'Merge conflict detected. Human review required.',
      }
    }

    return {
      success: false,
      error: err.message || 'Unknown merge error',
    }
  }
}
