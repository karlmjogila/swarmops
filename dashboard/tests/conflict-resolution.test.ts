/**
 * Conflict Resolution Tests
 * 
 * Tests parallel workers making changes and conflict detection/resolution.
 * Run with: npx tsx tests/conflict-resolution.test.ts
 */

import { mkdir, rm, writeFile, readFile, access } from 'fs/promises'
import { join } from 'path'
import { exec } from 'child_process'
import { promisify } from 'util'
import {
  createWorktree,
  commitWorktree,
  cleanupRunWorktrees,
  getWorkerBranch,
} from '../server/utils/worktree-manager'
import {
  mergeBranch,
  checkoutBranch,
  createBranch,
  branchExists,
  abortMerge,
  getConflictedFiles,
  getCurrentBranch,
  stageAll,
  commitMerge,
  sequentialMerge,
  getWorkerBranches,
  getPhaseBranch,
} from '../server/utils/conflict-resolver'

const execAsync = promisify(exec)

const TEST_REPO_BASE = '/tmp/swarmops-conflict-test'
const TEST_REPO = join(TEST_REPO_BASE, 'test-repo')
const TEST_RUN_ID = 'conflict-test-' + Date.now()

let passCount = 0
let failCount = 0

function log(msg: string) {
  console.log(msg)
}

function pass(name: string) {
  passCount++
  log(`  ✓ ${name}`)
}

function fail(name: string, err?: any) {
  failCount++
  log(`  ✗ ${name}`)
  if (err) log(`    Error: ${err.message || err}`)
}

async function assert(condition: boolean, name: string, err?: any) {
  if (condition) {
    pass(name)
  } else {
    fail(name, err || new Error('Assertion failed'))
  }
}

async function setupTestRepo() {
  log('\n📁 Setting up test repository...')
  
  await rm(TEST_REPO_BASE, { recursive: true, force: true })
  await mkdir(TEST_REPO, { recursive: true })
  
  await execAsync('git init', { cwd: TEST_REPO })
  await execAsync('git config user.email "test@example.com"', { cwd: TEST_REPO })
  await execAsync('git config user.name "Test User"', { cwd: TEST_REPO })
  
  // Create initial files - a shared file that workers will conflict on
  await writeFile(join(TEST_REPO, 'README.md'), '# Test Repository\n\nInitial content.\n')
  await writeFile(join(TEST_REPO, 'shared-config.json'), JSON.stringify({
    version: '1.0.0',
    settings: {
      debug: false,
      timeout: 30
    }
  }, null, 2))
  await writeFile(join(TEST_REPO, 'utils.ts'), `// Utility functions

export function helper() {
  return 'original';
}

export function anotherHelper() {
  return 42;
}
`)
  
  await execAsync('git add -A', { cwd: TEST_REPO })
  await execAsync('git commit -m "Initial commit"', { cwd: TEST_REPO })
  
  try {
    await execAsync('git branch -M main', { cwd: TEST_REPO })
  } catch {
    // Branch may already be main
  }
  
  log('  Test repo created at: ' + TEST_REPO)
}

async function cleanupTestRepo() {
  log('\n🧹 Cleaning up test repository...')
  await rm(TEST_REPO_BASE, { recursive: true, force: true })
  await rm(join('/tmp/swarmops-worktrees', TEST_RUN_ID), { recursive: true, force: true })
  log('  Cleanup complete')
}

// ============================================
// Test: Branch utility functions
// ============================================

async function testBranchUtilities() {
  log('\n🔧 Test: Branch utility functions')
  
  // Test getWorkerBranches
  const branches = getWorkerBranches('run-123', ['w1', 'w2', 'w3'])
  await assert(
    branches.length === 3 &&
    branches[0] === 'swarmops/run-123/worker-w1' &&
    branches[1] === 'swarmops/run-123/worker-w2' &&
    branches[2] === 'swarmops/run-123/worker-w3',
    'getWorkerBranches returns correct branch names'
  )
  
  // Test getPhaseBranch
  const phaseBranch = getPhaseBranch('run-123', 2)
  await assert(
    phaseBranch === 'swarmops/run-123/phase-2',
    'getPhaseBranch returns correct branch name'
  )
}

