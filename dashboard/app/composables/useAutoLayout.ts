import dagre from 'dagre'
import { useVueFlow } from '@vue-flow/core'
import type { Node, Edge } from '@vue-flow/core'

/**
 * Configuration options for auto-layout.
 */
export interface LayoutOptions {
  /** Layout direction: TB (top-bottom), BT, LR (left-right), RL */
  direction: 'TB' | 'BT' | 'LR' | 'RL'
  /** Width of each node for spacing calculations */
  nodeWidth: number
  /** Height of each node for spacing calculations */
  nodeHeight: number
  /** Horizontal spacing between adjacent nodes */
  nodeSpacing: number
  /** Vertical spacing between ranks/levels */
  rankSpacing: number
  /** Whether to animate node transitions */
  animate: boolean
  /** Animation duration in milliseconds */
  animationDuration: number
}

const defaultOptions: LayoutOptions = {
  direction: 'LR',
  nodeWidth: 200,
  nodeHeight: 80,
  nodeSpacing: 60,
  rankSpacing: 120,
  animate: true,
  animationDuration: 300,
}

/**
 * Composable for automatic graph layout using the Dagre library.
 * 
 * Dagre computes a hierarchical layout that minimizes edge crossings
 * and distributes nodes evenly. The layout respects the graph's
 * topological order (parents before children).
 * 
 * @param options - Layout configuration options
 * @returns Layout functions and state
 * 
 * @example
 * const { layout, layouting } = useAutoLayout({ direction: 'LR' })
 * 
 * // Trigger layout (async, animates by default)
 * await layout()
 */
export function useAutoLayout(options: Partial<LayoutOptions> = {}) {
  const { getNodes, getEdges, setNodes, fitView } = useVueFlow()
  const layouting = ref(false)
  const opts = { ...defaultOptions, ...options }

  /**
   * Computes node positions using the Dagre layout algorithm.
   * 
   * @param nodes - Array of Vue Flow nodes
   * @param edges - Array of Vue Flow edges
   * @returns Nodes with updated positions
   */
  function computeDagreLayout(nodes: Node[], edges: Edge[]): Node[] {
    const dagreGraph = new dagre.graphlib.Graph()
    
    dagreGraph.setDefaultEdgeLabel(() => ({}))
    dagreGraph.setGraph({
      rankdir: opts.direction,
      nodesep: opts.nodeSpacing,
      ranksep: opts.rankSpacing,
      marginx: 50,
      marginy: 50,
    })

    for (const node of nodes) {
      dagreGraph.setNode(node.id, {
        width: opts.nodeWidth,
        height: opts.nodeHeight,
      })
    }

    for (const edge of edges) {
      dagreGraph.setEdge(edge.source, edge.target)
    }

    dagre.layout(dagreGraph)

    return nodes.map((node) => {
      const dagreNode = dagreGraph.node(node.id)
      return {
        ...node,
        position: {
          x: dagreNode.x - opts.nodeWidth / 2,
          y: dagreNode.y - opts.nodeHeight / 2,
        },
      }
    })
  }

  /**
   * Smoothly animates nodes from current to target positions.
   * Uses cubic ease-out for natural-feeling motion.
   * 
   * @param nodes - Current nodes array
   * @param targetPositions - Map of node ID to target position
   * @param duration - Animation duration in milliseconds
   */
  function animateNodes(
    nodes: Node[],
    targetPositions: Map<string, { x: number; y: number }>,
    duration: number
  ): Promise<void> {
    return new Promise((resolve) => {
      const startPositions = new Map(
        nodes.map((n) => [n.id, { ...n.position }])
      )
      const startTime = performance.now()

      function animate(currentTime: number) {
        const elapsed = currentTime - startTime
        const progress = Math.min(elapsed / duration, 1)
        const eased = easeOutCubic(progress)

        const interpolated = nodes.map((node) => {
          const start = startPositions.get(node.id)!
          const target = targetPositions.get(node.id)!
          return {
            ...node,
            position: {
              x: start.x + (target.x - start.x) * eased,
              y: start.y + (target.y - start.y) * eased,
            },
          }
        })

        setNodes(interpolated)

        if (progress < 1) {
          requestAnimationFrame(animate)
        } else {
          resolve()
        }
      }

      requestAnimationFrame(animate)
    })
  }

  function easeOutCubic(t: number): number {
    return 1 - Math.pow(1 - t, 3)
  }

  /**
   * Applies automatic layout to the current graph.
   * Computes optimal positions and optionally animates the transition.
   * After layout, fits the viewport to show all nodes.
   */
  async function layout(): Promise<void> {
    const nodes = getNodes.value
    const edges = getEdges.value

    if (nodes.length === 0) return

    layouting.value = true

    try {
      const layoutedNodes = computeDagreLayout(nodes, edges)

      if (opts.animate) {
        const targetPositions = new Map(
          layoutedNodes.map((n) => [n.id, n.position])
        )
        await animateNodes(nodes, targetPositions, opts.animationDuration)
      } else {
        setNodes(layoutedNodes)
      }

      await nextTick()
      fitView({ padding: 0.2, duration: opts.animate ? 200 : 0 })
    } finally {
      layouting.value = false
    }
  }

  return {
    layout,
    layouting: readonly(layouting),
    computeDagreLayout,
  }
}
