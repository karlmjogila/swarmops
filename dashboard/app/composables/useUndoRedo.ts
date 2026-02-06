import type { Node, Edge } from '@vue-flow/core'

/**
 * Snapshot of graph state for undo/redo history.
 */
interface HistoryState {
  /** Deep clone of nodes at snapshot time */
  nodes: Node[]
  /** Deep clone of edges at snapshot time */
  edges: Edge[]
  /** Unix timestamp when snapshot was taken */
  timestamp: number
}

/**
 * Configuration options for undo/redo behavior.
 */
interface UndoRedoOptions {
  /** Maximum number of states to keep in history (default: 50) */
  maxHistory?: number
  /** Debounce delay before saving state (default: 300ms) */
  debounceMs?: number
}

/**
 * Creates a deep clone of nodes and edges for history snapshots.
 * Uses JSON serialization for simplicity and to break all references.
 */
function cloneState(nodes: Node[], edges: Edge[]): HistoryState {
  return {
    nodes: JSON.parse(JSON.stringify(nodes)),
    edges: JSON.parse(JSON.stringify(edges)),
    timestamp: Date.now(),
  }
}

/**
 * Compare two states for equality (ignoring position micro-changes)
 */
function statesEqual(a: HistoryState | null, b: HistoryState | null): boolean {
  if (!a || !b) return false
  if (a.nodes.length !== b.nodes.length) return false
  if (a.edges.length !== b.edges.length) return false

  // Compare node IDs and types (ignore position for now to avoid noise)
  const aNodeIds = a.nodes.map(n => `${n.id}:${n.type}`).sort().join(',')
  const bNodeIds = b.nodes.map(n => `${n.id}:${n.type}`).sort().join(',')
  if (aNodeIds !== bNodeIds) return false

  // Compare edges
  const aEdgeIds = a.edges.map(e => `${e.source}->${e.target}`).sort().join(',')
  const bEdgeIds = b.edges.map(e => `${e.source}->${e.target}`).sort().join(',')
  if (aEdgeIds !== bEdgeIds) return false

  return true
}

/**
 * Composable for undo/redo functionality in Vue Flow.
 * 
 * Maintains two stacks (undo/redo) of graph snapshots. Changes are
 * automatically tracked with debouncing to coalesce rapid edits.
 * 
 * Features:
 * - Automatic change detection via deep watch
 * - Debounced saves to avoid excessive history entries
 * - Batch operations for grouped changes
 * - Keyboard shortcut registration
 * - Configurable history limit
 * 
 * @param nodes - Reactive reference to Vue Flow nodes
 * @param edges - Reactive reference to Vue Flow edges
 * @param options - Configuration options
 * @returns Undo/redo state and actions
 * 
 * @example
 * const { canUndo, canRedo, undo, redo, registerKeyboardShortcuts } = useUndoRedo(nodes, edges)
 * 
 * onMounted(() => {
 *   const cleanup = registerKeyboardShortcuts()
 *   onUnmounted(cleanup)
 * })
 */
export function useUndoRedo(
  nodes: Ref<Node[]>,
  edges: Ref<Edge[]>,
  options: UndoRedoOptions = {}
) {
  const { maxHistory = 50, debounceMs = 300 } = options

  // History stacks
  const undoStack = ref<HistoryState[]>([])
  const redoStack = ref<HistoryState[]>([])

  // Flags to prevent recording during undo/redo operations
  const isUndoRedoing = ref(false)
  const isPaused = ref(false)

  // Debounce timer
  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  // Computed states
  const canUndo = computed(() => undoStack.value.length > 0)
  const canRedo = computed(() => redoStack.value.length > 0)
  const historyLength = computed(() => undoStack.value.length)

  /**
   * Save current state to undo stack
   */
  function saveState() {
    if (isUndoRedoing.value || isPaused.value) return

    const newState = cloneState(nodes.value, edges.value)
    const lastState = undoStack.value[undoStack.value.length - 1] ?? null

    // Don't save if state hasn't meaningfully changed
    if (statesEqual(newState, lastState)) return

    undoStack.value.push(newState)

    // Trim history if exceeding max
    if (undoStack.value.length > maxHistory) {
      undoStack.value.shift()
    }

    // Clear redo stack on new action
    redoStack.value = []
  }

  /**
   * Debounced state save - coalesces rapid changes
   */
  function saveStateDebounced() {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(saveState, debounceMs)
  }

  /**
   * Undo last action
   */
  function undo() {
    if (!canUndo.value) return false

    isUndoRedoing.value = true

    // Save current state to redo stack
    const currentState = cloneState(nodes.value, edges.value)
    redoStack.value.push(currentState)

    // Pop and apply previous state
    const previousState = undoStack.value.pop()!
    nodes.value = previousState.nodes
    edges.value = previousState.edges

    nextTick(() => {
      isUndoRedoing.value = false
    })

    return true
  }

  /**
   * Redo previously undone action
   */
  function redo() {
    if (!canRedo.value) return false

    isUndoRedoing.value = true

    // Save current state to undo stack
    const currentState = cloneState(nodes.value, edges.value)
    undoStack.value.push(currentState)

    // Pop and apply redo state
    const redoState = redoStack.value.pop()!
    nodes.value = redoState.nodes
    edges.value = redoState.edges

    nextTick(() => {
      isUndoRedoing.value = false
    })

    return true
  }

  /**
   * Clear all history
   */
  function clearHistory() {
    undoStack.value = []
    redoStack.value = []
  }

  /**
   * Pause history recording (useful during batch operations)
   */
  function pause() {
    isPaused.value = true
  }

  /**
   * Resume history recording and optionally save current state
   */
  function resume(saveCurrentState = true) {
    isPaused.value = false
    if (saveCurrentState) {
      saveState()
    }
  }

  /**
   * Execute a batch operation without recording intermediate states
   */
  function batch<T>(fn: () => T): T {
    pause()
    try {
      return fn()
    } finally {
      resume(true)
    }
  }

  /**
   * Initialize with current state as first history entry
   */
  function initialize() {
    clearHistory()
    saveState()
  }

  // Watch for changes to nodes and edges
  watch(
    [nodes, edges],
    () => {
      saveStateDebounced()
    },
    { deep: true }
  )

  // Keyboard shortcut handler
  function handleKeyboardShortcut(event: KeyboardEvent) {
    const isMod = event.metaKey || event.ctrlKey

    if (isMod && event.key === 'z') {
      if (event.shiftKey) {
        // Cmd/Ctrl+Shift+Z = Redo
        event.preventDefault()
        redo()
      } else {
        // Cmd/Ctrl+Z = Undo
        event.preventDefault()
        undo()
      }
    } else if (isMod && event.key === 'y') {
      // Cmd/Ctrl+Y = Redo (Windows convention)
      event.preventDefault()
      redo()
    }
  }

  /**
   * Register keyboard shortcuts for undo/redo
   * Call on component mount, returns cleanup function
   */
  function registerKeyboardShortcuts() {
    window.addEventListener('keydown', handleKeyboardShortcut)
    return () => {
      window.removeEventListener('keydown', handleKeyboardShortcut)
    }
  }

  return {
    // State
    canUndo,
    canRedo,
    historyLength,
    isRecording: computed(() => !isPaused.value),

    // Actions
    undo,
    redo,
    saveState,
    clearHistory,
    initialize,

    // Batch operations
    pause,
    resume,
    batch,

    // Keyboard shortcuts
    registerKeyboardShortcuts,
  }
}
