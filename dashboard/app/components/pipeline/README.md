# Pipeline Editor

A visual pipeline editor built with Vue Flow for creating and managing AI orchestration pipelines.

## Overview

The Pipeline Editor provides a drag-and-drop interface for building agent pipelines. Users can:
- Create pipelines with Start, End, and Role nodes
- Connect nodes to define execution flow
- Configure individual role nodes with model and thinking level overrides
- Run pipelines and monitor execution in real-time
- View agent logs during/after execution

## Architecture

```
pipelines/
├── [id].vue              # Main pipeline editor page
├── PipelineCanvas.vue    # Vue Flow canvas wrapper with drag-drop
├── PipelineSidebar.vue   # Node palette for drag-and-drop
├── PipelineToolbar.vue   # Save, run, layout, zoom controls
├── PipelinePropertiesPanel.vue  # Node configuration panel
├── KeyboardShortcutsHelp.vue    # Shortcuts modal
├── LogViewerModal.vue    # Real-time log viewer
├── RoleNode.vue          # Role node component
└── nodes/
    ├── StartNode.vue     # Start node component
    └── EndNode.vue       # End node component
```

## Components

### PipelineCanvas

Main canvas component wrapping Vue Flow with custom configuration.

**Features:**
- Drag-and-drop node creation from sidebar
- Connection validation (prevents cycles, self-connections, invalid handle types)
- Snap-to-grid (15px)
- MiniMap for navigation
- Custom theming matching SwarmOps design

**Props:**
- `nodes: PipelineNode[]` - Pipeline nodes
- `edges: PipelineEdge[]` - Pipeline edges

**Events:**
- `update:nodes` - Emitted when nodes change
- `update:edges` - Emitted when edges change
- `node-click` - Emitted when a node is clicked
- `connect` - Emitted when a connection is made

### PipelineSidebar

Draggable node palette containing:
- **Flow Control**: Start and End nodes
- **Agent Roles**: Dynamically loaded from `/api/orchestrator/roles`

Roles display:
- Name
- Thinking level badge (🧠 high, 💭 medium, 💡 low)
- Model shortname

### PipelineToolbar

Toolbar with pipeline controls:
- **Validation Summary**: Shows error/warning count, expandable error panel
- **Save Button**: Saves pipeline (disabled if invalid)
- **Run Button**: Starts pipeline execution
- **Auto Layout**: Arranges nodes using Dagre algorithm
- **Zoom Controls**: Zoom in/out, fit view, reset view

### PipelinePropertiesPanel

Right-side panel for configuring selected nodes.

**Role Node Configuration:**
- Label
- Role selection (dropdown)
- Model override
- Thinking level (None/Low/Medium/High)
- Action context

**Start/End Nodes:**
- Label only

### RoleNode

Custom Vue Flow node for agent roles with:
- Role icon and name
- Thinking level indicator
- Model display
- Execution status with visual feedback:
  - **Running**: Pulsing border animation, spinner
  - **Completed**: Green checkmark
  - **Error**: Red X, shake animation
  - **Pending**: Yellow border
- Logs button (visible when running/completed/error)
- Validation error tooltip

### LogViewerModal

Real-time log viewer modal with:
- Live log streaming (2s polling when running)
- Search/filter functionality
- Toggle for tool results visibility
- Auto-scroll with manual follow toggle
- Color-coded log entries by role (user/assistant/tool)

## Composables

### `usePipeline`

CRUD operations for pipelines.

```typescript
const {
  pipelines,        // Ref<Pipeline[]>
  pending,          // Ref<boolean>
  error,            // Ref<Error | null>
  refresh,          // () => Promise<void>
  createPipeline,   // (data) => Promise<Pipeline>
  updatePipeline,   // (id, data) => Promise<Pipeline>
  deletePipeline,   // (id) => Promise<void>
  runPipeline,      // (id) => Promise<void>
} = usePipeline()
```

### `usePipelineValidation`

Reactive pipeline graph validation.

```typescript
const {
  isValid,          // ComputedRef<boolean>
  errors,           // ComputedRef<ValidationIssue[]>
  hasCycles,        // ComputedRef<boolean>
  errorCount,       // ComputedRef<number>
  warningCount,     // ComputedRef<number>
  getNodeErrors,    // (nodeId: string) => ValidationIssue[]
  hasNodeError,     // (nodeId: string) => boolean
} = usePipelineValidation(graphRef)
```

**Validation Rules:**
- Must have exactly one Start node
- Must have exactly one End node
- No cycles allowed (DFS-based detection)
- Start node must have outgoing connections
- End node must have incoming connections
- No orphan nodes (warning)

### `usePipelineExecution`

Manages pipeline execution state with polling.

```typescript
const {
  isRunning,        // Ref<boolean>
  nodeStatuses,     // Ref<Map<string, ExecutionStatus>>
  error,            // Ref<string | null>
  completionPercent,// ComputedRef<number>
  start,            // (context?) => Promise<boolean>
  stop,             // () => Promise<boolean>
  setNodeMapping,   // (nodes: PipelineNode[]) => void
  getNodeStatus,    // (nodeId: string) => ExecutionStatus
} = usePipelineExecution({ pipelineId })
```

### `usePipelineExecutionContext`

Provides execution state to child components via Vue's provide/inject.

```typescript
// In parent
providePipelineExecution({
  nodeStatuses,
  isRunning,
  getNodeStatus,
})

// In child (e.g., RoleNode)
const ctx = usePipelineExecutionContext()
const status = ctx?.getNodeStatus(props.id) || 'idle'
```

### `useAutoLayout`

Dagre-based automatic graph layout.

