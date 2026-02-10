import { readFile } from 'fs/promises'
import { join } from 'path'
import { homedir } from 'os'

const GATEWAY_URL = process.env.OPENCLAW_GATEWAY_URL || 'http://127.0.0.1:18789'
const GATEWAY_TOKEN = process.env.OPENCLAW_GATEWAY_TOKEN || ''

interface LogMessage {
  role: 'user' | 'assistant' | 'tool'
  content: string
  timestamp?: string
  toolName?: string
}

interface GatewaySession {
  key: string
  sessionId: string
  transcriptPath: string
}

/**
 * Look up session info from gateway to get the actual transcript path
 */
async function getSessionTranscriptPath(sessionKey: string): Promise<string | null> {
  try {
    const response = await fetch(`${GATEWAY_URL}/tools/invoke`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${GATEWAY_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        tool: 'sessions_list',
        parameters: { limit: 100 }
      })
    })
    
    if (!response.ok) return null
    
    const data = await response.json()
    
    // Gateway wraps result in result.content[0].text (JSON string) or result.details
    let sessions: GatewaySession[] = []
    if (data.result?.details?.sessions) {
      sessions = data.result.details.sessions
    } else if (data.result?.content?.[0]?.text) {
      const parsed = JSON.parse(data.result.content[0].text)
      sessions = parsed.sessions || []
    } else if (data.sessions) {
      sessions = data.sessions
    }
    
    // Find session by key (URL decode for comparison)
    const decoded = decodeURIComponent(sessionKey)
    const session = sessions.find((s: GatewaySession) => s.key === decoded || s.key === sessionKey)
    
    if (session?.transcriptPath) {
      return session.transcriptPath
    }
    
    // Fallback: try sessionId directly
    if (session?.sessionId) {
      return `${session.sessionId}.jsonl`
    }
    
    return null
  } catch (err) {
    console.error('[logs] Failed to fetch session from gateway:', err)
    return null
  }
}

export default defineEventHandler(async (event): Promise<{ logs: LogMessage[] }> => {
  const rawSessionId = getRouterParam(event, 'sessionId')
  
  if (!rawSessionId) {
    throw createError({ statusCode: 400, message: 'Session ID required' })
  }

  // Look up transcript path from gateway
  const transcriptFile = await getSessionTranscriptPath(rawSessionId)
  
  if (!transcriptFile) {
    throw createError({ statusCode: 404, message: 'Session not found' })
  }
  
  const sessionsDir = join(homedir(), '.clawdbot', 'agents', 'main', 'sessions')
  const sessionPath = join(sessionsDir, transcriptFile)
  
  try {
    const content = await readFile(sessionPath, 'utf-8')
    const lines = content.trim().split('\n').filter(l => l.trim())
    
    const logs: LogMessage[] = []
    
    for (const line of lines) {
      try {
        const entry = JSON.parse(line)
        
        if (entry.type !== 'message') continue
        
        const msg = entry.message
        if (!msg) continue
        
        if (msg.role === 'user') {
          const text = extractTextContent(msg.content)
          if (text) {
            logs.push({
              role: 'user',
              content: text,
              timestamp: entry.timestamp
            })
          }
        } else if (msg.role === 'assistant') {
          const text = extractTextContent(msg.content)
          if (text) {
            logs.push({
              role: 'assistant',
              content: text,
              timestamp: entry.timestamp
            })
          }
        } else if (msg.role === 'toolResult') {
          const text = extractTextContent(msg.content)
          if (text) {
            logs.push({
              role: 'tool',
              content: text.slice(0, 500) + (text.length > 500 ? '...' : ''),
              timestamp: entry.timestamp,
              toolName: msg.toolName
            })
          }
        }
      } catch {
        // Skip malformed lines
      }
    }
    
    return { logs }
  } catch (err: any) {
    if (err.code === 'ENOENT') {
      throw createError({ statusCode: 404, message: 'Session not found' })
    }
    throw createError({ statusCode: 500, message: 'Failed to read session logs' })
  }
})

function extractTextContent(content: any): string {
  if (typeof content === 'string') return content
  
  if (Array.isArray(content)) {
    return content
      .filter((c: any) => c.type === 'text')
      .map((c: any) => c.text)
      .join('\n')
  }
  
  return ''
}
