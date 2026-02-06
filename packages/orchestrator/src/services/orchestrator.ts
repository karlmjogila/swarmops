/**
 * Orchestrator Service - Session-Work Linking
 * P1-12: Connects roles, work items, and sessions
 * P2: Extended with worker management (spawnWorker, superviseWorker, terminateWorker)
 */

import { WorkStorage, getWorkStorage } from '../storage/work';
import { RoleStorage, getRoleStorage } from '../storage/roles';
import { SessionStorage, getSessionStorage } from '../storage/sessions';
import { WorkItem, WorkStatus, WorkCreateInput } from '../types/work';
import { Role } from '../types/role';
import {
  TrackedSession,
  SessionSpawnInput,
  SessionTokenUsage,
  SessionStatus,
  ACTIVE_SESSION_STATUSES,
} from '../types/session';
import { NotFoundError, timestamp, generateId } from '../storage/base';

/**
 * Result of assigning a session to work
 */
export interface SessionAssignment {
  session: TrackedSession;
  workItem: WorkItem;
  role: Role;
}

/**
 * Session completion result
 */
export interface SessionCompletionResult {
  session: TrackedSession;
  workItem?: WorkItem;
  success: boolean;
}

/**
 * Service that orchestrates the relationship between roles, work items, and sessions
 */
export class OrchestratorService {
  private workStorage: WorkStorage;
  private roleStorage: RoleStorage;
  private sessionStorage: SessionStorage;

  constructor(
    workStorage?: WorkStorage,
    roleStorage?: RoleStorage,
    sessionStorage?: SessionStorage
  ) {
    this.workStorage = workStorage ?? getWorkStorage();
    this.roleStorage = roleStorage ?? getRoleStorage();
    this.sessionStorage = sessionStorage ?? getSessionStorage();
  }

  /**
   * Assign a session to a work item
   * Links the session to the work item and updates the work item's sessionKey
   */
  async assignSession(
    input: SessionSpawnInput,
    sessionKey?: string
  ): Promise<SessionAssignment> {
    // Validate role exists
    const role = await this.roleStorage.get(input.roleId);

    // Track the session
    const session = await this.sessionStorage.track(input, sessionKey);

    // If work item is specified, link it
    let workItem: WorkItem | undefined;
    if (input.workItemId) {
      workItem = await this.workStorage.get(input.workItemId);

      // Update work item with session key
      await this.workStorage.appendEvent(input.workItemId, {
        type: 'session_assigned',
        message: `Session ${session.sessionKey} assigned`,
        data: {
          sessionKey: session.sessionKey,
          roleId: input.roleId,
          label: input.label,
        },
      });

      // If work is pending, move it to queued
      if (workItem.status === 'pending') {
        workItem = await this.workStorage.updateStatus(input.workItemId, 'queued');
      }
    }

    return {
      session,
      workItem: workItem!,
      role,
    };
  }

  /**
   * Get the work item associated with a session
   */
  async getWorkForSession(sessionKey: string): Promise<WorkItem | null> {
    const session = await this.sessionStorage.get(sessionKey);

    if (!session.workItemId) {
      return null;
    }

    try {
      return await this.workStorage.get(session.workItemId);
    } catch (error) {
      if (error instanceof NotFoundError) {
        return null;
      }
      throw error;
    }
  }

  /**
   * Get all sessions associated with a work item
   */
  async getSessionsForWork(workItemId: string): Promise<TrackedSession[]> {
    const result = await this.sessionStorage.list({ workItemId });
    return result.sessions;
  }

  /**
   * Handle session completion - updates work status when session finishes successfully
   */
  async handleSessionComplete(
    sessionKey: string,
    output?: Record<string, unknown>,
    tokenUsage?: Partial<SessionTokenUsage>
  ): Promise<SessionCompletionResult> {
    // Mark session as stopped
    const session = await this.sessionStorage.markStopped(sessionKey, 0);

    // Update token usage if provided
    if (tokenUsage) {
      await this.sessionStorage.addTokenUsage(sessionKey, tokenUsage);
    }

    // Update associated work item if exists
    let workItem: WorkItem | undefined;
    if (session.workItemId) {
      try {
        // Set output if provided
        if (output) {
          await this.workStorage.setOutput(session.workItemId, output);
        }

        // Append completion event
        await this.workStorage.appendEvent(session.workItemId, {
          type: 'session_completed',
          message: `Session ${sessionKey} completed successfully`,
          data: {
            sessionKey,
            tokenUsage: session.tokenUsage,
          },
        });

        // Mark work as complete
        workItem = await this.workStorage.updateStatus(session.workItemId, 'complete');
      } catch (error) {
        // Work item may have been deleted or already completed
        console.error(`Failed to update work item ${session.workItemId}:`, error);
      }
    }

    return {
      session,
      workItem,
      success: true,
    };
  }