// ============================================
// Test: Basic branch operations
// ============================================

async function testBranchOperations() {
  log('\n🌿 Test: Basic branch operations')
  
  // Get current branch
  const currentBranch = await getCurrentBranch(TEST_REPO)
  await assert(currentBranch === 'main', 'getCurrentBranch returns main')
  
  // Create a new branch
  const createResult = await createBranch(TEST_REPO, 'test-branch-1')
  await assert(createResult.success, 'createBranch succeeds')
  
  // Verify branch exists
  const exists = await branchExists(TEST_REPO, 'test-branch-1')
  await assert(exists, 'branchExists returns true for created branch')
  
  // Verify we're on the new branch
  const newCurrent = await getCurrentBranch(TEST_REPO)
  await assert(newCurrent === 'test-branch-1', 'now on new branch')
  
  // Checkout back to main
  const checkoutResult = await checkoutBranch(TEST_REPO, 'main')
  await assert(checkoutResult.success, 'checkoutBranch succeeds')
  
  // Verify non-existent branch
  const notExists = await branchExists(TEST_REPO, 'non-existent-branch')
  await assert(!notExists, 'branchExists returns false for non-existent branch')
  
  // Clean up test branch
  await execAsync('git branch -D test-branch-1', { cwd: TEST_REPO })
}

// ============================================
// Test: Parallel workers with non-conflicting changes
// ============================================

async function testNonConflictingParallelWorkers() {
  log('\n🔀 Test: Parallel workers with non-conflicting changes')
  
  // Create 3 worktrees for parallel workers
  const worker1 = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'nc-worker-1',
    baseBranch: 'main',
  })
  const worker2 = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'nc-worker-2',
    baseBranch: 'main',
  })
  const worker3 = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'nc-worker-3',
    baseBranch: 'main',
  })
  
  await assert(
    worker1.ok && worker2.ok && worker3.ok,
    'all worktrees created successfully'
  )
  
  // Each worker makes changes to DIFFERENT files
  if (worker1.worktree) {
    await writeFile(join(worker1.worktree.path, 'worker1-file.txt'), 'Created by worker 1')
    await commitWorktree({ worktreePath: worker1.worktree.path, message: 'Worker 1: Add new file' })
  }
  
  if (worker2.worktree) {
    await writeFile(join(worker2.worktree.path, 'worker2-file.txt'), 'Created by worker 2')
    await commitWorktree({ worktreePath: worker2.worktree.path, message: 'Worker 2: Add new file' })
  }
  
  if (worker3.worktree) {
    await writeFile(join(worker3.worktree.path, 'worker3-file.txt'), 'Created by worker 3')
    await commitWorktree({ worktreePath: worker3.worktree.path, message: 'Worker 3: Add new file' })
  }
  
  // Create a phase branch from main
  await checkoutBranch(TEST_REPO, 'main')
  const phaseBranch = `${TEST_RUN_ID}/phase-nc`
  await createBranch(TEST_REPO, phaseBranch, 'main')
  
  // Sequential merge should succeed without conflicts
  const mergeResult = await sequentialMerge(
    TEST_REPO,
    phaseBranch,
    [
      worker1.worktree!.branch,
      worker2.worktree!.branch,
      worker3.worktree!.branch,
    ]
  )
  
  await assert(mergeResult.success, 'sequential merge succeeds')
  await assert(mergeResult.mergedBranches.length === 3, 'all 3 branches merged')
  await assert(!mergeResult.conflicted, 'no conflicts detected')
  
  // Verify all files exist on the phase branch
  try {
    await access(join(TEST_REPO, 'worker1-file.txt'))
    await access(join(TEST_REPO, 'worker2-file.txt'))
    await access(join(TEST_REPO, 'worker3-file.txt'))
    pass('all worker files present after merge')
  } catch (err) {
    fail('all worker files present after merge', err)
  }
  
  // Cleanup
  await checkoutBranch(TEST_REPO, 'main')
  await execAsync(`git branch -D "${phaseBranch}"`, { cwd: TEST_REPO })
}

