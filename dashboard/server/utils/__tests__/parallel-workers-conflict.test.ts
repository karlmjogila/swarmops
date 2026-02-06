/**
 * Integration test: Parallel workers with conflict resolution
 * 
 * Tests the complete flow:
 * 1. Create worktrees for multiple parallel workers
 * 2. Simulate workers making conflicting changes
 * 3. Attempt sequential merge
 * 4. Verify conflict detection
 * 5. Simulate conflict resolution
 * 6. Resume and complete merge
 */

import { mkdir, rm, writeFile, readFile } from 'fs/promises'
import { join } from 'path'
import { exec as execCallback } from 'child_process'
import { promisify } from 'util'
import {
  createWorktree,
  commitWorktree,
  cleanupRunWorktrees,
  getWorkerBranch,
} from '../worktree-manager'
import {
  mergeBranch,
  sequentialMerge,
  abortMerge,
  checkoutBranch,
  branchExists,
  getConflictedFiles,
  stageAll,
  commitMerge,
  createBranch,
} from '../conflict-resolver'

const exec = promisify(execCallback)

const TEST_DIR = '/tmp/swarmops-test-parallel-workers'
const RUN_ID = `test-${Date.now()}`

interface TestResult {
  name: string
  passed: boolean
  error?: string
  duration: number
}

const results: TestResult[] = []

async function runTest(name: string, fn: () => Promise<void>): Promise<void> {
  const start = Date.now()
  try {
    await fn()
    results.push({ name, passed: true, duration: Date.now() - start })
    console.log(`  ✅ ${name}`)
  } catch (err: any) {
    results.push({ name, passed: false, error: err.message, duration: Date.now() - start })
    console.log(`  ❌ ${name}: ${err.message}`)
  }
}

async function setupTestRepo(): Promise<string> {
  const repoDir = join(TEST_DIR, 'repo')
  
  // Clean up any previous test
  await rm(TEST_DIR, { recursive: true, force: true })
  await mkdir(repoDir, { recursive: true })
  
  // Initialize git repo
  await exec('git init', { cwd: repoDir })
  await exec('git config user.email "test@swarmops.test"', { cwd: repoDir })
  await exec('git config user.name "SwarmOps Test"', { cwd: repoDir })
  
  // Create initial files
  await writeFile(join(repoDir, 'README.md'), '# Test Project\n\nInitial commit.\n')
  await writeFile(join(repoDir, 'config.ts'), `export const config = {
  name: 'test-project',
  version: '1.0.0',
  settings: {
    debug: false,
    timeout: 30000,
  }
}
`)
  await writeFile(join(repoDir, 'utils.ts'), `export function helper() {
  return 'original'
}

export function formatData(data: string) {
  return data.trim()
}

export function validateInput(input: string) {
  return input.length > 0
}
`)

  await exec('git add -A', { cwd: repoDir })
  await exec('git commit -m "Initial commit"', { cwd: repoDir })
  
  // Create a main branch alias
  try {
    await exec('git branch -M main', { cwd: repoDir })
  } catch {
    // May already be on main
  }
  
  return repoDir
}