  /**
   * Handle session failure - updates work status when session fails
   */
  async handleSessionFailed(
    sessionKey: string,
    error: string,
    exitCode?: number,
    tokenUsage?: Partial<SessionTokenUsage>
  ): Promise<SessionCompletionResult> {
    // Mark session as stopped with error
    const session = await this.sessionStorage.markStopped(sessionKey, exitCode ?? 1, error);

    // Update token usage if provided
    if (tokenUsage) {
      await this.sessionStorage.addTokenUsage(sessionKey, tokenUsage);
    }

    // Update associated work item if exists
    let workItem: WorkItem | undefined;
    if (session.workItemId) {
      try {
        // Append failure event
        await this.workStorage.appendEvent(session.workItemId, {
          type: 'session_failed',
          message: `Session ${sessionKey} failed: ${error}`,
          data: {
            sessionKey,
            error,
            exitCode,
            tokenUsage: session.tokenUsage,
          },
        });

        // Mark work as failed
        workItem = await this.workStorage.updateStatus(session.workItemId, 'failed', error);
      } catch (err) {
        // Work item may have been deleted
        console.error(`Failed to update work item ${session.workItemId}:`, err);
      }
    }

    return {
      session,
      workItem,
      success: false,
    };
  }

  /**
   * Start a session's work - marks session active and work running
   */
  async startSessionWork(sessionKey: string): Promise<SessionAssignment | null> {
    const session = await this.sessionStorage.markActive(sessionKey);
    const role = await this.roleStorage.get(session.roleId);

    let workItem: WorkItem | undefined;
    if (session.workItemId) {
      try {
        // Move work to running
        workItem = await this.workStorage.updateStatus(session.workItemId, 'running');
        
        await this.workStorage.appendEvent(session.workItemId, {
          type: 'session_started',
          message: `Session ${sessionKey} started work`,
        });
      } catch (error) {
        // May already be running or in invalid state
        console.error(`Failed to start work ${session.workItemId}:`, error);
        workItem = await this.workStorage.get(session.workItemId).catch(() => undefined);
      }
    }

    return {
      session,
      workItem: workItem!,
      role,
    };
  }

  /**
   * Record activity for a session - updates lastActivityAt
   */
  async recordActivity(
    sessionKey: string,
    tokenUsage?: Partial<SessionTokenUsage>
  ): Promise<TrackedSession> {
    let session = await this.sessionStorage.update(sessionKey, {
      lastActivityAt: timestamp(),
    });

    if (tokenUsage) {
      session = await this.sessionStorage.addTokenUsage(sessionKey, tokenUsage);
    }

    return session;
  }

  /**
   * Get the role for a session
   */
  async getRoleForSession(sessionKey: string): Promise<Role> {
    const session = await this.sessionStorage.get(sessionKey);
    return this.roleStorage.get(session.roleId);
  }

  /**
   * Cancel a session and its associated work
   */
  async cancelSession(sessionKey: string, reason: string): Promise<SessionCompletionResult> {
    const session = await this.sessionStorage.markStopped(sessionKey, 130, reason);

    let workItem: WorkItem | undefined;
    if (session.workItemId) {
      try {
        workItem = await this.workStorage.cancel(session.workItemId, reason);
      } catch (error) {
        console.error(`Failed to cancel work ${session.workItemId}:`, error);
      }
    }

    return {
      session,
      workItem,
      success: false,
    };
  }

  /**
   * Get summary of all active sessions and their work
   */
  async getActiveSessionSummary(): Promise<Array<{
    session: TrackedSession;
    workItem?: WorkItem;
    role?: Role;
  }>> {
    const activeSessions = await this.sessionStorage.getActiveSessions();
    
    const summaries = await Promise.all(
      activeSessions.map(async (session) => {
        const workItem = session.workItemId 
          ? await this.workStorage.get(session.workItemId).catch(() => undefined)
          : undefined;
        
        const role = await this.roleStorage.get(session.roleId).catch(() => undefined);

        return {
          session,
          workItem,
          role,
        };
      })
    );

    return summaries;
  }

