// Pipeline type definitions for Vue Flow pipeline editor

export type NodeType = 'start' | 'end' | 'role'

export type ExecutionStatus = 'idle' | 'pending' | 'running' | 'completed' | 'error' | 'skipped'

export interface Position {
  x: number
  y: number
}

export interface NodeDimensions {
  width: number
  height: number
}

// Base node data shared across all node types
export interface BaseNodeData {
  label: string
  description?: string
}

// Start node - entry point of pipeline
export interface StartNodeData extends BaseNodeData {
  type: 'start'
}

// End node - exit point of pipeline
export interface EndNodeData extends BaseNodeData {
  type: 'end'
}

// Role node - represents an agent role in the pipeline
export interface RoleNodeData extends BaseNodeData {
  type: 'role'
  roleId?: string
  config?: Record<string, unknown>
  // Execution state (runtime only, not persisted)
  executionStatus?: ExecutionStatus
  executionError?: string
  executionStartedAt?: string
  executionCompletedAt?: string
}

export type PipelineNodeData = StartNodeData | EndNodeData | RoleNodeData

// Pipeline node as stored/used by Vue Flow
export interface PipelineNode {
  id: string
  type: NodeType
  position: Position
  data: PipelineNodeData
  // Optional Vue Flow properties
  dimensions?: NodeDimensions
  selected?: boolean
  dragging?: boolean
}

// Connection handle types
export type HandleType = 'source' | 'target'

// Pipeline edge (connection between nodes)
export interface PipelineEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
  // Edge styling
  type?: 'default' | 'smoothstep' | 'step' | 'straight'
  animated?: boolean
  label?: string
  // Runtime state
  selected?: boolean
}

// Pipeline viewport state
export interface Viewport {
  x: number
  y: number
  zoom: number
}

// Pipeline graph data (nodes and edges)
export interface PipelineGraph {
  nodes: PipelineNode[]
  edges: PipelineEdge[]
  viewport?: Viewport
}

// Pipeline metadata and configuration
export interface PipelineMetadata {
  name: string
  description?: string
  version?: number
  createdAt: string
  updatedAt: string
  createdBy?: string
  tags?: string[]
}

// Full pipeline definition
export interface Pipeline extends PipelineMetadata {
  id: string
  graph: PipelineGraph
  isDefault?: boolean
}

// Pipeline list item (summary for listing)
export interface PipelineListItem {
  id: string
  name: string
  description?: string
  isDefault: boolean
  nodeCount: number
  edgeCount: number
  createdAt: string
  updatedAt: string
}

// Pipeline creation payload
export interface CreatePipelinePayload {
  name: string
  description?: string
  graph?: PipelineGraph
  isDefault?: boolean
}

// Pipeline update payload
export interface UpdatePipelinePayload {
  name?: string
  description?: string
  graph?: PipelineGraph
  isDefault?: boolean
}

// Validation result for a single issue
export interface ValidationIssue {
  type: 'error' | 'warning'
  code: string
  message: string
  nodeId?: string
  edgeId?: string
}

// Pipeline validation result
export interface PipelineValidation {
  valid: boolean
  issues: ValidationIssue[]
}

// Execution state for a single node
export interface NodeExecutionState {
  nodeId: string
  status: ExecutionStatus
  startedAt?: string
  completedAt?: string
  error?: string
  logs?: string[]
  output?: unknown
}

// Pipeline execution state
export interface PipelineExecution {
  id: string
  pipelineId: string
  status: ExecutionStatus
  startedAt: string
  completedAt?: string
  nodeStates: Record<string, NodeExecutionState>
  error?: string
}

// Pipeline execution summary for listing
export interface PipelineExecutionSummary {
  id: string
  pipelineId: string
  pipelineName: string
  status: ExecutionStatus
  startedAt: string
  completedAt?: string
  duration?: number
}

// Drag event payload from sidebar
export interface DragNodePayload {
  type: NodeType
  label: string
}

// Auto-layout options
export interface LayoutOptions {
  direction: 'TB' | 'BT' | 'LR' | 'RL'
  nodeSpacing: number
  rankSpacing: number
}

// Undo/redo history entry
export interface HistoryState {
  graph: PipelineGraph
  timestamp: number
}
