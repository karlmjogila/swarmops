import { readFile, writeFile } from 'fs/promises'
import { join } from 'path'
import type { ProjectState } from '../../../types/project'
import { requireAuth, validateProjectName } from '../../../utils/security'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const name = validateProjectName(getRouterParam(event, 'name'))
  
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Project name required' })
  }

  const projectPath = join(config.projectsDir, name)
  const statePath = join(projectPath, 'state.json')

  try {
    const stateRaw = await readFile(statePath, 'utf-8')
    const state: ProjectState = JSON.parse(stateRaw)

    // Toggle archived status
    state.archived = !state.archived
    state.archivedAt = state.archived ? new Date().toISOString() : undefined

    await writeFile(statePath, JSON.stringify(state, null, 2))

    return {
      success: true,
      archived: state.archived,
      archivedAt: state.archivedAt
    }
  } catch (err) {
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to archive project: ${err}`
    })
  }
})