  /**
   * Clean up stale sessions and optionally their work items
   */
  async cleanup(maxAgeMs: number, cancelStaleWork: boolean = false): Promise<{
    prunedSessions: number;
    cancelledWork: number;
  }> {
    // Get sessions that will be pruned
    const activeSessions = await this.sessionStorage.getActiveSessions();
    const now = Date.now();
    let cancelledWork = 0;

    if (cancelStaleWork) {
      for (const session of activeSessions) {
        const lastActivity = new Date(session.lastActivityAt).getTime();
        const age = now - lastActivity;

        if (age > maxAgeMs && session.workItemId) {
          try {
            await this.workStorage.cancel(session.workItemId, 'Session timed out');
            cancelledWork++;
          } catch {
            // Work may already be completed
          }
        }
      }
    }

    const prunedSessions = await this.sessionStorage.pruneStale(maxAgeMs);

    return {
      prunedSessions,
      cancelledWork,
    };
  }

  // ==========================================
  // P2: Worker Management Methods
  // ==========================================

  /**
   * Spawn a new worker with the specified role to execute a task
   * Creates a work item and assigns a new session to it
   */
  async spawnWorker(
    roleId: string,
    task: string,
    options?: {
      label?: string;
      input?: Record<string, unknown>;
      tags?: string[];
      priority?: number;
    }
  ): Promise<{
    session: TrackedSession;
    workItem: WorkItem;
    role: Role;
  }> {
    // Validate role exists
    const role = await this.roleStorage.get(roleId);

    // Create work item for this task
    const workInput: WorkCreateInput = {
      type: 'task',
      roleId,
      title: options?.label || `Worker task: ${task.substring(0, 50)}...`,
      description: task,
      input: options?.input,
      tags: options?.tags,
      priority: options?.priority,
    };

    const workItem = await this.workStorage.create(workInput);

    // Generate unique session key
    const sessionId = generateId();
    const sessionKey = `agent:worker:${roleId}:${sessionId}`;

    // Assign session to work
    const assignment = await this.assignSession({
      roleId,
      workItemId: workItem.id,
      label: options?.label || `worker-${roleId}-${sessionId.substring(0, 8)}`,
      task,
    }, sessionKey);

    return {
      session: assignment.session,
      workItem: assignment.workItem,
      role,
    };
  }

  /**
   * Supervise a worker session - monitors progress and returns status
   */
  async superviseWorker(sessionKey: string): Promise<{
    session: TrackedSession;
    workItem?: WorkItem;
    role?: Role;
    isActive: boolean;
    isHealthy: boolean;
    staleDuration?: number;
    recommendation?: 'continue' | 'restart' | 'terminate';
  }> {
    const session = await this.sessionStorage.get(sessionKey);
    const isActive = ACTIVE_SESSION_STATUSES.includes(session.status);

    // Get associated work item
    let workItem: WorkItem | undefined;
    if (session.workItemId) {
      try {
        workItem = await this.workStorage.get(session.workItemId);
      } catch {
        // Work item may have been deleted
      }
    }

    // Get role
    let role: Role | undefined;
    try {
      role = await this.roleStorage.get(session.roleId);
    } catch {
      // Role may have been deleted
    }

    // Calculate staleness
    const now = Date.now();
    const lastActivity = new Date(session.lastActivityAt).getTime();
    const staleDuration = now - lastActivity;

    // Determine health status
    const staleThresholdMs = 300000; // 5 minutes
    const isHealthy = isActive && staleDuration < staleThresholdMs;

    // Generate recommendation
    let recommendation: 'continue' | 'restart' | 'terminate' | undefined;
    if (!isActive) {
      recommendation = session.status === 'stopped' && !session.error ? 'continue' : 'terminate';
    } else if (!isHealthy) {
      recommendation = staleDuration > staleThresholdMs * 2 ? 'terminate' : 'restart';
    } else {
      recommendation = 'continue';
    }

    return {
      session,
      workItem,
      role,
      isActive,
      isHealthy,
      staleDuration,
      recommendation,
    };
  }

