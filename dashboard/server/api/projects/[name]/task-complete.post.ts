import { join } from 'path'
import { randomUUID } from 'crypto'
import { appendFile, readFile } from 'fs/promises'
import { 
  logActivity, 
  checkAndAdvancePhase, 
  triggerOrchestrator, 
  triggerPhaseWork 
} from '../../../utils/auto-advance'
import { onWorkerComplete, getPhaseState } from '../../../utils/phase-collector'
import { mergePhaseWithReview } from '../../../utils/phase-merger'
import { broadcastProjectUpdate } from '../../../plugins/websocket'
import {
  initRetryState,
  recordAttempt,
  getRetryState,
  calculateRetryDelay,
  canRetry,
  clearRetryState,
  DEFAULT_RETRY_POLICY,
} from '../../../utils/retry-handler'
import { DASHBOARD_URL } from '../../../utils/paths'
import { createEscalation, resolveEscalationsByTaskId } from '../../../utils/escalation-store'
import { createWorktree, getWorkerBranch } from '../../../utils/worktree-manager'
import { wakeAgent } from '../../../utils/agent'
import { parseTaskGraph, markTaskDone } from '../../../utils/orchestrator'
import { updateTaskStatus } from '../../../utils/task-registry'
import { requireAuth, validateProjectName } from '../../../utils/security'

interface TaskCompleteRequest {
  taskId: string
  success?: boolean
  message?: string
  runId?: string
  phaseNumber?: number
  error?: string  // Error message if worker failed
}

// Pending worker retries
const pendingWorkerRetries = new Map<string, ReturnType<typeof setTimeout>>()

// Hash taskId to a unique number for per-task retry tracking
function hashTaskId(taskId: string): number {
  let hash = 0
  for (let i = 0; i < taskId.length; i++) {
    const char = taskId.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash // Convert to 32bit integer
  }
  return Math.abs(hash) % 100000 // Keep within range
}

/**
 * Handle worker failure with retry logic
 */
