/**
 * WorktreeManager - Git worktree management for parallel workers
 * 
 * Creates isolated worktrees for each worker so they can work in parallel
 * without conflicting. Each worker gets a unique branch and directory.
 */

import { mkdir, rm, access } from 'fs/promises'
import { join } from 'path'
import { execFile } from 'child_process'
import { promisify } from 'util'

const execFileAsync = promisify(execFile)

const WORKTREE_BASE = process.env.SWARMOPS_WORKTREE_DIR || '/tmp/swarmops-worktrees'

export interface WorktreeInfo {
  runId: string
  workerId: string
  path: string
  branch: string
  baseBranch: string
  repoDir: string
}

export interface CreateWorktreeResult {
  ok: boolean
  worktree?: WorktreeInfo
  error?: string
}

export interface CommitResult {
  ok: boolean
  commitHash?: string
  error?: string
}

export interface CleanupResult {
  ok: boolean
  error?: string
}

/**
 * Get the worktree path for a worker
 */
export function getWorktreePath(runId: string, workerId: string): string {
  return join(WORKTREE_BASE, runId, workerId)
}

/**
 * Get the branch name for a worker
 */
export function getWorkerBranch(runId: string, workerId: string): string {
  return `swarmops/${runId}/worker-${workerId}`
}

/**
 * Create a new worktree for a worker
 * 
 * Creates a fresh worktree branched from the specified base branch.
 * The worker will work in isolation and can later merge their changes.
 */
export async function createWorktree(opts: {
  repoDir: string
  runId: string
  workerId: string
  baseBranch?: string
}): Promise<CreateWorktreeResult> {
  const { repoDir, runId, workerId, baseBranch = 'main' } = opts
  
  const worktreePath = getWorktreePath(runId, workerId)
  const branch = getWorkerBranch(runId, workerId)

  try {
    // Verify repo exists
    await access(join(repoDir, '.git'))
  } catch {
    return { ok: false, error: `Not a git repository: ${repoDir}` }
  }

  try {
    // Create base directory if needed
    await mkdir(join(WORKTREE_BASE, runId), { recursive: true })

    // Check if worktree already exists
    try {
      await access(worktreePath)
      // Already exists - clean it up first
      await removeWorktree(repoDir, worktreePath)
    } catch {
      // Doesn't exist, good
    }

    // Make sure the branch doesn't already exist (leftover from previous run)
    try {
      await execFileAsync('git', ['branch', '-D', branch], { cwd: repoDir })
    } catch {
      // Branch doesn't exist, that's fine
    }

    // Fetch latest from remote (best effort)
    try {
      await execFileAsync('git', ['fetch', 'origin'], { cwd: repoDir })
    } catch {
      // May not have remote configured, continue anyway
    }

    // Create worktree with new branch from base
    await execFileAsync('git', ['worktree', 'add', '-b', branch, worktreePath, baseBranch], { cwd: repoDir })

    return {
      ok: true,
      worktree: {
        runId,
        workerId,
        path: worktreePath,
        branch,
        baseBranch,
        repoDir,
      },
    }
  } catch (err: any) {
    return { ok: false, error: err.message || 'Failed to create worktree' }
  }
}

/**
 * Commit all changes in a worktree
 * 
 * Stages all changes and creates a commit. Returns the commit hash.
 * If there are no changes, returns success with no commit hash.
 */
export async function commitWorktree(opts: {
  worktreePath: string
  message: string
  author?: string
}): Promise<CommitResult> {
  const { worktreePath, message, author } = opts

  try {
    // Check if worktree exists
    await access(worktreePath)
  } catch {
    return { ok: false, error: `Worktree not found: ${worktreePath}` }
  }

  try {
    // Stage all changes
    await execFileAsync('git', ['add', '-A'], { cwd: worktreePath })

    // Check if there are changes to commit
    const { stdout: status } = await execFileAsync('git', ['status', '--porcelain'], { cwd: worktreePath })
    
    if (!status.trim()) {
      // No changes to commit
      return { ok: true }
    }

    // Build commit args (safe - no shell involved)
    const commitArgs = ['commit', '-m', message]
    if (author) {
      commitArgs.push('--author', author)
    }

    await execFileAsync('git', commitArgs, { cwd: worktreePath })

    // Get the commit hash
    const { stdout: hash } = await execFileAsync('git', ['rev-parse', 'HEAD'], { cwd: worktreePath })

    return { ok: true, commitHash: hash.trim() }
  } catch (err: any) {
    return { ok: false, error: err.message || 'Failed to commit changes' }
  }
}

/**
 * Push worktree branch to remote
 */
export async function pushWorktree(opts: {
  worktreePath: string
  remote?: string
}): Promise<{ ok: boolean; error?: string }> {
  const { worktreePath, remote = 'origin' } = opts

  try {
    // Get current branch name
    const { stdout: branch } = await execFileAsync('git', ['rev-parse', '--abbrev-ref', 'HEAD'], { cwd: worktreePath })
    
    // Push to remote
    await execFileAsync('git', ['push', '-u', remote, branch.trim()], { cwd: worktreePath })

    return { ok: true }
  } catch (err: any) {
    return { ok: false, error: err.message || 'Failed to push worktree' }
  }
}

