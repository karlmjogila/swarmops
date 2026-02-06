import { describe, it, expect } from 'vitest'
import { ref, computed } from 'vue'
import { validatePipelineGraph, usePipelineValidation } from '../usePipelineValidation'
import type { PipelineGraph, PipelineNode, PipelineEdge } from '~/app/types/pipeline'

// Helper to create nodes
function createNode(id: string, type: 'start' | 'end' | 'role', label = ''): PipelineNode {
  return {
    id,
    type,
    position: { x: 0, y: 0 },
    data: { label: label || id, type } as any,
  }
}

// Helper to create edges
function createEdge(source: string, target: string): PipelineEdge {
  return {
    id: `e-${source}-${target}`,
    source,
    target,
  }
}

describe('validatePipelineGraph', () => {
  describe('empty graph', () => {
    it('returns valid with warning for empty graph', () => {
      const graph: PipelineGraph = { nodes: [], edges: [] }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(true)
      expect(result.issues).toHaveLength(1)
      expect(result.issues[0].code).toBe('EMPTY_GRAPH')
      expect(result.issues[0].type).toBe('warning')
    })
  })

  describe('start node validation', () => {
    it('detects missing start node', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('role1', 'role'),
          createNode('end', 'end'),
        ],
        edges: [createEdge('role1', 'end')],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(false)
      expect(result.issues.some(i => i.code === 'NO_START_NODE')).toBe(true)
    })

    it('detects multiple start nodes', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start1', 'start'),
          createNode('start2', 'start'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start1', 'end'),
          createEdge('start2', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(false)
      expect(result.issues.some(i => i.code === 'MULTIPLE_START_NODES')).toBe(true)
    })

    it('detects start node with no outgoing edges', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('end', 'end'),
        ],
        edges: [],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(false)
      expect(result.issues.some(i => i.code === 'START_NO_OUTGOING')).toBe(true)
    })
  })

  describe('end node validation', () => {
    it('detects missing end node', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('role1', 'role'),
        ],
        edges: [createEdge('start', 'role1')],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(false)
      expect(result.issues.some(i => i.code === 'NO_END_NODE')).toBe(true)
    })

    it('detects multiple end nodes', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('end1', 'end'),
          createNode('end2', 'end'),
        ],
        edges: [
          createEdge('start', 'end1'),
          createEdge('start', 'end2'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(false)
      expect(result.issues.some(i => i.code === 'MULTIPLE_END_NODES')).toBe(true)
    })

    it('detects end node with no incoming edges', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('role1', 'role'),
          createNode('end', 'end'),
        ],
        edges: [createEdge('start', 'role1')],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(false)
      expect(result.issues.some(i => i.code === 'END_NO_INCOMING')).toBe(true)
    })
  })

  describe('cycle detection', () => {
    it('detects simple 2-node cycle', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('a', 'role'),
          createNode('b', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'a'),
          createEdge('a', 'b'),
          createEdge('b', 'a'),
          createEdge('b', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(false)
      expect(result.issues.some(i => i.code === 'CYCLE_DETECTED')).toBe(true)
    })

    it('detects 3-node cycle', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('a', 'role'),
          createNode('b', 'role'),
          createNode('c', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'a'),
          createEdge('a', 'b'),
          createEdge('b', 'c'),
          createEdge('c', 'a'),
          createEdge('c', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(false)
      expect(result.issues.some(i => i.code === 'CYCLE_DETECTED')).toBe(true)
    })

    it('detects self-loop', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('loop', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'loop'),
          createEdge('loop', 'loop'),
          createEdge('loop', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(false)
      expect(result.issues.some(i => i.code === 'CYCLE_DETECTED')).toBe(true)
    })

    it('detects diamond pattern with back-edge', () => {
      // Diamond: start -> a -> c -> end
      //          start -> b -> c -> end
      // Plus back-edge: c -> a (creates cycle)
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('a', 'role'),
          createNode('b', 'role'),
          createNode('c', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'a'),
          createEdge('start', 'b'),
          createEdge('a', 'c'),
          createEdge('b', 'c'),
          createEdge('c', 'a'),
          createEdge('c', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(false)
      expect(result.issues.some(i => i.code === 'CYCLE_DETECTED')).toBe(true)
    })

    it('detects nested cycles', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('a', 'role'),
          createNode('b', 'role'),
          createNode('c', 'role'),
          createNode('d', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'a'),
          createEdge('a', 'b'),
          createEdge('b', 'c'),
          createEdge('c', 'b'),
          createEdge('c', 'd'),
          createEdge('d', 'a'),
          createEdge('d', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(false)
      const cycleIssues = result.issues.filter(i => i.code === 'CYCLE_DETECTED')
      expect(cycleIssues.length).toBeGreaterThanOrEqual(1)
    })

    it('passes valid DAG with diamond pattern', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('a', 'role'),
          createNode('b', 'role'),
          createNode('c', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'a'),
          createEdge('start', 'b'),
          createEdge('a', 'c'),
          createEdge('b', 'c'),
          createEdge('c', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.issues.some(i => i.code === 'CYCLE_DETECTED')).toBe(false)
    })

    it('passes valid linear pipeline', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('a', 'role'),
          createNode('b', 'role'),
          createNode('c', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'a'),
          createEdge('a', 'b'),
          createEdge('b', 'c'),
          createEdge('c', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(true)
      expect(result.issues.some(i => i.code === 'CYCLE_DETECTED')).toBe(false)
    })

    it('passes complex valid DAG', () => {
      // Complex graph with multiple paths, no cycles
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('a', 'role'),
          createNode('b', 'role'),
          createNode('c', 'role'),
          createNode('d', 'role'),
          createNode('e', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'a'),
          createEdge('start', 'b'),
          createEdge('a', 'c'),
          createEdge('a', 'd'),
          createEdge('b', 'd'),
          createEdge('c', 'e'),
          createEdge('d', 'e'),
          createEdge('e', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(true)
      expect(result.issues.some(i => i.code === 'CYCLE_DETECTED')).toBe(false)
    })
  })

  describe('orphan node detection', () => {
    it('detects role node with no connections', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('connected', 'role'),
          createNode('orphan', 'role', 'Orphan Node'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'connected'),
          createEdge('connected', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      const orphanIssue = result.issues.find(i => i.code === 'ORPHAN_NODE')
      expect(orphanIssue).toBeDefined()
      expect(orphanIssue?.nodeId).toBe('orphan')
      expect(orphanIssue?.message).toContain('Orphan Node')
    })

    it('detects start node with no outgoing edges as orphan-like', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('role1', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('role1', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      const orphanWarning = result.issues.find(
        i => i.code === 'ORPHAN_NODE' && i.nodeId === 'start'
      )
      expect(orphanWarning).toBeDefined()
    })

    it('detects end node with no incoming edges as orphan-like', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('role1', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'role1'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      const orphanWarning = result.issues.find(
        i => i.code === 'ORPHAN_NODE' && i.nodeId === 'end'
      )
      expect(orphanWarning).toBeDefined()
    })

    it('does not flag connected nodes as orphans', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('a', 'role'),
          createNode('b', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'a'),
          createEdge('a', 'b'),
          createEdge('b', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.issues.some(i => i.code === 'ORPHAN_NODE')).toBe(false)
    })

    it('detects multiple orphan nodes', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('orphan1', 'role', 'Orphan 1'),
          createNode('orphan2', 'role', 'Orphan 2'),
          createNode('connected', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'connected'),
          createEdge('connected', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      const orphanIssues = result.issues.filter(i => i.code === 'ORPHAN_NODE')
      expect(orphanIssues).toHaveLength(2)
    })
  })

  describe('invalid edge detection', () => {
    it('detects edge with non-existent source', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'end'),
          createEdge('ghost', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(false)
      expect(result.issues.some(i => i.code === 'INVALID_EDGE_SOURCE')).toBe(true)
    })

    it('detects edge with non-existent target', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'end'),
          createEdge('start', 'ghost'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(false)
      expect(result.issues.some(i => i.code === 'INVALID_EDGE_TARGET')).toBe(true)
    })
  })

  describe('valid pipelines', () => {
    it('validates minimal valid pipeline', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('end', 'end'),
        ],
        edges: [createEdge('start', 'end')],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(true)
      expect(result.issues.filter(i => i.type === 'error')).toHaveLength(0)
    })

    it('validates pipeline with single role', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('worker', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'worker'),
          createEdge('worker', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(true)
    })

    it('validates parallel branches pipeline', () => {
      const graph: PipelineGraph = {
        nodes: [
          createNode('start', 'start'),
          createNode('a', 'role'),
          createNode('b', 'role'),
          createNode('c', 'role'),
          createNode('end', 'end'),
        ],
        edges: [
          createEdge('start', 'a'),
          createEdge('start', 'b'),
          createEdge('start', 'c'),
          createEdge('a', 'end'),
          createEdge('b', 'end'),
          createEdge('c', 'end'),
        ],
      }
      const result = validatePipelineGraph(graph)
      
      expect(result.valid).toBe(true)
    })
  })
})