// ============================================
// Test: Parallel workers with conflicting changes
// ============================================

async function testConflictingParallelWorkers() {
  log('\n💥 Test: Parallel workers with conflicting changes')
  
  // Create 2 worktrees for parallel workers
  const worker1 = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'conflict-worker-1',
    baseBranch: 'main',
  })
  const worker2 = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'conflict-worker-2',
    baseBranch: 'main',
  })
  
  await assert(worker1.ok && worker2.ok, 'conflicting worktrees created')
  
  // Both workers modify the SAME file differently
  if (worker1.worktree) {
    await writeFile(
      join(worker1.worktree.path, 'utils.ts'),
      `// Utility functions - Worker 1 version

export function helper() {
  return 'worker1-implementation';
}

export function anotherHelper() {
  return 100;  // Changed by worker 1
}

export function newWorker1Function() {
  return 'worker1-only';
}
`
    )
    await commitWorktree({
      worktreePath: worker1.worktree.path,
      message: 'Worker 1: Update utils.ts'
    })
  }
  
  if (worker2.worktree) {
    await writeFile(
      join(worker2.worktree.path, 'utils.ts'),
      `// Utility functions - Worker 2 version

export function helper() {
  return 'worker2-implementation';
}

export function anotherHelper() {
  return 200;  // Changed by worker 2
}

export function newWorker2Function() {
  return 'worker2-only';
}
`
    )
    await commitWorktree({
      worktreePath: worker2.worktree.path,
      message: 'Worker 2: Update utils.ts'
    })
  }
  
  // Create a phase branch from main
  await checkoutBranch(TEST_REPO, 'main')
  const phaseBranch = `${TEST_RUN_ID}/phase-conflict`
  await createBranch(TEST_REPO, phaseBranch, 'main')
  
  // First merge should succeed
  const merge1 = await mergeBranch(TEST_REPO, worker1.worktree!.branch, {
    message: 'Merge worker 1'
  })
  await assert(merge1.success, 'first worker merge succeeds')
  await assert(!merge1.conflicted, 'first merge has no conflicts')
  
  // Second merge should CONFLICT
  const merge2 = await mergeBranch(TEST_REPO, worker2.worktree!.branch, {
    message: 'Merge worker 2'
  })
  await assert(!merge2.success, 'second worker merge fails')
  await assert(merge2.conflicted === true, 'conflict detected')
  await assert(
    merge2.conflictFiles?.includes('utils.ts'),
    'utils.ts is in conflict files'
  )
  
  // Get conflicted files using utility
  const conflictedFiles = await getConflictedFiles(TEST_REPO)
  await assert(
    conflictedFiles.includes('utils.ts'),
    'getConflictedFiles finds utils.ts'
  )
  
  // Read the file to verify conflict markers are present
  const conflictContent = await readFile(join(TEST_REPO, 'utils.ts'), 'utf-8')
  await assert(
    conflictContent.includes('<<<<<<<') && conflictContent.includes('>>>>>>>'),
    'conflict markers present in file'
  )
  
  // Abort the merge
  await abortMerge(TEST_REPO)
  
  // Verify we can read the file cleanly again
  const cleanContent = await readFile(join(TEST_REPO, 'utils.ts'), 'utf-8')
  await assert(
    !cleanContent.includes('<<<<<<<'),
    'conflict markers gone after abort'
  )
  
  // Cleanup
  await checkoutBranch(TEST_REPO, 'main')
  await execAsync(`git branch -D "${phaseBranch}"`, { cwd: TEST_REPO })
}

// ============================================
// Test: Sequential merge with partial conflict
// ============================================

