import { readdir, readFile } from 'fs/promises'
import { join } from 'path'
import type { ProjectState, Iteration } from '../../types/project'
import { validateProjectName } from '../../utils/security'

interface SpecFile {
  name: string
  content: string
}

interface ProjectDetail {
  name: string
  state: ProjectState | null
  progress: string | null
  plan: string | null
  specs: SpecFile[]
  logs: Iteration[]
}

async function readFileOrNull(path: string): Promise<string | null> {
  try {
    return await readFile(path, 'utf-8')
  } catch {
    return null
  }
}

async function loadSpecs(projectPath: string): Promise<SpecFile[]> {
  const specsDir = join(projectPath, 'specs')
  try {
    const entries = await readdir(specsDir, { withFileTypes: true })
    const mdFiles = entries.filter(e => e.isFile() && e.name.endsWith('.md'))
    
    const specs = await Promise.all(
      mdFiles.map(async (file) => {
        const content = await readFileOrNull(join(specsDir, file.name))
        return { name: file.name, content: content ?? '' }
      })
    )
    return specs
  } catch {
    return []
  }
}

async function loadLogs(projectPath: string): Promise<Iteration[]> {
  const logsDir = join(projectPath, 'logs')
  try {
    const entries = await readdir(logsDir, { withFileTypes: true })
    const jsonFiles = entries
      .filter(e => e.isFile() && e.name.endsWith('.json'))
      .map(e => e.name)
      .sort((a, b) => b.localeCompare(a))
      .slice(0, 20)

    const logs = await Promise.all(
      jsonFiles.map(async (file) => {
        try {
          const content = await readFile(join(logsDir, file), 'utf-8')
          return JSON.parse(content) as Iteration
        } catch {
          return null
        }
      })
    )
    return logs.filter((log: Iteration | null): log is Iteration => log !== null)
  } catch {
    return []
  }
}

export default defineEventHandler(async (event): Promise<ProjectDetail> => {
  const config = useRuntimeConfig(event)
  const name = validateProjectName(getRouterParam(event, 'name'))
  
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Project name required' })
  }

  const projectPath = join(config.projectsDir, name)

  const [stateRaw, progress, plan, specs, logs] = await Promise.all([
    readFileOrNull(join(projectPath, 'state.json')),
    readFileOrNull(join(projectPath, 'progress.md')),
    readFileOrNull(join(projectPath, 'IMPLEMENTATION_PLAN.md')),
    loadSpecs(projectPath),
    loadLogs(projectPath)
  ])

  let state: ProjectState | null = null
  if (stateRaw) {
    try {
      state = JSON.parse(stateRaw)
    } catch {}
  }

  return {
    name,
    state,
    progress,
    plan,
    specs,
    logs
  }
})
