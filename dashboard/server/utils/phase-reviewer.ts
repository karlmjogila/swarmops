/**
 * PhaseReviewer - Sequential multi-role code review
 * 
 * Spawns reviewers in sequence: reviewer -> security-reviewer -> designer (conditional)
 * Each reviewer must approve before the next is spawned.
 * Only when ALL approve does the phase merge to main.
 */

import { spawnSession } from './gateway-client'
import { getRoleConfig, type RoleConfig } from './role-loader'
import { exec as execCallback } from 'child_process'
import { promisify } from 'util'

const execPromise = promisify(execCallback)

import { type ReviewDecision } from './review-state'

export interface ReviewResult {
  decision: ReviewDecision
  comments?: string
  fixInstructions?: string
  escalationReason?: string
}

export interface PhaseReviewRequest {
  runId: string
  phaseName: string
  phaseNumber: number
  projectDir: string
  phaseBranch: string
  targetBranch?: string
  projectContext?: string
  // Review chain tracking
  reviewChain?: string[]
  currentReviewerIndex?: number
  currentReviewerRole?: string
}

export interface SpawnReviewResult {
  ok: boolean
  sessionKey?: string
  error?: string
  chain?: string[]
  currentRole?: string
}

// In-memory tracking of pending reviews
const pendingReviews = new Map<string, PhaseReviewRequest>()

// Review chain state per run+phase
const reviewChains = new Map<string, {
  chain: string[]
  currentIndex: number
  approvals: string[] // roles that approved
}>()

function chainKey(runId: string, phaseNumber: number): string {
  return `${runId}:phase-${phaseNumber}`
}

/**
 * Detect if phase changes include frontend files
 */
async function hasChangedFrontendFiles(
  repoDir: string,
  phaseBranch: string,
  targetBranch: string = 'main'
): Promise<boolean> {
  try {
    const { stdout } = await execPromise(
      `git diff --name-only "${targetBranch}...${phaseBranch}"`,
      { cwd: repoDir }
    )
    const files = stdout.trim().split('\n').filter(Boolean)
    const frontendPatterns = [
      /\.vue$/, /\.tsx$/, /\.jsx$/, /\.css$/, /\.scss$/,
      /components\//, /pages\//, /layouts\//, /assets\//
    ]
    return files.some(f => frontendPatterns.some(p => p.test(f)))
  } catch {
    // If git diff fails, skip designer review
    return false
  }
}

/**
 * Start a sequential review chain for a project
 * Called from auto-advance.ts when entering review phase
 */
export async function startReviewChain(opts: {
  projectName: string
  projectPath: string
  dashboardPath: string
  runId?: string
  phaseNumber?: number
  phaseBranch?: string
  targetBranch?: string
}): Promise<SpawnReviewResult> {
  const { projectName, projectPath, dashboardPath } = opts
  const runId = opts.runId || `review-${Date.now()}`
  const phaseNumber = opts.phaseNumber || 1
  const phaseBranch = opts.phaseBranch || 'main'
  const targetBranch = opts.targetBranch || 'main'

  // Build review chain: always reviewer + security-reviewer, conditionally designer
  const chain: string[] = ['reviewer', 'security-reviewer']

  const hasFrontend = await hasChangedFrontendFiles(dashboardPath, phaseBranch, targetBranch)
  if (hasFrontend) {
    chain.push('designer')
  }

  // Store chain state
  const key = chainKey(runId, phaseNumber)
  reviewChains.set(key, {
    chain,
    currentIndex: 0,
    approvals: [],
  })

  console.log(`[phase-reviewer] Starting review chain: ${chain.join(' → ')} (frontend: ${hasFrontend})`)

  // Spawn the first reviewer
  const result = await spawnChainReviewer({
    runId,
    phaseName: `phase-${phaseNumber}`,
    phaseNumber,
    projectDir: dashboardPath,
    phaseBranch,
    targetBranch,
    reviewChain: chain,
    currentReviewerIndex: 0,
    currentReviewerRole: chain[0],
  }, projectName, projectPath)

  return { ...result, chain }
}

/**
 * Advance to the next reviewer in the chain after an approval
 * Returns null if all reviewers approved (chain complete)
 */
