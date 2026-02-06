/**
 * PhaseMerger - Sequential merge of phase worker branches with conflict detection
 * 
 * Orchestrates the merge process for a completed phase:
 * 1. Collects branches from phase-collector
 * 2. Sequentially merges each worker branch into the phase branch
 * 3. Detects and reports conflicts for AI resolution
 * 4. Triggers AI code review on successful merge
 */

import {
  mergeBranch,
  checkoutBranch,
  branchExists,
  abortMerge,
  getConflictedFiles,
  getCurrentBranch,
  spawnConflictResolver,
} from './conflict-resolver'
import {
  spawnSmartConflictResolver,
  logConflictResolution,
} from './smart-conflict-resolver'
import {
  getPhaseState,
  collectPhaseBranches,
  completePhase,
  failPhase,
} from './phase-collector'
import {
  spawnPhaseReviewer,
  type PhaseReviewRequest,
  type SpawnReviewResult,
} from './phase-reviewer'
import { exec as execCallback } from 'child_process'
import { promisify } from 'util'

const exec = promisify(execCallback)

export interface PhaseMergeResult {
  success: boolean
  status: 'completed' | 'conflict' | 'failed' | 'no-changes'
  phaseBranch?: string
  mergedBranches: string[]
  conflictInfo?: ConflictInfo
  resolverSession?: string  // Session key of spawned AI conflict resolver
  reviewerSession?: string  // Session key of spawned AI reviewer (on success)
  error?: string
}

export interface ConflictInfo {
  failedBranch: string
  conflictFiles: string[]
  phaseBranch: string
  remainingBranches: string[]
  mergeBase: string
}

/**
 * Execute sequential merge for a completed phase
 * 
 * This is the main entry point for merging a phase's worker branches.
 * Call this after all workers in a phase have completed successfully.
 */
