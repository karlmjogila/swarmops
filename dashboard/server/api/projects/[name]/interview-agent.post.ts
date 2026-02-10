import { readFile, writeFile, appendFile, mkdir } from 'fs/promises'
import { join } from 'path'
import { existsSync } from 'fs'
import { randomUUID } from 'crypto'
import { tmpdir } from 'os'
import { broadcastProjectUpdate } from '../../../plugins/websocket'
import { updateProjectPhase, triggerPhaseWork, logActivity } from '../../../utils/auto-advance'
import type { InterviewState } from './interview.get'
import { requireAuth, validateProjectName } from '../../../utils/security'

// Phrases that indicate the interview is complete
const COMPLETION_PHRASES = [
  'interview complete',
  'ready to proceed',
  'ready for planning',
  'ready for the planning phase',
  'ready for the main agent',
  'proceed to planning',
  'move to planning'
]

function isInterviewComplete(response: string): boolean {
  const lowerResponse = response.toLowerCase()
  return COMPLETION_PHRASES.some(phrase => lowerResponse.includes(phrase))
}

interface PostBody {
  userMessage?: string
  image?: string // base64 data URL
}

interface InterviewStateWithSession extends InterviewState {
  sessionKey?: string // Persistent session for fast follow-ups
}

async function saveImageToTemp(dataUrl: string): Promise<string | null> {
  const match = dataUrl.match(/^data:image\/([^;]+);base64,(.+)$/)
  if (!match) return null
  
  const ext = match[1] === 'jpeg' ? 'jpg' : match[1]
  const base64Data = match[2]
  const buffer = Buffer.from(base64Data, 'base64')
  
  const tempDir = join(tmpdir(), 'swarmops-interview-images')
  await mkdir(tempDir, { recursive: true })
  
  const filename = `interview-image-${Date.now()}.${ext}`
  const filepath = join(tempDir, filename)
  
  await writeFile(filepath, buffer)
  return filepath
}

// Simple lock to prevent concurrent interview agents per project
const activeInterviews = new Map<string, Promise<any>>()

function getGatewayConfig() {
  return {
    url: process.env.OPENCLAW_GATEWAY_URL || 'http://127.0.0.1:18789',
    token: process.env.OPENCLAW_GATEWAY_TOKEN || ''
  }
}

async function invokeGateway(gw: { url: string, token: string }, tool: string, args: any): Promise<any> {
  const response = await fetch(`${gw.url}/tools/invoke`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${gw.token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ tool, args })
  })
  
  if (!response.ok) {
    throw new Error(`Gateway error: ${response.status}`)
  }
  
  return response.json()
}

async function pollForResponse(gw: { url: string, token: string }, sessionKey: string, maxWaitMs: number = 60000): Promise<string | null> {
  const startTime = Date.now()
  let pollInterval = 300 // Start faster
  
  while (Date.now() - startTime < maxWaitMs) {
    await new Promise(resolve => setTimeout(resolve, pollInterval))
    if (pollInterval < 2000) pollInterval += 200
    
    try {
      const data = await invokeGateway(gw, 'sessions_history', {
        sessionKey,
        limit: 20,
        includeTools: false
      })
      
      const result = data.result?.details || data.result || {}
      const messages = result.messages || []
      
      if (messages.length === 0) continue
      
      // Find the last assistant message
      let lastAssistantMsg = null
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'assistant') {
          lastAssistantMsg = messages[i]
          break
        }
      }
      
      if (!lastAssistantMsg) continue
      
      // Check if the agent has finished
      const stopReason = lastAssistantMsg.stopReason
      if (stopReason === 'toolUse') {
        console.log('[interview-agent] Agent still processing...')
        continue
      }
      
      // Agent finished - extract text content
      if (typeof lastAssistantMsg.content === 'string') {
        return lastAssistantMsg.content
      }
      if (Array.isArray(lastAssistantMsg.content)) {
        const textPart = lastAssistantMsg.content.find((c: any) => c.type === 'text')
        if (textPart?.text) {
          return textPart.text
        }
      }
    } catch (err) {
      console.error('[interview-agent] Poll error:', err)
    }
  }
  
  return null
}

function buildInitialPrompt(projectName: string, goal: string): string {
  return `You are an interviewer for the SwarmOps project "${projectName}".

**User's Goal:**
${goal}

**Your Task:**
1. Ask 2-3 clarifying questions to understand scope, constraints, and success criteria
2. Keep questions concise and specific to THIS project
3. When you have enough info (after 2-3 exchanges), summarize and say: "Ready to proceed to planning?"

Start by acknowledging the goal and asking your first clarifying question.
Keep your response conversational and focused. Don't write code yet.`
}

