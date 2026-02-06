import { readFile } from 'fs/promises'
import { join } from 'path'
import { existsSync } from 'fs'
import { validateProjectName } from '../../../utils/security'

export interface InterviewMessage {
  id: string
  timestamp: string
  role: 'user' | 'agent'
  content: string
  image?: string // base64 data URL for UI display
  imagePath?: string // file path for agent to analyze
}

export interface InterviewState {
  messages: InterviewMessage[]
  complete: boolean
}

export default defineEventHandler(async (event): Promise<InterviewState> => {
  const name = validateProjectName(getRouterParam(event, 'name'))
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Project name required' })
  }

  const config = useRuntimeConfig(event)
  const projectDir = join(config.projectsDir, name)
  const interviewFile = join(projectDir, 'interview.json')

  if (!existsSync(projectDir)) {
    throw createError({ statusCode: 404, statusMessage: 'Project not found' })
  }

  // Default state
  const defaultState: InterviewState = {
    messages: [],
    complete: false
  }

  if (!existsSync(interviewFile)) {
    return defaultState
  }

  try {
    const content = await readFile(interviewFile, 'utf-8')
    const data = JSON.parse(content)
    return {
      messages: data.messages || [],
      complete: data.complete || false
    }
  } catch (err) {
    console.error('Failed to read interview state:', err)
    return defaultState
  }
})
