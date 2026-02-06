/**
 * Worktree Manager Tests
 * 
 * Tests worktree creation, commit, and cleanup functionality.
 * Run with: npx tsx tests/worktree-manager.test.ts
 */

import { mkdir, rm, writeFile, readFile, access } from 'fs/promises'
import { join } from 'path'
import { exec } from 'child_process'
import { promisify } from 'util'
import {
  createWorktree,
  commitWorktree,
  cleanupWorktree,
  cleanupRunWorktrees,
  listRunWorktrees,
  getWorktreePath,
  getWorkerBranch,
} from '../server/utils/worktree-manager'

const execAsync = promisify(exec)

const TEST_REPO_BASE = '/tmp/swarmops-worktree-test'
const TEST_REPO = join(TEST_REPO_BASE, 'test-repo')
const TEST_RUN_ID = 'test-run-' + Date.now()

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
  
  // Clean up any existing test directory
  await rm(TEST_REPO_BASE, { recursive: true, force: true })
  await mkdir(TEST_REPO, { recursive: true })
  
  // Initialize git repo
  await execAsync('git init', { cwd: TEST_REPO })
  await execAsync('git config user.email "test@example.com"', { cwd: TEST_REPO })
  await execAsync('git config user.name "Test User"', { cwd: TEST_REPO })
  
  // Create initial file and commit
  await writeFile(join(TEST_REPO, 'README.md'), '# Test Repository\n')
  await execAsync('git add -A', { cwd: TEST_REPO })
  await execAsync('git commit -m "Initial commit"', { cwd: TEST_REPO })
  
  // Ensure we're on main branch
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
  // Also clean up any worktrees we created
  await rm(join('/tmp/swarmops-worktrees', TEST_RUN_ID), { recursive: true, force: true })
  log('  Cleanup complete')
}

async function testWorktreePaths() {
  log('\n📍 Test: Worktree path generation')
  
  const path = getWorktreePath('run-123', 'worker-abc')
  await assert(
    path === '/tmp/swarmops-worktrees/run-123/worker-abc',
    'getWorktreePath returns correct path'
  )
  
  const branch = getWorkerBranch('run-123', 'worker-abc')
  await assert(
    branch === 'swarmops/run-123/worker-worker-abc',
    'getWorkerBranch returns correct branch name'
  )
}

async function testCreateWorktree() {
  log('\n🌲 Test: Worktree creation')
  
  const result = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'worker-1',
    baseBranch: 'main',
  })
  
  await assert(result.ok === true, 'createWorktree succeeds')
  await assert(result.worktree !== undefined, 'worktree info returned')
  
  if (result.worktree) {
    await assert(
      result.worktree.runId === TEST_RUN_ID,
      'worktree has correct runId'
    )
    await assert(
      result.worktree.workerId === 'worker-1',
      'worktree has correct workerId'
    )
    await assert(
      result.worktree.branch === `swarmops/${TEST_RUN_ID}/worker-worker-1`,
      'worktree has correct branch'
    )
    
    // Verify the worktree directory exists
    try {
      await access(result.worktree.path)
      pass('worktree directory exists')
    } catch {
      fail('worktree directory exists')
    }
    
    // Verify it's a valid git worktree
    try {
      const { stdout } = await execAsync('git status', { cwd: result.worktree.path })
      await assert(stdout.includes('nothing to commit'), 'worktree is clean git repo')
    } catch (err) {
      fail('worktree is valid git directory', err)
    }
    
    // Verify branch was created
    try {
      const { stdout: branch } = await execAsync('git rev-parse --abbrev-ref HEAD', { cwd: result.worktree.path })
      await assert(
        branch.trim() === result.worktree.branch,
        'worktree is on correct branch'
      )
    } catch (err) {
      fail('worktree is on correct branch', err)
    }
  }
  
  return result.worktree
}

