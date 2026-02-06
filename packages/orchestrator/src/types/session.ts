/**
 * Session Tracking Data Model
 * P1-10: Types for tracking agent sessions and their lifecycle
 */

/**
 * Session lifecycle status
 */
export type SessionStatus = 
  | 'starting'  // Session is being spawned
  | 'active'    // Session is actively processing
  | 'idle'      // Session has no pending work
  | 'stopping'  // Session is gracefully shutting down
  | 'stopped';  // Session has terminated

/**
 * Token usage tracking for a session
 */
export interface SessionTokenUsage {
  /** Input tokens consumed */
  input: number;
  /** Output tokens generated */
  output: number;
  /** Thinking/reasoning tokens (extended thinking) */
  thinking: number;
}

/**
 * A tracked session in the orchestrator
 */
export interface TrackedSession {
  /** Unique session key (format: agent:main:subagent:uuid) */
  sessionKey: string;
  /** Session ID (the UUID portion) */
  sessionId: string;
  /** Work item ID this session is executing */
  workItemId?: string;
  /** Role ID this session is running as */
  roleId: string;
  /** Current session status */
  status: SessionStatus;
  /** Human-readable label for the session */
  label: string;
  /** When the session was spawned */
  spawnedAt: string;
  /** When the session last had activity */
  lastActivityAt: string;
  /** Cumulative token usage */
  tokenUsage: SessionTokenUsage;
  /** Optional task description */
  task?: string;
  /** Optional error message if session failed */
  error?: string;
  /** Optional exit code when stopped */
  exitCode?: number;
}

/**
 * Input for spawning a new session
 */
export interface SessionSpawnInput {
  /** Role ID to use for the session */
  roleId: string;
  /** Work item ID to associate (optional) */
  workItemId?: string;
  /** Human-readable label */
  label: string;
  /** Task description to send to the session */
  task: string;
}

/**
 * Filters for listing sessions
 */
export interface SessionListFilters {
  /** Filter by status */
  status?: SessionStatus | SessionStatus[];
  /** Filter by role ID */
  roleId?: string;
  /** Filter by work item ID */
  workItemId?: string;
  /** Filter by label (partial match) */
  labelContains?: string;
  /** Only include sessions active since this timestamp */
  activeSince?: string;
  /** Limit number of results */
  limit?: number;
  /** Offset for pagination */
  offset?: number;
}

/**
 * Result of session list query
 */
export interface SessionListResult {
  /** Sessions matching the query */
  sessions: TrackedSession[];
  /** Total count (before pagination) */
  total: number;
  /** Whether there are more results */
  hasMore: boolean;
}

/**
 * Update payload for session modifications
 */
export interface SessionUpdateInput {
  /** New status */
  status?: SessionStatus;
  /** Update last activity timestamp */
  lastActivityAt?: string;
  /** Update token usage */
  tokenUsage?: Partial<SessionTokenUsage>;
  /** Set error message */
  error?: string;
  /** Set exit code */
  exitCode?: number;
}

/**
 * Default token usage values
 */
export const DEFAULT_TOKEN_USAGE: SessionTokenUsage = {
  input: 0,
  output: 0,
  thinking: 0,
};

/**
 * Session status that indicates the session is still alive
 */
export const ACTIVE_SESSION_STATUSES: SessionStatus[] = ['starting', 'active', 'idle'];

/**
 * Session status that indicates the session has terminated
 */
export const TERMINAL_SESSION_STATUSES: SessionStatus[] = ['stopping', 'stopped'];
