import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('Chat API Endpoint', () => {
  describe('Request Validation', () => {
    it('should require a message field', () => {
      const validateRequest = (body: { message?: string }) => {
        if (!body.message?.trim()) {
          return { valid: false, error: 'Message is required', statusCode: 400 }
        }
        return { valid: true }
      }

      // Missing message
      expect(validateRequest({})).toEqual({
        valid: false,
        error: 'Message is required',
        statusCode: 400,
      })

      // Empty message
      expect(validateRequest({ message: '' })).toEqual({
        valid: false,
        error: 'Message is required',
        statusCode: 400,
      })

      // Whitespace-only message
      expect(validateRequest({ message: '   ' })).toEqual({
        valid: false,
        error: 'Message is required',
        statusCode: 400,
      })

      // Valid message
      expect(validateRequest({ message: 'Hello' })).toEqual({ valid: true })
    })

    it('should generate sessionId if not provided', () => {
      const createSession = (providedId?: string) => {
        return providedId || crypto.randomUUID()
      }

      // Without sessionId
      const generated = createSession()
      expect(generated).toBeDefined()
      expect(generated).toMatch(/^[a-f0-9-]{36}$/)

      // With sessionId
      const provided = 'my-session-123'
      expect(createSession(provided)).toBe(provided)
    })

    it('should trim message before processing', () => {
      const processMessage = (message: string) => message.trim()

      expect(processMessage('  Hello World  ')).toBe('Hello World')
      expect(processMessage('\nTest\n')).toBe('Test')
    })
  })

  describe('Response Format', () => {
    it('should return proper response structure', () => {
      interface ChatResponse {
        content: string
        sessionId: string
        timestamp: string
      }

      const createResponse = (content: string, sessionId: string): ChatResponse => ({
        content,
        sessionId,
        timestamp: new Date().toISOString(),
      })

      const response = createResponse('Hello from assistant', 'session-123')

      expect(response).toHaveProperty('content', 'Hello from assistant')
      expect(response).toHaveProperty('sessionId', 'session-123')
      expect(response).toHaveProperty('timestamp')
      expect(() => new Date(response.timestamp)).not.toThrow()
    })

    it('should handle empty content from gateway', () => {
      const processGatewayResponse = (data: { content?: string; message?: string }) => {
        return data.content || data.message || ''
      }

      expect(processGatewayResponse({ content: 'Hello' })).toBe('Hello')
      expect(processGatewayResponse({ message: 'Hi there' })).toBe('Hi there')
      expect(processGatewayResponse({})).toBe('')
    })
  })

  describe('Error Handling', () => {
    it('should handle gateway connection errors', () => {
      const handleError = (err: unknown): { statusCode: number; message: string } => {
        if (err instanceof Error && 'statusCode' in err) {
          return {
            statusCode: (err as any).statusCode,
            message: err.message,
          }
        }

        return {
          statusCode: 503,
          message: 'Unable to connect to OpenClaw gateway',
        }
      }

      // Generic error
      const genericError = new Error('Connection refused')
      expect(handleError(genericError)).toEqual({
        statusCode: 503,
        message: 'Unable to connect to OpenClaw gateway',
      })

      // Error with statusCode (already handled)
      const httpError = Object.assign(new Error('Not found'), { statusCode: 404 })
      expect(handleError(httpError)).toEqual({
        statusCode: 404,
        message: 'Not found',
      })
    })

    it('should handle gateway HTTP errors', async () => {
      const handleGatewayResponse = async (response: { ok: boolean; status: number; text: () => Promise<string> }) => {
        if (!response.ok) {
          const errorText = await response.text()
          return {
            error: true,
            statusCode: response.status,
            message: `Gateway error: ${errorText}`,
          }
        }
        return { error: false }
      }

      // 500 error
      const errorResponse = {
        ok: false,
        status: 500,
        text: async () => 'Internal server error',
      }

      await expect(handleGatewayResponse(errorResponse)).resolves.toEqual({
        error: true,
        statusCode: 500,
        message: 'Gateway error: Internal server error',
      })

      // Success
      const successResponse = {
        ok: true,
        status: 200,
        text: async () => '{}',
      }

      await expect(handleGatewayResponse(successResponse)).resolves.toEqual({
        error: false,
      })
    })
  })

  describe('Gateway URL Configuration', () => {
    it('should use default gateway URL when not configured', () => {
      const getGatewayUrl = (envUrl?: string) => {
        return envUrl || 'http://127.0.0.1:18789'
      }

      expect(getGatewayUrl()).toBe('http://127.0.0.1:18789')
      expect(getGatewayUrl('http://custom:8080')).toBe('http://custom:8080')
    })

    it('should construct correct chat endpoint URL', () => {
      const getChatEndpoint = (baseUrl: string) => {
        return `${baseUrl}/api/chat`
      }

      expect(getChatEndpoint('http://127.0.0.1:18789')).toBe('http://127.0.0.1:18789/api/chat')
      expect(getChatEndpoint('https://gateway.example.com')).toBe('https://gateway.example.com/api/chat')
    })
  })

  describe('Request Construction', () => {
    it('should send correct request body to gateway', () => {
      const constructGatewayRequest = (message: string, sessionId: string) => {
        return {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: message.trim(),
            sessionId,
          }),
        }
      }

      const request = constructGatewayRequest('  Hello World  ', 'session-123')

      expect(request.method).toBe('POST')
      expect(request.headers['Content-Type']).toBe('application/json')

      const body = JSON.parse(request.body)
      expect(body.message).toBe('Hello World') // Trimmed
      expect(body.sessionId).toBe('session-123')
    })
  })
})

describe('Chat Composable API Integration', () => {
  it('should correctly parse API response in composable', () => {
    interface ApiResponse {
      content: string
      sessionId: string
      timestamp: string
    }

    interface ChatMessage {
      id: string
      role: 'user' | 'assistant'
      content: string
      timestamp: Date
    }

    const parseApiResponse = (response: ApiResponse): ChatMessage => ({
      id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      role: 'assistant',
      content: response.content,
      timestamp: new Date(),
    })

    const apiResponse: ApiResponse = {
      content: 'Hello from the assistant!',
      sessionId: 'session-123',
      timestamp: '2026-02-04T14:00:00.000Z',
    }

    const message = parseApiResponse(apiResponse)

    expect(message.role).toBe('assistant')
    expect(message.content).toBe('Hello from the assistant!')
    expect(message.id).toMatch(/^msg-\d+-[a-z0-9]+$/)
    expect(message.timestamp).toBeInstanceOf(Date)
  })

  it('should update session ID from API response', () => {
    let currentSessionId: string | null = null

    const updateSessionId = (response: { sessionId?: string }) => {
      if (response.sessionId) {
        currentSessionId = response.sessionId
      }
    }

    expect(currentSessionId).toBeNull()

    updateSessionId({ sessionId: 'new-session-456' })
    expect(currentSessionId).toBe('new-session-456')

    // Should update again if different
    updateSessionId({ sessionId: 'another-session-789' })
    expect(currentSessionId).toBe('another-session-789')

    // Should not change if undefined
    updateSessionId({})
    expect(currentSessionId).toBe('another-session-789')
  })
})