async function testSequentialMergeWithConflict() {
  log('\n🔄 Test: Sequential merge stops at conflict')
  
  // Create 3 workers
  const workers = await Promise.all([
    createWorktree({ repoDir: TEST_REPO, runId: TEST_RUN_ID, workerId: 'seq-1', baseBranch: 'main' }),
    createWorktree({ repoDir: TEST_REPO, runId: TEST_RUN_ID, workerId: 'seq-2', baseBranch: 'main' }),
    createWorktree({ repoDir: TEST_REPO, runId: TEST_RUN_ID, workerId: 'seq-3', baseBranch: 'main' }),
  ])
  
  await assert(workers.every(w => w.ok), 'all sequential worktrees created')
  
  // Worker 1: Non-conflicting change
  await writeFile(join(workers[0].worktree!.path, 'seq-file-1.txt'), 'Worker 1 content')
  await commitWorktree({ worktreePath: workers[0].worktree!.path, message: 'Seq 1' })
  
  // Worker 2: Modifies shared-config.json
  await writeFile(
    join(workers[1].worktree!.path, 'shared-config.json'),
    JSON.stringify({ version: '2.0.0', settings: { debug: true, timeout: 60, newSetting: 'worker2' } }, null, 2)
  )
  await commitWorktree({ worktreePath: workers[1].worktree!.path, message: 'Seq 2' })
  
  // Worker 3: Also modifies shared-config.json (conflict with worker 2)
  await writeFile(
    join(workers[2].worktree!.path, 'shared-config.json'),
    JSON.stringify({ version: '3.0.0', settings: { debug: false, timeout: 120, worker3Setting: true } }, null, 2)
  )
  await commitWorktree({ worktreePath: workers[2].worktree!.path, message: 'Seq 3' })
  
  // Create phase branch
  await checkoutBranch(TEST_REPO, 'main')
  const phaseBranch = `${TEST_RUN_ID}/phase-seq`
  await createBranch(TEST_REPO, phaseBranch, 'main')
  
  // Sequential merge: should succeed for 1 and 2, fail at 3
  const result = await sequentialMerge(
    TEST_REPO,
    phaseBranch,
    [
      workers[0].worktree!.branch,
      workers[1].worktree!.branch,
      workers[2].worktree!.branch,
    ]
  )
  
  await assert(!result.success, 'sequential merge fails')
  await assert(result.mergedBranches.length === 2, 'first 2 branches merged successfully')
  await assert(
    result.mergedBranches.includes(workers[0].worktree!.branch),
    'worker 1 branch in merged list'
  )
  await assert(
    result.mergedBranches.includes(workers[1].worktree!.branch),
    'worker 2 branch in merged list'
  )
  await assert(
    result.failedBranch === workers[2].worktree!.branch,
    'worker 3 branch is the failed branch'
  )
  await assert(
    result.conflictFiles?.includes('shared-config.json'),
    'shared-config.json is conflicted'
  )
  
  // Abort and cleanup
  await abortMerge(TEST_REPO)
  await checkoutBranch(TEST_REPO, 'main')
  await execAsync(`git branch -D "${phaseBranch}"`, { cwd: TEST_REPO })
}

// ============================================
// Test: Manual conflict resolution flow
// ============================================

async function testManualConflictResolution() {
  log('\n🛠️ Test: Manual conflict resolution flow')
  
  // Create 2 workers with conflicts
  const worker1 = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'manual-1',
    baseBranch: 'main',
  })
  const worker2 = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'manual-2',
    baseBranch: 'main',
  })
  
  // Both modify README
  await writeFile(join(worker1.worktree!.path, 'README.md'), '# Worker 1 Version\n\nWorker 1 was here.')
  await commitWorktree({ worktreePath: worker1.worktree!.path, message: 'Worker 1 README' })
  
  await writeFile(join(worker2.worktree!.path, 'README.md'), '# Worker 2 Version\n\nWorker 2 was here.')
  await commitWorktree({ worktreePath: worker2.worktree!.path, message: 'Worker 2 README' })
  
  // Create phase branch and start merging
  await checkoutBranch(TEST_REPO, 'main')
  const phaseBranch = `${TEST_RUN_ID}/phase-manual`
  await createBranch(TEST_REPO, phaseBranch, 'main')
  
  // Merge worker 1 (success)
  await mergeBranch(TEST_REPO, worker1.worktree!.branch, { message: 'Merge worker 1' })
  
  // Merge worker 2 (conflict)
  const mergeResult = await mergeBranch(TEST_REPO, worker2.worktree!.branch, { message: 'Merge worker 2' })
  await assert(mergeResult.conflicted === true, 'merge creates conflict')
  
  // SIMULATE manual resolution: resolve the conflict
  const resolvedContent = `# Combined Version

Both workers contributed:
- Worker 1 was here.
- Worker 2 was here.
`
  await writeFile(join(TEST_REPO, 'README.md'), resolvedContent)
  
  // Stage the resolved file
  await stageAll(TEST_REPO)
  
  // Commit the merge resolution
  const commitResult = await commitMerge(TEST_REPO, 'Resolved README conflict: combined both versions')
  await assert(commitResult.success, 'merge commit succeeds')
  
  // Verify the resolved content is correct
  const finalContent = await readFile(join(TEST_REPO, 'README.md'), 'utf-8')
  await assert(
    finalContent.includes('Worker 1') && finalContent.includes('Worker 2'),
    'resolved content contains both worker contributions'
  )
  
  // Cleanup
  await checkoutBranch(TEST_REPO, 'main')
  await execAsync(`git branch -D "${phaseBranch}"`, { cwd: TEST_REPO })
}

