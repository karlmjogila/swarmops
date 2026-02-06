/**
 * Test script for worktree-manager.ts
 * 
 * Tests worktree creation, commits, and cleanup operations
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
} from './worktree-manager'

const execAsync = promisify(exec)

const TEST_REPO_DIR = '/tmp/swarmops-worktree-test-repo'
const TEST_RUN_ID = 'test-run-' + Date.now()

async function setupTestRepo(): Promise<void> {
  // Clean up any existing test repo
  await rm(TEST_REPO_DIR, { recursive: true, force: true })
  
  // Create fresh test repo
  await mkdir(TEST_REPO_DIR, { recursive: true })
  await execAsync('git init -b main', { cwd: TEST_REPO_DIR })
  await execAsync('git config user.email "test@swarmops.local"', { cwd: TEST_REPO_DIR })
  await execAsync('git config user.name "SwarmOps Test"', { cwd: TEST_REPO_DIR })
  
  // Create initial commit
  await writeFile(join(TEST_REPO_DIR, 'README.md'), '# Test Repo\n')
  await execAsync('git add -A && git commit -m "Initial commit"', { cwd: TEST_REPO_DIR })
  
  console.log('✅ Test repo created at', TEST_REPO_DIR)
}

async function cleanupTestRepo(): Promise<void> {
  await rm(TEST_REPO_DIR, { recursive: true, force: true })
  console.log('✅ Test repo cleaned up')
}

async function testWorktreeCreation(): Promise<boolean> {
  console.log('\n📁 Testing worktree creation...')
  
  const result = await createWorktree({
    repoDir: TEST_REPO_DIR,
    runId: TEST_RUN_ID,
    workerId: '1',
    baseBranch: 'main',
  })

  if (!result.ok || !result.worktree) {
    console.error('❌ Worktree creation failed:', result.error)
    return false
  }

  // Verify worktree exists
  try {
    await access(result.worktree.path)
    await access(join(result.worktree.path, '.git'))
  } catch {
    console.error('❌ Worktree directory does not exist')
    return false
  }

  // Verify branch was created
  const expectedBranch = getWorkerBranch(TEST_RUN_ID, '1')
  const { stdout: currentBranch } = await execAsync(
    'git rev-parse --abbrev-ref HEAD',
    { cwd: result.worktree.path }
  )
  
  if (currentBranch.trim() !== expectedBranch) {
    console.error(`❌ Wrong branch: expected ${expectedBranch}, got ${currentBranch.trim()}`)
    return false
  }

  console.log('✅ Worktree created:', result.worktree.path)
  console.log('✅ Branch:', result.worktree.branch)
  return true
}

async function testWorktreeCommit(): Promise<boolean> {
  console.log('\n📝 Testing worktree commit...')
  
  const worktreePath = getWorktreePath(TEST_RUN_ID, '1')
  
  // Create a test file
  await writeFile(join(worktreePath, 'test-file.txt'), 'Hello from worker-1\n')
  
  const result = await commitWorktree({
    worktreePath,
    message: 'Test commit from worker-1',
    author: 'Worker 1 <worker1@swarmops.local>',
  })

  if (!result.ok) {
    console.error('❌ Commit failed:', result.error)
    return false
  }

  if (!result.commitHash) {
    console.error('❌ No commit hash returned')
    return false
  }

  // Verify commit exists
  const { stdout: logOutput } = await execAsync(
    `git log --oneline -1`,
    { cwd: worktreePath }
  )

  if (!logOutput.includes('Test commit from worker-1')) {
    console.error('❌ Commit message not found in log')
    return false
  }

  console.log('✅ Commit created:', result.commitHash.substring(0, 8))
  return true
}

async function testMultipleWorktrees(): Promise<boolean> {
  console.log('\n👥 Testing multiple parallel worktrees...')
  
  // Create two more worktrees
  const workers = ['2', '3']
  
  for (const workerId of workers) {
    const result = await createWorktree({
      repoDir: TEST_REPO_DIR,
      runId: TEST_RUN_ID,
      workerId,
      baseBranch: 'main',
    })

    if (!result.ok) {
      console.error(`❌ Failed to create worktree for ${workerId}:`, result.error)
      return false
    }

    // Make a change in each worktree
    const worktreePath = result.worktree!.path
    await writeFile(join(worktreePath, `worker-${workerId}.txt`), `Hello from worker-${workerId}\n`)
    
    await commitWorktree({
      worktreePath,
      message: `Changes from worker-${workerId}`,
    })
  }

  // List all worktrees
  const listResult = await listRunWorktrees({
    repoDir: TEST_REPO_DIR,
    runId: TEST_RUN_ID,
  })

  if (!listResult.ok || !listResult.worktrees) {
    console.error('❌ Failed to list worktrees:', listResult.error)
    return false
  }

  if (listResult.worktrees.length !== 3) {
    console.error(`❌ Expected 3 worktrees, found ${listResult.worktrees.length}`)
    return false
  }

  console.log('✅ Created 3 parallel worktrees')
  console.log('   Workers:', listResult.worktrees.map(w => w.workerId).join(', '))
  return true
}

async function testWorktreeCleanup(): Promise<boolean> {
  console.log('\n🧹 Testing single worktree cleanup...')
  
  const result = await cleanupWorktree({
    repoDir: TEST_REPO_DIR,
    runId: TEST_RUN_ID,
    workerId: '1',
    deleteBranch: true,
  })

  if (!result.ok) {
    console.error('❌ Cleanup failed:', result.error)
    return false
  }

  // Verify worktree is gone
  const worktreePath = getWorktreePath(TEST_RUN_ID, '1')
  try {
    await access(worktreePath)
    console.error('❌ Worktree directory still exists')
    return false
  } catch {
    // Expected - directory should not exist
  }

  // Verify branch is gone
  const branch = getWorkerBranch(TEST_RUN_ID, '1')
  const { stdout: branches } = await execAsync('git branch', { cwd: TEST_REPO_DIR })
  if (branches.includes(branch)) {
    console.error('❌ Branch still exists')
    return false
  }

  console.log('✅ Single worktree cleaned up')
  return true
}

async function testRunCleanup(): Promise<boolean> {
  console.log('\n🧹 Testing full run cleanup...')
  
  const result = await cleanupRunWorktrees({
    repoDir: TEST_REPO_DIR,
    runId: TEST_RUN_ID,
    deleteBranches: true,
  })

  if (!result.ok) {
    console.error('❌ Run cleanup failed:', result.error)
    return false
  }

  // Verify all worktrees are gone
  const listResult = await listRunWorktrees({
    repoDir: TEST_REPO_DIR,
    runId: TEST_RUN_ID,
  })

  if (listResult.worktrees && listResult.worktrees.length > 0) {
    console.error('❌ Worktrees still exist after cleanup')
    return false
  }

  // Verify all branches are gone
  const branchPrefix = `swarmops/${TEST_RUN_ID}/`
  const { stdout: branches } = await execAsync('git branch', { cwd: TEST_REPO_DIR })
  if (branches.includes(branchPrefix)) {
    console.error('❌ Branches still exist after cleanup')
    return false
  }

  console.log('✅ All run worktrees cleaned up')
  return true
}

async function testEdgeCases(): Promise<boolean> {
  console.log('\n⚠️  Testing edge cases...')
  
  // Test creating worktree in non-existent repo
  const result1 = await createWorktree({
    repoDir: '/tmp/does-not-exist-12345',
    runId: 'test',
    workerId: 'worker',
  })
  
  if (result1.ok) {
    console.error('❌ Should have failed for non-existent repo')
    return false
  }
  console.log('✅ Correctly fails for non-existent repo')

  // Test committing in non-existent worktree
  const result2 = await commitWorktree({
    worktreePath: '/tmp/does-not-exist-12345',
    message: 'test',
  })
  
  if (result2.ok) {
    console.error('❌ Should have failed for non-existent worktree')
    return false
  }
  console.log('✅ Correctly fails for non-existent worktree')

  // Test creating worktree twice (should clean up first and recreate)
  const result3 = await createWorktree({
    repoDir: TEST_REPO_DIR,
    runId: TEST_RUN_ID,
    workerId: 'duplicate-test',
  })
  
  if (!result3.ok) {
    console.error('❌ First worktree creation failed:', result3.error)
    return false
  }

  const result4 = await createWorktree({
    repoDir: TEST_REPO_DIR,
    runId: TEST_RUN_ID,
    workerId: 'duplicate-test',
  })
  
  if (!result4.ok) {
    console.error('❌ Second worktree creation failed:', result4.error)
    return false
  }
  console.log('✅ Handles duplicate worktree creation')

  // Clean up
  await cleanupWorktree({
    repoDir: TEST_REPO_DIR,
    runId: TEST_RUN_ID,
    workerId: 'duplicate-test',
    deleteBranch: true,
  })

  return true
}

async function runAllTests(): Promise<void> {
  console.log('🧪 SwarmOps Worktree Manager Tests')
  console.log('='.repeat(50))
  
  let allPassed = true

  try {
    await setupTestRepo()
    
    if (!await testWorktreeCreation()) allPassed = false
    if (!await testWorktreeCommit()) allPassed = false
    if (!await testMultipleWorktrees()) allPassed = false
    if (!await testWorktreeCleanup()) allPassed = false
    if (!await testRunCleanup()) allPassed = false
    if (!await testEdgeCases()) allPassed = false

  } catch (err) {
    console.error('💥 Unexpected error:', err)
    allPassed = false
  } finally {
    await cleanupTestRepo()
  }

  console.log('\n' + '='.repeat(50))
  if (allPassed) {
    console.log('✅ All tests passed!')
  } else {
    console.log('❌ Some tests failed!')
    process.exit(1)
  }
}

// Run tests
runAllTests()
