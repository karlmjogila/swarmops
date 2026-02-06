import { computed, type Ref, type ComputedRef } from 'vue'
import type { PipelineGraph, PipelineNode, PipelineEdge, ValidationIssue, PipelineValidation } from '~/types/pipeline'

/**
 * DFS-based cycle detection using Tarjan's algorithm variant.
 * 
 * Uses three sets to track node states during traversal:
 * - visited: nodes that have been fully processed
 * - recursionStack: nodes currently in the DFS path
 * - path: ordered list of nodes in current path (for extracting cycle)
 * 
 * @param nodes - Array of pipeline nodes
 * @param edges - Array of pipeline edges
 * @returns Array of cycles, where each cycle is an array of node IDs
 * 
 * @example
 * // Graph with cycle: A -> B -> C -> A
 * const cycles = detectCycles(nodes, edges)
 * // Returns: [['A', 'B', 'C', 'A']]
 */
function detectCycles(nodes: PipelineNode[], edges: PipelineEdge[]): string[][] {
  const adjacency = new Map<string, string[]>()
  const nodeIds = new Set(nodes.map(n => n.id))

  // Build adjacency list
  for (const node of nodes) {
    adjacency.set(node.id, [])
  }
  for (const edge of edges) {
    if (nodeIds.has(edge.source) && nodeIds.has(edge.target)) {
      adjacency.get(edge.source)!.push(edge.target)
    }
  }

  const cycles: string[][] = []
  const visited = new Set<string>()
  const recursionStack = new Set<string>()
  const path: string[] = []

  function dfs(nodeId: string): boolean {
    visited.add(nodeId)
    recursionStack.add(nodeId)
    path.push(nodeId)

    const neighbors = adjacency.get(nodeId) || []
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (dfs(neighbor)) return true
      } else if (recursionStack.has(neighbor)) {
        // Found cycle - extract it from path
        const cycleStart = path.indexOf(neighbor)
        const cycle = path.slice(cycleStart)
        cycle.push(neighbor) // close the cycle
        cycles.push(cycle)
      }
    }

    path.pop()
    recursionStack.delete(nodeId)
    return false
  }

  for (const node of nodes) {
    if (!visited.has(node.id)) {
      dfs(node.id)
    }
  }

  return cycles
}

/**
 * Find nodes that are disconnected from the pipeline graph.
 * 
 * A node is considered orphan if:
 * - Start node: has no outgoing edges
 * - End node: has no incoming edges  
 * - Role node: has neither incoming nor outgoing edges
 * 
 * @param nodes - Array of pipeline nodes
 * @param edges - Array of pipeline edges
 * @returns Array of orphaned nodes
 */
function findOrphanNodes(nodes: PipelineNode[], edges: PipelineEdge[]): PipelineNode[] {
  if (nodes.length <= 1) return []

  const hasIncoming = new Set<string>()
  const hasOutgoing = new Set<string>()

  for (const edge of edges) {
    hasOutgoing.add(edge.source)
    hasIncoming.add(edge.target)
  }

  return nodes.filter(node => {
    // Start nodes don't need incoming edges
    if (node.type === 'start') return !hasOutgoing.has(node.id)
    // End nodes don't need outgoing edges
    if (node.type === 'end') return !hasIncoming.has(node.id)
    // Role nodes need both
    return !hasIncoming.has(node.id) && !hasOutgoing.has(node.id)
  })
}

/**
 * Find nodes of a specific type
 */
function findNodesByType(nodes: PipelineNode[], type: PipelineNode['type']): PipelineNode[] {
  return nodes.filter(n => n.type === type)
}

/**
 * Validates a pipeline graph against structural rules.
 * 
 * Validation checks performed:
 * 1. Empty graph (warning)
 * 2. Exactly one Start node (error if 0 or >1)
 * 3. Exactly one End node (error if 0 or >1)
 * 4. No cycles in the graph (error for each cycle)
 * 5. No orphan nodes (warning)
 * 6. Start node has outgoing connections (error)
 * 7. End node has incoming connections (error)
 * 8. Edges reference valid nodes (error)
 * 
 * @param graph - Pipeline graph containing nodes and edges
 * @returns Validation result with valid flag and array of issues
 * 
 * @example
 * const result = validatePipelineGraph({ nodes, edges })
 * if (!result.valid) {
 *   console.log('Errors:', result.issues.filter(i => i.type === 'error'))
 * }
 */
