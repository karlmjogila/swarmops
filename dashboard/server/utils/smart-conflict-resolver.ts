/**
 * SmartConflictResolver - AI-powered merge conflict resolution with task context
 * 
 * Enhances basic conflict resolution by including:
 * - Worker task descriptions (what each worker was trying to do)
 * - Project goal/context
 * - File content from both branches
 * 
 * This allows the AI to make intelligent decisions about how to combine
 * conflicting changes while preserving both workers' contributions.
 */

import { exec as execCallback } from 'child_process'
import { promisify } from 'util'
import { readFile, writeFile } from 'fs/promises'
import { join } from 'path'
import { spawnSession } from './gateway-client'
import { DASHBOARD_URL } from './paths'
import { getPhaseState, getWorkerTaskContexts } from './phase-collector'
import { stageFile, commitMerge, getConflictContent } from './conflict-resolver'

const exec = promisify(execCallback)

export interface TaskContext {
  workerId: string
  taskId: string
  taskDescription?: string
}

export interface SmartResolverRequest {
  runId: string
  phaseNumber: number
  repoPath: string
  sourceBranch: string  // The branch being merged (has conflicts)
  targetBranch: string  // The target branch (phase branch)
  conflictFiles: string[]
  projectGoal?: string  // Optional project-level context
}

export interface SmartResolverResult {
  success: boolean
  sessionKey?: string
  resolvedFiles?: string[]
  error?: string
}

/**
 * Spawn an AI agent to resolve merge conflicts with full task context
 */
export async function spawnSmartConflictResolver(
  request: SmartResolverRequest
): Promise<SmartResolverResult> {
  const { runId, phaseNumber, repoPath, sourceBranch, targetBranch, conflictFiles, projectGoal } = request

  // Get phase state for task context
  const phaseState = await getPhaseState(runId, phaseNumber)
  
  // Get task contexts for the conflicting branches
  let sourceTaskContext: TaskContext | undefined
  let targetTaskContexts: Map<string, TaskContext> | undefined
  
  if (phaseState) {
    const contexts = getWorkerTaskContexts(phaseState, [sourceBranch, targetBranch])
    sourceTaskContext = contexts.get(sourceBranch)
    
    // Get all previously merged worker contexts
    if (phaseState.collectedBranches) {
      targetTaskContexts = getWorkerTaskContexts(phaseState, phaseState.collectedBranches)
    }
  }

  // Build conflict details for each file
  const conflictDetails: string[] = []
  
  for (const file of conflictFiles) {
    const content = await getConflictContent(repoPath, file)
    const baseContent = await getFileAtRef(repoPath, file, `${targetBranch}~1`) // Base version
    const sourceContent = await getFileAtRef(repoPath, file, sourceBranch)
    const targetContent = await getFileAtRef(repoPath, file, targetBranch)
    
    conflictDetails.push(`
### File: ${file}

**Current conflict markers:**
\`\`\`
${content}
\`\`\`

**Source branch (${sourceBranch}) version:**
\`\`\`
${sourceContent || '(file does not exist in source)'}
\`\`\`

**Target branch (${targetBranch}) version:**
\`\`\`
${targetContent || '(file does not exist in target)'}
\`\`\`
`)
  }

  const prompt = buildSmartResolverPrompt({
    runId,
    phaseNumber,
    repoPath,
    sourceBranch,
    targetBranch,
    sourceTaskContext,
    targetTaskContexts,
    projectGoal,
    conflictFiles,
    conflictDetails,
  })

  const label = `smart-resolver:phase-${phaseNumber}:${runId}`.slice(0, 64)

  try {
    const result = await spawnSession({
      task: prompt,
      label,
      runTimeoutSeconds: 300,  // 5 minutes max
    })

    if (result.ok && result.sessionKey) {
      console.log(`[smart-resolver] Spawned resolver agent: ${result.sessionKey}`)
      return {
        success: true,
        sessionKey: result.sessionKey,
      }
    }

    return {
      success: false,
      error: result.error || 'Failed to spawn resolver agent',
    }
  } catch (err: any) {
    return {
      success: false,
      error: err.message || 'Unknown error spawning resolver',
    }
  }
}

/**
 * Get file content at a specific git ref
 */
async function getFileAtRef(repoPath: string, filePath: string, ref: string): Promise<string | null> {
  try {
    const { stdout } = await exec(`git show ${ref}:"${filePath}"`, { cwd: repoPath })
    return stdout
  } catch {
    return null
  }
}

