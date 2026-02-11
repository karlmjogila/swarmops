---
name: api-design
description: >
  Design and implement robust, consistent REST and GraphQL APIs with proper error handling,
  validation, status codes, pagination, and authentication patterns. Trigger this skill for
  any task involving API endpoints, route handlers, middleware, request/response design,
  or backend service interfaces. Also trigger on phrases like "build an API", "create endpoint",
  "REST service", or any request involving HTTP interface design.
triggers:
  - api
  - endpoint
  - rest
  - graphql
  - route
  - middleware
  - backend
  - handler
  - request
  - response
  - crud
  - webhook
---

# API Design Excellence

Build APIs that are intuitive, consistent, and resilient. A well-designed API is a contract — treat it with the same rigor as a public interface. Every endpoint should be predictable, well-documented by its own structure, and defensive against misuse.

## Core Principles

1. **Consistency over cleverness** — Every endpoint should feel like it belongs to the same API. Same naming conventions, same error format, same pagination style, everywhere.
2. **Fail loudly, recover gracefully** — Validate early, return clear errors, never swallow exceptions silently.
3. **Design for the consumer** — The person calling your API shouldn't need to read the source code to understand it.

## URL & Resource Design

### Naming Conventions
```
# Resources are nouns, plural, kebab-case
GET    /api/projects
GET    /api/projects/:id
POST   /api/projects
PATCH  /api/projects/:id
DELETE /api/projects/:id

# Sub-resources for relationships
GET    /api/projects/:id/tasks
POST   /api/projects/:id/tasks

# Actions that don't map to CRUD use verbs as sub-paths
POST   /api/projects/:id/archive
POST   /api/projects/:id/orchestrate
```

### Rules
- Never use verbs in resource URLs (`/getProjects` is wrong)
- Use plural nouns consistently (`/projects` not `/project`)
- Nest sub-resources max 2 levels deep (`/projects/:id/tasks/:taskId` — not deeper)
- Use query params for filtering, sorting, pagination: `?status=active&sort=-createdAt&limit=20`

## Request Handling

### Input Validation
Validate at the boundary. Never trust incoming data.

```typescript
// Validate and sanitize BEFORE any business logic
const body = await readBody(event)

// Required fields
if (!body.name?.trim()) {
  throw createError({ statusCode: 400, statusMessage: 'Name is required' })
}

// Type checking
if (typeof body.priority !== 'number' || body.priority < 1 || body.priority > 5) {
  throw createError({ statusCode: 400, statusMessage: 'Priority must be 1-5' })
}

// Length limits (prevent abuse)
if (body.description && body.description.length > 10000) {
  throw createError({ statusCode: 400, statusMessage: 'Description too long (max 10000 chars)' })
}

// Sanitize strings — strip control characters, trim whitespace
const name = body.name.trim().replace(/[\x00-\x1F\x7F]/g, '')
```

### Path Parameters
Always validate path params — they come from user-controlled URLs.

```typescript
const id = getRouterParam(event, 'id')
if (!id || !/^[a-zA-Z0-9_-]+$/.test(id)) {
  throw createError({ statusCode: 400, statusMessage: 'Invalid ID format' })
}
```

## Response Design

### Consistent Shape
Every response follows the same structure:

```typescript
// Success responses
{ "data": { ... } }                    // Single resource
{ "data": [...], "meta": { ... } }     // Collection with pagination

// Error responses
{
  "error": {
    "statusCode": 400,
    "message": "Human-readable description",
    "code": "VALIDATION_ERROR",        // Machine-readable code
    "details": [                       // Optional: specific field errors
      { "field": "email", "message": "Invalid email format" }
    ]
  }
}
```

### Status Codes — Use Them Correctly
```
200  OK           — Successful GET, PATCH
201  Created      — Successful POST that created a resource
204  No Content   — Successful DELETE
400  Bad Request  — Validation error, malformed input
401  Unauthorized — Missing or invalid authentication
403  Forbidden    — Authenticated but not allowed
404  Not Found    — Resource doesn't exist
409  Conflict     — Duplicate resource, state conflict
422  Unprocessable — Semantically invalid (valid JSON but wrong data)
429  Too Many     — Rate limited
500  Server Error — Unexpected failure (log it, alert on it)
503  Unavailable  — Dependency down (database, external API)
```

### Pagination
Use cursor-based pagination for large datasets, offset for simple cases:

