/**
 * Pipeline Data Model & Types
 * P2: Types for pipeline execution and orchestration
 */

import { WorkStatus } from './work';

/**
 * Convergence criteria for quality loops
 */
export interface ConvergenceCriteria {
  /** Maximum iterations before stopping */
  maxIterations: number;
  /** Minimum quality score (0-1) to consider converged */
  minScore?: number;
  /** Custom success criteria expression */
  successCriteria?: string;
  /** Role ID for review (defaults to 'reviewer') */
  reviewerRoleId?: string;
  /** Whether self-review is enabled */
  selfReview?: boolean;
}

/**
 * Default convergence settings
 */
export const DEFAULT_CONVERGENCE: ConvergenceCriteria = {
  maxIterations: 3,
  minScore: 0.8,
  selfReview: true,
  reviewerRoleId: 'reviewer',
};

/**
 * Pipeline step execution status
 */
export type PipelineStepStatus = 
  | 'pending'     // Not yet started
  | 'running'     // Currently executing
  | 'converging'  // In convergence loop
  | 'complete'    // Successfully finished
  | 'failed'      // Failed with error
  | 'skipped';    // Skipped due to condition

/**
 * A single step in a pipeline
 */
export interface PipelineStep {
  /** Unique step identifier */
  id: string;
  /** Step name for display */
  name: string;
  /** Role ID to execute this step */
  roleId: string;
  /** Action/task description to perform */
  action: string;
  /** Input template (can reference previous step outputs via {{stepId.output}}) */
  input?: Record<string, unknown>;
  /** Expected output schema description */
  outputSchema?: string;
  /** Convergence settings for this step */
  convergence?: ConvergenceCriteria;
  /** Whether this step is optional */
  optional?: boolean;
  /** Condition expression for execution (e.g., "{{step1.output.success}} === true") */
  condition?: string;
  /** Timeout in milliseconds */
  timeoutMs?: number;
  /** Retry count on failure */
  retryCount?: number;
  /** Step order index */
  order: number;
}

/**
 * Step execution state during a pipeline run
 */
export interface PipelineStepState {
  /** Step ID */
  stepId: string;
  /** Current status */
  status: PipelineStepStatus;
  /** Session key if currently running */
  sessionKey?: string;
  /** Work item ID if created */
  workItemId?: string;
  /** Output from execution */
  output?: Record<string, unknown>;
  /** Error message if failed */
  error?: string;
  /** Number of convergence iterations */
  iterations: number;
  /** Convergence review results */
  reviews?: Array<{
    iteration: number;
    score: number;
    feedback: string;
    passed: boolean;
  }>;
  /** When step started */
  startedAt?: string;
  /** When step completed */
  completedAt?: string;
}

/**
 * Pipeline run status
 */
export type PipelineRunStatus = 
  | 'pending'     // Created but not started
  | 'running'     // Currently executing steps
  | 'paused'      // Paused by user or system
  | 'complete'    // All steps completed successfully
  | 'failed'      // A step failed and pipeline stopped
  | 'cancelled';  // Cancelled by user

/**
 * State of a pipeline run
 */
export interface PipelineRunState {
  /** Unique run identifier */
  id: string;
  /** Pipeline ID being executed */
  pipelineId: string;
  /** Current run status */
  status: PipelineRunStatus;
  /** Current step index (0-based) */
  currentStepIndex: number;
  /** State of each step */
  stepStates: PipelineStepState[];
  /** Global input provided at run start */
  input?: Record<string, unknown>;
  /** Final output (aggregated from steps) */
  output?: Record<string, unknown>;
  /** Error message if failed */
  error?: string;
  /** When run was created */
  createdAt: string;
  /** When run was last updated */
  updatedAt: string;
  /** When run started executing */
  startedAt?: string;
  /** When run completed */
  completedAt?: string;
}

/**
 * Pipeline definition
 */
export interface Pipeline {
  /** Unique identifier */
  id: string;
  /** Pipeline name */
  name: string;
  /** Description of what the pipeline does */
  description: string;
  /** Ordered list of steps */
  steps: PipelineStep[];
  /** Default input schema/template */
  inputSchema?: Record<string, unknown>;
  /** Global convergence settings (can be overridden per step) */
  defaultConvergence?: ConvergenceCriteria;
  /** Whether pipeline should auto-continue on step completion */
  autoContinue: boolean;
  /** Whether to stop on first step failure */
  stopOnFailure: boolean;
  /** Optional tags for categorization */
  tags?: string[];
  /** When pipeline was created */
  createdAt: string;
  /** When pipeline was last updated */
  updatedAt: string;
}