export async function mergePhase(opts: {
  runId: string
  phaseNumber: number
}): Promise<PhaseMergeResult> {
  const { runId, phaseNumber } = opts

  console.log(`[phase-merger] Starting merge for phase ${phaseNumber} of run ${runId}`)

  const phaseState = await getPhaseState(runId, phaseNumber)
  if (!phaseState) {
    return {
      success: false,
      status: 'failed',
      mergedBranches: [],
      error: `Phase ${phaseNumber} not found for run ${runId}`,
    }
  }

  const failedWorkers = phaseState.workers.filter(w => w.status === 'failed')
  if (failedWorkers.length > 0) {
    const failedIds = failedWorkers.map(w => w.workerId).join(', ')
    return {
      success: false,
      status: 'failed',
      mergedBranches: [],
      error: `Cannot merge phase with failed workers: ${failedIds}`,
    }
  }

  const runningWorkers = phaseState.workers.filter(w => w.status === 'running')
  if (runningWorkers.length > 0) {
    const runningIds = runningWorkers.map(w => w.workerId).join(', ')
    return {
      success: false,
      status: 'failed',
      mergedBranches: [],
      error: `Cannot merge phase with running workers: ${runningIds}`,
    }
  }

  const collectResult = await collectPhaseBranches({ runId, phaseNumber })
  if (!collectResult.success) {
    return {
      success: false,
      status: 'failed',
      mergedBranches: [],
      error: collectResult.error || 'Failed to collect phase branches',
    }
  }

  if (!collectResult.workerBranches || collectResult.workerBranches.length === 0) {
    console.log(`[phase-merger] No branches to merge for phase ${phaseNumber}`)
    await completePhase({ runId, phaseNumber })
    return {
      success: true,
      status: 'no-changes',
      phaseBranch: collectResult.phaseBranch,
      mergedBranches: [],
    }
  }

  const { phaseBranch, workerBranches } = collectResult as {
    phaseBranch: string
    workerBranches: string[]
  }

  console.log(`[phase-merger] Merging ${workerBranches.length} branches into ${phaseBranch}`)

  const mergeResult = await executeSequentialMerge({
    repoDir: phaseState.repoDir,
    phaseBranch,
    workerBranches,
    baseBranch: phaseState.baseBranch,
  })

  if (mergeResult.success) {
    console.log(`[phase-merger] Phase ${phaseNumber} merged successfully`)
    await completePhase({ runId, phaseNumber })
    
    // Trigger AI code review after successful merge
    let reviewerSession: string | undefined
    const reviewResult = await triggerReviewForPhase({
      runId,
      phaseNumber,
      phaseName: `Phase ${phaseNumber}`,
      phaseBranch,
    })
    
    if (reviewResult.sessionKey) {
      reviewerSession = reviewResult.sessionKey
      console.log(`[phase-merger] Review triggered for phase ${phaseNumber}: ${reviewerSession}`)
    } else if (reviewResult.error) {
      console.error(`[phase-merger] Failed to trigger review: ${reviewResult.error}`)
    }
    
    return {
      success: true,
      status: 'completed',
      phaseBranch,
      mergedBranches: mergeResult.mergedBranches,
      reviewerSession,
    }
  }

  if (mergeResult.conflicted && mergeResult.failedBranch) {
    console.log(`[phase-merger] Conflict detected merging ${mergeResult.failedBranch}`)
    
    const failedIndex = workerBranches.indexOf(mergeResult.failedBranch)
    const remainingBranches = workerBranches.slice(failedIndex + 1)
    const conflictFiles = mergeResult.conflictFiles || []

    let resolverSession: string | undefined
    if (conflictFiles.length > 0) {
      console.log(`[phase-merger] Spawning smart AI conflict resolver for ${conflictFiles.length} conflicted file(s)`)
      
      // Log conflict resolution started
      if (phaseState.projectPath) {
        await logConflictResolution({
          projectPath: phaseState.projectPath,
          runId,
          phaseNumber,
          conflictFiles,
          sourceBranch: mergeResult.failedBranch,
          targetBranch: phaseBranch,
          status: 'started',
        })
      }
      
      // Use smart resolver with task context
      const resolverResult = await spawnSmartConflictResolver({
        runId,
        phaseNumber,
        repoPath: phaseState.repoDir,
        sourceBranch: mergeResult.failedBranch,
        targetBranch: phaseBranch,
        conflictFiles,
        projectGoal: phaseState.projectName ? `SwarmOps project: ${phaseState.projectName}` : undefined,
      })

      if (resolverResult.success && resolverResult.sessionKey) {
        resolverSession = resolverResult.sessionKey
        console.log(`[phase-merger] Smart conflict resolver spawned: ${resolverSession}`)
      } else {
        console.error(`[phase-merger] Failed to spawn smart conflict resolver: ${resolverResult.error}`)
        
        // Log failure
        if (phaseState.projectPath) {
          await logConflictResolution({
            projectPath: phaseState.projectPath,
            runId,
            phaseNumber,
            conflictFiles,
            sourceBranch: mergeResult.failedBranch,
            targetBranch: phaseBranch,
            status: 'failed',
            error: resolverResult.error,
          })
        }
      }
    }

    return {
      success: false,
      status: 'conflict',
      phaseBranch,
      mergedBranches: mergeResult.mergedBranches,
      resolverSession,
      conflictInfo: {
        failedBranch: mergeResult.failedBranch,
        conflictFiles,
        phaseBranch,
        remainingBranches,
        mergeBase: phaseState.baseBranch,
      },
    }
  }

  console.log(`[phase-merger] Phase ${phaseNumber} merge failed: ${mergeResult.error}`)
  await failPhase({ runId, phaseNumber, error: mergeResult.error || 'Unknown error' })
  return {
    success: false,
    status: 'failed',
    phaseBranch,
    mergedBranches: mergeResult.mergedBranches,
    error: mergeResult.error,
  }
}

async function executeSequentialMerge(opts: {
  repoDir: string
  phaseBranch: string
  workerBranches: string[]
  baseBranch: string
}): Promise<{
  success: boolean
  conflicted?: boolean
  mergedBranches: string[]
  failedBranch?: string
  conflictFiles?: string[]
  error?: string
}> {
  const { repoDir, phaseBranch, workerBranches } = opts
  const mergedBranches: string[] = []

  const originalBranch = await getCurrentBranch(repoDir)

  const checkoutResult = await checkoutBranch(repoDir, phaseBranch)
  if (!checkoutResult.success) {
    return {
      success: false,
      mergedBranches,
      error: `Failed to checkout phase branch ${phaseBranch}: ${checkoutResult.error}`,
    }
  }

  for (let i = 0; i < workerBranches.length; i++) {
    const branch = workerBranches[i]
    console.log(`[phase-merger] Merging branch ${i + 1}/${workerBranches.length}: ${branch}`)

    const exists = await branchExists(repoDir, branch)
    if (!exists) {
      console.log(`[phase-merger] Branch ${branch} does not exist, skipping`)
      continue
    }

    const result = await mergeBranch(repoDir, branch, {
      message: `Merge worker branch ${branch}`,
    })

    if (result.conflicted) {
      const conflictFiles = await getConflictedFiles(repoDir)
      return {
        success: false,
        conflicted: true,
        mergedBranches,
        failedBranch: branch,
        conflictFiles,
      }
    }

    if (!result.success) {
      await abortMerge(repoDir)
      await checkoutBranch(repoDir, originalBranch)
      return {
        success: false,
        mergedBranches,
        failedBranch: branch,
        error: result.error || `Failed to merge ${branch}`,
      }
    }

    mergedBranches.push(branch)
    console.log(`[phase-merger] Successfully merged ${branch}`)
  }

  console.log(`[phase-merger] All ${mergedBranches.length} branches merged successfully`)
  return {
    success: true,
    mergedBranches,
  }
}

