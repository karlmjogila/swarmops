import { spawn } from 'child_process'
import { readFile } from 'fs/promises'
import { join } from 'path'
import { homedir } from 'os'

interface SessionDetail {
  key: string
  kind: string
  sessionId: string
  model?: string
  messages?: any[]
  tokens?: {
    input: number
    output: number
    total: number
  }
}

async function getSessionStore(): Promise<any> {
  // Read the sessions store directly for detailed info
  const storePath = join(homedir(), '.openclaw', 'agents', 'main', 'sessions', 'sessions.json')
  try {
    const data = await readFile(storePath, 'utf-8')
    return JSON.parse(data)
  } catch (e) {
    throw new Error(`Failed to read session store: ${e}`)
  }
}

async function getSessionById(sessionId: string): Promise<SessionDetail | null> {
  const store = await getSessionStore()
  
  // Sessions are stored by key directly in the store object (not nested in .sessions)
  for (const [key, session] of Object.entries(store)) {
    // Skip non-session entries (like metadata)
    if (typeof session !== 'object' || !session) continue
    
    const s = session as any
    if (s.sessionId === sessionId) {
      return {
        key,
        kind: s.kind,
        sessionId: s.sessionId,
        model: s.model,
        messages: s.messages || [],
        tokens: {
          input: s.inputTokens || 0,
          output: s.outputTokens || 0,
          total: s.totalTokens || 0
        }
      }
    }
  }
  
  return null
}

export default defineEventHandler(async (event) => {
  const sessionId = getRouterParam(event, 'id')
  
  if (!sessionId) {
    throw createError({ statusCode: 400, statusMessage: 'Session ID required' })
  }

  try {
    const session = await getSessionById(sessionId)
    
    if (!session) {
      throw createError({ statusCode: 404, statusMessage: 'Session not found' })
    }

    // Format messages for display (truncate very long content)
    const formattedMessages = session.messages?.map((msg: any) => ({
      role: msg.role,
      content: typeof msg.content === 'string' 
        ? (msg.content.length > 2000 ? msg.content.slice(0, 2000) + '...' : msg.content)
        : msg.content,
      timestamp: msg.timestamp,
      model: msg.model
    })) || []

    return {
      success: true,
      session: {
        ...session,
        messages: formattedMessages,
        messageCount: session.messages?.length || 0
      }
    }
  } catch (error) {
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to fetch session: ${error.message}`
    })
  }
})