async function main() {
  console.log('\n🧪 Testing Parallel Workers with Conflict Resolution\n')
  console.log(`Run ID: ${RUN_ID}`)
  console.log(`Test directory: ${TEST_DIR}\n`)

  let repoDir: string

  // Setup
  console.log('📁 Setting up test repository...')
  try {
    repoDir = await setupTestRepo()
    console.log('   Repository created\n')
  } catch (err: any) {
    console.error(`Failed to setup test repo: ${err.message}`)
    process.exit(1)
  }

  // Test 1: Create worktrees for multiple workers
  console.log('📦 Test Suite 1: Worktree Creation')
  
  await runTest('Create worktree for worker-1', async () => {
    const result = await createWorktree({
      repoDir,
      runId: RUN_ID,
      workerId: 'worker-1',
      baseBranch: 'main',
    })
    if (!result.ok) throw new Error(result.error || 'Failed to create worktree')
    if (!result.worktree) throw new Error('No worktree info returned')
    
    // Verify worktree exists
    const exists = await branchExists(repoDir, result.worktree.branch)
    if (!exists) throw new Error('Worker branch not created')
  })

  await runTest('Create worktree for worker-2', async () => {
    const result = await createWorktree({
      repoDir,
      runId: RUN_ID,
      workerId: 'worker-2',
      baseBranch: 'main',
    })
    if (!result.ok) throw new Error(result.error || 'Failed to create worktree')
  })

  await runTest('Create worktree for worker-3', async () => {
    const result = await createWorktree({
      repoDir,
      runId: RUN_ID,
      workerId: 'worker-3',
      baseBranch: 'main',
    })
    if (!result.ok) throw new Error(result.error || 'Failed to create worktree')
  })

  // Test 2: Simulate worker changes (non-conflicting)
  console.log('\n📝 Test Suite 2: Non-Conflicting Changes')

  const worktree1 = `/tmp/swarmops-worktrees/${RUN_ID}/worker-1`
  const worktree2 = `/tmp/swarmops-worktrees/${RUN_ID}/worker-2`
  const worktree3 = `/tmp/swarmops-worktrees/${RUN_ID}/worker-3`

  await runTest('Worker-1 adds new file (no conflict)', async () => {
    await writeFile(join(worktree1, 'feature1.ts'), `export function feature1() {
  return 'Feature 1 implementation'
}
`)
    const result = await commitWorktree({
      worktreePath: worktree1,
      message: 'Add feature1.ts',
    })
    if (!result.ok) throw new Error(result.error || 'Failed to commit')
    if (!result.commitHash) throw new Error('No commit created')
  })

  await runTest('Worker-2 adds different file (no conflict)', async () => {
    await writeFile(join(worktree2, 'feature2.ts'), `export function feature2() {
  return 'Feature 2 implementation'
}
`)
    const result = await commitWorktree({
      worktreePath: worktree2,
      message: 'Add feature2.ts',
    })
    if (!result.ok) throw new Error(result.error || 'Failed to commit')
  })

  await runTest('Worker-3 modifies README (no conflict)', async () => {
    const currentContent = await readFile(join(worktree3, 'README.md'), 'utf-8')
    await writeFile(join(worktree3, 'README.md'), currentContent + '\n## Worker 3 Section\n\nAdded by worker 3.\n')
    const result = await commitWorktree({
      worktreePath: worktree3,
      message: 'Update README.md',
    })
    if (!result.ok) throw new Error(result.error || 'Failed to commit')
  })

  // Test 3: Merge non-conflicting branches
  console.log('\n🔀 Test Suite 3: Non-Conflicting Merge')

  const branch1 = getWorkerBranch(RUN_ID, 'worker-1')
  const branch2 = getWorkerBranch(RUN_ID, 'worker-2')
  const branch3 = getWorkerBranch(RUN_ID, 'worker-3')

  await runTest('Create phase branch from main', async () => {
    const result = await createBranch(repoDir, `swarmops/${RUN_ID}/phase-1`, 'main')
    if (!result.success) throw new Error(result.error || 'Failed to create phase branch')
  })

  await runTest('Sequential merge succeeds for non-conflicting branches', async () => {
    const result = await sequentialMerge(
      repoDir,
      `swarmops/${RUN_ID}/phase-1`,
      [branch1, branch2, branch3]
    )
    if (!result.success) throw new Error(result.error || `Merge failed at ${result.failedBranch}`)
    if (result.mergedBranches.length !== 3) throw new Error(`Expected 3 merged, got ${result.mergedBranches.length}`)
  })

  // Test 4: Create conflicting changes
  console.log('\n⚔️  Test Suite 4: Conflicting Changes')

  // Reset repo state and create new worktrees
  await cleanupRunWorktrees({ repoDir, runId: RUN_ID, deleteBranches: true })
  await checkoutBranch(repoDir, 'main')

  const RUN_ID_2 = `test-conflict-${Date.now()}`

  await runTest('Create fresh worktrees for conflict test', async () => {
    const r1 = await createWorktree({ repoDir, runId: RUN_ID_2, workerId: 'worker-a', baseBranch: 'main' })
    const r2 = await createWorktree({ repoDir, runId: RUN_ID_2, workerId: 'worker-b', baseBranch: 'main' })
    if (!r1.ok || !r2.ok) throw new Error('Failed to create worktrees')
  })

  const worktreeA = `/tmp/swarmops-worktrees/${RUN_ID_2}/worker-a`
  const worktreeB = `/tmp/swarmops-worktrees/${RUN_ID_2}/worker-b`

  await runTest('Worker-A modifies utils.ts (line 2)', async () => {
    await writeFile(join(worktreeA, 'utils.ts'), `export function helper() {
  return 'modified by worker A'
}

export function formatData(data: string) {
  return data.trim()
}

export function validateInput(input: string) {
  return input.length > 0
}
`)
    const result = await commitWorktree({
      worktreePath: worktreeA,
      message: 'Worker A: Modify helper function',
    })
    if (!result.ok) throw new Error(result.error || 'Failed to commit')
  })

  await runTest('Worker-B modifies same line in utils.ts (conflict!)', async () => {
    await writeFile(join(worktreeB, 'utils.ts'), `export function helper() {
  return 'modified by worker B'
}

export function formatData(data: string) {
  return data.trim()
}

export function validateInput(input: string) {
  return input.length > 0
}
`)
    const result = await commitWorktree({
      worktreePath: worktreeB,
      message: 'Worker B: Modify helper function differently',
    })
    if (!result.ok) throw new Error(result.error || 'Failed to commit')
  })

  // Test 5: Detect merge conflict
  console.log('\n🔍 Test Suite 5: Conflict Detection')

  const branchA = getWorkerBranch(RUN_ID_2, 'worker-a')
  const branchB = getWorkerBranch(RUN_ID_2, 'worker-b')

  await runTest('Create phase branch for conflict test', async () => {
    const result = await createBranch(repoDir, `swarmops/${RUN_ID_2}/phase-1`, 'main')
    if (!result.success) throw new Error(result.error || 'Failed to create phase branch')
  })

  await runTest('First branch merges successfully', async () => {
    await checkoutBranch(repoDir, `swarmops/${RUN_ID_2}/phase-1`)
    const result = await mergeBranch(repoDir, branchA, { message: 'Merge worker-a' })
    if (!result.success) throw new Error('First merge should succeed')
    if (result.conflicted) throw new Error('First merge should not conflict')
  })

  await runTest('Second branch causes conflict', async () => {
    const result = await mergeBranch(repoDir, branchB, { message: 'Merge worker-b' })
    if (result.success) throw new Error('Second merge should fail with conflict')
    if (!result.conflicted) throw new Error('Should detect conflict')
    if (!result.conflictFiles || result.conflictFiles.length === 0) {
      throw new Error('Should return conflicted files')
    }
    if (!result.conflictFiles.includes('utils.ts')) {
      throw new Error(`Expected utils.ts in conflict files, got: ${result.conflictFiles.join(', ')}`)
    }
  })

  await runTest('Get conflicted files list', async () => {
    const files = await getConflictedFiles(repoDir)
    if (files.length === 0) throw new Error('Should have conflicted files')
    if (!files.includes('utils.ts')) throw new Error('utils.ts should be conflicted')
  })

  // Test 6: Simulate conflict resolution
  console.log('\n🔧 Test Suite 6: Conflict Resolution')

  await runTest('Read conflict markers from file', async () => {
    const content = await readFile(join(repoDir, 'utils.ts'), 'utf-8')
    if (!content.includes('<<<<<<<')) throw new Error('Missing start conflict marker')
    if (!content.includes('=======')) throw new Error('Missing separator marker')
    if (!content.includes('>>>>>>>')) throw new Error('Missing end conflict marker')
  })

  await runTest('Resolve conflict manually (simulate AI)', async () => {
    // AI would understand both changes and merge them intelligently
    // Here we simulate that by writing a resolved version
    const resolvedContent = `export function helper() {
  // Combined changes from worker A and B
  return 'modified by both workers A and B'
}

export function formatData(data: string) {
  return data.trim()
}

export function validateInput(input: string) {
  return input.length > 0
}
`
    await writeFile(join(repoDir, 'utils.ts'), resolvedContent)
  })

  await runTest('Stage resolved files', async () => {
    await stageAll(repoDir)
  })

  await runTest('Commit merge resolution', async () => {
    const result = await commitMerge(repoDir, 'Resolved merge conflict between worker-a and worker-b')
    if (!result.success) throw new Error(result.error || 'Failed to commit merge')
  })

  await runTest('Verify no remaining conflicts', async () => {
    const files = await getConflictedFiles(repoDir)
    if (files.length !== 0) throw new Error(`Still have conflicts: ${files.join(', ')}`)
  })

  // Test 7: Verify final state
  console.log('\n✅ Test Suite 7: Final Verification')

  await runTest('Both worker changes are present in merged branch', async () => {
    const content = await readFile(join(repoDir, 'utils.ts'), 'utf-8')
    if (!content.includes('both workers A and B')) {
      throw new Error('Merged content should mention both workers')
    }
  })

  await runTest('Phase branch has all commits', async () => {
    const { stdout } = await exec('git log --oneline', { cwd: repoDir })
    if (!stdout.includes('Worker A')) throw new Error('Missing Worker A commit')
    if (!stdout.includes('Worker B')) throw new Error('Missing Worker B commit')
    if (!stdout.includes('Resolved merge')) throw new Error('Missing resolution commit')
  })

  // Cleanup
  console.log('\n🧹 Cleaning up...')
  await cleanupRunWorktrees({ repoDir, runId: RUN_ID, deleteBranches: true })
  await cleanupRunWorktrees({ repoDir, runId: RUN_ID_2, deleteBranches: true })
  await rm(TEST_DIR, { recursive: true, force: true })

  // Summary
  console.log('\n' + '='.repeat(60))
  console.log('📊 TEST SUMMARY')
  console.log('='.repeat(60))
  
  const passed = results.filter(r => r.passed).length
  const failed = results.filter(r => !r.passed).length
  const totalTime = results.reduce((sum, r) => sum + r.duration, 0)
  
  console.log(`\n   Total:  ${results.length} tests`)
  console.log(`   Passed: ${passed} ✅`)
  console.log(`   Failed: ${failed} ❌`)
  console.log(`   Time:   ${totalTime}ms`)
  
  if (failed > 0) {
    console.log('\n   Failed tests:')
    results.filter(r => !r.passed).forEach(r => {
      console.log(`   - ${r.name}: ${r.error}`)
    })
  }
  
  console.log('\n' + '='.repeat(60))
  
  if (failed > 0) {
    console.log('\n❌ Some tests failed!\n')
    process.exit(1)
  } else {
    console.log('\n✅ All tests passed!\n')
    process.exit(0)
  }
}

// Run tests
main().catch(err => {
  console.error('Test runner failed:', err)
  process.exit(1)
})
