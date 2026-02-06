import { writeFile, mkdir } from 'fs/promises'
import { join } from 'path'
import { tmpdir } from 'os'

interface ChatRequest {
  message: string
  sessionKey?: string  // Reuse existing session for continuity
  image?: string
}

interface ChatResponse {
  content: string
  sessionKey: string
  timestamp: string
}

function getGatewayConfig(event: any) {
  const config = useRuntimeConfig(event)
  return {
    url: config.gatewayUrl || 'http://127.0.0.1:18789',
    token: config.gatewayToken || ''
  }
}

async function saveImageToTemp(dataUrl: string): Promise<string | null> {
  const match = dataUrl.match(/^data:image\/([^;]+);base64,(.+)$/)
  if (!match) return null
  
  const ext = match[1] === 'jpeg' ? 'jpg' : match[1]
  const base64Data = match[2]
  const buffer = Buffer.from(base64Data, 'base64')
  
  const tempDir = join(tmpdir(), 'swarmops-chat-images')
  await mkdir(tempDir, { recursive: true })
  
  const filename = `chat-image-${Date.now()}.${ext}`
  const filepath = join(tempDir, filename)
  
  await writeFile(filepath, buffer)
  return filepath
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
    const text = await response.text()
    console.error('[chat] Gateway error:', response.status, text.slice(0, 500))
    throw new Error(`Gateway error: ${response.status}`)
  }
  
  return response.json()
}

async function pollForResponse(gw: { url: string, token: string }, sessionKey: string, maxWaitMs: number = 120000): Promise<string> {
  const startTime = Date.now()
  let pollInterval = 500
  
  while (Date.now() - startTime < maxWaitMs) {
    await new Promise(resolve => setTimeout(resolve, pollInterval))
    if (pollInterval < 2000) pollInterval += 100
    
    try {
      const data = await invokeGateway(gw, 'sessions_history', {
        sessionKey,
        limit: 10,
        includeTools: false
      })
      
      const result = data.result?.details || data.result || {}
      const messages = result.messages || []
      
      // Look for the last assistant message
      for (let i = messages.length - 1; i >= 0; i--) {
        const msg = messages[i]
        if (msg.role === 'assistant') {
          if (typeof msg.content === 'string') {
            return msg.content
          }
          if (Array.isArray(msg.content)) {
            const textPart = msg.content.find((c: any) => c.type === 'text')
            if (textPart?.text) {
              return textPart.text
            }
          }
        }
      }
    } catch (err) {
      console.error('[chat] Poll error:', err)
    }
  }
  
  return 'Response timed out'
}

export default defineEventHandler(async (event): Promise<ChatResponse> => {
  const body = await readBody<ChatRequest>(event)

  if (!body.message?.trim() && !body.image) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Message or image is required'
    })
  }

  const gw = getGatewayConfig(event)

  try {
    let messageContent = body.message?.trim() || ''
    
    // Handle image attachment
    if (body.image) {
      const imagePath = await saveImageToTemp(body.image)
      if (imagePath) {
        const imageNote = `\n\n[Image attached: ${imagePath}]\nPlease use the image tool to analyze this file.`
        messageContent = messageContent ? messageContent + imageNote : `Please analyze this image: ${imagePath}`
      }
    }

    let sessionKey = body.sessionKey

    if (sessionKey) {
      // Continue existing conversation with sessions_send
      console.log('[chat] Continuing session:', sessionKey)
      
      const sendData = await invokeGateway(gw, 'sessions_send', {
        sessionKey,
        message: messageContent,
        timeoutSeconds: 120
      })
      
      const result = sendData.result?.details || sendData.result || {}
      const content = result.reply || result.response || result.content || result.message || 'No response'
      
      return {
        content,
        sessionKey,
        timestamp: new Date().toISOString()
      }
    } else {
      // First message - spawn a new dedicated agent
      console.log('[chat] Spawning new chat session')
      
      const spawnData = await invokeGateway(gw, 'sessions_spawn', {
        task: `You are a helpful assistant in the SwarmOps dashboard chat. The user says: ${messageContent}`,
        label: `swarmops-chat-${Date.now()}`,
        model: 'sonnet'
      })
      
      const spawnResult = spawnData.result?.details || spawnData.result || {}
      sessionKey = spawnResult.childSessionKey
      
      if (!sessionKey) {
        throw new Error('Failed to spawn chat agent')
      }
      
      console.log('[chat] Spawned new session:', sessionKey)
      
      // Poll for the initial response
      const content = await pollForResponse(gw, sessionKey, 120000)

      return {
        content,
        sessionKey,
        timestamp: new Date().toISOString()
      }
    }
  } catch (err) {
    if ((err as any).statusCode) {
      throw err
    }

    console.error('[chat] Error:', err)
    throw createError({
      statusCode: 503,
      statusMessage: 'AI gateway is currently unavailable'
    })
  }
})