/**
 * Clean up a single worktree
 */
export async function cleanupWorktree(opts: {
  repoDir: string
  runId: string
  workerId: string
  deleteBranch?: boolean
}): Promise<CleanupResult> {
  const { repoDir, runId, workerId, deleteBranch = false } = opts
  
  const worktreePath = getWorktreePath(runId, workerId)
  const branch = getWorkerBranch(runId, workerId)

  try {
    // Remove the worktree
    await removeWorktree(repoDir, worktreePath)

    // Optionally delete the branch
    if (deleteBranch) {
      try {
        await execFileAsync('git', ['branch', '-D', branch], { cwd: repoDir })
      } catch {
        // Branch may already be deleted
      }
    }

    return { ok: true }
  } catch (err: any) {
    return { ok: false, error: err.message || 'Failed to cleanup worktree' }
  }
}

/**
 * Clean up all worktrees for a run
 */
export async function cleanupRunWorktrees(opts: {
  repoDir: string
  runId: string
  deleteBranches?: boolean
}): Promise<CleanupResult> {
  const { repoDir, runId, deleteBranches = false } = opts
  const runDir = join(WORKTREE_BASE, runId)

  try {
    // List all worktrees for this run
    const { stdout: worktreeList } = await execFileAsync('git', ['worktree', 'list', '--porcelain'], { cwd: repoDir })
    
    // Parse worktree paths that belong to this run
    const lines = worktreeList.split('\n')
    const runWorktrees: string[] = []
    
    for (const line of lines) {
      if (line.startsWith('worktree ')) {
        const path = line.slice('worktree '.length)
        if (path.startsWith(runDir)) {
          runWorktrees.push(path)
        }
      }
    }

    // Remove each worktree
    for (const path of runWorktrees) {
      await removeWorktree(repoDir, path)
    }

    // Delete branches if requested
    if (deleteBranches) {
      const branchPrefix = `swarmops/${runId}/`
      const { stdout: branches } = await execFileAsync('git', ['branch'], { cwd: repoDir })
      
      for (const branch of branches.split('\n')) {
        const trimmed = branch.replace(/^\*?\s*/, '').trim()
        if (trimmed.startsWith(branchPrefix)) {
          try {
            await execFileAsync('git', ['branch', '-D', trimmed], { cwd: repoDir })
          } catch {
            // Ignore branch deletion failures
          }
        }
      }
    }

    // Remove the run directory
    try {
      await rm(runDir, { recursive: true, force: true })
    } catch {
      // Directory may not exist
    }

    return { ok: true }
  } catch (err: any) {
    return { ok: false, error: err.message || 'Failed to cleanup run worktrees' }
  }
}

/**
 * List all worktrees for a run
 */
export async function listRunWorktrees(opts: {
  repoDir: string
  runId: string
}): Promise<{ ok: boolean; worktrees?: WorktreeInfo[]; error?: string }> {
  const { repoDir, runId } = opts
  const runDir = join(WORKTREE_BASE, runId)

  try {
    const { stdout: worktreeList } = await execFileAsync('git', ['worktree', 'list', '--porcelain'], { cwd: repoDir })
    
    const worktrees: WorktreeInfo[] = []
    const lines = worktreeList.split('\n')
    
    let currentPath = ''
    let currentBranch = ''
    
    for (const line of lines) {
      if (line.startsWith('worktree ')) {
        currentPath = line.slice('worktree '.length)
      } else if (line.startsWith('branch refs/heads/')) {
        currentBranch = line.slice('branch refs/heads/'.length)
      } else if (line === '' && currentPath.startsWith(runDir)) {
        // End of worktree entry, save if it belongs to this run
        const workerId = currentPath.split('/').pop() || ''
        worktrees.push({
          runId,
          workerId,
          path: currentPath,
          branch: currentBranch,
          baseBranch: 'main', // We don't track this, assume main
          repoDir,
        })
        currentPath = ''
        currentBranch = ''
      }
    }

    return { ok: true, worktrees }
  } catch (err: any) {
    return { ok: false, error: err.message || 'Failed to list worktrees' }
  }
}

/**
 * Remove a worktree using git commands
 */
async function removeWorktree(repoDir: string, worktreePath: string): Promise<void> {
  try {
    // Try normal removal first
    await execFileAsync('git', ['worktree', 'remove', worktreePath], { cwd: repoDir })
  } catch {
    // Force removal if normal fails
    try {
      await execFileAsync('git', ['worktree', 'remove', '--force', worktreePath], { cwd: repoDir })
    } catch {
      // If git command fails, manually clean up
      await rm(worktreePath, { recursive: true, force: true })
      await execFileAsync('git', ['worktree', 'prune'], { cwd: repoDir })
    }
  }
}

// escapeShellArg removed - using execFile instead (no shell invocation)