/**
 * Resume merge after conflict resolution
 */
export async function resumeMerge(opts: {
  runId: string
  phaseNumber: number
  remainingBranches: string[]
}): Promise<PhaseMergeResult> {
  const { runId, phaseNumber, remainingBranches } = opts

  console.log(`[phase-merger] Resuming merge for phase ${phaseNumber}, ${remainingBranches.length} branches remaining`)

  const phaseState = await getPhaseState(runId, phaseNumber)
  if (!phaseState) {
    return {
      success: false,
      status: 'failed',
      mergedBranches: [],
      error: `Phase ${phaseNumber} not found`,
    }
  }

  const phaseBranch = phaseState.phaseBranch
  if (!phaseBranch) {
    return {
      success: false,
      status: 'failed',
      mergedBranches: [],
      error: 'Phase branch not set',
    }
  }

  if (remainingBranches.length === 0) {
    console.log(`[phase-merger] No remaining branches, phase complete`)
    await completePhase({ runId, phaseNumber })
    
    // Trigger AI code review after successful merge completion
    let reviewerSession: string | undefined
    const reviewResult = await triggerReviewForPhase({
      runId,
      phaseNumber,
      phaseName: `Phase ${phaseNumber}`,
      phaseBranch,
    })
    
    if (reviewResult.sessionKey) {
      reviewerSession = reviewResult.sessionKey
      console.log(`[phase-merger] Review triggered for phase ${phaseNumber}: ${reviewerSession}`)
    } else if (reviewResult.error) {
      console.error(`[phase-merger] Failed to trigger review: ${reviewResult.error}`)
    }
    
    return {
      success: true,
      status: 'completed',
      phaseBranch,
      mergedBranches: [],
      reviewerSession,
    }
  }

  const mergeResult = await executeSequentialMerge({
    repoDir: phaseState.repoDir,
    phaseBranch,
    workerBranches: remainingBranches,
    baseBranch: phaseState.baseBranch,
  })

  if (mergeResult.success) {
    console.log(`[phase-merger] Phase ${phaseNumber} merge resumed and completed`)
    await completePhase({ runId, phaseNumber })
    
    // Trigger AI code review after successful merge
    let reviewerSession: string | undefined
    const reviewResult = await triggerReviewForPhase({
      runId,
      phaseNumber,
      phaseName: `Phase ${phaseNumber}`,
      phaseBranch,
    })
    
    if (reviewResult.sessionKey) {
      reviewerSession = reviewResult.sessionKey
      console.log(`[phase-merger] Review triggered for phase ${phaseNumber} after resumed merge: ${reviewerSession}`)
    } else if (reviewResult.error) {
      console.error(`[phase-merger] Failed to trigger review: ${reviewResult.error}`)
    }
    
    return {
      success: true,
      status: 'completed',
      phaseBranch,
      mergedBranches: mergeResult.mergedBranches,
      reviewerSession,
    }
  }

  if (mergeResult.conflicted && mergeResult.failedBranch) {
    const failedIndex = remainingBranches.indexOf(mergeResult.failedBranch)
    const newRemaining = remainingBranches.slice(failedIndex + 1)
    const conflictFiles = mergeResult.conflictFiles || []

    let resolverSession: string | undefined
    if (conflictFiles.length > 0) {
      console.log(`[phase-merger] Spawning smart AI conflict resolver for ${conflictFiles.length} conflicted file(s) (resumed merge)`)
      
      // Log conflict resolution started
      if (phaseState.projectPath) {
        await logConflictResolution({
          projectPath: phaseState.projectPath,
          runId,
          phaseNumber,
          conflictFiles,
          sourceBranch: mergeResult.failedBranch,
          targetBranch: phaseBranch,
          status: 'started',
        })
      }
      
      // Use smart resolver with task context
      const resolverResult = await spawnSmartConflictResolver({
        runId,
        phaseNumber,
        repoPath: phaseState.repoDir,
        sourceBranch: mergeResult.failedBranch,
        targetBranch: phaseBranch,
        conflictFiles,
        projectGoal: phaseState.projectName ? `SwarmOps project: ${phaseState.projectName}` : undefined,
      })

      if (resolverResult.success && resolverResult.sessionKey) {
        resolverSession = resolverResult.sessionKey
        console.log(`[phase-merger] Smart conflict resolver spawned: ${resolverSession}`)
      } else {
        console.error(`[phase-merger] Failed to spawn smart conflict resolver: ${resolverResult.error}`)
      }
    }

    return {
      success: false,
      status: 'conflict',
      phaseBranch,
      mergedBranches: mergeResult.mergedBranches,
      resolverSession,
      conflictInfo: {
        failedBranch: mergeResult.failedBranch,
        conflictFiles,
        phaseBranch,
        remainingBranches: newRemaining,
        mergeBase: phaseState.baseBranch,
      },
    }
  }

  await failPhase({ runId, phaseNumber, error: mergeResult.error || 'Unknown error' })
  return {
    success: false,
    status: 'failed',
    phaseBranch,
    mergedBranches: mergeResult.mergedBranches,
    error: mergeResult.error,
  }
}

