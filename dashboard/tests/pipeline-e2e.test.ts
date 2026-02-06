/**
 * Pipeline End-to-End Tests
 * 
 * Tests the full pipeline flow: spawn → worktree → complete → merge
 * Tests the pipeline components without actually spawning OpenClaw sessions.
 * 
 * Run with: npx tsx tests/pipeline-e2e.test.ts
 */

import { mkdir, rm, writeFile, readFile, access } from 'fs/promises'
import { join } from 'path'
import { exec } from 'child_process'
import { promisify } from 'util'

// Import pipeline components
import {
  createWorktree,
  commitWorktree,
  cleanupWorktree,
  cleanupRunWorktrees,
  listRunWorktrees,
  getWorktreePath,
  getWorkerBranch,
} from '../server/utils/worktree-manager'
import {
  initPhase,
  onWorkerComplete,
  collectPhaseBranches,
  getPhaseState,
  completePhase,
  isPhaseReadyForCollection,
  getPhaseWorkerOutputs,
} from '../server/utils/phase-collector'
import {
  mergeBranch,
  checkoutBranch,
  createBranch,
  branchExists,
  sequentialMerge,
  getCurrentBranch,
  getPhaseBranch,
  getWorkerBranches,
  abortMerge,
  getConflictedFiles,
  stageAll,
  commitMerge,
} from '../server/utils/conflict-resolver'
import {
  getPhaseMergeStats,
  detectPotentialConflicts,
} from '../server/utils/phase-merger'
import {
  buildFixerPrompt,
  getPendingReview,
  listPendingReviews,
} from '../server/utils/phase-reviewer'

const execAsync = promisify(exec)

// Test configuration
const TEST_REPO_BASE = '/tmp/swarmops-e2e-test'
const TEST_REPO = join(TEST_REPO_BASE, 'test-repo')
const TEST_RUN_ID = 'e2e-test-' + Date.now()

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

// === TEST SETUP ===

