<script setup lang="ts">
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { MiniMap } from '@vue-flow/minimap'
import type { Node, Edge, Connection } from '@vue-flow/core'
import type { PipelineNode, PipelineEdge, NodeType, RoleNodeData } from '~/types/pipeline'
import RoleNode from './RoleNode.vue'
import StartNode from './nodes/StartNode.vue'
import EndNode from './nodes/EndNode.vue'
import '@vue-flow/minimap/dist/style.css'

const props = defineProps<{
  nodes: PipelineNode[]
  edges: PipelineEdge[]
}>()

const emit = defineEmits<{
  'update:nodes': [nodes: PipelineNode[]]
  'update:edges': [edges: PipelineEdge[]]
  'nodes-change': [changes: unknown[]]
  'edges-change': [changes: unknown[]]
  'connect': [connection: Connection]
  'node-click': [event: MouseEvent, node: PipelineNode]
}>()

// Vue Flow instance and utilities
const {
  screenToFlowCoordinate,
  onConnect,
  onNodesChange,
  onEdgesChange,
  addNodes,
  getNode,
} = useVueFlow()

// Connection validation
function isValidConnection(connection: Connection): boolean {
  const { source, target, sourceHandle, targetHandle } = connection
  
  // Rule 1: Prevent self-connections
  if (source === target) {
    return false
  }

  // Get source and target nodes
  const sourceNode = getNode.value(source!)
  const targetNode = getNode.value(target!)

  if (!sourceNode || !targetNode) {
    return false
  }

  // Rule 2: Start nodes can only have outgoing connections
  // Start nodes cannot be a target
  if (targetNode.type === 'start') {
    return false
  }

  // Rule 3: End nodes can only have incoming connections
  // End nodes cannot be a source
  if (sourceNode.type === 'end') {
    return false
  }

  // Rule 4: Validate handle types for role nodes
  if (sourceNode.type === 'role') {
    if (sourceHandle && sourceHandle !== 'source') {
      return false
    }
  }

  if (targetNode.type === 'role') {
    if (targetHandle && targetHandle !== 'target') {
      return false
    }
  }

  // Rule 5: Prevent duplicate connections
  const existingConnection = props.edges.find(
    edge => edge.source === source && edge.target === target
  )
  if (existingConnection) {
    return false
  }

  return true
}

// Custom node types registration
const nodeTypes = {
  role: markRaw(RoleNode),
  start: markRaw(StartNode),
  end: markRaw(EndNode),
}

// Track drag state for visual feedback
const isDragOver = ref(false)

// Handle drag over - allow drop
function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
  isDragOver.value = true
}

function onDragLeave() {
  isDragOver.value = false
}

// Handle drop - create new node at drop position
function onDrop(event: DragEvent) {
  event.preventDefault()
  isDragOver.value = false

  if (!event.dataTransfer) return

  const dataStr = event.dataTransfer.getData('application/vueflow')
  if (!dataStr) return

  let dragData: Record<string, unknown>
  try {
    dragData = JSON.parse(dataStr)
  } catch {
    console.error('Failed to parse drag data')
    return
  }

  const nodeType = dragData.type as NodeType
  if (!nodeType) return

  // Calculate drop position relative to canvas viewport
  // screenToFlowCoordinate converts screen coordinates to flow coordinates
  const position = screenToFlowCoordinate({
    x: event.clientX,
    y: event.clientY,
  })

  // Generate unique node ID
  const nodeId = `${nodeType}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`

  // Create node based on type
  const newNode = createNode(nodeId, nodeType, position, dragData)

  // Add node to flow
  addNodes([newNode])

  // Emit updated nodes list
  const updatedNodes = [...props.nodes, newNode as PipelineNode]
  emit('update:nodes', updatedNodes)
}

// Create node with proper data structure based on type
function createNode(
  id: string,
  type: NodeType,
  position: { x: number; y: number },
  dragData: Record<string, unknown>
): Node {
  const baseNode = {
    id,
    type,
    position,
  }

  switch (type) {
    case 'start':
      return {
        ...baseNode,
        data: {
          type: 'start',
          label: (dragData.label as string) || 'Start',
        },
      }

    case 'end':
      return {
        ...baseNode,
        data: {
          type: 'end',
          label: (dragData.label as string) || 'End',
        },
      }

    case 'role':
      return {
        ...baseNode,
        data: {
          type: 'role',
          label: (dragData.roleName as string) || 'Role',
          roleId: dragData.roleId as string,
          roleName: dragData.roleName as string,
          model: dragData.model as string | undefined,
          thinkingLevel: dragData.thinkingLevel as RoleNodeData['executionStatus'] | undefined,
        } satisfies RoleNodeData,
      }

    default:
      return {
        ...baseNode,
        data: {
          label: 'Unknown',
        },
      }
  }
}

