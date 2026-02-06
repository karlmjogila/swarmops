/**
 * Work Item Data Model & Types
 * P1-06: Core types for the work ledger system
 */

/**
 * Work item status lifecycle
 */
export type WorkStatus = 
  | 'pending'     // Created but not yet queued
  | 'queued'      // Waiting in queue for execution
  | 'running'     // Currently being executed
  | 'converging'  // In convergence/review phase
  | 'complete'    // Successfully completed
  | 'failed'      // Failed with error
  | 'cancelled';  // Cancelled by user or system

/**
 * Type of work being performed
 */
export type WorkType = 
  | 'task'      // Single atomic task
  | 'pipeline'  // Multi-step workflow
  | 'batch'     // Multiple parallel tasks
  | 'review'    // Human review step
  | 'converge'; // Convergence/synthesis step

/**
 * Event that occurred during work execution
 */
export interface WorkEvent {
  /** When the event occurred */
  timestamp: string;
  /** Type of event (e.g., 'started', 'output', 'error', 'retry') */
  type: string;
  /** Human-readable message */
  message: string;
  /** Optional additional data */
  data?: Record<string, unknown>;
}

/**
 * Timestamps for work item lifecycle
 */
export interface WorkTimestamps {
  /** When the work item was created */
  createdAt: string;
  /** When the work item was last updated */
  updatedAt: string;
  /** When the work item started executing */
  startedAt?: string;
  /** When the work item completed (success, failure, or cancelled) */
  completedAt?: string;
}

/**
 * A work item in the ledger
 */
export interface WorkItem {
  /** Unique identifier */
  id: string;
  /** Type of work */
  type: WorkType;
  /** Current status */
  status: WorkStatus;
  /** Role ID assigned to execute this work */
  roleId?: string;
  /** Session key for tracking execution context */
  sessionKey?: string;
  /** Parent work item ID (for hierarchical work) */
  parentId?: string;
  /** Child work item IDs */
  childIds: string[];
  /** Short title describing the work */
  title: string;
  /** Detailed description of what needs to be done */
  description?: string;
  /** Input data/context for the work */
  input?: Record<string, unknown>;
  /** Output/result of the work */
  output?: Record<string, unknown>;
  /** Number of iterations/attempts */
  iterations: number;
  /** Lifecycle timestamps */
  timestamps: WorkTimestamps;
  /** Event history */
  events: WorkEvent[];
  /** Optional tags for categorization */
  tags?: string[];
  /** Optional priority (higher = more important) */
  priority?: number;
  /** Optional error message if failed */
  error?: string;
}

/**
 * Input for creating a new work item
 */
export interface WorkCreateInput {
  /** Type of work */
  type: WorkType;
  /** Role ID to assign (optional) */
  roleId?: string;
  /** Session key (optional) */
  sessionKey?: string;
  /** Parent work item ID (optional) */
  parentId?: string;
  /** Title (required) */
  title: string;
  /** Description (optional) */
  description?: string;
  /** Input data (optional) */
  input?: Record<string, unknown>;
  /** Tags (optional) */
  tags?: string[];
  /** Priority (optional, default 0) */
  priority?: number;
}

/**
 * Input for appending an event to a work item
 */
export interface WorkEventInput {
  /** Event type */
  type: string;
  /** Event message */
  message: string;
  /** Optional additional data */
  data?: Record<string, unknown>;
}

/**
 * Query filters for listing work items
 */
export interface WorkQueryFilters {
  /** Filter by date (YYYY-MM-DD) */
  date?: string;
  /** Filter by date range start (inclusive) */
  fromDate?: string;
  /** Filter by date range end (inclusive) */
  toDate?: string;
  /** Filter by status */
  status?: WorkStatus | WorkStatus[];
  /** Filter by type */
  type?: WorkType | WorkType[];
  /** Filter by role ID */
  roleId?: string;
  /** Filter by parent ID */
  parentId?: string;
  /** Filter by tag */
  tag?: string;
  /** Limit number of results */
  limit?: number;
  /** Offset for pagination */
  offset?: number;
}

/**
 * Result of a work item list query
 */
export interface WorkListResult {
  /** Work items matching the query */
  items: WorkItem[];
  /** Total count (before pagination) */
  total: number;
  /** Whether there are more results */
  hasMore: boolean;
}
