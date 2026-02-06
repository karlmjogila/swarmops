/**
 * ConflictResolver - Git merge and AI-powered conflict resolution
 * 
 * Handles merging worker branches and spawning AI to resolve conflicts.
 */

import { exec as execCallback } from 'child_process'
import { promisify } from 'util'
import { spawnSession } from './gateway-client'

const exec = promisify(execCallback)

export interface MergeResult {
  success: boolean
  conflicted: boolean
  conflictFiles?: string[]
  error?: string
}

export interface ConflictResolutionResult {
  success: boolean
  sessionKey?: string
  error?: string
}

/**
 * Attempt to merge a branch into the current branch
 */
export async function mergeBranch(
  repoPath: string,
  sourceBranch: string,
  options?: { noCommit?: boolean; message?: string }
): Promise<MergeResult> {
  try {
    const args = ['merge', sourceBranch]
    
    if (options?.noCommit) {
      args.push('--no-commit')
    }
    if (options?.message) {
      args.push('-m', `"${options.message}"`)
    }

    await exec(`git ${args.join(' ')}`, { cwd: repoPath })
    return { success: true, conflicted: false }
  } catch (err: any) {
    const stderr = err.stderr || ''
    const stdout = err.stdout || ''
    
    // Check if it's a conflict
    if (stderr.includes('CONFLICT') || stdout.includes('CONFLICT') || stderr.includes('Automatic merge failed')) {
      const conflictFiles = await getConflictedFiles(repoPath)
      return { success: false, conflicted: true, conflictFiles }
    }

    return { success: false, conflicted: false, error: err.message }
  }
}

/**
 * Get list of files with merge conflicts
 */
export async function getConflictedFiles(repoPath: string): Promise<string[]> {
  try {
    const { stdout } = await exec('git diff --name-only --diff-filter=U', { cwd: repoPath })
    return stdout.trim().split('\n').filter(Boolean)
  } catch {
    return []
  }
}

/**
 * Abort an in-progress merge
 */
export async function abortMerge(repoPath: string): Promise<void> {
  try {
    await exec('git merge --abort', { cwd: repoPath })
  } catch {
    // May fail if no merge in progress, that's fine
  }
}

/**
 * Get conflict markers content for a file
 */
export async function getConflictContent(repoPath: string, filePath: string): Promise<string> {
  try {
    const { stdout } = await exec(`cat "${filePath}"`, { cwd: repoPath })
    return stdout
  } catch (err: any) {
    return `Error reading file: ${err.message}`
  }
}

/**
 * Check if repo has uncommitted changes
 */
export async function hasUncommittedChanges(repoPath: string): Promise<boolean> {
  try {
    const { stdout } = await exec('git status --porcelain', { cwd: repoPath })
    return stdout.trim().length > 0
  } catch {
    return false
  }
}

/**
 * Get current branch name
 */
export async function getCurrentBranch(repoPath: string): Promise<string> {
  try {
    const { stdout } = await exec('git rev-parse --abbrev-ref HEAD', { cwd: repoPath })
    return stdout.trim()
  } catch {
    return ''
  }
}

/**
 * Check if a branch exists
 */
export async function branchExists(repoPath: string, branchName: string): Promise<boolean> {
  try {
    await exec(`git rev-parse --verify ${branchName}`, { cwd: repoPath })
    return true
  } catch {
    return false
  }
}

/**
 * Checkout a branch
 */
export async function checkoutBranch(repoPath: string, branchName: string): Promise<{ success: boolean; error?: string }> {
  try {
    await exec(`git checkout ${branchName}`, { cwd: repoPath })
    return { success: true }
  } catch (err: any) {
    return { success: false, error: err.message }
  }
}

/**
 * Create and checkout a new branch
 */
export async function createBranch(
  repoPath: string,
  branchName: string,
  fromBranch?: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const base = fromBranch || 'HEAD'
    await exec(`git checkout -b ${branchName} ${base}`, { cwd: repoPath })
    return { success: true }
  } catch (err: any) {
    return { success: false, error: err.message }
  }
}

/**
 * Stage resolved files
 */
export async function stageFile(repoPath: string, filePath: string): Promise<void> {
  await exec(`git add "${filePath}"`, { cwd: repoPath })
}

/**
 * Stage all changes
 */
export async function stageAll(repoPath: string): Promise<void> {
  await exec('git add -A', { cwd: repoPath })
}

/**
 * Commit merge resolution
 */
export async function commitMerge(repoPath: string, message?: string): Promise<{ success: boolean; error?: string }> {
  try {
    const msg = message || 'Resolved merge conflicts'
    await exec(`git commit -m "${msg}"`, { cwd: repoPath })
    return { success: true }
  } catch (err: any) {
    return { success: false, error: err.message }
  }
}