// ============================================
// Test: Multiple files in conflict
// ============================================

async function testMultipleFileConflicts() {
  log('\n📚 Test: Multiple files in conflict')
  
  const worker1 = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'multi-1',
    baseBranch: 'main',
  })
  const worker2 = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'multi-2',
    baseBranch: 'main',
  })
  
  // Worker 1 modifies multiple files
  await writeFile(join(worker1.worktree!.path, 'README.md'), '# Worker 1 README')
  await writeFile(join(worker1.worktree!.path, 'shared-config.json'), '{"worker": 1}')
  await writeFile(join(worker1.worktree!.path, 'utils.ts'), 'export const x = 1;')
  await commitWorktree({ worktreePath: worker1.worktree!.path, message: 'Worker 1 multi' })
  
  // Worker 2 modifies the same files differently
  await writeFile(join(worker2.worktree!.path, 'README.md'), '# Worker 2 README')
  await writeFile(join(worker2.worktree!.path, 'shared-config.json'), '{"worker": 2}')
  await writeFile(join(worker2.worktree!.path, 'utils.ts'), 'export const x = 2;')
  await commitWorktree({ worktreePath: worker2.worktree!.path, message: 'Worker 2 multi' })
  
  // Setup phase branch
  await checkoutBranch(TEST_REPO, 'main')
  const phaseBranch = `${TEST_RUN_ID}/phase-multi`
  await createBranch(TEST_REPO, phaseBranch, 'main')
  
  // Merge worker 1
  await mergeBranch(TEST_REPO, worker1.worktree!.branch, { message: 'Merge worker 1' })
  
  // Merge worker 2 - should have multiple conflicts
  const mergeResult = await mergeBranch(TEST_REPO, worker2.worktree!.branch, { message: 'Merge worker 2' })
  await assert(mergeResult.conflicted === true, 'multiple conflicts detected')
  
  const conflictFiles = await getConflictedFiles(TEST_REPO)
  await assert(conflictFiles.length === 3, `detected 3 conflicted files (got ${conflictFiles.length})`)
  await assert(conflictFiles.includes('README.md'), 'README.md in conflicts')
  await assert(conflictFiles.includes('shared-config.json'), 'shared-config.json in conflicts')
  await assert(conflictFiles.includes('utils.ts'), 'utils.ts in conflicts')
  
  // Abort and cleanup
  await abortMerge(TEST_REPO)
  await checkoutBranch(TEST_REPO, 'main')
  await execAsync(`git branch -D "${phaseBranch}"`, { cwd: TEST_REPO })
}

// ============================================
// Test: Non-existent branch handling
// ============================================