async function testCreateMultipleWorktrees() {
  log('\n🌲🌲 Test: Multiple worktree creation')
  
  const result2 = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'worker-2',
    baseBranch: 'main',
  })
  
  const result3 = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'worker-3',
    baseBranch: 'main',
  })
  
  await assert(result2.ok && result3.ok, 'multiple worktrees created successfully')
  
  // Verify they're independent
  if (result2.worktree && result3.worktree) {
    await assert(
      result2.worktree.path !== result3.worktree.path,
      'worktrees have different paths'
    )
    await assert(
      result2.worktree.branch !== result3.worktree.branch,
      'worktrees have different branches'
    )
  }
}

async function testCommitWorktree(worktreePath?: string) {
  log('\n💾 Test: Worktree commit')
  
  if (!worktreePath) {
    fail('worktree path required for commit test')
    return
  }
  
  // Create a new file in the worktree
  const testFile = join(worktreePath, 'test-file.txt')
  await writeFile(testFile, 'Hello from worker!\n')
  
  // Commit the changes
  const commitResult = await commitWorktree({
    worktreePath,
    message: 'Test commit from worker',
    author: 'Test Worker <worker@test.com>',
  })
  
  await assert(commitResult.ok === true, 'commitWorktree succeeds')
  await assert(commitResult.commitHash !== undefined, 'commit hash returned')
  
  if (commitResult.commitHash) {
    // Verify commit exists
    try {
      const { stdout } = await execAsync(`git log -1 --format=%H ${commitResult.commitHash}`, { cwd: worktreePath })
      await assert(
        stdout.trim() === commitResult.commitHash,
        'commit hash is valid'
      )
    } catch (err) {
      fail('commit hash is valid', err)
    }
    
    // Verify commit message
    try {
      const { stdout: msg } = await execAsync(`git log -1 --format=%s`, { cwd: worktreePath })
      await assert(
        msg.trim() === 'Test commit from worker',
        'commit has correct message'
      )
    } catch (err) {
      fail('commit has correct message', err)
    }
  }
  
  // Test commit with no changes
  const noChangeResult = await commitWorktree({
    worktreePath,
    message: 'This should not create a commit',
  })
  
  await assert(noChangeResult.ok === true, 'commit with no changes succeeds')
  await assert(noChangeResult.commitHash === undefined, 'no commit hash when no changes')
}

async function testListWorktrees() {
  log('\n📋 Test: List worktrees')
  
  const result = await listRunWorktrees({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
  })
  
  await assert(result.ok === true, 'listRunWorktrees succeeds')
  await assert(result.worktrees !== undefined, 'worktrees array returned')
  
  if (result.worktrees) {
    await assert(
      result.worktrees.length >= 3,
      `found ${result.worktrees.length} worktrees (expected >= 3)`
    )
    
    const workerIds = result.worktrees.map(w => w.workerId)
    await assert(
      workerIds.includes('worker-1') && workerIds.includes('worker-2') && workerIds.includes('worker-3'),
      'all expected workers found'
    )
  }
}

async function testCleanupSingleWorktree() {
  log('\n🗑️ Test: Single worktree cleanup')
  
  const worktreePath = getWorktreePath(TEST_RUN_ID, 'worker-3')
  
  // Verify worktree exists before cleanup
  try {
    await access(worktreePath)
    pass('worktree exists before cleanup')
  } catch {
    fail('worktree exists before cleanup')
    return
  }
  
  const result = await cleanupWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'worker-3',
    deleteBranch: true,
  })
  
  await assert(result.ok === true, 'cleanupWorktree succeeds')
  
  // Verify worktree directory is gone
  try {
    await access(worktreePath)
    fail('worktree directory removed')
  } catch {
    pass('worktree directory removed')
  }
  
  // Verify branch is deleted
  try {
    const { stdout: branches } = await execAsync('git branch', { cwd: TEST_REPO })
    const branchName = getWorkerBranch(TEST_RUN_ID, 'worker-3')
    await assert(
      !branches.includes(branchName),
      'branch deleted'
    )
  } catch (err) {
    fail('branch deleted', err)
  }
}