  /**
   * Terminate a worker session
   * Optionally cancels associated work or marks it as failed
   */
  async terminateWorker(
    sessionKey: string,
    options?: {
      reason?: string;
      cancelWork?: boolean;
      markWorkFailed?: boolean;
    }
  ): Promise<{
    session: TrackedSession;
    workItem?: WorkItem;
    terminated: boolean;
  }> {
    const reason = options?.reason || 'Worker terminated';
    const cancelWork = options?.cancelWork ?? true;
    const markWorkFailed = options?.markWorkFailed ?? false;

    // Get session first
    const session = await this.sessionStorage.get(sessionKey);

    // Handle work item
    let workItem: WorkItem | undefined;
    if (session.workItemId) {
      try {
        const currentWork = await this.workStorage.get(session.workItemId);
        
        if (cancelWork && currentWork.status !== 'complete' && currentWork.status !== 'cancelled') {
          workItem = await this.workStorage.cancel(session.workItemId, reason);
        } else if (markWorkFailed && currentWork.status === 'running') {
          workItem = await this.workStorage.updateStatus(session.workItemId, 'failed', reason);
        } else {
          workItem = currentWork;
        }
      } catch {
        // Work item may not exist
      }
    }

    // Mark session as stopped
    const stoppedSession = await this.sessionStorage.markStopped(sessionKey, 130, reason);

    return {
      session: stoppedSession,
      workItem,
      terminated: true,
    };
  }

  /**
   * List all active workers with their status
   */
  async listActiveWorkers(): Promise<Array<{
    session: TrackedSession;
    workItem?: WorkItem;
    role?: Role;
    staleDuration: number;
  }>> {
    const activeSessions = await this.sessionStorage.getActiveSessions();
    const now = Date.now();

    const workers = await Promise.all(
      activeSessions.map(async (session) => {
        let workItem: WorkItem | undefined;
        let role: Role | undefined;

        if (session.workItemId) {
          try {
            workItem = await this.workStorage.get(session.workItemId);
          } catch {
            // Ignore
          }
        }

        try {
          role = await this.roleStorage.get(session.roleId);
        } catch {
          // Ignore
        }

        const lastActivity = new Date(session.lastActivityAt).getTime();
        const staleDuration = now - lastActivity;

        return {
          session,
          workItem,
          role,
          staleDuration,
        };
      })
    );

    return workers;
  }

  /**
   * Restart a stale or failed worker
   * Creates a new session for the same work item
   */
  async restartWorker(
    sessionKey: string,
    options?: {
      newTask?: string;
      preserveTokenUsage?: boolean;
    }
  ): Promise<{
    oldSession: TrackedSession;
    newSession: TrackedSession;
    workItem?: WorkItem;
    role: Role;
  }> {
    // Get the old session
    const oldSession = await this.sessionStorage.get(sessionKey);
    const role = await this.roleStorage.get(oldSession.roleId);

    // Terminate old session if still active
    if (ACTIVE_SESSION_STATUSES.includes(oldSession.status)) {
      await this.sessionStorage.markStopped(sessionKey, 0, 'Restarted');
    }

    // Get work item if exists
    let workItem: WorkItem | undefined;
    if (oldSession.workItemId) {
      try {
        workItem = await this.workStorage.get(oldSession.workItemId);
        
        // Reset work status if it was running or failed
        if (workItem.status === 'running' || workItem.status === 'failed') {
          workItem = await this.workStorage.updateStatus(oldSession.workItemId, 'queued');
        }
      } catch {
        // Work may not exist
      }
    }

    // Create new session
    const newSessionId = generateId();
    const newSessionKey = `agent:worker:${oldSession.roleId}:${newSessionId}`;

    const assignment = await this.assignSession({
      roleId: oldSession.roleId,
      workItemId: oldSession.workItemId,
      label: oldSession.label.replace(/-[a-f0-9]{8}$/, `-${newSessionId.substring(0, 8)}`),
      task: options?.newTask || oldSession.task || 'Restarted task',
    }, newSessionKey);

    // Preserve token usage if requested
    if (options?.preserveTokenUsage && oldSession.tokenUsage) {
      await this.sessionStorage.addTokenUsage(newSessionKey, oldSession.tokenUsage);
    }

    return {
      oldSession,
      newSession: assignment.session,
      workItem: assignment.workItem,
      role,
    };
  }
}

/** Singleton instance */
let defaultService: OrchestratorService | null = null;

/**
 * Get the default OrchestratorService instance
 */
export function getOrchestratorService(): OrchestratorService {
  if (!defaultService) {
    defaultService = new OrchestratorService();
  }
  return defaultService;
}
