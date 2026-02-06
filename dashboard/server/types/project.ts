export type ProjectStatus = 'pending' | 'running' | 'paused' | 'completed' | 'error'
export type ProjectPhase = 'interview' | 'spec' | 'build' | 'review' | 'complete'

export interface Project {
  name: string
  phase: ProjectPhase
  iteration: number
  status: ProjectStatus
  startedAt: string
  completedAt?: string
  path: string
}

export interface Iteration {
  iteration: number
  timestamp: string
  success: boolean
  done: boolean
  output?: string
  duration?: number
  tokensUsed?: number
  filesChanged?: string[]
}

export interface HistoryEntry {
  iteration: number
  timestamp: string
}

export interface ProjectState {
  project: string
  phase: ProjectPhase
  iteration: number
  status: ProjectStatus
  startedAt: string
  completedAt?: string
  history: HistoryEntry[]
}

export interface Progress {
  status: string
  completedTasks: string[]
  currentTask: string | null
  blockers: string[]
  filesCreated: string[]
  notes: string[]
  raw: string
}

export type ControlActionType = 'kill' | 'pause' | 'resume' | 'trigger' | 'phase-change'

export interface ControlAction {
  type: ControlActionType
  project: string
  phase?: ProjectPhase
  timestamp?: string
}

export interface ProjectListItem extends Project {
  iterationCount: number
  lastActivity?: string
}
