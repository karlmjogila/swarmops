import { mkdir, writeFile, access } from 'fs/promises'
import { join } from 'path'
import type { ProjectState } from '../../types/project'

interface CreateProjectBody {
  name: string
  description?: string
}

interface CreateProjectResponse {
  name: string
  description?: string
  path: string
  createdAt: string
}

export default defineEventHandler(async (event): Promise<CreateProjectResponse> => {
  const config = useRuntimeConfig(event)
  const projectsDir = config.projectsDir

  // Parse and validate body
  const body = await readBody<CreateProjectBody>(event)
  
  if (!body?.name) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Project name is required'
    })
  }

  const name = body.name.trim()
  
  // Validate name format: lowercase, hyphens, no spaces
  const namePattern = /^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z]$/
  if (!namePattern.test(name)) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Invalid project name. Use lowercase letters, numbers, and hyphens only. Must start with a letter.'
    })
  }

  if (name.length < 2 || name.length > 100) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Project name must be between 2 and 100 characters'
    })
  }

  const projectPath = join(projectsDir, name)

  // Check if project already exists
  try {
    await access(projectPath)
    throw createError({
      statusCode: 409,
      statusMessage: `Project "${name}" already exists`
    })
  } catch (err: unknown) {
    // ENOENT means directory doesn't exist - that's what we want
    if ((err as NodeJS.ErrnoException).code !== 'ENOENT') {
      throw err
    }
  }

  const now = new Date().toISOString()

  // Create project directory structure
  try {
    // Create main project directory
    await mkdir(projectPath, { recursive: true })

    // Create specs directory
    await mkdir(join(projectPath, 'specs'), { recursive: true })

    // Create logs directory (for iteration logs)
    await mkdir(join(projectPath, 'logs'), { recursive: true })

    // Create initial state.json
    const initialState: ProjectState = {
      project: name,
      phase: 'interview',
      iteration: 0,
      status: 'pending',
      startedAt: now,
      history: []
    }
    await writeFile(
      join(projectPath, 'state.json'),
      JSON.stringify(initialState, null, 2),
      'utf-8'
    )

    // Create initial progress.md with phase format that dashboard can parse
    const progressContent = `# Progress: ${name}

## Status: Initialized

## Completed Tasks
- [x] Project created
- [x] Initial setup complete

---

### Phase 1: Planning
**Status:** Pending

- [ ] Define objectives and requirements
- [ ] Create implementation plan
- [ ] Review scope

---

### Phase 2: Implementation
**Status:** Pending

- [ ] Core functionality
- [ ] Integration work
- [ ] Testing

---

### Phase 3: Review
**Status:** Pending

- [ ] Code review
- [ ] Documentation
- [ ] Final testing

---

## Notes
${body.description || '_No description provided._'}

Created: ${new Date(now).toLocaleString()}
`
    await writeFile(
      join(projectPath, 'progress.md'),
      progressContent,
      'utf-8'
    )

    // Create README in specs folder
    const specsReadme = `# Specifications

This directory contains the project specifications.

Add your spec files here (e.g., \`requirements.md\`, \`architecture.md\`).
`
    await writeFile(
      join(projectPath, 'specs', 'README.md'),
      specsReadme,
      'utf-8'
    )

    // Interview agent will be spawned when user opens the project in the UI
    // via /api/projects/[name]/interview-agent endpoint

    return {
      name,
      description: body.description,
      path: projectPath,
      createdAt: now
    }
  } catch (err) {
    console.error('Failed to create project:', err)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to create project directory'
    })
  }
})
