import { readdir, readFile, stat } from 'fs/promises'
import { join } from 'path'
import type { ProjectListItem, ProjectState } from '../../types/project'

export default defineEventHandler(async (event): Promise<ProjectListItem[]> => {
  const config = useRuntimeConfig(event)
  const projectsDir = config.projectsDir
  const query = getQuery(event)
  const showArchived = query.archived === 'true'
  const projects: ProjectListItem[] = []

  try {
    const entries = await readdir(projectsDir, { withFileTypes: true })
    const dirs = entries.filter(e => e.isDirectory())

    await Promise.all(dirs.map(async (dir: { name: string }) => {
      const projectPath = join(projectsDir, dir.name)
      const statePath = join(projectPath, 'state.json')

      try {
        const stateRaw = await readFile(statePath, 'utf-8')
        const state: ProjectState = JSON.parse(stateRaw)

        const lastEntry = state.history?.[state.history.length - 1]

        projects.push({
          name: state.project,
          phase: state.phase,
          iteration: state.iteration,
          status: state.status,
          startedAt: state.startedAt,
          completedAt: state.completedAt,
          path: projectPath,
          iterationCount: state.history?.length ?? state.iteration,
          lastActivity: lastEntry?.timestamp ?? state.startedAt,
          archived: state.archived ?? false,
          archivedAt: state.archivedAt
        })
      } catch {
        const dirStat = await stat(projectPath)
        projects.push({
          name: dir.name,
          phase: 'interview',
          iteration: 0,
          status: 'pending',
          startedAt: dirStat.birthtime.toISOString(),
          path: projectPath,
          iterationCount: 0,
          archived: false
        })
      }
    }))

    // Filter by archived status
    const filtered = projects.filter(p => showArchived ? p.archived : !p.archived)

    return filtered.sort((a, b) => {
      const aTime = a.lastActivity ?? a.startedAt
      const bTime = b.lastActivity ?? b.startedAt
      return new Date(bTime).getTime() - new Date(aTime).getTime()
    })
  } catch (err) {
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to read projects directory'
    })
  }
})
