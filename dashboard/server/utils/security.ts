/**
 * Security utilities for API routes
 * 
 * Provides:
 * - Path traversal protection for project names
 * - API authentication via bearer token
 * - Input sanitization helpers
 */

import { H3Event, createError, getHeader } from 'h3'

/**
 * Validate and sanitize a project name to prevent path traversal.
 * Allows: alphanumeric, hyphens, underscores, dots (not leading).
 * Rejects: slashes, backslashes, double dots, empty strings.
 */
export function validateProjectName(name: string | undefined): string {
  if (!name || typeof name !== 'string') {
    throw createError({ statusCode: 400, statusMessage: 'Project name is required' })
  }

  const trimmed = name.trim()

  if (
    trimmed.includes('..') ||
    trimmed.includes('/') ||
    trimmed.includes('\\') ||
    trimmed.startsWith('.') ||
    trimmed.length === 0 ||
    trimmed.length > 128
  ) {
    throw createError({ statusCode: 400, statusMessage: 'Invalid project name' })
  }

  if (!/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(trimmed)) {
    throw createError({ statusCode: 400, statusMessage: 'Invalid project name: only alphanumeric, hyphens, underscores, and dots allowed' })
  }

  return trimmed
}

/**
 * Validate a generic ID parameter (pipeline ID, role ID, etc.)
 */
export function validateId(id: string | undefined, label = 'ID'): string {
  if (!id || typeof id !== 'string') {
    throw createError({ statusCode: 400, statusMessage: `${label} is required` })
  }

  const trimmed = id.trim()

  if (!/^[a-zA-Z0-9][a-zA-Z0-9._-]{0,255}$/.test(trimmed)) {
    throw createError({ statusCode: 400, statusMessage: `Invalid ${label}` })
  }

  return trimmed
}

/**
 * Authenticate an API request via Bearer token.
 * If SWARMOPS_API_TOKEN is not configured, auth is disabled (with warning).
 */
export function requireAuth(event: H3Event): void {
  const expectedToken = process.env.SWARMOPS_API_TOKEN

  if (!expectedToken) {
    if (!(globalThis as any).__authWarned) {
      console.warn('[security] SWARMOPS_API_TOKEN not set - API auth DISABLED. Set this env var in production.')
      ;(globalThis as any).__authWarned = true
    }
    return
  }

  const authHeader = getHeader(event, 'authorization')

  if (!authHeader) {
    throw createError({ statusCode: 401, statusMessage: 'Authentication required' })
  }

  const token = authHeader.startsWith('Bearer ')
    ? authHeader.slice(7)
    : authHeader

  if (!timingSafeEqual(token, expectedToken)) {
    throw createError({ statusCode: 401, statusMessage: 'Invalid authentication token' })
  }
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  let result = 0
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i)
  }
  return result === 0
}

/**
 * Validate a string is safe for shell usage.
 * Rejects strings with dangerous shell metacharacters.
 */
export function validateShellSafe(value: string, label = 'value'): string {
  if (/[;&|`$(){}!\n\r<>'"\\]/.test(value)) {
    throw createError({
      statusCode: 400,
      statusMessage: `${label} contains invalid characters`
    })
  }
  return value
}