/**
 * Merge phase and trigger AI review on success
 * 
 * This is the main orchestration function that combines merge + review.
 * Use this instead of mergePhase() directly when you want automatic review
 * after a successful merge.
 */
export async function mergePhaseWithReview(opts: {
  runId: string
  phaseNumber: number
  phaseName?: string
  projectContext?: string
}): Promise<PhaseMergeResult> {
  const { runId, phaseNumber, phaseName, projectContext } = opts

  console.log(`[phase-merger] Starting merge+review for phase ${phaseNumber} of run ${runId}`)

  const mergeResult = await mergePhase({ runId, phaseNumber })

  if (mergeResult.success && (mergeResult.status === 'completed' || mergeResult.status === 'no-changes')) {
    const reviewResult = await triggerReviewForPhase({
      runId,
      phaseNumber,
      phaseName: phaseName || `phase-${phaseNumber}`,
      phaseBranch: mergeResult.phaseBranch,
      projectContext,
    })

    if (reviewResult.sessionKey) {
      console.log(`[phase-merger] Review triggered for phase ${phaseNumber}: ${reviewResult.sessionKey}`)
      mergeResult.reviewerSession = reviewResult.sessionKey
    } else if (reviewResult.error) {
      console.error(`[phase-merger] Failed to trigger review: ${reviewResult.error}`)
    }
  }

  return mergeResult
}

/**
 * Resume merge after conflict resolution and trigger review on success
 */
export async function resumeMergeWithReview(opts: {
  runId: string
  phaseNumber: number
  remainingBranches: string[]
  phaseName?: string
  projectContext?: string
}): Promise<PhaseMergeResult> {
  const { runId, phaseNumber, remainingBranches, phaseName, projectContext } = opts

  console.log(`[phase-merger] Resuming merge+review for phase ${phaseNumber}`)

  const mergeResult = await resumeMerge({ runId, phaseNumber, remainingBranches })

  if (mergeResult.success && mergeResult.status === 'completed') {
    const reviewResult = await triggerReviewForPhase({
      runId,
      phaseNumber,
      phaseName: phaseName || `phase-${phaseNumber}`,
      phaseBranch: mergeResult.phaseBranch,
      projectContext,
    })

    if (reviewResult.sessionKey) {
      console.log(`[phase-merger] Review triggered after resumed merge: ${reviewResult.sessionKey}`)
      mergeResult.reviewerSession = reviewResult.sessionKey
    } else if (reviewResult.error) {
      console.error(`[phase-merger] Failed to trigger review: ${reviewResult.error}`)
    }
  }

  return mergeResult
}

/**
 * Trigger review for a phase that's already merged
 * 
 * Use this when you need to re-trigger a review (e.g., after fixes)
 * without re-merging the branches.
 */