export default defineEventHandler(async (event) => {
  requireAuth(event)
  const name = validateProjectName(getRouterParam(event, 'name'))
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Project name required' })
  }

  // Check if there's already an active interview for this project
  const existingPromise = activeInterviews.get(name)
  if (existingPromise) {
    console.log(`[interview-agent] Already processing for ${name}, waiting...`)
    try {
      await existingPromise
    } catch {}
    return { ok: true, message: 'Concurrent request completed', spawned: false }
  }

  const body = await readBody<PostBody>(event) || {}
  const config = useRuntimeConfig(event)
  const projectDir = join(config.projectsDir, name)
  const interviewFile = join(projectDir, 'interview.json')
  const progressFile = join(projectDir, 'progress.md')

  if (!existsSync(projectDir)) {
    throw createError({ statusCode: 404, statusMessage: 'Project not found' })
  }

  // Extract goal from progress.md
  let goal = 'No goal specified'
  if (existsSync(progressFile)) {
    try {
      const progress = await readFile(progressFile, 'utf-8')
      const match = progress.match(/## Notes\n(.+?)(?:\n\n|Created:|$)/s)
      if (match) {
        const notes = match[1].trim()
        if (notes !== '_No description provided._') {
          goal = notes
        }
      }
    } catch {}
  }

  // Load existing interview state
  let state: InterviewStateWithSession = { messages: [], complete: false }
  if (existsSync(interviewFile)) {
    try {
      const content = await readFile(interviewFile, 'utf-8')
      state = JSON.parse(content)
    } catch {}
  }

  if (state.complete) {
    return { ok: true, message: 'Interview already complete', spawned: false }
  }

  const gw = getGatewayConfig()

  // Build message content with image if provided
  let messageContent = body.userMessage || ''
  let imagePath: string | null = null
  
  if (body.image) {
    imagePath = await saveImageToTemp(body.image)
    if (imagePath) {
      const imageNote = `\n\n[Image attached: ${imagePath}]\nUse the image tool to analyze this if relevant.`
      messageContent = messageContent ? messageContent + imageNote : `Please look at this image: ${imagePath}`
    }
  }

  // Save user message to state if provided
  if (body.userMessage || body.image) {
    const message: any = {
      id: randomUUID(),
      timestamp: new Date().toISOString(),
      role: 'user' as const,
      content: body.userMessage || '(image attached)'
    }
    if (body.image) {
      message.image = body.image
    }
    if (imagePath) {
      message.imagePath = imagePath
    }
    state.messages.push(message)
    await writeFile(interviewFile, JSON.stringify(state, null, 2))
    broadcastProjectUpdate(name, 'interview.json')
  }

  // Create and store the promise to prevent concurrent spawns
  const interviewPromise = (async () => {
    try {
      let agentResponse: string | null = null
      
      if (state.sessionKey && messageContent) {
        // FAST PATH: Continue existing session with sessions_send
        console.log(`[interview-agent] Continuing session: ${state.sessionKey}`)
        
        const sendData = await invokeGateway(gw, 'sessions_send', {
          sessionKey: state.sessionKey,
          message: messageContent,
          timeoutSeconds: 60
        })
        
        const result = sendData.result?.details || sendData.result || {}
        agentResponse = result.reply || result.response || result.content || result.message || null
        
      } else {
        // SPAWN PATH: First message or no session yet
        console.log(`[interview-agent] Spawning new session for: ${name}`)
        
        const initialPrompt = buildInitialPrompt(name, goal)
        const taskPrompt = messageContent 
          ? `${initialPrompt}\n\n**User's first message:**\n${messageContent}`
          : initialPrompt
        
        const spawnData = await invokeGateway(gw, 'sessions_spawn', {
          task: taskPrompt,
          label: `interview-${name}`,
          model: 'sonnet'
        })
        
        const spawnResult = spawnData.result?.details || spawnData.result || {}
        const sessionKey = spawnResult.childSessionKey
        
        if (!sessionKey) {
          throw new Error('Failed to spawn interview agent')
        }
        
        // Save sessionKey for future fast follow-ups
        state.sessionKey = sessionKey
        await writeFile(interviewFile, JSON.stringify(state, null, 2))
        
        console.log(`[interview-agent] Spawned session: ${sessionKey}`)
        
        // Poll for initial response
        agentResponse = await pollForResponse(gw, sessionKey, 60000)
      }
      
      if (agentResponse) {
        // Check if response indicates interview completion
        const complete = isInterviewComplete(agentResponse)
        
        // Save agent's response
        state.messages.push({
          id: randomUUID(),
          timestamp: new Date().toISOString(),
          role: 'agent' as const,
          content: agentResponse
        })
        
        if (complete) {
          state.complete = true
        }
        
        await writeFile(interviewFile, JSON.stringify(state, null, 2))
        broadcastProjectUpdate(name, 'interview.json')
        
        console.log(`[interview-agent] Got response (${agentResponse.length} chars), complete=${complete}`)
        
        // Log activity
        try {
          const activityFile = join(projectDir, 'activity.jsonl')
          await appendFile(activityFile, JSON.stringify({
            id: randomUUID(),
            timestamp: new Date().toISOString(),
            type: 'event',
            message: complete ? 'Interview complete' : (state.messages.length <= 2 ? 'Interview started' : 'Agent responded'),
            agent: 'interviewer'
          }) + '\n')
          broadcastProjectUpdate(name, 'activity.jsonl')
        } catch {}
        
        // Auto-advance to spec phase if complete
        if (complete) {
          try {
            console.log(`[interview-agent] Auto-advancing to spec phase...`)
            await updateProjectPhase(projectDir, name, 'spec')
            const triggerResult = await triggerPhaseWork(projectDir, name, 'spec')
            await logActivity(projectDir, name, 'progress', 
              `Interview complete → Auto-advanced to spec phase. ${triggerResult.message}`)
          } catch (err) {
            console.error('[interview-agent] Failed to auto-advance:', err)
          }
        }
        
        return {
          ok: true,
          spawned: !state.sessionKey,
          continued: !!state.sessionKey,
          response: agentResponse,
          messageCount: state.messages.length,
          complete
        }
      } else {
        return { ok: false, error: 'Agent did not respond in time' }
      }
    } catch (err: any) {
      console.error('[interview-agent] Error:', err)
      return { ok: false, error: err.message || 'Failed to get interview response' }
    }
  })()
  
  activeInterviews.set(name, interviewPromise)
  
  try {
    return await interviewPromise
  } finally {
    activeInterviews.delete(name)
  }
})