/**
 * Input for creating a new pipeline
 */
export interface PipelineCreateInput {
  /** Pipeline name (required) */
  name: string;
  /** Description (optional) */
  description?: string;
  /** Initial steps (optional, can add later) */
  steps?: Array<Omit<PipelineStep, 'id' | 'order'>>;
  /** Input schema (optional) */
  inputSchema?: Record<string, unknown>;
  /** Default convergence settings (optional) */
  defaultConvergence?: ConvergenceCriteria;
  /** Auto-continue on step completion (default: true) */
  autoContinue?: boolean;
  /** Stop on first failure (default: true) */
  stopOnFailure?: boolean;
  /** Tags (optional) */
  tags?: string[];
}

/**
 * Input for updating an existing pipeline
 */
export interface PipelineUpdateInput {
  /** Updated name */
  name?: string;
  /** Updated description */
  description?: string;
  /** Replace all steps */
  steps?: Array<Omit<PipelineStep, 'id' | 'order'>>;
  /** Updated input schema */
  inputSchema?: Record<string, unknown>;
  /** Updated default convergence */
  defaultConvergence?: ConvergenceCriteria;
  /** Updated auto-continue setting */
  autoContinue?: boolean;
  /** Updated stop on failure setting */
  stopOnFailure?: boolean;
  /** Updated tags */
  tags?: string[];
}

/**
 * Input for adding a step to a pipeline
 */
export interface PipelineStepInput {
  /** Step name */
  name: string;
  /** Role ID to execute */
  roleId: string;
  /** Action/task description */
  action: string;
  /** Input template */
  input?: Record<string, unknown>;
  /** Output schema description */
  outputSchema?: string;
  /** Convergence settings */
  convergence?: ConvergenceCriteria;
  /** Optional step */
  optional?: boolean;
  /** Execution condition */
  condition?: string;
  /** Timeout in ms */
  timeoutMs?: number;
  /** Retry count */
  retryCount?: number;
  /** Position to insert (default: end) */
  position?: number;
}

/**
 * Input for starting a pipeline run
 */
export interface PipelineRunInput {
  /** Pipeline ID to run */
  pipelineId: string;
  /** Input data for the run */
  input?: Record<string, unknown>;
  /** Override auto-continue for this run */
  autoContinue?: boolean;
  /** Start from specific step index */
  startFromStep?: number;
}

/**
 * Query filters for listing pipelines
 */
export interface PipelineQueryFilters {
  /** Filter by name (partial match) */
  nameContains?: string;
  /** Filter by tag */
  tag?: string;
  /** Limit number of results */
  limit?: number;
  /** Offset for pagination */
  offset?: number;
}

/**
 * Result of a pipeline list query
 */
export interface PipelineListResult {
  /** Pipelines matching the query */
  pipelines: Pipeline[];
  /** Total count (before pagination) */
  total: number;
  /** Whether there are more results */
  hasMore: boolean;
}

/**
 * Query filters for listing pipeline runs
 */
export interface PipelineRunQueryFilters {
  /** Filter by pipeline ID */
  pipelineId?: string;
  /** Filter by status */
  status?: PipelineRunStatus | PipelineRunStatus[];
  /** Filter by date range start */
  fromDate?: string;
  /** Filter by date range end */
  toDate?: string;
  /** Limit number of results */
  limit?: number;
  /** Offset for pagination */
  offset?: number;
}

/**
 * Result of a pipeline run list query
 */
export interface PipelineRunListResult {
  /** Runs matching the query */
  runs: PipelineRunState[];
  /** Total count (before pagination) */
  total: number;
  /** Whether there are more results */
  hasMore: boolean;
}

/**
 * Events emitted during pipeline execution
 */
export type PipelineEvent = 
  | { type: 'run_started'; runId: string; pipelineId: string }
  | { type: 'step_started'; runId: string; stepId: string; stepIndex: number }
  | { type: 'step_converging'; runId: string; stepId: string; iteration: number }
  | { type: 'step_completed'; runId: string; stepId: string; output?: Record<string, unknown> }
  | { type: 'step_failed'; runId: string; stepId: string; error: string }
  | { type: 'step_skipped'; runId: string; stepId: string; reason: string }
  | { type: 'run_completed'; runId: string; output?: Record<string, unknown> }
  | { type: 'run_failed'; runId: string; error: string }
  | { type: 'run_paused'; runId: string; reason?: string }
  | { type: 'run_cancelled'; runId: string; reason?: string };