export async function triggerPhaseReview(opts: {
  runId: string
  phaseNumber: number
  phaseName?: string
  projectContext?: string
}): Promise<SpawnReviewResult> {
  const { runId, phaseNumber, phaseName, projectContext } = opts

  console.log(`[phase-merger] Triggering review for phase ${phaseNumber} of run ${runId}`)

  const phaseState = await getPhaseState(runId, phaseNumber)
  if (!phaseState) {
    return {
      ok: false,
      error: `Phase ${phaseNumber} not found for run ${runId}`,
    }
  }

  if (phaseState.status !== 'completed') {
    return {
      ok: false,
      error: `Phase ${phaseNumber} is not completed (status: ${phaseState.status})`,
    }
  }

  if (!phaseState.phaseBranch) {
    return {
      ok: false,
      error: `Phase ${phaseNumber} has no phase branch`,
    }
  }

  const reviewRequest: PhaseReviewRequest = {
    runId,
    phaseName: phaseName || `Phase ${phaseNumber}`,
    phaseNumber,
    projectDir: phaseState.repoDir,
    phaseBranch: phaseState.phaseBranch,
    targetBranch: phaseState.baseBranch || 'main',
    projectContext,
  }

  const result = await spawnPhaseReviewer(reviewRequest)

  if (result.ok) {
    console.log(`[phase-merger] Review triggered for phase ${phaseNumber}, session: ${result.sessionKey}`)
  } else {
    console.error(`[phase-merger] Failed to trigger review: ${result.error}`)
  }

  return result
}

/**
 * Internal: Trigger phase review by spawning reviewer agent
 */
async function triggerReviewForPhase(opts: {
  runId: string
  phaseNumber: number
  phaseName: string
  phaseBranch?: string
  projectContext?: string
}): Promise<{ sessionKey?: string; error?: string }> {
  const { runId, phaseNumber, phaseName, phaseBranch, projectContext } = opts

  const phaseState = await getPhaseState(runId, phaseNumber)
  if (!phaseState) {
    return { error: `Phase ${phaseNumber} not found` }
  }

  const finalPhaseBranch = phaseBranch || phaseState.phaseBranch
  if (!finalPhaseBranch) {
    return { error: 'No phase branch available for review' }
  }

  const result = await spawnPhaseReviewer({
    runId,
    phaseName,
    phaseNumber,
    projectDir: phaseState.repoDir,
    phaseBranch: finalPhaseBranch,
    targetBranch: phaseState.baseBranch,
    projectContext,
  })

  if (result.ok && result.sessionKey) {
    return { sessionKey: result.sessionKey }
  }

  return { error: result.error || 'Failed to spawn reviewer' }
}

/**
 * Get merge statistics for a phase
 */
export async function getPhaseMergeStats(opts: {
  runId: string
  phaseNumber: number
}): Promise<{
  totalBranches: number
  branchesWithChanges: number
  estimatedConflictRisk: 'low' | 'medium' | 'high'
}> {
  const phaseState = await getPhaseState(opts.runId, opts.phaseNumber)
  if (!phaseState) {
    return { totalBranches: 0, branchesWithChanges: 0, estimatedConflictRisk: 'low' }
  }

  const totalBranches = phaseState.workers.length
  const branchesWithChanges = phaseState.collectedBranches?.length || 0

  let estimatedConflictRisk: 'low' | 'medium' | 'high' = 'low'
  if (branchesWithChanges > 5) {
    estimatedConflictRisk = 'high'
  } else if (branchesWithChanges > 2) {
    estimatedConflictRisk = 'medium'
  }

  return {
    totalBranches,
    branchesWithChanges,
    estimatedConflictRisk,
  }
}

/**
 * Check if files might conflict between branches
 */
export async function detectPotentialConflicts(opts: {
  repoDir: string
  branches: string[]
  baseBranch: string
}): Promise<{ file: string; branches: string[] }[]> {
  const { repoDir, branches, baseBranch } = opts
  const fileChanges = new Map<string, string[]>()

  for (const branch of branches) {
    try {
      const { stdout } = await exec(
        `git diff --name-only ${baseBranch}...${branch}`,
        { cwd: repoDir }
      )
      const files = stdout.trim().split('\n').filter(Boolean)
      
      for (const file of files) {
        const branchList = fileChanges.get(file) || []
        branchList.push(branch)
        fileChanges.set(file, branchList)
      }
    } catch {
      // Branch may not exist or have issues
    }
  }

  const conflicts: { file: string; branches: string[] }[] = []
  for (const [file, branchList] of Array.from(fileChanges.entries())) {
    if (branchList.length > 1) {
      conflicts.push({ file, branches: branchList })
    }
  }

  return conflicts
}