export async function advanceReviewChain(
  runId: string,
  phaseNumber: number,
  approvedRole: string,
  request: PhaseReviewRequest
): Promise<SpawnReviewResult | null> {
  const key = chainKey(runId, phaseNumber)
  const chainState = reviewChains.get(key)

  if (!chainState) {
    console.warn(`[phase-reviewer] No chain state for ${key}, treating as single review`)
    return null // Chain complete
  }

  // Record approval
  chainState.approvals.push(approvedRole)
  chainState.currentIndex++

  console.log(`[phase-reviewer] ${approvedRole} approved (${chainState.approvals.length}/${chainState.chain.length})`)

  // Check if chain is complete
  if (chainState.currentIndex >= chainState.chain.length) {
    console.log(`[phase-reviewer] Review chain complete: all ${chainState.chain.length} reviewers approved`)
    reviewChains.delete(key)
    return null // All approved
  }

  // Spawn next reviewer
  const nextRole = chainState.chain[chainState.currentIndex]
  console.log(`[phase-reviewer] Spawning next reviewer: ${nextRole} (${chainState.currentIndex + 1}/${chainState.chain.length})`)

  const result = await spawnChainReviewer({
    ...request,
    currentReviewerIndex: chainState.currentIndex,
    currentReviewerRole: nextRole,
    reviewChain: chainState.chain,
  }, request.projectDir, request.projectDir)

  return result
}

/**
 * Reset chain to first reviewer (after a fix)
 */
export function resetReviewChain(runId: string, phaseNumber: number): void {
  const key = chainKey(runId, phaseNumber)
  const chainState = reviewChains.get(key)
  if (chainState) {
    chainState.currentIndex = 0
    chainState.approvals = []
    console.log(`[phase-reviewer] Chain reset to first reviewer: ${chainState.chain[0]}`)
  }
}

/**
 * Get current chain state
 */
export function getReviewChainState(runId: string, phaseNumber: number): {
  chain: string[]
  currentIndex: number
  currentRole: string
  approvals: string[]
  remaining: string[]
} | null {
  const key = chainKey(runId, phaseNumber)
  const state = reviewChains.get(key)
  if (!state) return null
  return {
    chain: state.chain,
    currentIndex: state.currentIndex,
    currentRole: state.chain[state.currentIndex] || state.chain[state.chain.length - 1],
    approvals: state.approvals,
    remaining: state.chain.slice(state.currentIndex),
  }
}

/**
 * Spawn a specific reviewer from the chain with its role config
 */
async function spawnChainReviewer(
  request: PhaseReviewRequest,
  projectName: string,
  projectPath: string,
): Promise<SpawnReviewResult> {
  const roleId = request.currentReviewerRole || 'reviewer'
  const roleConfig = await getRoleConfig(roleId)

  const reviewPrompt = buildReviewPrompt({
    ...request,
    roleConfig,
    projectName,
  })

  const label = `${roleId}:${request.phaseName}:phase-${request.phaseNumber}`

  try {
    const result = await spawnSession({
      task: reviewPrompt,
      label,
      model: roleConfig.model,
      thinking: roleConfig.thinking,
      cleanup: 'keep',
    })

    if (result.ok && result.result) {
      const sessionKey = result.result.childSessionKey

      // Track pending review
      pendingReviews.set(sessionKey, request)

      console.log(`[phase-reviewer] Spawned ${roleId} (model: ${roleConfig.model}, thinking: ${roleConfig.thinking})`)
      return { ok: true, sessionKey, currentRole: roleId }
    } else {
      return { ok: false, error: result.error?.message || `Failed to spawn ${roleId}` }
    }
  } catch (err: any) {
    return { ok: false, error: err.message || `Exception spawning ${roleId}` }
  }
}

/**
 * Build review prompt using role configuration
 */
function buildReviewPrompt(opts: PhaseReviewRequest & {
  roleConfig: RoleConfig
  projectName: string
}): string {
  const {
    runId, phaseName, phaseNumber, projectDir, phaseBranch,
    targetBranch = 'main', roleConfig, projectName,
    reviewChain, currentReviewerIndex,
  } = opts

  const chainInfo = reviewChain
    ? `\n\n## Review Chain\nYou are reviewer ${(currentReviewerIndex || 0) + 1} of ${reviewChain.length}: ${reviewChain.join(' → ')}\nYour role: **${roleConfig.name}**`
    : ''

  return `[SWARMOPS ${roleConfig.name?.toUpperCase() || 'REVIEWER'}] Phase: ${phaseName} (Phase ${phaseNumber})
Run ID: ${runId}
${chainInfo}

## Your Role
${roleConfig.instructions || 'Review the code changes for this phase.'}

## Review Instructions
1. Navigate to the project: \`cd ${projectDir}\`
2. Review the diff between ${phaseBranch} and ${targetBranch}:
   \`\`\`bash
   git diff ${targetBranch}...${phaseBranch}
   \`\`\`
3. Focus on your specialization as ${roleConfig.name}

## Decision Criteria
- **approve** if: Changes pass your review criteria
- **fix** if: Issues found that can be described for another agent to fix
- **escalate** if: Complex issues requiring human judgment

## IMPORTANT: Report Your Decision

\`\`\`bash
curl -X POST http://localhost:3939/api/orchestrator/review-result \\
  -H "Content-Type: application/json" \\
  -d '{
    "runId": "${runId}",
    "phaseNumber": ${phaseNumber},
    "decision": "approve|fix|escalate",
    "comments": "Your review comments",
    "fixInstructions": "If fix, what to change",
    "escalationReason": "If escalate, why"
  }'
\`\`\`

Choose ONE decision. Begin your review now.`
}

