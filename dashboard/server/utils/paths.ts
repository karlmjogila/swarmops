import { join, resolve } from 'path'

// Centralized path configuration
// All paths can be overridden via environment variables
// Uses resolve() to handle relative paths like '../projects' correctly

export const ORCHESTRATOR_DATA_DIR = resolve(process.cwd(), process.env.ORCHESTRATOR_DATA_DIR || '../data/orchestrator')
export const PROJECTS_DIR = resolve(process.cwd(), process.env.PROJECTS_DIR || '../projects')
export const DASHBOARD_PATH = process.env.DASHBOARD_PATH || process.cwd()
export const DASHBOARD_URL = `http://localhost:${process.env.PORT || 3939}`

// Derived paths
export const ROLES_FILE = join(ORCHESTRATOR_DATA_DIR, 'roles.json')
export const PIPELINES_FILE = join(ORCHESTRATOR_DATA_DIR, 'pipelines.json')
export const WORK_QUEUE_FILE = join(ORCHESTRATOR_DATA_DIR, 'work-queue.json')
export const TASK_REGISTRY_FILE = join(ORCHESTRATOR_DATA_DIR, 'task-registry.json')
export const RETRY_STATE_FILE = join(ORCHESTRATOR_DATA_DIR, 'retry-state.json')
export const ESCALATIONS_FILE = join(ORCHESTRATOR_DATA_DIR, 'escalations.json')
export const PROMPTS_DIR = join(ORCHESTRATOR_DATA_DIR, 'prompts')
export const SKILLS_DIR = join(ORCHESTRATOR_DATA_DIR, 'skills')
export const PROJECT_RUNS_DIR = join(ORCHESTRATOR_DATA_DIR, 'project-runs')
