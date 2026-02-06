/**
 * Type exports for the Agent Orchestration Platform
 */

export * from './role';
export * from './work';
export * from './session';
export * from './pipeline';

// Re-export commonly used types for convenience
export type {
  Role,
  RoleCreateInput,
  RoleUpdateInput,
  ThinkingLevel,
  ModelId,
} from './role';

export type {
  WorkStatus,
  WorkType,
  WorkItem,
  WorkEvent,
  WorkTimestamps,
  WorkCreateInput,
  WorkEventInput,
  WorkQueryFilters,
  WorkListResult,
} from './work';

export type {
  SessionStatus,
  SessionTokenUsage,
  TrackedSession,
  SessionSpawnInput,
  SessionListFilters,
  SessionListResult,
  SessionUpdateInput,
} from './session';

export type {
  Pipeline,
  PipelineStep,
  PipelineStepState,
  PipelineRunState,
  PipelineCreateInput,
  PipelineUpdateInput,
  PipelineStepInput,
  PipelineRunInput,
  PipelineQueryFilters,
  PipelineListResult,
  PipelineRunQueryFilters,
  PipelineRunListResult,
  PipelineEvent,
  PipelineRunStatus,
  PipelineStepStatus,
  ConvergenceCriteria,
} from './pipeline';

export {
  DEFAULT_TOKEN_USAGE,
  ACTIVE_SESSION_STATUSES,
  TERMINAL_SESSION_STATUSES,
} from './session';

export {
  DEFAULT_CONVERGENCE,
} from './pipeline';
