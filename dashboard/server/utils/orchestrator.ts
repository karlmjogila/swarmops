import { readFile, writeFile } from 'fs/promises'
import { join } from 'path'

export interface GraphTask {
  id: string
  title: string
  done: boolean
  depends: string[]
  role: string
  line: number // Line number in progress.md for updates
}

export interface TaskGraph {
  tasks: Map<string, GraphTask>
  order: string[] // Topological order
}

/**
 * Parse tasks from progress.md with dependency annotations
 * Format: - [ ] Task title @id(task-id) @depends(dep1,dep2) @role(reviewer)
 */
export function parseTaskGraph(progressMd: string): TaskGraph {
  const tasks = new Map<string, Task>()
  const lines = progressMd.split('\n')
  
  let taskIndex = 0
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    
    // Match task lines: - [ ] or - [x]
    const taskMatch = line.match(/^(\s*)-\s*\[([ xX])\]\s*(.+)/)
    if (!taskMatch) continue
    
    const done = taskMatch[2].toLowerCase() === 'x'
    let title = taskMatch[3].trim()
    
    // Extract annotations
    const idMatch = title.match(/@id\(([^)]+)\)/)
    const dependsMatch = title.match(/@depends\(([^)]+)\)/)
    const roleMatch = title.match(/@role\(([^)]+)\)/)
    
    // Generate id if not specified
    const id = idMatch ? idMatch[1] : `task-${taskIndex}`
    const depends = dependsMatch ? dependsMatch[1].split(',').map(d => d.trim()) : []
    const role = roleMatch?.[1] || 'builder'
    
    // Clean title (remove annotations)
    title = title
      .replace(/@id\([^)]+\)/g, '')
      .replace(/@depends\([^)]+\)/g, '')
      .replace(/@role\([^)]+\)/g, '')
      .trim()
    
    tasks.set(id, { id, title, done, depends, role, line: i })
    taskIndex++
  }
  
  // Topological sort for execution order
  const order = topologicalSort(tasks)
  
  return { tasks, order }
}

/**
 * Topological sort using Kahn's algorithm
 */
function topologicalSort(tasks: Map<string, GraphTask>): string[] {
  const inDegree = new Map<string, number>()
  const adjList = new Map<string, string[]>()
  
  // Initialize
  for (const [id, task] of tasks) {
    inDegree.set(id, task.depends.length)
    for (const dep of task.depends) {
      const edges = adjList.get(dep) || []
      edges.push(id)
      adjList.set(dep, edges)
    }
  }
  
  // Find all tasks with no dependencies
  const queue: string[] = []
  for (const [id, degree] of inDegree) {
    if (degree === 0) queue.push(id)
  }
  
  const result: string[] = []
  while (queue.length > 0) {
    const id = queue.shift()!
    result.push(id)
    
    for (const dependent of (adjList.get(id) || [])) {
      const newDegree = (inDegree.get(dependent) || 1) - 1
      inDegree.set(dependent, newDegree)
      if (newDegree === 0) queue.push(dependent)
    }
  }
  
  return result
}

/**
 * Get tasks that are ready to run (dependencies satisfied, not done)
 */
export function getReadyTasks(graph: TaskGraph): GraphTask[] {
  const ready: GraphTask[] = []
  
  for (const id of graph.order) {
    const task = graph.tasks.get(id)!
    if (task.done) continue
    
    // Check if all dependencies are done
    const depsOk = task.depends.every(depId => {
      const dep = graph.tasks.get(depId)
      return dep?.done === true
    })
    
    if (depsOk) ready.push(task)
  }
  
  return ready
}

/**
 * Mark a task as done in progress.md
 */
export async function markTaskDone(projectPath: string, taskId: string): Promise<void> {
  const progressPath = join(projectPath, 'progress.md')
  const content = await readFile(progressPath, 'utf-8')
  const graph = parseTaskGraph(content)
  
  const task = graph.tasks.get(taskId)
  if (!task) return
  
  const lines = content.split('\n')
  // Replace [ ] with [x] on the task line
  lines[task.line] = lines[task.line].replace(/\[\s\]/, '[x]')
  
  await writeFile(progressPath, lines.join('\n'))
}

/**
 * Get parallel execution groups from task graph
 * Returns array of task arrays that can run in parallel
 */
export function getParallelGroups(graph: TaskGraph): GraphTask[][] {
  const groups: GraphTask[][] = []
  const done = new Set<string>()
  
  // Mark already-done tasks
  for (const [id, task] of graph.tasks) {
    if (task.done) done.add(id)
  }
  
  while (done.size < graph.tasks.size) {
    const group: GraphTask[] = []
    
    for (const [id, task] of graph.tasks) {
      if (done.has(id)) continue
      
      // Check if all dependencies are done
      const depsOk = task.depends.every(depId => done.has(depId))
      if (depsOk) group.push(task)
    }
    
    if (group.length === 0) break // Cycle or error
    
    groups.push(group)
    for (const task of group) done.add(task.id)
  }
  
  return groups
}