/**
 * Build the smart resolver prompt with full context
 */
function buildSmartResolverPrompt(opts: {
  runId: string
  phaseNumber: number
  repoPath: string
  sourceBranch: string
  targetBranch: string
  sourceTaskContext?: TaskContext
  targetTaskContexts?: Map<string, TaskContext>
  projectGoal?: string
  conflictFiles: string[]
  conflictDetails: string[]
}): string {
  const {
    runId,
    phaseNumber,
    repoPath,
    sourceBranch,
    targetBranch,
    sourceTaskContext,
    targetTaskContexts,
    projectGoal,
    conflictFiles,
    conflictDetails,
  } = opts

  // Build task context section
  let taskContextSection = ''
  
  if (sourceTaskContext?.taskDescription) {
    taskContextSection += `
## Source Branch Task (${sourceBranch})
Worker: ${sourceTaskContext.workerId}
Task: ${sourceTaskContext.taskDescription}
`
  }

  if (targetTaskContexts && targetTaskContexts.size > 0) {
    taskContextSection += `
## Previously Merged Tasks (in ${targetBranch})
`
    for (const [branch, ctx] of targetTaskContexts) {
      if (ctx.taskDescription) {
        taskContextSection += `- **${ctx.workerId}**: ${ctx.taskDescription}\n`
      }
    }
  }

  return `# AI Merge Conflict Resolution Task

You are resolving git merge conflicts in a SwarmOps pipeline.

## Repository
Path: ${repoPath}
Run ID: ${runId}
Phase: ${phaseNumber}

## Branches
- **Source Branch**: ${sourceBranch} (being merged in)
- **Target Branch**: ${targetBranch} (receiving the merge)

${projectGoal ? `## Project Goal\n${projectGoal}\n` : ''}
${taskContextSection}

## Conflicted Files (${conflictFiles.length})
${conflictFiles.map(f => `- ${f}`).join('\n')}

## Conflict Details
${conflictDetails.join('\n---\n')}

## Your Task

1. **Understand the intent**: Read both task descriptions to understand what each worker was trying to accomplish.

2. **Resolve conflicts intelligently**:
   - Preserve ALL meaningful contributions from both branches
   - If workers modified different parts, include both changes
   - If workers modified the same code, merge their intents logically
   - Ensure the result compiles/runs without syntax errors

3. **Apply the resolution**:
   \`\`\`bash
   cd ${repoPath}
   # Edit each conflicted file to remove conflict markers and produce merged content
   # Then stage and commit:
   git add ${conflictFiles.join(' ')}
   git commit -m "Resolved conflicts: merged ${sourceBranch} into ${targetBranch}"
   \`\`\`

4. **Report completion**:
   \`\`\`bash
   curl -X POST ${DASHBOARD_URL}/api/orchestrator/worker-complete \\
     -H "Content-Type: application/json" \\
     -d '{"runId": "${runId}", "stepOrder": -1, "status": "completed", "output": "Smart-resolved ${conflictFiles.length} conflict(s)"}'
   \`\`\`

## Guidelines
- DO NOT lose any worker's contributions unless they directly contradict
- If both workers added imports, include all unique imports
- If both workers added functions, include all functions
- If both workers modified the same function, combine their changes sensibly
- Test your resolution mentally for correctness before committing

If you cannot resolve the conflicts automatically, report with \`"status": "failed"\` and explain why.`
}

/**
 * Log conflict resolution activity
 */
export async function logConflictResolution(opts: {
  projectPath: string
  runId: string
  phaseNumber: number
  conflictFiles: string[]
  sourceBranch: string
  targetBranch: string
  status: 'started' | 'completed' | 'failed'
  error?: string
}): Promise<void> {
  const { projectPath, runId, phaseNumber, conflictFiles, sourceBranch, targetBranch, status, error } = opts
  
  const activityFile = join(projectPath, 'activity.jsonl')
  
  const entry = {
    type: 'conflict-resolution',
    timestamp: new Date().toISOString(),
    runId,
    phaseNumber,
    sourceBranch,
    targetBranch,
    conflictFiles,
    status,
    error,
  }
  
  try {
    const line = JSON.stringify(entry) + '\n'
    const { appendFile } = await import('fs/promises')
    await appendFile(activityFile, line)
  } catch (err) {
    console.error('[smart-resolver] Failed to log activity:', err)
  }
}