```typescript
const { layout, layouting, computeDagreLayout } = useAutoLayout({
  direction: 'LR',      // 'TB' | 'BT' | 'LR' | 'RL'
  nodeWidth: 200,
  nodeHeight: 80,
  nodeSpacing: 60,
  rankSpacing: 120,
  animate: true,
  animationDuration: 300,
})

await layout() // Animates nodes to computed positions
```

### `useUndoRedo`

Undo/redo history for nodes and edges.

```typescript
const {
  canUndo,          // ComputedRef<boolean>
  canRedo,          // ComputedRef<boolean>
  historyLength,    // ComputedRef<number>
  undo,             // () => boolean
  redo,             // () => boolean
  saveState,        // () => void
  clearHistory,     // () => void
  initialize,       // () => void
  batch,            // <T>(fn: () => T) => T
  registerKeyboardShortcuts, // () => () => void
} = useUndoRedo(nodesRef, edgesRef, { maxHistory: 50, debounceMs: 300 })
```

### `useAutoSave`

Debounced auto-save with status tracking.

```typescript
const {
  saving,           // Ref<boolean>
  error,            // Ref<string | null>
  lastSaved,        // Ref<Date | null>
  hasUnsavedChanges,// Ref<boolean>
  saveNow,          // () => Promise<void>
  cancel,           // () => void
} = useAutoSave({
  source: graphRef,
  onSave: async (data) => { /* save logic */ },
  debounceMs: 2000,
})
```

## API Endpoints

### Pipelines

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orchestrator/pipelines` | List all pipelines |
| GET | `/api/orchestrator/pipelines/[id]` | Get pipeline by ID |
| POST | `/api/orchestrator/pipelines` | Create pipeline |
| PUT | `/api/orchestrator/pipelines/[id]` | Update pipeline |
| DELETE | `/api/orchestrator/pipelines/[id]` | Delete pipeline |
| POST | `/api/orchestrator/pipelines/[id]/run` | Run pipeline |
| GET | `/api/orchestrator/pipelines/[id]/runs` | Get pipeline runs |

### Roles

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orchestrator/roles` | List all roles |
| POST | `/api/orchestrator/roles` | Create role |
| PUT | `/api/orchestrator/roles/[id]` | Update role |
| DELETE | `/api/orchestrator/roles/[id]` | Delete role |

### Execution

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orchestrator/runs` | Get active runs |
| GET | `/api/orchestrator/workers` | Get active workers |
| GET | `/api/orchestrator/workers/[sessionId]/logs` | Get worker logs |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/⌘ + S` | Save pipeline |
| `Ctrl/⌘ + Z` | Undo |
| `Ctrl/⌘ + Shift + Z` | Redo |
| `Ctrl/⌘ + Y` | Redo (Windows) |
| `Ctrl/⌘ + A` | Select all nodes |
| `Delete` / `Backspace` | Delete selected |
| `Escape` | Deselect all |
| `?` | Toggle shortcuts help |
| `Scroll` | Zoom in/out |
| `Drag canvas` | Pan view |

## Types

### PipelineNode

```typescript
interface PipelineNode {
  id: string
  type: 'start' | 'end' | 'role'
  position: { x: number; y: number }
  data: StartNodeData | EndNodeData | RoleNodeData
}

interface RoleNodeData {
  type: 'role'
  label: string
  roleId?: string
  config?: {
    model?: string
    thinkingLevel?: 'none' | 'low' | 'medium' | 'high'
    action?: string
  }
  executionStatus?: ExecutionStatus
}
```

### PipelineEdge

```typescript
interface PipelineEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
  type?: 'default' | 'smoothstep' | 'step' | 'straight'
  animated?: boolean
}
```

### ExecutionStatus

```typescript
type ExecutionStatus = 'idle' | 'pending' | 'running' | 'completed' | 'error' | 'skipped'
```

### ValidationIssue

```typescript
interface ValidationIssue {
  type: 'error' | 'warning'
  code: string
  message: string
  nodeId?: string
  edgeId?: string
}
```

## Usage Example

```vue
<script setup>
import { usePipeline } from '~/composables/usePipeline'
import { usePipelineValidation } from '~/composables/usePipelineValidation'

const nodes = ref([
  { id: 'start-1', type: 'start', position: { x: 100, y: 200 }, data: { label: 'Start' } },
  { id: 'role-1', type: 'role', position: { x: 300, y: 200 }, data: { label: 'Reviewer', roleId: 'reviewer' } },
  { id: 'end-1', type: 'end', position: { x: 500, y: 200 }, data: { label: 'End' } },
])

const edges = ref([
  { id: 'e1', source: 'start-1', target: 'role-1' },
  { id: 'e2', source: 'role-1', target: 'end-1' },
])

const graph = computed(() => ({ nodes: nodes.value, edges: edges.value }))
const { isValid, errors } = usePipelineValidation(graph)
const { createPipeline } = usePipeline()

async function save() {
  if (!isValid.value) return
  await createPipeline({ name: 'My Pipeline', graph: graph.value })
}
</script>
```

## Styling

The editor uses CSS custom properties for theming:

```css
--swarm-bg: #11111b
--swarm-bg-card: #1e1e2e
--swarm-bg-hover: #181825
--swarm-border: #313244
--swarm-text-primary: #cdd6f4
--swarm-text-secondary: #a6adc8
--swarm-text-muted: #6c7086
--swarm-accent: #89b4fa
--swarm-accent-bg: rgba(137, 180, 250, 0.1)
--swarm-success: #a6e3a1
--swarm-error: #ef4444
--swarm-warning: #f59e0b
```
