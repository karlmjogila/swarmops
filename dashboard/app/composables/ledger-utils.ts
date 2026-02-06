/**
 * Ledger utilities for grouping activity events by project
 */

export interface LedgerEntry {
  id: string
  timestamp: string
  type: string
  message: string
  agent?: string
  taskId?: string
  phaseNumber?: number
  workerId?: string
  workerBranch?: string
  runId?: string
  success?: boolean
  mergeStatus?: string
  allSucceeded?: boolean
  error?: string
  projectName?: string
}

export interface ProjectGroup {
  projectName: string
  entries: LedgerEntry[]
  latestTimestamp: string
  createdAt: string
  stats: {
    spawns: number
    completions: number
    errors: number
    phases: number
  }
}

/**
 * Group ledger entries by project name.
 * Returns array sorted by most recent activity.
 */
export function groupEntriesByProject(entries: LedgerEntry[]): ProjectGroup[] {
  const groupMap = new Map<string, LedgerEntry[]>()

  for (const entry of entries) {
    const name = entry.projectName
    if (!name) continue
    const group = groupMap.get(name)
    if (group) {
      group.push(entry)
    } else {
      groupMap.set(name, [entry])
    }
  }

  const groups: ProjectGroup[] = []

  for (const [projectName, projectEntries] of groupMap) {
    // Already sorted newest-first from API
    const timestamps = projectEntries
      .map(e => e.timestamp)
      .filter(t => t)

    const stats = {
      spawns: projectEntries.filter(e => e.type === 'spawn').length,
      completions: projectEntries.filter(e =>
        e.type === 'complete' || e.type === 'worker-complete' || e.type === 'phase-complete'
      ).length,
      errors: projectEntries.filter(e =>
        e.type === 'error' || e.type === 'failed'
      ).length,
      phases: new Set(projectEntries.filter(e => e.phaseNumber).map(e => e.phaseNumber)).size
    }

    groups.push({
      projectName,
      entries: projectEntries,
      latestTimestamp: timestamps[0] || '',
      createdAt: timestamps[timestamps.length - 1] || '',
      stats,
    })
  }

  groups.sort((a, b) => b.latestTimestamp.localeCompare(a.latestTimestamp))
  return groups
}