describe('usePipelineValidation composable', () => {
  it('provides reactive validation state', () => {
    const graph = ref<PipelineGraph>({
      nodes: [
        createNode('start', 'start'),
        createNode('end', 'end'),
      ],
      edges: [createEdge('start', 'end')],
    })
    
    const { isValid, errors, hasCycles, errorCount, warningCount } = usePipelineValidation(graph)
    
    expect(isValid.value).toBe(true)
    expect(errors.value.filter(e => e.type === 'error')).toHaveLength(0)
    expect(hasCycles.value).toBe(false)
    expect(errorCount.value).toBe(0)
    expect(warningCount.value).toBe(0)
  })

  it('updates when graph changes', () => {
    const graph = ref<PipelineGraph>({
      nodes: [
        createNode('start', 'start'),
        createNode('end', 'end'),
      ],
      edges: [createEdge('start', 'end')],
    })
    
    const { isValid, errorCount } = usePipelineValidation(graph)
    
    expect(isValid.value).toBe(true)
    
    graph.value = {
      nodes: [
        createNode('start', 'start'),
        createNode('a', 'role'),
        createNode('end', 'end'),
      ],
      edges: [
        createEdge('start', 'a'),
        createEdge('a', 'start'),
        createEdge('a', 'end'),
      ],
    }
    
    expect(isValid.value).toBe(false)
    expect(errorCount.value).toBeGreaterThan(0)
  })

  it('works with computed graph', () => {
    const nodes = ref([
      createNode('start', 'start'),
      createNode('end', 'end'),
    ])
    const edges = ref([createEdge('start', 'end')])
    
    const graph = computed(() => ({ nodes: nodes.value, edges: edges.value }))
    const { isValid } = usePipelineValidation(graph)
    
    expect(isValid.value).toBe(true)
    
    nodes.value = [...nodes.value, createNode('orphan', 'role', 'Orphan')]
    
    expect(isValid.value).toBe(true)
    const { errors } = usePipelineValidation(graph)
    expect(errors.value.some(e => e.code === 'ORPHAN_NODE')).toBe(true)
  })

  it('provides errorsByNode lookup', () => {
    const graph = ref<PipelineGraph>({
      nodes: [
        createNode('start1', 'start'),
        createNode('start2', 'start'),
        createNode('end', 'end'),
      ],
      edges: [
        createEdge('start1', 'end'),
        createEdge('start2', 'end'),
      ],
    })
    
    const { errorsByNode, getNodeErrors, hasNodeError } = usePipelineValidation(graph)
    
    expect(hasNodeError('start2')).toBe(true)
    expect(getNodeErrors('start2').length).toBeGreaterThan(0)
    expect(errorsByNode.value.has('start2')).toBe(true)
  })

  it('provides errorsByEdge lookup', () => {
    const graph = ref<PipelineGraph>({
      nodes: [
        createNode('start', 'start'),
        createNode('end', 'end'),
      ],
      edges: [
        createEdge('start', 'end'),
        createEdge('ghost', 'end'),
      ],
    })
    
    const { errorsByEdge, getEdgeErrors, hasEdgeError } = usePipelineValidation(graph)
    
    expect(hasEdgeError('e-ghost-end')).toBe(true)
    expect(getEdgeErrors('e-ghost-end').length).toBeGreaterThan(0)
    expect(errorsByEdge.value.has('e-ghost-end')).toBe(true)
  })

  it('detects cycles via hasCycles', () => {
    const graph = ref<PipelineGraph>({
      nodes: [
        createNode('start', 'start'),
        createNode('a', 'role'),
        createNode('b', 'role'),
        createNode('end', 'end'),
      ],
      edges: [
        createEdge('start', 'a'),
        createEdge('a', 'b'),
        createEdge('b', 'a'),
        createEdge('b', 'end'),
      ],
    })
    
    const { hasCycles } = usePipelineValidation(graph)
    
    expect(hasCycles.value).toBe(true)
  })

  it('counts errors and warnings separately', () => {
    const graph = ref<PipelineGraph>({
      nodes: [
        createNode('start', 'start'),
        createNode('connected', 'role'),
        createNode('orphan', 'role', 'Orphan Node'),
        createNode('end', 'end'),
      ],
      edges: [
        createEdge('start', 'connected'),
        createEdge('connected', 'end'),
      ],
    })
    
    const { errorCount, warningCount } = usePipelineValidation(graph)
    
    expect(warningCount.value).toBeGreaterThanOrEqual(1)
    expect(errorCount.value).toBe(0)
  })
})