async function handleWorkerFailure(params: {
  taskId: string
  runId: string
  phaseNumber: number
  projectName: string
  projectPath: string
  error: string
}): Promise<{
  willRetry: boolean
  attemptNumber: number
  maxAttempts: number
  delayMs?: number
  escalationId?: string
}> {
  const { taskId, runId, phaseNumber, projectName, projectPath, error } = params
  // Use task-specific retry state with proper unique key per task
  const stepKey = phaseNumber * 100000 + hashTaskId(taskId)
  
  // Get or initialize retry state
  let retryState = await getRetryState(runId, stepKey)
  
  if (!retryState) {
    retryState = await initRetryState({
      runId,
      stepOrder: stepKey,
      taskId,
      policy: DEFAULT_RETRY_POLICY,
    })
  }
  
  // Record this failed attempt
  retryState = await recordAttempt({
    runId,
    stepOrder: stepKey,
    success: false,
    error,
  })
  
  const attemptNumber = retryState.attempts.length
  const maxAttempts = retryState.policy.maxAttempts
  
  console.log(`[task-complete-retry] Worker ${taskId} failed (attempt ${attemptNumber}/${maxAttempts}): ${error}`)
  
  // Check if exhausted
  if (retryState.status === 'exhausted') {
    console.log(`[task-complete-retry] Worker ${taskId} exhausted all ${maxAttempts} retries, creating escalation`)
    
    // Create escalation
    const escalation = await createEscalation({
      runId,
      pipelineId: `project:${projectName}`,
      pipelineName: projectName,
      stepOrder: phaseNumber,
      roleId: 'builder',
      roleName: 'Builder',
      taskId,
      error: `Worker failed after ${attemptNumber} attempts: ${error}`,
      attemptCount: attemptNumber,
      maxAttempts,
      projectDir: projectPath,
      severity: 'high',
    })
    
    // Log escalation
    const activityFile = join(projectPath, 'activity.jsonl')
    const escalationEvent = {
      id: randomUUID(),
      timestamp: new Date().toISOString(),
      type: 'worker-escalated',
      message: `Worker ${taskId} failed after ${attemptNumber} attempts, escalated`,
      agent: 'orchestrator',
      runId,
      phaseNumber,
      taskId,
      escalationId: escalation.id,
      error,
    }
    await appendFile(activityFile, JSON.stringify(escalationEvent) + '\n')
    broadcastProjectUpdate(projectName, 'activity.jsonl')
    
    return {
      willRetry: false,
      attemptNumber,
      maxAttempts,
      escalationId: escalation.id,
    }
  }
  
  // Calculate delay and schedule retry
  const delayMs = calculateRetryDelay(retryState)
  const retryKey = `${runId}:${taskId}`
  console.log(`[task-complete-retry] Scheduling worker ${taskId} retry in ${delayMs}ms`)
  
  // Log retry scheduled
  const activityFile = join(projectPath, 'activity.jsonl')
  const retryEvent = {
    id: randomUUID(),
    timestamp: new Date().toISOString(),
    type: 'worker-retry-scheduled',
    message: `Worker ${taskId} failed, retry ${attemptNumber + 1}/${maxAttempts} in ${Math.round(delayMs/1000)}s`,
    agent: 'orchestrator',
    runId,
    phaseNumber,
    taskId,
    attemptNumber,
    maxAttempts,
    delayMs,
  }
  await appendFile(activityFile, JSON.stringify(retryEvent) + '\n')
  broadcastProjectUpdate(projectName, 'activity.jsonl')
  
  // Cancel existing retry if any
  if (pendingWorkerRetries.has(retryKey)) {
    clearTimeout(pendingWorkerRetries.get(retryKey)!)
    pendingWorkerRetries.delete(retryKey)
  }
  
  // Schedule retry via orchestrate
  const timeout = setTimeout(async () => {
    pendingWorkerRetries.delete(retryKey)
    
    try {
      console.log(`[task-complete-retry] Executing retry for worker ${taskId}`)
      
      // Trigger orchestrate to re-spawn
      const response = await fetch(`${DASHBOARD_URL}/api/projects/${projectName}/orchestrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'continue' }),
      })
      
      if (!response.ok) {
        console.error(`[task-complete-retry] Retry trigger failed:`, await response.text())
      }
    } catch (err) {
      console.error(`[task-complete-retry] Failed to trigger retry:`, err)
    }
  }, delayMs)
  
  pendingWorkerRetries.set(retryKey, timeout)
  
  return {
    willRetry: true,
    attemptNumber,
    maxAttempts,
    delayMs,
  }
}

export default defineEventHandler(async (event) => {
  requireAuth(event)
  const config = useRuntimeConfig(event)
  const name = validateProjectName(getRouterParam(event, 'name'))
  
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Project name required' })
  }

  const body = await readBody<TaskCompleteRequest>(event)
  const projectPath = join(config.projectsDir, name)
  
  // Log task completion
  await logActivity(projectPath, name, 'complete', 
    `Task completed: ${body.taskId}`, { 
      taskId: body.taskId,
      success: body.success ?? true,
      builderMessage: body.message,
      runId: body.runId,
      phaseNumber: body.phaseNumber,
    })
  
  // Update task registry status
  await updateTaskStatus({
    projectName: name,
    taskId: body.taskId,
    status: body.success === false ? 'failed' : 'completed',
    output: body.message,
    error: body.success === false ? (body.error || body.message) : undefined,
  })
  
  // If we have runId and phaseNumber, use the new pipeline flow
  if (body.runId && body.phaseNumber) {
    console.log(`[task-complete] Processing task ${body.taskId} for run ${body.runId}, phase ${body.phaseNumber}`)
    
    try {
      // Check if worker failed - handle with retry logic
      if (body.success === false) {
        console.log(`[task-complete] Worker ${body.taskId} reported failure, checking retry policy`)
        
        const retryResult = await handleWorkerFailure({
          taskId: body.taskId,
          runId: body.runId,
          phaseNumber: body.phaseNumber,
          projectName: name,
          projectPath,
          error: body.message || 'Worker failed',
        })
        
        if (retryResult.willRetry) {
          // Retry scheduled - don't mark as complete in phase collector yet
          return {
            status: 'retry-scheduled',
            taskId: body.taskId,
            runId: body.runId,
            phaseNumber: body.phaseNumber,
            message: `Worker ${body.taskId} failed, retry ${retryResult.attemptNumber + 1}/${retryResult.maxAttempts} scheduled in ${Math.round((retryResult.delayMs || 0)/1000)}s`,
            retryInfo: retryResult,
          }
        }
        
        if (retryResult.escalationId) {
          // Exhausted retries - escalated, but continue with phase
          // Notify phase collector with skipped status so phase can continue
          const phaseResult = await onWorkerComplete({
            runId: body.runId,
            phaseNumber: body.phaseNumber,
            workerId: body.taskId,
            status: 'failed', // Mark as failed but phase can continue
            output: body.message,
            error: `Escalated after ${retryResult.attemptNumber} retries`,
          })
          
          console.log(`[task-complete] Worker ${body.taskId} escalated, phase complete: ${phaseResult.phaseComplete}`)
          
          return {
            status: 'escalated',
            taskId: body.taskId,
            runId: body.runId,
            phaseNumber: body.phaseNumber,
            message: `Worker ${body.taskId} failed after ${retryResult.attemptNumber} retries, escalated`,
            escalationId: retryResult.escalationId,
            phaseComplete: phaseResult.phaseComplete,
          }
        }
      }
      
      // Worker succeeded or we're handling a successful completion
      // Notify phase-collector that this worker completed
      const phaseResult = await onWorkerComplete({
        runId: body.runId,
        phaseNumber: body.phaseNumber,
        workerId: body.taskId,
        status: 'completed',
        output: body.message,
      })
      
      // Mark the task as done in progress.md (server-side, not relying on worker)
      try {
        await markTaskDone(projectPath, body.taskId)
        console.log(`[task-complete] Marked task ${body.taskId} as done in progress.md`)
      } catch (err) {
        console.error(`[task-complete] Failed to mark task done in progress.md:`, err)
      }
      
      // Clear any retry state on success
      const successStepKey = body.phaseNumber * 100000 + hashTaskId(body.taskId)
      await clearRetryState(body.runId, successStepKey).catch(() => {})
      
      // Auto-resolve any open escalations for this task
      const resolvedEscalations = await resolveEscalationsByTaskId(
        body.taskId,
        'Task completed successfully on retry',
        'orchestrator'
      )
      if (resolvedEscalations.length > 0) {
        console.log(`[task-complete] Auto-resolved ${resolvedEscalations.length} escalation(s) for task ${body.taskId}`)
        
        // Log escalation resolution to activity
        const activityFile = join(projectPath, 'activity.jsonl')
        for (const esc of resolvedEscalations) {
          const resolveEvent = {
            id: randomUUID(),
            timestamp: new Date().toISOString(),
            type: 'escalation-resolved',
            message: `Escalation ${esc.id} auto-resolved: task ${body.taskId} completed successfully`,
            agent: 'orchestrator',
            runId: body.runId,
            phaseNumber: body.phaseNumber,
            taskId: body.taskId,
            escalationId: esc.id,
          }
          await appendFile(activityFile, JSON.stringify(resolveEvent) + '\n')
        }
        broadcastProjectUpdate(name, 'activity.jsonl')
      }
      
      console.log(`[task-complete] Worker ${body.taskId} completed successfully`)
      console.log(`[task-complete] Phase complete: ${phaseResult.phaseComplete}, all succeeded: ${phaseResult.allSucceeded}`)
      
      // Log phase worker completion to activity
      const activityFile = join(projectPath, 'activity.jsonl')
      const workerEvent = {
        id: randomUUID(),
        timestamp: new Date().toISOString(),
        type: 'worker-complete',
        message: `Worker ${body.taskId} completed in phase ${body.phaseNumber}`,
        agent: 'orchestrator',
        runId: body.runId,
        phaseNumber: body.phaseNumber,
        workerId: body.taskId,
        phaseComplete: phaseResult.phaseComplete,
      }
      await appendFile(activityFile, JSON.stringify(workerEvent) + '\n')
      broadcastProjectUpdate(name, 'activity.jsonl')
      
      // Check if all workers in this phase are done
      if (phaseResult.phaseComplete) {
        console.log(`[task-complete] Phase ${body.phaseNumber} complete, triggering merge+review`)
        
        // Log phase completion
        const phaseCompleteEvent = {
          id: randomUUID(),
          timestamp: new Date().toISOString(),
          type: 'phase-complete',
          message: `Phase ${body.phaseNumber} completed, starting merge and review`,
          agent: 'orchestrator',
          runId: body.runId,
          phaseNumber: body.phaseNumber,
          allSucceeded: phaseResult.allSucceeded,
        }
        await appendFile(activityFile, JSON.stringify(phaseCompleteEvent) + '\n')
        broadcastProjectUpdate(name, 'activity.jsonl')
        
        // Trigger phase merge and review if all succeeded
        if (phaseResult.allSucceeded) {
          const mergeResult = await mergePhaseWithReview({
            runId: body.runId,
            phaseNumber: body.phaseNumber,
            phaseName: `${name}-phase-${body.phaseNumber}`,
            projectContext: `Project: ${name}`,
          })
          
          console.log(`[task-complete] Merge result: ${mergeResult.status}`)
          
          // Log merge result
          const mergeEvent = {
            id: randomUUID(),
            timestamp: new Date().toISOString(),
            type: 'phase-merge',
            message: `Phase ${body.phaseNumber} merge: ${mergeResult.status}`,
            agent: 'orchestrator',
            runId: body.runId,
            phaseNumber: body.phaseNumber,
            mergeStatus: mergeResult.status,
            mergedBranches: mergeResult.mergedBranches,
            phaseBranch: mergeResult.phaseBranch,
            reviewerSession: mergeResult.reviewerSession,
            resolverSession: mergeResult.resolverSession,
            error: mergeResult.error,
          }
          await appendFile(activityFile, JSON.stringify(mergeEvent) + '\n')
          broadcastProjectUpdate(name, 'activity.jsonl')
          
          if (mergeResult.success) {
            // Check if we should advance to next phase or continue with more tasks
            const advanceResult = await checkAndAdvancePhase(projectPath, name, config)
            
            if (advanceResult.advanced && advanceResult.newPhase) {
              const triggerResult = await triggerPhaseWork(projectPath, name, advanceResult.newPhase)
              
              return {
                status: 'phase-merged-and-advanced',
                taskId: body.taskId,
                runId: body.runId,
                phaseNumber: body.phaseNumber,
                mergeResult: {
                  status: mergeResult.status,
                  phaseBranch: mergeResult.phaseBranch,
                  mergedBranches: mergeResult.mergedBranches,
                  reviewerSession: mergeResult.reviewerSession,
                },
                newPhase: advanceResult.newPhase,
                message: `Phase ${body.phaseNumber} merged. ${advanceResult.message}`,
                triggerResult,
              }
            }
            
            // Continue with more ready tasks
            const orchestratorResult = await triggerOrchestrator(projectPath, name)
            
            return {
              status: 'phase-merged',
              taskId: body.taskId,
              runId: body.runId,
              phaseNumber: body.phaseNumber,
              mergeResult: {
                status: mergeResult.status,
                phaseBranch: mergeResult.phaseBranch,
                mergedBranches: mergeResult.mergedBranches,
                reviewerSession: mergeResult.reviewerSession,
              },
              message: `Phase ${body.phaseNumber} merged successfully`,
              orchestratorResult,
            }
          }
          
          // Merge had conflicts or failed
          if (mergeResult.status === 'conflict') {
            return {
              status: 'phase-conflict',
              taskId: body.taskId,
              runId: body.runId,
              phaseNumber: body.phaseNumber,
              message: `Phase ${body.phaseNumber} has merge conflicts`,
              conflictInfo: mergeResult.conflictInfo,
              resolverSession: mergeResult.resolverSession,
            }
          }
          
          return {
            status: 'phase-merge-failed',
            taskId: body.taskId,
            runId: body.runId,
            phaseNumber: body.phaseNumber,
            message: `Phase ${body.phaseNumber} merge failed: ${mergeResult.error}`,
            error: mergeResult.error,
          }
        }
        
        // Phase complete but not all succeeded - some workers failed
        return {
          status: 'phase-complete-with-failures',
          taskId: body.taskId,
          runId: body.runId,
          phaseNumber: body.phaseNumber,
          message: `Phase ${body.phaseNumber} complete but some workers failed`,
          phaseState: phaseResult.phaseState,
        }
      }
      
      // Phase not complete yet - continue normally
      // Check if we should also advance phases (for tasks not tracked by phase-collector)
      const advanceResult = await checkAndAdvancePhase(projectPath, name, config)
      
      if (advanceResult.advanced && advanceResult.newPhase) {
        const triggerResult = await triggerPhaseWork(projectPath, name, advanceResult.newPhase)
        
        return {
          status: 'phase-advanced',
          taskId: body.taskId,
          runId: body.runId,
          phaseNumber: body.phaseNumber,
          newPhase: advanceResult.newPhase,
          message: advanceResult.message,
          triggerResult,
        }
      }
      
      // Phase didn't advance - check for more ready tasks
      const orchestratorResult = await triggerOrchestrator(projectPath, name)
      
      return {
        status: 'continue',
        taskId: body.taskId,
        runId: body.runId,
        phaseNumber: body.phaseNumber,
        message: orchestratorResult.message,
        details: orchestratorResult.details,
        pipelineTracking: true,
      }
      
    } catch (err: any) {
      console.error(`[task-complete] Error processing pipeline task:`, err)
      // Fall through to legacy handling
    }
  }
  
  // Legacy flow (no runId/phaseNumber)
  // Check if phase should advance (all tasks done → review)
  const advanceResult = await checkAndAdvancePhase(projectPath, name, config)
  
  if (advanceResult.advanced && advanceResult.newPhase) {
    // Trigger work for new phase
    const triggerResult = await triggerPhaseWork(projectPath, name, advanceResult.newPhase)
    
    return {
      status: 'phase-advanced',
      taskId: body.taskId,
      newPhase: advanceResult.newPhase,
      message: advanceResult.message,
      triggerResult
    }
  }
  
  // Phase didn't advance - check for more ready tasks
  const orchestratorResult = await triggerOrchestrator(projectPath, name)
  
  return {
    status: 'continue',
    taskId: body.taskId,
    message: orchestratorResult.message,
    details: orchestratorResult.details
  }
})