async function setupTestRepo() {
  log('\n📁 Setting up test repository...')
  
  await rm(TEST_REPO_BASE, { recursive: true, force: true })
  await mkdir(TEST_REPO, { recursive: true })
  
  await execAsync('git init', { cwd: TEST_REPO })
  await execAsync('git config user.email "test@swarmops.dev"', { cwd: TEST_REPO })
  await execAsync('git config user.name "SwarmOps Test"', { cwd: TEST_REPO })
  
  // Create initial project structure
  await mkdir(join(TEST_REPO, 'src'), { recursive: true })
  await writeFile(join(TEST_REPO, 'README.md'), '# E2E Test Project\n\nInitial content.\n')
  await writeFile(join(TEST_REPO, 'package.json'), JSON.stringify({
    name: 'e2e-test-project',
    version: '1.0.0',
    scripts: { test: 'echo "test"' }
  }, null, 2))
  await writeFile(join(TEST_REPO, 'src/index.ts'), `// Main entry point
export function main() {
  console.log('Hello from E2E test')
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

// === E2E TEST: Full Pipeline Flow (without actual session spawning) ===

async function testFullPipelineFlow() {
  log('\n🚀 Test: Full pipeline flow (worktree → complete → merge)')
  
  // === STEP 1: Initialize Phase with Multiple Workers ===
  log('\n  📋 Step 1: Initialize phase with 3 parallel workers')
  
  const workerIds = ['worker-api', 'worker-ui', 'worker-tests']
  const taskIds = workerIds.map(id => `task-${id}`)
  
  const phaseState = await initPhase({
    runId: TEST_RUN_ID,
    phaseNumber: 1,
    repoDir: TEST_REPO,
    baseBranch: 'main',
    workerIds,
    taskIds,
    projectPath: TEST_REPO,
    projectName: 'e2e-test-project',
  })
  
  await assert(
    phaseState.workers.length === 3,
    'phase initialized with 3 workers'
  )
  await assert(
    phaseState.status === 'running',
    'phase status is running'
  )
  await assert(
    phaseState.projectName === 'e2e-test-project',
    'project name stored'
  )
  
  // === STEP 2: Create Worktrees for Each Worker ===
  log('\n  🌲 Step 2: Create worktrees for parallel workers')
  
  const worktrees: { workerId: string; path: string; branch: string }[] = []
  
  for (const workerId of workerIds) {
    const result = await createWorktree({
      repoDir: TEST_REPO,
      runId: TEST_RUN_ID,
      workerId,
      baseBranch: 'main',
    })
    
    await assert(result.ok === true, `worktree created for ${workerId}`)
    
    if (result.worktree) {
      worktrees.push({
        workerId,
        path: result.worktree.path,
        branch: result.worktree.branch,
      })
    }
  }
  
  await assert(worktrees.length === 3, 'all 3 worktrees created')
  
  // Verify worktrees are independent
  const paths = worktrees.map(w => w.path)
  const uniquePaths = new Set(paths)
  await assert(uniquePaths.size === 3, 'worktrees have unique paths')
  
  // Verify branches are correct
  const expectedBranches = workerIds.map(id => getWorkerBranch(TEST_RUN_ID, id))
  for (let i = 0; i < worktrees.length; i++) {
    await assert(
      worktrees[i].branch === expectedBranches[i],
      `branch correct for ${workerIds[i]}`
    )
  }
  
  // === STEP 3: Simulate Worker Making Changes ===
  log('\n  ✍️ Step 3: Simulate workers making changes in their worktrees')
  
  // Worker 1: API changes
  const apiWorktree = worktrees.find(w => w.workerId === 'worker-api')!
  await writeFile(join(apiWorktree.path, 'src/api.ts'), `// API module
export async function fetchData() {
  return { status: 'ok', data: [] }
}
`)
  const apiCommit = await commitWorktree({
    worktreePath: apiWorktree.path,
    message: 'Add API module',
    author: 'Worker API <api@swarmops.dev>',
  })
  await assert(apiCommit.ok, 'API worker commit succeeded')
  await assert(apiCommit.commitHash !== undefined, 'API commit hash returned')
  
  // Worker 2: UI changes
  const uiWorktree = worktrees.find(w => w.workerId === 'worker-ui')!
  await writeFile(join(uiWorktree.path, 'src/ui.ts'), `// UI module
export function renderApp() {
  return '<div>Hello World</div>'
}
`)
  const uiCommit = await commitWorktree({
    worktreePath: uiWorktree.path,
    message: 'Add UI module',
    author: 'Worker UI <ui@swarmops.dev>',
  })
  await assert(uiCommit.ok, 'UI worker commit succeeded')
  
  // Worker 3: Test changes
  const testWorktree = worktrees.find(w => w.workerId === 'worker-tests')!
  await writeFile(join(testWorktree.path, 'src/tests.ts'), `// Test module
export function runTests() {
  console.log('All tests passed!')
  return true
}
`)
  const testCommit = await commitWorktree({
    worktreePath: testWorktree.path,
    message: 'Add test module',
    author: 'Worker Tests <tests@swarmops.dev>',
  })
  await assert(testCommit.ok, 'Test worker commit succeeded')
  
  // === STEP 4: Mark Workers as Complete ===
  log('\n  ✅ Step 4: Mark workers as complete')
  
  for (let i = 0; i < workerIds.length; i++) {
    const workerId = workerIds[i]
    const result = await onWorkerComplete({
      runId: TEST_RUN_ID,
      phaseNumber: 1,
      workerId,
      status: 'completed',
      output: `${workerId} completed successfully`,
    })
    
    if (i < workerIds.length - 1) {
      await assert(!result.phaseComplete, `phase not complete after ${workerId}`)
    } else {
      await assert(result.phaseComplete === true, 'last worker triggers phase complete')
      await assert(result.allSucceeded === true, 'all workers succeeded')
    }
  }
  
  // Check phase ready for collection
  const currentPhaseState = await getPhaseState(TEST_RUN_ID, 1)
  await assert(
    isPhaseReadyForCollection(currentPhaseState!),
    'phase is ready for collection'
  )
  
  // Get worker outputs
  const outputs = getPhaseWorkerOutputs(currentPhaseState!)
  await assert(
    outputs.includes('worker-api') && outputs.includes('worker-ui') && outputs.includes('worker-tests'),
    'worker outputs captured'
  )
  
  // === STEP 5: Collect Phase Branches ===
  log('\n  📦 Step 5: Collect phase branches')
  
  const collectResult = await collectPhaseBranches({
    runId: TEST_RUN_ID,
    phaseNumber: 1,
  })
  
  await assert(collectResult.success === true, 'branch collection succeeded')
  await assert(collectResult.workerBranches?.length === 3, 'collected 3 worker branches')
  await assert(collectResult.phaseBranch !== undefined, 'phase branch created')
  
  const expectedPhaseBranch = getPhaseBranch(TEST_RUN_ID, 1)
  await assert(
    collectResult.phaseBranch === expectedPhaseBranch,
    'phase branch name correct'
  )
  
  // === STEP 6: Sequential Merge of Phase Branches ===
  log('\n  🔀 Step 6: Sequential merge of phase branches')
  
  const { phaseBranch, workerBranches } = collectResult as {
    phaseBranch: string
    workerBranches: string[]
  }
  
  // Checkout phase branch
  await checkoutBranch(TEST_REPO, phaseBranch)
  
  // Sequential merge all worker branches
  const mergeResult = await sequentialMerge(
    TEST_REPO,
    phaseBranch,
    workerBranches
  )
  
  await assert(mergeResult.success === true, 'sequential merge succeeded')
  await assert(mergeResult.mergedBranches.length === 3, 'all 3 branches merged')
  await assert(!mergeResult.conflicted, 'no conflicts detected')
  
  // === STEP 7: Verify Merged Result ===
  log('\n  🔍 Step 7: Verify merged result has all changes')
  
  // Check all files exist in the merged result
  try {
    await access(join(TEST_REPO, 'src/api.ts'))
    pass('api.ts exists in merged branch')
  } catch {
    fail('api.ts exists in merged branch')
  }
  
  try {
    await access(join(TEST_REPO, 'src/ui.ts'))
    pass('ui.ts exists in merged branch')
  } catch {
    fail('ui.ts exists in merged branch')
  }
  
  try {
    await access(join(TEST_REPO, 'src/tests.ts'))
    pass('tests.ts exists in merged branch')
  } catch {
    fail('tests.ts exists in merged branch')
  }
  
  // Verify file contents
  const apiContent = await readFile(join(TEST_REPO, 'src/api.ts'), 'utf-8')
  await assert(apiContent.includes('fetchData'), 'api.ts has correct content')
  
  const uiContent = await readFile(join(TEST_REPO, 'src/ui.ts'), 'utf-8')
  await assert(uiContent.includes('renderApp'), 'ui.ts has correct content')
  
  const testContent = await readFile(join(TEST_REPO, 'src/tests.ts'), 'utf-8')
  await assert(testContent.includes('runTests'), 'tests.ts has correct content')
  
  // === STEP 8: Mark Phase Complete ===
  log('\n  ✨ Step 8: Complete phase')
  
  await completePhase({ runId: TEST_RUN_ID, phaseNumber: 1 })
  
  const completedPhase = await getPhaseState(TEST_RUN_ID, 1)
  await assert(completedPhase?.status === 'completed', 'phase status is completed')
  await assert(completedPhase?.completedAt !== undefined, 'completedAt timestamp set')
  
  // Switch back to main
  await checkoutBranch(TEST_REPO, 'main')
  
  // === STEP 9: Cleanup Worktrees ===
  log('\n  🗑️ Step 9: Cleanup worktrees')
  
  const cleanupResult = await cleanupRunWorktrees({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    deleteBranches: false, // Keep branches for inspection
  })
  
  await assert(cleanupResult.ok === true, 'worktree cleanup succeeded')
  
  // Verify worktrees are gone
  const remaining = await listRunWorktrees({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
  })
  
  await assert(
    remaining.worktrees?.length === 0,
    'all worktrees cleaned up'
  )
}

// === E2E TEST: Conflict Detection and Resolution Flow ===

async function testConflictResolutionFlow() {
  log('\n💥 Test: Conflict detection and resolution flow')
  
  const conflictRunId = `conflict-test-${Date.now()}`
  
  // Initialize phase with 2 workers that will conflict
  const workerIds = ['conflict-worker-1', 'conflict-worker-2']
  const taskIds = workerIds.map(id => `task-${id}`)
  
  await initPhase({
    runId: conflictRunId,
    phaseNumber: 1,
    repoDir: TEST_REPO,
    baseBranch: 'main',
    workerIds,
    taskIds,
  })
  
  // Create worktrees
  const wt1 = await createWorktree({
    repoDir: TEST_REPO,
    runId: conflictRunId,
    workerId: 'conflict-worker-1',
    baseBranch: 'main',
  })
  
  const wt2 = await createWorktree({
    repoDir: TEST_REPO,
    runId: conflictRunId,
    workerId: 'conflict-worker-2',
    baseBranch: 'main',
  })
  
  await assert(wt1.ok && wt2.ok, 'conflict worktrees created')
  
  // Both workers modify the SAME file differently
  await writeFile(
    join(wt1.worktree!.path, 'README.md'),
    '# Modified by Worker 1\n\nWorker 1 changes.'
  )
  await commitWorktree({
    worktreePath: wt1.worktree!.path,
    message: 'Worker 1: Modify README',
  })
  
  await writeFile(
    join(wt2.worktree!.path, 'README.md'),
    '# Modified by Worker 2\n\nWorker 2 changes.'
  )
  await commitWorktree({
    worktreePath: wt2.worktree!.path,
    message: 'Worker 2: Modify README',
  })
  
  pass('both workers modified same file')
  
  // Mark workers complete
  await onWorkerComplete({
    runId: conflictRunId,
    phaseNumber: 1,
    workerId: 'conflict-worker-1',
    status: 'completed',
  })
  
  await onWorkerComplete({
    runId: conflictRunId,
    phaseNumber: 1,
    workerId: 'conflict-worker-2',
    status: 'completed',
  })
  
  // Collect branches
  const collectResult = await collectPhaseBranches({
    runId: conflictRunId,
    phaseNumber: 1,
  })
  
  await assert(collectResult.success, 'conflict branches collected')
  
  // Sequential merge - should detect conflict
  const { phaseBranch, workerBranches } = collectResult as {
    phaseBranch: string
    workerBranches: string[]
  }
  
  await checkoutBranch(TEST_REPO, phaseBranch)
  
  const mergeResult = await sequentialMerge(
    TEST_REPO,
    phaseBranch,
    workerBranches
  )
  
  await assert(!mergeResult.success, 'merge fails due to conflict')
  await assert(
    mergeResult.conflictFiles && mergeResult.conflictFiles.length > 0,
    'conflict detected (conflictFiles present)'
  )
  await assert(
    mergeResult.conflictFiles?.includes('README.md'),
    'README.md identified as conflicted file'
  )
  await assert(
    mergeResult.failedBranch !== undefined,
    'failed branch identified'
  )
  await assert(
    mergeResult.mergedBranches.length >= 1,
    'first branch merged before conflict'
  )
  
  // Get conflicted files
  const conflicted = await getConflictedFiles(TEST_REPO)
  await assert(
    conflicted.includes('README.md'),
    'getConflictedFiles returns README.md'
  )
  
  // Abort merge and cleanup
  await abortMerge(TEST_REPO)
  await checkoutBranch(TEST_REPO, 'main')
  
  await cleanupRunWorktrees({
    repoDir: TEST_REPO,
    runId: conflictRunId,
    deleteBranches: true,
  })
}

// === E2E TEST: Manual Conflict Resolution Flow ===

async function testManualConflictResolution() {
  log('\n🛠️ Test: Manual conflict resolution and merge commit')
  
  const resolveRunId = `resolve-test-${Date.now()}`
  
  // Setup 2 conflicting workers
  await initPhase({
    runId: resolveRunId,
    phaseNumber: 1,
    repoDir: TEST_REPO,
    baseBranch: 'main',
    workerIds: ['resolve-w1', 'resolve-w2'],
    taskIds: ['task-1', 'task-2'],
  })
  
  const wt1 = await createWorktree({
    repoDir: TEST_REPO,
    runId: resolveRunId,
    workerId: 'resolve-w1',
    baseBranch: 'main',
  })
  
  const wt2 = await createWorktree({
    repoDir: TEST_REPO,
    runId: resolveRunId,
    workerId: 'resolve-w2',
    baseBranch: 'main',
  })
  
  // Create conflicting changes
  await writeFile(join(wt1.worktree!.path, 'config.json'), '{"version": 1}')
  await commitWorktree({ worktreePath: wt1.worktree!.path, message: 'W1: config' })
  
  await writeFile(join(wt2.worktree!.path, 'config.json'), '{"version": 2}')
  await commitWorktree({ worktreePath: wt2.worktree!.path, message: 'W2: config' })
  
  // Complete workers
  await onWorkerComplete({ runId: resolveRunId, phaseNumber: 1, workerId: 'resolve-w1', status: 'completed' })
  await onWorkerComplete({ runId: resolveRunId, phaseNumber: 1, workerId: 'resolve-w2', status: 'completed' })
  
  // Collect and start merge
  const collect = await collectPhaseBranches({ runId: resolveRunId, phaseNumber: 1 })
  const { phaseBranch, workerBranches } = collect as { phaseBranch: string; workerBranches: string[] }
  
  await checkoutBranch(TEST_REPO, phaseBranch)
  
  // Merge first branch (succeeds)
  const merge1 = await mergeBranch(TEST_REPO, workerBranches[0], { message: 'Merge W1' })
  await assert(merge1.success, 'first merge succeeds')
  
  // Merge second branch (conflicts)
  const merge2 = await mergeBranch(TEST_REPO, workerBranches[1], { message: 'Merge W2' })
  await assert(merge2.conflicted === true, 'second merge conflicts')
  
  // Manually resolve conflict
  await writeFile(join(TEST_REPO, 'config.json'), '{"version": 3, "resolved": true}')
  await stageAll(TEST_REPO)
  
  // Commit the merge resolution
  const commitResult = await commitMerge(TEST_REPO, 'Resolved config conflict')
  await assert(commitResult.success, 'merge commit succeeds')
  
  // Verify resolved content
  const resolved = await readFile(join(TEST_REPO, 'config.json'), 'utf-8')
  await assert(resolved.includes('"resolved": true'), 'conflict was resolved')
  
  // Cleanup
  await checkoutBranch(TEST_REPO, 'main')
  await cleanupRunWorktrees({ repoDir: TEST_REPO, runId: resolveRunId, deleteBranches: true })
}

// === E2E TEST: Worker Failure and Phase Continuation ===

async function testWorkerFailureFlow() {
  log('\n⚠️ Test: Worker failure and phase continuation')
  
  const failRunId = `fail-test-${Date.now()}`
  
  // Initialize phase with 3 workers, one will fail
  const workerIds = ['success-1', 'failing-worker', 'success-2']
  const taskIds = workerIds.map(id => `task-${id}`)
  
  await initPhase({
    runId: failRunId,
    phaseNumber: 1,
    repoDir: TEST_REPO,
    baseBranch: 'main',
    workerIds,
    taskIds,
  })
  
  // Create worktrees only for successful workers
  for (const workerId of ['success-1', 'success-2']) {
    const wt = await createWorktree({
      repoDir: TEST_REPO,
      runId: failRunId,
      workerId,
      baseBranch: 'main',
    })
    
    if (wt.ok && wt.worktree) {
      await writeFile(
        join(wt.worktree.path, `${workerId}.txt`),
        `Content from ${workerId}`
      )
      await commitWorktree({
        worktreePath: wt.worktree.path,
        message: `${workerId}: Add file`,
      })
    }
  }
  
  // Mark successful workers complete
  await onWorkerComplete({
    runId: failRunId,
    phaseNumber: 1,
    workerId: 'success-1',
    status: 'completed',
    output: 'Success 1 done',
  })
  
  // Mark one worker as failed
  const failResult = await onWorkerComplete({
    runId: failRunId,
    phaseNumber: 1,
    workerId: 'failing-worker',
    status: 'failed',
    error: 'Simulated failure for testing',
  })
  
  await assert(!failResult.phaseComplete, 'phase not complete after failure')
  await assert(!failResult.allSucceeded, 'not all workers succeeded')
  
  // Mark last worker complete
  const lastResult = await onWorkerComplete({
    runId: failRunId,
    phaseNumber: 1,
    workerId: 'success-2',
    status: 'completed',
    output: 'Success 2 done',
  })
  
  await assert(lastResult.phaseComplete, 'phase complete after last worker')
  await assert(!lastResult.allSucceeded, 'not all succeeded (one failed)')
  
  // Get phase state to verify
  const phaseState = await getPhaseState(failRunId, 1)
  await assert(phaseState !== null, 'phase state exists')
  
  const failedWorkers = phaseState!.workers.filter(w => w.status === 'failed')
  await assert(failedWorkers.length === 1, 'one worker marked as failed')
  await assert(
    failedWorkers[0].workerId === 'failing-worker',
    'correct worker marked as failed'
  )
  await assert(
    failedWorkers[0].error === 'Simulated failure for testing',
    'failure error recorded'
  )
  
  // Try to collect - should fail due to failed worker
  const collectResult = await collectPhaseBranches({
    runId: failRunId,
    phaseNumber: 1,
  })
  
  await assert(!collectResult.success, 'collection fails due to failed worker')
  await assert(
    collectResult.error?.includes('failed'),
    'error mentions failed workers'
  )
  
  // Cleanup
  await cleanupRunWorktrees({
    repoDir: TEST_REPO,
    runId: failRunId,
    deleteBranches: true,
  })
}

// === E2E TEST: Phase Merge Statistics and Conflict Detection ===

async function testPhaseMergeStatsAndConflictPrediction() {
  log('\n📊 Test: Phase merge statistics and potential conflict detection')
  
  const statsRunId = `stats-test-${Date.now()}`
  
  // Initialize phase with 5 workers
  const workerIds = ['stat-w1', 'stat-w2', 'stat-w3', 'stat-w4', 'stat-w5']
  const taskIds = workerIds.map(id => `task-${id}`)
  
  await initPhase({
    runId: statsRunId,
    phaseNumber: 1,
    repoDir: TEST_REPO,
    baseBranch: 'main',
    workerIds,
    taskIds,
  })
  
  // Create worktrees and commits for all workers
  // Make w1 and w5 modify the same file to create potential conflict
  for (const workerId of workerIds) {
    const wt = await createWorktree({
      repoDir: TEST_REPO,
      runId: statsRunId,
      workerId,
      baseBranch: 'main',
    })
    
    if (wt.ok && wt.worktree) {
      // Workers 1 and 5 both modify shared.txt
      if (workerId === 'stat-w1' || workerId === 'stat-w5') {
        await writeFile(
          join(wt.worktree.path, 'shared.txt'),
          `Content from ${workerId}`
        )
      }
      // All workers create unique files
      await writeFile(
        join(wt.worktree.path, `${workerId}.txt`),
        `Content from ${workerId}`
      )
      await commitWorktree({
        worktreePath: wt.worktree.path,
        message: `${workerId}: Add files`,
      })
    }
    
    await onWorkerComplete({
      runId: statsRunId,
      phaseNumber: 1,
      workerId,
      status: 'completed',
    })
  }
  
  // Collect branches
  const collect = await collectPhaseBranches({
    runId: statsRunId,
    phaseNumber: 1,
  })
  
  await assert(collect.success, 'branches collected for stats')
  
  // Get merge stats
  const stats = await getPhaseMergeStats({
    runId: statsRunId,
    phaseNumber: 1,
  })
  
  await assert(stats.totalBranches === 5, 'total branches is 5')
  await assert(stats.branchesWithChanges === 5, 'all 5 branches have changes')
  await assert(
    stats.estimatedConflictRisk === 'medium' || stats.estimatedConflictRisk === 'high',
    'conflict risk assessed correctly for 5 branches'
  )
  
  // Detect potential conflicts
  const potentialConflicts = await detectPotentialConflicts({
    repoDir: TEST_REPO,
    branches: collect.workerBranches!,
    baseBranch: 'main',
  })
  
  await assert(potentialConflicts.length > 0, 'potential conflicts detected')
  
  const sharedConflict = potentialConflicts.find(c => c.file === 'shared.txt')
  await assert(sharedConflict !== undefined, 'shared.txt identified as potential conflict')
  await assert(
    sharedConflict?.branches.length === 2,
    'shared.txt modified by 2 branches'
  )
  
  // Cleanup
  await cleanupRunWorktrees({
    repoDir: TEST_REPO,
    runId: statsRunId,
    deleteBranches: true,
  })
}

// === E2E TEST: Review Prompt Building ===

async function testReviewPromptBuilding() {
  log('\n📝 Test: Review and fixer prompt building')
  
  // Test fixer prompt building
  const fixerPrompt = buildFixerPrompt({
    runId: 'test-run',
    phaseName: 'test-phase',
    phaseNumber: 1,
    projectDir: '/test/project',
    phaseBranch: 'swarmops/test/phase-1',
    fixInstructions: 'Fix the API endpoint to handle errors properly',
    reviewComments: 'Missing error handling in fetchData function',
  })
  
  await assert(fixerPrompt.includes('SWARMOPS FIXER'), 'fixer prompt has header')
  await assert(fixerPrompt.includes('test-phase'), 'fixer prompt has phase name')
  await assert(fixerPrompt.includes('Fix the API endpoint'), 'fixer prompt has instructions')
  await assert(fixerPrompt.includes('Missing error handling'), 'fixer prompt has review comments')
  await assert(fixerPrompt.includes('fix-complete'), 'fixer prompt has completion webhook')
  
  // Test pending reviews tracking
  const pending = listPendingReviews()
  await assert(Array.isArray(pending), 'listPendingReviews returns array')
  
  // Test getPendingReview for non-existent session
  const notFound = getPendingReview('non-existent-session')
  await assert(notFound === undefined, 'non-existent review returns undefined')
}

// === E2E TEST: Utility Functions ===

async function testUtilityFunctions() {
  log('\n🔧 Test: Utility functions')
  
  // Test getWorkerBranch
  const branch = getWorkerBranch('test-run', 'worker-1')
  await assert(
    branch === 'swarmops/test-run/worker-worker-1',
    'getWorkerBranch returns correct format'
  )
  
  // Test getPhaseBranch
  const phaseBranch = getPhaseBranch('test-run', 2)
  await assert(
    phaseBranch === 'swarmops/test-run/phase-2',
    'getPhaseBranch returns correct format'
  )
  
  // Test getWorkerBranches
  const branches = getWorkerBranches('test-run', ['w1', 'w2', 'w3'])
  await assert(branches.length === 3, 'getWorkerBranches returns correct count')
  await assert(
    branches[0] === 'swarmops/test-run/worker-w1',
    'first branch correct'
  )
  
  // Test getWorktreePath
  const wtPath = getWorktreePath('test-run', 'worker-1')
  await assert(
    wtPath === '/tmp/swarmops-worktrees/test-run/worker-1',
    'getWorktreePath returns correct format'
  )
}

// === MAIN TEST RUNNER ===

async function main() {
  log('====================================')
  log('  Pipeline E2E Test Suite')
  log('====================================')
  
  try {
    await setupTestRepo()
    
    // Run all E2E tests
    await testUtilityFunctions()
    await testFullPipelineFlow()
    await testConflictResolutionFlow()
    await testManualConflictResolution()
    await testWorkerFailureFlow()
    await testPhaseMergeStatsAndConflictPrediction()
    await testReviewPromptBuilding()
    
  } catch (err: any) {
    log(`\n❌ Test suite failed: ${err.message}`)
    console.error(err)
    failCount++
  } finally {
    // Cleanup any remaining test artifacts
    try {
      await cleanupTestRepo()
    } catch {
      // May fail if already cleaned
    }
  }
  
  log('\n====================================')
  log(`  Results: ${passCount} passed, ${failCount} failed`)
  log('====================================')
  
  if (failCount > 0) {
    process.exit(1)
  }
}

main()