```typescript
// Offset pagination (simple, fine for < 10k records)
GET /api/tasks?offset=0&limit=20

{
  "data": [...],
  "meta": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "hasMore": true
  }
}

// Cursor pagination (scalable, stable ordering)
GET /api/activity?cursor=eyJ0IjoiMjAyNC0wMS0xMCJ9&limit=50

{
  "data": [...],
  "meta": {
    "nextCursor": "eyJ0IjoiMjAyNC0wMS0xMSJ9",
    "hasMore": true
  }
}
```

## Error Handling

### Structured Error Pattern
```typescript
// Define application error codes
const ErrorCodes = {
  VALIDATION_ERROR: 400,
  NOT_FOUND: 404,
  DUPLICATE: 409,
  RATE_LIMITED: 429,
  INTERNAL: 500,
  DEPENDENCY_FAILED: 503,
} as const

// Throw structured errors
throw createError({
  statusCode: 404,
  statusMessage: `Project '${name}' not found`,
  data: { code: 'NOT_FOUND', resource: 'project', id: name }
})
```

### Never Expose Internals
```typescript
// BAD — leaks implementation details
throw createError({ statusCode: 500, statusMessage: err.stack })

// GOOD — log internally, return generic message
console.error('[api] Database query failed:', err)
throw createError({ statusCode: 503, statusMessage: 'Service temporarily unavailable' })
```

### Always Handle Async Errors
```typescript
// Every async operation must be caught
try {
  const data = await readFile(path, 'utf-8')
  return JSON.parse(data)
} catch (err) {
  if ((err as NodeJS.ErrnoException).code === 'ENOENT') {
    throw createError({ statusCode: 404, statusMessage: 'Resource not found' })
  }
  console.error('[api] Unexpected error:', err)
  throw createError({ statusCode: 500, statusMessage: 'Internal server error' })
}
```

## Authentication & Authorization

### Pattern
```typescript
// Auth check at the top of every protected handler
export default defineEventHandler(async (event) => {
  requireAuth(event)  // Throws 401 if not authenticated

  // Authorization — check specific permissions
  const project = await getProject(name)
  if (project.ownerId !== event.context.userId) {
    throw createError({ statusCode: 403, statusMessage: 'Not authorized' })
  }

  // ... handler logic
})
```

### Token Patterns
- API tokens in `Authorization: Bearer <token>` header
- Session cookies for browser clients (httpOnly, secure, sameSite)
- Never in query parameters (they end up in logs)

## Idempotency

Operations that can be retried safely:
- GET, HEAD, OPTIONS — always idempotent
- PUT — replace entire resource (idempotent by nature)
- DELETE — deleting twice returns 204 both times
- POST — use idempotency keys for critical operations:

```typescript
const idempotencyKey = getHeader(event, 'Idempotency-Key')
if (idempotencyKey) {
  const existing = await getByIdempotencyKey(idempotencyKey)
  if (existing) return existing  // Return cached result
}
```

## Rate Limiting

Protect your API from abuse:
```typescript
// Simple in-memory rate limiter
const rateLimits = new Map<string, { count: number, resetAt: number }>()

function checkRateLimit(key: string, maxRequests: number, windowMs: number) {
  const now = Date.now()
  const entry = rateLimits.get(key)

  if (!entry || now > entry.resetAt) {
    rateLimits.set(key, { count: 1, resetAt: now + windowMs })
    return
  }

  if (entry.count >= maxRequests) {
    throw createError({
      statusCode: 429,
      statusMessage: 'Too many requests',
      data: { retryAfter: Math.ceil((entry.resetAt - now) / 1000) }
    })
  }

  entry.count++
}
```

## Quality Checklist

- [ ] All inputs validated and sanitized at the boundary
- [ ] Consistent response shape across all endpoints
- [ ] Correct HTTP status codes (not everything is 200 or 500)
- [ ] Error responses include machine-readable code and human-readable message
- [ ] No internal details leaked in error responses
- [ ] Authentication checked before any business logic
- [ ] Path parameters validated (no injection via URL)
- [ ] Async errors caught and handled (no unhandled promise rejections)
- [ ] Large collections paginated
- [ ] Content-Type headers set correctly

## Anti-Patterns

- Returning 200 for errors with `{ success: false }` in the body
- Using GET for state-changing operations
- Putting sensitive data in query parameters
- Inconsistent naming (camelCase in one endpoint, snake_case in another)
- Nested resources deeper than 2 levels
- Returning the entire database record including internal fields
- Silently ignoring unknown request body fields (validate strictly)
- Using sequential integer IDs in URLs (use UUIDs or slugs)