export function validatePipelineGraph(graph: PipelineGraph): PipelineValidation {
  const issues: ValidationIssue[] = []
  const { nodes, edges } = graph

  // Check for empty graph
  if (nodes.length === 0) {
    issues.push({
      type: 'warning',
      code: 'EMPTY_GRAPH',
      message: 'Pipeline has no nodes',
    })
    return { valid: true, issues }
  }

  // Check for multiple start nodes
  const startNodes = findNodesByType(nodes, 'start')
  if (startNodes.length === 0) {
    issues.push({
      type: 'error',
      code: 'NO_START_NODE',
      message: 'Pipeline must have at least one start node',
    })
  } else if (startNodes.length > 1) {
    issues.push({
      type: 'error',
      code: 'MULTIPLE_START_NODES',
      message: `Pipeline has ${startNodes.length} start nodes, expected 1`,
      nodeId: startNodes[1].id,
    })
  }

  // Check for multiple end nodes
  const endNodes = findNodesByType(nodes, 'end')
  if (endNodes.length === 0) {
    issues.push({
      type: 'error',
      code: 'NO_END_NODE',
      message: 'Pipeline must have at least one end node',
    })
  } else if (endNodes.length > 1) {
    issues.push({
      type: 'error',
      code: 'MULTIPLE_END_NODES',
      message: `Pipeline has ${endNodes.length} end nodes, expected 1`,
      nodeId: endNodes[1].id,
    })
  }

  // Check for cycles
  const cycles = detectCycles(nodes, edges)
  for (const cycle of cycles) {
    const cycleStr = cycle.join(' → ')
    issues.push({
      type: 'error',
      code: 'CYCLE_DETECTED',
      message: `Cycle detected: ${cycleStr}`,
      nodeId: cycle[0],
    })
  }

  // Check for orphan nodes
  const orphans = findOrphanNodes(nodes, edges)
  for (const orphan of orphans) {
    issues.push({
      type: 'warning',
      code: 'ORPHAN_NODE',
      message: `Node "${orphan.data.label}" is not connected to the graph`,
      nodeId: orphan.id,
    })
  }

  // Check start node has outgoing edges
  for (const start of startNodes) {
    const hasOutgoing = edges.some(e => e.source === start.id)
    if (!hasOutgoing) {
      issues.push({
        type: 'error',
        code: 'START_NO_OUTGOING',
        message: 'Start node has no outgoing connections',
        nodeId: start.id,
      })
    }
  }

  // Check end node has incoming edges
  for (const end of endNodes) {
    const hasIncoming = edges.some(e => e.target === end.id)
    if (!hasIncoming) {
      issues.push({
        type: 'error',
        code: 'END_NO_INCOMING',
        message: 'End node has no incoming connections',
        nodeId: end.id,
      })
    }
  }

  // Check for edges referencing non-existent nodes
  const nodeIds = new Set(nodes.map(n => n.id))
  for (const edge of edges) {
    if (!nodeIds.has(edge.source)) {
      issues.push({
        type: 'error',
        code: 'INVALID_EDGE_SOURCE',
        message: `Edge references non-existent source node: ${edge.source}`,
        edgeId: edge.id,
      })
    }
    if (!nodeIds.has(edge.target)) {
      issues.push({
        type: 'error',
        code: 'INVALID_EDGE_TARGET',
        message: `Edge references non-existent target node: ${edge.target}`,
        edgeId: edge.id,
      })
    }
  }

  const valid = !issues.some(i => i.type === 'error')
  return { valid, issues }
}

/**
 * Vue composable for reactive pipeline validation.
 * 
 * Automatically recomputes validation when the graph changes, providing:
 * - Overall validity state
 * - Error and warning counts
 * - Per-node and per-edge error lookups
 * - Cycle detection state
 * 
 * @param graph - Reactive reference to the pipeline graph
 * @returns Reactive validation state and helper functions
 * 
 * @example
 * const graph = computed(() => ({ nodes: nodes.value, edges: edges.value }))
 * const { isValid, errors, getNodeErrors, hasNodeError } = usePipelineValidation(graph)
 * 
 * // Use in template
 * // :class="{ 'has-error': hasNodeError(node.id) }"
 */
export function usePipelineValidation(graph: Ref<PipelineGraph> | ComputedRef<PipelineGraph>) {
  const validation = computed(() => validatePipelineGraph(graph.value))

  const isValid = computed(() => validation.value.valid)
  const errors = computed(() => validation.value.issues)
  const hasCycles = computed(() => errors.value.some(e => e.code === 'CYCLE_DETECTED'))

  const errorCount = computed(() => errors.value.filter(e => e.type === 'error').length)
  const warningCount = computed(() => errors.value.filter(e => e.type === 'warning').length)

  const errorsByNode = computed(() => {
    const map = new Map<string, ValidationIssue[]>()
    for (const error of errors.value) {
      if (error.nodeId) {
        if (!map.has(error.nodeId)) map.set(error.nodeId, [])
        map.get(error.nodeId)!.push(error)
      }
    }
    return map
  })

  const errorsByEdge = computed(() => {
    const map = new Map<string, ValidationIssue[]>()
    for (const error of errors.value) {
      if (error.edgeId) {
        if (!map.has(error.edgeId)) map.set(error.edgeId, [])
        map.get(error.edgeId)!.push(error)
      }
    }
    return map
  })

  function getNodeErrors(nodeId: string): ValidationIssue[] {
    return errorsByNode.value.get(nodeId) || []
  }

  function getEdgeErrors(edgeId: string): ValidationIssue[] {
    return errorsByEdge.value.get(edgeId) || []
  }

  function hasNodeError(nodeId: string): boolean {
    return errorsByNode.value.has(nodeId)
  }

  function hasEdgeError(edgeId: string): boolean {
    return errorsByEdge.value.has(edgeId)
  }

  return {
    // Core validation state
    isValid,
    errors,
    hasCycles,
    validation,
    // Counts
    errorCount,
    warningCount,
    // Lookup helpers
    errorsByNode,
    errorsByEdge,
    getNodeErrors,
    getEdgeErrors,
    hasNodeError,
    hasEdgeError,
  }
}