async function testCleanupAllWorktrees() {
  log('\n🗑️🗑️ Test: Cleanup all run worktrees')
  
  const result = await cleanupRunWorktrees({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    deleteBranches: true,
  })
  
  await assert(result.ok === true, 'cleanupRunWorktrees succeeds')
  
  // Verify run directory is gone
  const runDir = join('/tmp/swarmops-worktrees', TEST_RUN_ID)
  try {
    await access(runDir)
    fail('run directory removed')
  } catch {
    pass('run directory removed')
  }
  
  // Verify no worktrees remain for this run
  const listResult = await listRunWorktrees({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
  })
  
  await assert(
    listResult.ok && listResult.worktrees?.length === 0,
    'no worktrees remain after cleanup'
  )
  
  // Verify all branches are cleaned up
  try {
    const { stdout: branches } = await execAsync('git branch', { cwd: TEST_REPO })
    const prefix = `swarmops/${TEST_RUN_ID}/`
    await assert(
      !branches.includes(prefix),
      'all run branches deleted'
    )
  } catch (err) {
    fail('all run branches deleted', err)
  }
}

async function testEdgeCases() {
  log('\n⚠️ Test: Edge cases')
  
  // Test with non-existent repo
  const badRepoResult = await createWorktree({
    repoDir: '/nonexistent/repo',
    runId: 'test',
    workerId: 'worker',
  })
  await assert(
    badRepoResult.ok === false && badRepoResult.error?.includes('Not a git repository'),
    'createWorktree fails for non-existent repo'
  )
  
  // Test cleanup of non-existent worktree (should succeed gracefully)
  const cleanupResult = await cleanupWorktree({
    repoDir: TEST_REPO,
    runId: 'nonexistent-run',
    workerId: 'nonexistent-worker',
  })
  await assert(cleanupResult.ok === true, 'cleanup of non-existent worktree succeeds')
  
  // Test commit on non-existent worktree
  const commitResult = await commitWorktree({
    worktreePath: '/nonexistent/worktree',
    message: 'test',
  })
  await assert(
    commitResult.ok === false && commitResult.error?.includes('not found'),
    'commit on non-existent worktree fails gracefully'
  )
}

async function testRecreateWorktree() {
  log('\n🔄 Test: Recreate existing worktree')
  
  // Create a worktree
  const result1 = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'worker-recreate',
    baseBranch: 'main',
  })
  await assert(result1.ok === true, 'first worktree creation succeeds')
  
  // Create a file in it
  if (result1.worktree) {
    await writeFile(join(result1.worktree.path, 'file1.txt'), 'content')
  }
  
  // Recreate the same worktree (should replace it)
  const result2 = await createWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'worker-recreate',
    baseBranch: 'main',
  })
  await assert(result2.ok === true, 'recreate worktree succeeds')
  
  // Verify the old file is gone (fresh worktree)
  if (result2.worktree) {
    try {
      await access(join(result2.worktree.path, 'file1.txt'))
      fail('recreated worktree is fresh (old file gone)')
    } catch {
      pass('recreated worktree is fresh (old file gone)')
    }
  }
  
  // Cleanup
  await cleanupWorktree({
    repoDir: TEST_REPO,
    runId: TEST_RUN_ID,
    workerId: 'worker-recreate',
    deleteBranch: true,
  })
}

async function main() {
  log('====================================')
  log('  Worktree Manager Test Suite')
  log('====================================')
  
  try {
    await setupTestRepo()
    
    await testWorktreePaths()
    const worktree = await testCreateWorktree()
    await testCreateMultipleWorktrees()
    await testCommitWorktree(worktree?.path)
    await testListWorktrees()
    await testCleanupSingleWorktree()
    await testCleanupAllWorktrees()
    await testEdgeCases()
    await testRecreateWorktree()
    
  } catch (err: any) {
    log(`\n❌ Test suite failed: ${err.message}`)
    console.error(err)
  } finally {
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