/**
 * Spawn an AI agent to resolve merge conflicts
 */
export async function spawnConflictResolver(opts: {
  runId: string
  pipelineName: string
  repoPath: string
  sourceBranch: string
  targetBranch: string
  conflictFiles: string[]
}): Promise<ConflictResolutionResult> {
  const prompt = buildConflictResolverPrompt(opts)
  const label = `conflict-resolver:${opts.pipelineName}:${opts.runId}`

  try {
    const result = await spawnSession({
      task: prompt,
      label,
      model: 'anthropic/claude-sonnet-4',
      thinking: 'low',
      cleanup: 'keep',
    })

    if (result.ok && result.result) {
      return {
        success: true,
        sessionKey: result.result.childSessionKey,
      }
    }

    return {
      success: false,
      error: result.error?.message || 'Failed to spawn conflict resolver',
    }
  } catch (err: any) {
    return {
      success: false,
      error: err.message || 'Exception spawning conflict resolver',
    }
  }
}

/**
 * Build prompt for AI conflict resolver
 */
function buildConflictResolverPrompt(opts: {
  runId: string
  pipelineName: string
  repoPath: string
  sourceBranch: string
  targetBranch: string
  conflictFiles: string[]
}): string {
  const fileList = opts.conflictFiles.map(f => `  - ${f}`).join('\n')

  return `[SWARMOPS CONFLICT RESOLVER] Pipeline: ${opts.pipelineName}
Run ID: ${opts.runId}

## Situation
A merge conflict occurred while merging branch \`${opts.sourceBranch}\` into \`${opts.targetBranch}\`.

## Repository
Path: ${opts.repoPath}

## Conflicted Files
${fileList}

## Your Task
1. Navigate to the repository: \`cd ${opts.repoPath}\`
2. Examine each conflicted file
3. Resolve the conflicts by:
   - Understanding what each branch was trying to do
   - Combining the changes intelligently (don't just pick one side)
   - Removing conflict markers (<<<<<<<, =======, >>>>>>>)
4. Stage the resolved files: \`git add <file>\`
5. Complete the merge: \`git commit -m "Resolved merge conflicts between ${opts.sourceBranch} and ${opts.targetBranch}"\`

## Conflict Resolution Guidelines
- Preserve functionality from BOTH branches when possible
- If changes are in different parts of a file, include both
- If changes conflict directly, understand the intent and merge logically
- Test that the result makes sense (no syntax errors, no duplicate code)
- Keep the code clean and consistent

## When Done
Report completion with:
\`\`\`bash
curl -X POST http://localhost:3939/api/orchestrator/worker-complete \\
  -H "Content-Type: application/json" \\
  -d '{"runId": "${opts.runId}", "stepOrder": -1, "status": "completed", "output": "Resolved ${opts.conflictFiles.length} conflict(s) in merge from ${opts.sourceBranch}"}'
\`\`\`

If you cannot resolve the conflicts, use \`"status": "failed"\` with an explanation.`
}

/**
 * Sequentially merge multiple branches into target
 * Returns on first conflict or after all succeed
 */
export async function sequentialMerge(
  repoPath: string,
  targetBranch: string,
  sourceBranches: string[]
): Promise<{
  success: boolean
  mergedBranches: string[]
  failedBranch?: string
  conflictFiles?: string[]
  error?: string
}> {
  const mergedBranches: string[] = []

  // Checkout target branch
  const checkoutResult = await checkoutBranch(repoPath, targetBranch)
  if (!checkoutResult.success) {
    return {
      success: false,
      mergedBranches,
      error: `Failed to checkout ${targetBranch}: ${checkoutResult.error}`,
    }
  }

  for (const branch of sourceBranches) {
    const exists = await branchExists(repoPath, branch)
    if (!exists) {
      return {
        success: false,
        mergedBranches,
        failedBranch: branch,
        error: `Branch ${branch} does not exist`,
      }
    }

    const result = await mergeBranch(repoPath, branch, {
      message: `Merge ${branch} into ${targetBranch}`,
    })

    if (result.conflicted) {
      return {
        success: false,
        mergedBranches,
        failedBranch: branch,
        conflictFiles: result.conflictFiles,
      }
    }

    if (!result.success) {
      return {
        success: false,
        mergedBranches,
        failedBranch: branch,
        error: result.error,
      }
    }

    mergedBranches.push(branch)
  }

  return { success: true, mergedBranches }
}

/**
 * Collect worker branches for a phase
 */
export function getWorkerBranches(runId: string, workerIds: string[]): string[] {
  return workerIds.map(id => `swarmops/${runId}/worker-${id}`)
}

/**
 * Get the phase merge branch name
 */
export function getPhaseBranch(runId: string, phaseNumber: number): string {
  return `swarmops/${runId}/phase-${phaseNumber}`
}