// Forward Vue Flow events to parent
onNodesChange((changes) => {
  emit('nodes-change', changes)
})

onEdgesChange((changes) => {
  emit('edges-change', changes)
})

onConnect((connection) => {
  emit('connect', connection)
})

function handleNodeClick(event: MouseEvent, node: Node) {
  emit('node-click', event, node as PipelineNode)
}

// MiniMap node color based on type
function getNodeColor(node: Node): string {
  switch (node.type) {
    case 'start':
      return '#a6e3a1' // green
    case 'end':
      return '#f38ba8' // red
    case 'role':
      return '#89b4fa' // blue
    default:
      return '#6c7086' // muted gray
  }
}
</script>

<template>
  <div 
    class="pipeline-canvas"
    :class="{ 'drag-over': isDragOver }"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <VueFlow
      :nodes="nodes"
      :edges="edges"
      :node-types="nodeTypes"
      :default-viewport="{ x: 0, y: 0, zoom: 1 }"
      :min-zoom="0.25"
      :max-zoom="2"
      :snap-to-grid="true"
      :snap-grid="[15, 15]"
      :is-valid-connection="isValidConnection"
      fit-view-on-init
      class="vue-flow-canvas"
      @node-click="handleNodeClick"
    >
      <!-- Background pattern -->
      <template #default>
        <slot />
      </template>

      <!-- MiniMap in bottom-right corner -->
      <MiniMap
        :node-color="getNodeColor"
        :node-stroke-color="getNodeColor"
        :mask-color="'rgba(17, 17, 27, 0.8)'"
        pannable
        zoomable
      />
    </VueFlow>

    <!-- Drop zone indicator -->
    <Transition name="fade">
      <div v-if="isDragOver" class="drop-indicator">
        <div class="drop-indicator-content">
          <UIcon name="i-heroicons-plus-circle" class="w-8 h-8" />
          <span>Drop to add node</span>
        </div>
      </div>
    </Transition>

    <!-- Empty state hint -->
    <div v-if="!nodes.length" class="empty-hint">
      <UIcon name="i-heroicons-cursor-arrow-ripple" class="w-10 h-10" />
      <p>Drag nodes from the sidebar to start building your pipeline</p>
    </div>
  </div>
</template>

<style scoped>
.pipeline-canvas {
  position: relative;
  width: 100%;
  height: 100%;
  background: var(--swarm-bg, #11111b);
  border-radius: 8px;
  overflow: hidden;
}

.vue-flow-canvas {
  width: 100%;
  height: 100%;
}

/* Vue Flow theme overrides */
:deep(.vue-flow__background) {
  background-color: var(--swarm-bg, #11111b);
}

:deep(.vue-flow__background pattern circle) {
  fill: var(--swarm-border, #313244);
}

:deep(.vue-flow__edge-path) {
  stroke: var(--swarm-border, #313244);
  stroke-width: 2;
}

:deep(.vue-flow__edge.selected .vue-flow__edge-path) {
  stroke: var(--swarm-accent, #89b4fa);
}

:deep(.vue-flow__edge:hover .vue-flow__edge-path) {
  stroke: var(--swarm-accent, #89b4fa);
}

:deep(.vue-flow__connection-line) {
  stroke: var(--swarm-accent, #89b4fa);
  stroke-width: 2;
}

:deep(.vue-flow__controls) {
  background: var(--swarm-bg-card, #1e1e2e);
  border: 1px solid var(--swarm-border, #313244);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

:deep(.vue-flow__controls-button) {
  background: transparent;
  border: none;
  color: var(--swarm-text-secondary, #a6adc8);
  width: 28px;
  height: 28px;
}

:deep(.vue-flow__controls-button:hover) {
  background: var(--swarm-bg-hover, #181825);
  color: var(--swarm-text-primary, #cdd6f4);
}

:deep(.vue-flow__minimap) {
  background: var(--swarm-bg-card, #1e1e2e);
  border: 1px solid var(--swarm-border, #313244);
  border-radius: 8px;
  bottom: 16px;
  right: 16px;
  top: auto;
  left: auto;
}

:deep(.vue-flow__minimap-mask) {
  fill: rgba(17, 17, 27, 0.8);
}

/* Drag over state */
.pipeline-canvas.drag-over {
  outline: 2px dashed var(--swarm-accent, #89b4fa);
  outline-offset: -2px;
}

/* Drop indicator */
.drop-indicator {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(137, 180, 250, 0.05);
  pointer-events: none;
  z-index: 100;
}

.drop-indicator-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--swarm-accent, #89b4fa);
  font-size: 14px;
  font-weight: 500;
}

/* Empty hint */
.empty-hint {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--swarm-text-muted, #6c7086);
  pointer-events: none;
  text-align: center;
  padding: 24px;
}

.empty-hint p {
  font-size: 14px;
  max-width: 280px;
  margin: 0;
}

/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