/**
 * Handle a reviewer's decision callback
 */
export function handleReviewResult(
  sessionKey: string,
  result: ReviewResult
): PhaseReviewRequest | undefined {
  const request = pendingReviews.get(sessionKey)
  if (request) {
    pendingReviews.delete(sessionKey)
  }
  return request
}

/**
 * Get a pending review by session key
 */
export function getPendingReview(sessionKey: string): PhaseReviewRequest | undefined {
  return pendingReviews.get(sessionKey)
}

/**
 * List all pending reviews
 */
export function listPendingReviews(): PhaseReviewRequest[] {
  return Array.from(pendingReviews.values())
}

/**
 * Build a prompt for a fixer agent
 */
export function buildFixerPrompt(opts: {
  runId: string
  phaseName: string
  phaseNumber: number
  projectDir: string
  phaseBranch: string
  fixInstructions: string
  reviewComments?: string
}): string {
  const { runId, phaseName, phaseNumber, projectDir, phaseBranch, fixInstructions, reviewComments } = opts

  return `[SWARMOPS FIXER] Phase: ${phaseName} (Phase ${phaseNumber})
Run ID: ${runId}

## Your Role
You are fixing issues identified in code review.

## Review Feedback
${reviewComments ? `### Comments\n${reviewComments}\n` : ''}
### Required Fixes
${fixInstructions}

## Instructions
1. Navigate to the project: \`cd ${projectDir}\`
2. Checkout the phase branch: \`git checkout ${phaseBranch}\`
3. Make the requested fixes
4. Commit your changes with a descriptive message
5. Report completion:

\`\`\`bash
curl -X POST http://localhost:3939/api/orchestrator/fix-complete \\
  -H "Content-Type: application/json" \\
  -d '{
    "runId": "${runId}",
    "phaseNumber": ${phaseNumber},
    "status": "completed",
    "summary": "Description of fixes made"
  }'
\`\`\`

If you cannot complete the fixes:
\`\`\`bash
curl -X POST http://localhost:3939/api/orchestrator/fix-complete \\
  -H "Content-Type: application/json" \\
  -d '{
    "runId": "${runId}",
    "phaseNumber": ${phaseNumber},
    "status": "failed",
    "error": "Description of what went wrong"
  }'
\`\`\``
}

/**
 * Spawn a fixer agent
 */
export async function spawnFixer(opts: {
  runId: string
  phaseName: string
  phaseNumber: number
  projectDir: string
  phaseBranch: string
  fixInstructions: string
  reviewComments?: string
}): Promise<SpawnReviewResult> {
  const fixerPrompt = buildFixerPrompt(opts)
  const label = `fixer:${opts.phaseName}:phase-${opts.phaseNumber}`

  try {
    const builderRole = await getRoleConfig('builder')
    const result = await spawnSession({
      task: fixerPrompt,
      label,
      model: builderRole.model,
      thinking: builderRole.thinking,
      cleanup: 'keep',
    })

    if (result.ok && result.result) {
      return { ok: true, sessionKey: result.result.childSessionKey }
    } else {
      return { ok: false, error: result.error?.message || 'Failed to spawn fixer' }
    }
  } catch (err: any) {
    return { ok: false, error: err.message || 'Exception spawning fixer' }
  }
}

/**
 * Spawn a phase reviewer (legacy single-reviewer compat)
 */
export async function spawnPhaseReviewer(
  request: PhaseReviewRequest
): Promise<SpawnReviewResult> {
  const roleConfig = await getRoleConfig('reviewer')
  const reviewPrompt = buildReviewPrompt({
    ...request,
    roleConfig,
    projectName: request.projectDir.split('/').pop() || 'unknown',
    targetBranch: request.targetBranch || 'main',
  })

  const label = `reviewer:${request.phaseName}:phase-${request.phaseNumber}`

  try {
    const result = await spawnSession({
      task: reviewPrompt,
      label,
      model: roleConfig.model,
      thinking: roleConfig.thinking,
      cleanup: 'keep',
    })

    if (result.ok && result.result) {
      const sessionKey = result.result.childSessionKey
      pendingReviews.set(sessionKey, request)
      return { ok: true, sessionKey }
    } else {
      return { ok: false, error: result.error?.message || 'Failed to spawn reviewer' }
    }
  } catch (err: any) {
    return { ok: false, error: err.message || 'Exception spawning reviewer' }
  }
}