async function testNonExistentBranchHandling() {
  log('\n❓ Test: Non-existent branch handling')
  
  await checkoutBranch(TEST_REPO, 'main')
  const phaseBranch = `${TEST_RUN_ID}/phase-nonexistent`
  await createBranch(TEST_REPO, phaseBranch, 'main')
  
  // Try to merge a non-existent branch
  const result = await sequentialMerge(
    TEST_REPO,
    phaseBranch,
    ['non-existent-branch-xyz']
  )
  
  await assert(!result.success, 'sequential merge fails for non-existent branch')
  await assert(
    result.error?.includes('does not exist') || result.failedBranch === 'non-existent-branch-xyz',
    'error indicates branch does not exist'
  )
  
  // Cleanup
  await checkoutBranch(TEST_REPO, 'main')
  await execAsync(`git branch -D "${phaseBranch}"`, { cwd: TEST_REPO })
}

// ============================================
// Test: Large scale parallel workers (stress test)
// ============================================

async function testLargeScaleParallelWorkers() {
  log('\n🚀 Test: Large scale parallel workers (5 workers, no conflicts)')
  
  const workerCount = 5
  const workers: Awaited<ReturnType<typeof createWorktree>>[] = []
  
  // Create workers in parallel
  const createPromises = []
  for (let i = 0; i < workerCount; i++) {
    createPromises.push(
      createWorktree({
        repoDir: TEST_REPO,
        runId: TEST_RUN_ID,
        workerId: `scale-worker-${i}`,
        baseBranch: 'main',
      })
    )
  }
  const results = await Promise.all(createPromises)
  workers.push(...results)
  
  await assert(
    workers.every(w => w.ok),
    `all ${workerCount} worktrees created successfully`
  )
  
  // Each worker creates their own file
  for (let i = 0; i < workerCount; i++) {
    const wt = workers[i].worktree!
    await writeFile(join(wt.path, `scale-file-${i}.txt`), `Content from worker ${i}\nTimestamp: ${Date.now()}`)
    await commitWorktree({ worktreePath: wt.path, message: `Worker ${i}: Add scale file` })
  }
  
  // Create phase branch
  await checkoutBranch(TEST_REPO, 'main')
  const phaseBranch = `${TEST_RUN_ID}/phase-scale`
  await createBranch(TEST_REPO, phaseBranch, 'main')
  
  // Sequential merge all
  const branches = workers.map(w => w.worktree!.branch)
  const mergeResult = await sequentialMerge(TEST_REPO, phaseBranch, branches)
  
  await assert(mergeResult.success, 'large scale merge succeeds')
  await assert(
    mergeResult.mergedBranches.length === workerCount,
    `all ${workerCount} branches merged`
  )
  
  // Verify all files exist
  let allFilesExist = true
  for (let i = 0; i < workerCount; i++) {
    try {
      await access(join(TEST_REPO, `scale-file-${i}.txt`))
    } catch {
      allFilesExist = false
      break
    }
  }
  await assert(allFilesExist, `all ${workerCount} scale files present after merge`)
  
  // Cleanup
  await checkoutBranch(TEST_REPO, 'main')
  await execAsync(`git branch -D "${phaseBranch}"`, { cwd: TEST_REPO })
}

// ============================================
// Main test runner
// ============================================

async function main() {
  log('====================================')
  log('  Conflict Resolution Test Suite')
  log('====================================')
  
  try {
    await setupTestRepo()
    
    await testBranchUtilities()
    await testBranchOperations()
    await testNonConflictingParallelWorkers()
    await testConflictingParallelWorkers()
    await testSequentialMergeWithConflict()
    await testManualConflictResolution()
    await testMultipleFileConflicts()
    await testNonExistentBranchHandling()
    await testLargeScaleParallelWorkers()
    
  } catch (err: any) {
    log(`\n❌ Test suite failed: ${err.message}`)
    console.error(err)
  } finally {
    // Cleanup all worktrees created during tests
    try {
      await cleanupRunWorktrees({
        repoDir: TEST_REPO,
        runId: TEST_RUN_ID,
        deleteBranches: true,
      })
    } catch {
      // May fail if already cleaned
    }
    await cleanupTestRepo()
  }
  
  log('\n====================================')
  log(`  Results: ${passCount} passed, ${failCount} failed`)
  log('====================================')
  
  if (failCount > 0) {
    process.exit(1)
  }
}

main()
