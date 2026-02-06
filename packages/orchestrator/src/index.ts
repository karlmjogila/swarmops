/**
 * @ralph/orchestrator
 * 
 * Agent orchestration platform for managing roles, pipelines, and work sessions.
 */

export const VERSION = '0.1.0';

// Export all modules
export * from './types';
export * from './storage';
export * from './api';
export * from './validation';
export * from './state';
export * from './services';

// Re-export key items for convenience
export { 
  Role, 
  RoleCreateInput, 
  RoleUpdateInput,
  ThinkingLevel,
  ModelId,
  DEFAULT_ROLE_VALUES,
  BUILTIN_ROLES,
} from './types';

export type {
  WorkStatus,
  WorkType,
  WorkItem,
  WorkEvent,
  WorkCreateInput,
  WorkEventInput,
  WorkQueryFilters,
  WorkListResult,
} from './types';

export type {
  SessionStatus,
  SessionTokenUsage,
  TrackedSession,
  SessionSpawnInput,
  SessionListFilters,
  SessionListResult,
  SessionUpdateInput,
} from './types';

export {
  DEFAULT_TOKEN_USAGE,
  ACTIVE_SESSION_STATUSES,
  TERMINAL_SESSION_STATUSES,
} from './types';

export {
  RoleStorage,
  getRoleStorage,
  StorageError,
  NotFoundError,
  ConflictError,
} from './storage';

export {
  WorkStorage,
  getWorkStorage,
  InvalidTransitionError,
} from './storage';

export {
  SessionStorage,
  getSessionStorage,
} from './storage';

export {
  Router,
  createApiRouter,
  createApiHandler,
  createRolesRouter,
  createWorkRouter,
} from './api';

export {
  ValidationError,
  validateRoleCreate,
  validateRoleUpdate,
} from './validation';

export {
  WorkStateMachine,
  getWorkStateMachine,
  workStateMachine,
  TERMINAL_STATES,
} from './state';

export {
  OrchestratorService,
  getOrchestratorService,
} from './services';

export type {
  SessionAssignment,
  SessionCompletionResult,
} from './services';

// Phase 4: OpenClaw Integration
export {
  OpenClawService,
  getOpenClawService,
  resetOpenClawService,
} from './services';

export type {
  OpenClawConfig,
  OpenClawSpawnOptions,
  OpenClawSessionInfo,
  OpenClawSendOptions,
  OpenClawResponse,
} from './services';

// Phase 4: Webhooks
export {
  WebhookService,
  getWebhookService,
  resetWebhookService,
} from './services';

export type {
  WebhookConfig,
  WebhookCreateInput,
  WebhookUpdateInput,
  WebhookEventType,
  WebhookPayload,
  WebhookDelivery,
} from './services';

// Phase 4: Config Export/Import
export {
  ConfigExportService,
  getConfigExportService,
  resetConfigExportService,
} from './services';

export type {
  ExportBundle,
  ExportManifest,
  ExportedRole,
  ExportedPipeline,
  ExportedWebhook,
  ExportOptions,
  ImportOptions,
  ImportResult,
} from './services';

// Phase 4 API routers
export {
  createWebhooksRouter,
  createConfigRouter,
  createOpenClawRouter,
} from './api';
