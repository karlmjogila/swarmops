---
name: api-design
description: >
  Design and implement robust, consistent REST, GraphQL, and gRPC APIs with proper error handling,
  validation, status codes, pagination, versioning, caching, and authentication patterns. Trigger
  this skill for any task involving API endpoints, route handlers, middleware, request/response
  design, OpenAPI specs, protobuf definitions, API gateways, or backend service interfaces.
triggers:
  - api
  - endpoint
  - rest
  - graphql
  - route
  - middleware
  - handler
  - request
  - response
  - crud
  - webhook
  - openapi
  - swagger
  - grpc
  - protobuf
  - api gateway
  - cache-control
  - etag
  - versioning
---

# API Design Excellence

Build APIs that are intuitive, consistent, and resilient. A well-designed API is a contract — treat it with the same rigor as a public interface. Every endpoint should be predictable, self-documenting, and defensive against misuse. Services are self-contained and export via port binding — no runtime server injection, no external container dependency.

## Core Principles

1. **Consistency over cleverness** — Same naming, same error format, same pagination style, everywhere.
2. **Fail loudly, recover gracefully** — Validate early, return clear errors, never swallow exceptions.
3. **Design for the consumer** — The caller shouldn't need source code to understand the API.
4. **Contract first** — Write a test that asserts the contract, then build the handler.

## URL & Resource Design

```
# Nouns, plural, kebab-case — ALWAYS version in the URL
GET    /api/v1/projects            POST   /api/v1/projects
GET    /api/v1/projects/:id        PATCH  /api/v1/projects/:id
DELETE /api/v1/projects/:id
GET    /api/v1/projects/:id/tasks  # Sub-resources (max 2 levels deep)
POST   /api/v1/projects/:id/archive  # Non-CRUD actions use verb sub-paths
```

- NEVER use verbs in resource URLs (`/getProjects` is wrong)
- Use plural nouns (`/projects` not `/project`)
- Query params for filtering/sorting/pagination: `?status=active&sort=-createdAt&limit=20`

## TDD: Contract-First Development

ALWAYS write a contract test before implementing. The test IS the specification.

```typescript
// __tests__/api/projects.test.ts — WRITE THIS FIRST
describe('POST /api/v1/projects', () => {
  it('creates a project and returns 201', async () => {
    const res = await $fetch('/api/v1/projects', {
      method: 'POST', body: { name: 'my-project', description: 'Test' },
    })
    expect(res.status).toBe(201)
    expect(res.data).toMatchObject({ id: expect.any(String), name: 'my-project' })
  })

  it('returns 400 when name is missing', async () => {
    const res = await $fetch('/api/v1/projects', {
      method: 'POST', body: {}, ignoreResponseError: true,
    })
    expect(res.status).toBe(400)
    expect(res.error.code).toBe('VALIDATION_ERROR')
  })

  it('returns 409 on duplicate name', async () => {
    await $fetch('/api/v1/projects', { method: 'POST', body: { name: 'dup' } })
    const res = await $fetch('/api/v1/projects', {
      method: 'POST', body: { name: 'dup' }, ignoreResponseError: true,
    })
    expect(res.status).toBe(409)
  })
})
```

## Request Handling

```typescript
// Validate at the boundary — NEVER trust incoming data
const body = await readBody(event)
if (!body.name?.trim())
  throw createError({ statusCode: 400, statusMessage: 'Name is required' })
if (typeof body.priority !== 'number' || body.priority < 1 || body.priority > 5)
  throw createError({ statusCode: 400, statusMessage: 'Priority must be 1-5' })
if (body.description?.length > 10000)
  throw createError({ statusCode: 400, statusMessage: 'Description too long (max 10000)' })
const name = body.name.trim().replace(/[\x00-\x1F\x7F]/g, '')

// ALWAYS validate path params — user-controlled URLs
const id = getRouterParam(event, 'id')
if (!id || !/^[a-zA-Z0-9_-]+$/.test(id))
  throw createError({ statusCode: 400, statusMessage: 'Invalid ID format' })
```

## Response Design

```typescript
// Success
{ "data": { ... } }                 // Single resource
{ "data": [...], "meta": { ... } }  // Collection

// Error — ALWAYS machine-readable code + human-readable message
{ "error": { "statusCode": 400, "code": "VALIDATION_ERROR", "message": "Name is required",
    "details": [{ "field": "name", "message": "Required" }] } }
```

### Status Codes
```
200 OK — GET, PATCH       400 Bad Request     409 Conflict        500 Server Error
201 Created — POST        401 Unauthorized    422 Unprocessable   503 Unavailable
204 No Content — DELETE   403 Forbidden       429 Too Many
304 Not Modified — ETag   404 Not Found
```

### Pagination
```typescript
// Offset (< 10k records): GET /api/v1/tasks?offset=0&limit=20
{ "data": [...], "meta": { "total": 150, "limit": 20, "offset": 0, "hasMore": true } }
// Cursor (scalable): GET /api/v1/activity?cursor=abc123&limit=50
{ "data": [...], "meta": { "nextCursor": "def456", "hasMore": true } }
```

## Error Handling

```typescript
// BAD — leaks internals
throw createError({ statusCode: 500, statusMessage: err.stack })
// GOOD — log internally, return generic
console.error('[api] Query failed:', err)
throw createError({ statusCode: 503, statusMessage: 'Service temporarily unavailable' })

// ALWAYS catch async errors
try {
  return JSON.parse(await readFile(path, 'utf-8'))
} catch (err) {
  if ((err as NodeJS.ErrnoException).code === 'ENOENT')
    throw createError({ statusCode: 404, statusMessage: 'Resource not found' })
  throw createError({ statusCode: 500, statusMessage: 'Internal server error' })
}
```

## Authentication & Authorization

```typescript
export default defineEventHandler(async (event) => {
  requireAuth(event)  // 401 if not authenticated
  const project = await getProject(name)
  if (project.ownerId !== event.context.userId)
    throw createError({ statusCode: 403, statusMessage: 'Not authorized' })
})
```

- Tokens in `Authorization: Bearer <token>` header. NEVER in query parameters.
- Session cookies: httpOnly, secure, sameSite.

## Idempotency

GET/HEAD/OPTIONS always idempotent. PUT idempotent by nature. DELETE returns 204 twice. POST — use idempotency keys:

```typescript
const key = getHeader(event, 'Idempotency-Key')
if (key) { const existing = await getByIdempotencyKey(key); if (existing) return existing }
```

## Rate Limiting

```typescript
const rateLimits = new Map<string, { count: number, resetAt: number }>()
function checkRateLimit(key: string, max: number, windowMs: number) {
  const now = Date.now(), entry = rateLimits.get(key)
  if (!entry || now > entry.resetAt) { rateLimits.set(key, { count: 1, resetAt: now + windowMs }); return }
  if (entry.count >= max) throw createError({ statusCode: 429, statusMessage: 'Too many requests' })
  entry.count++
}
```

ALWAYS return headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

## API Versioning

URL path versioning is primary — most explicit, most debuggable: `/api/v1/...`, `/api/v2/...`

Header versioning secondary: `Accept: application/vnd.myapi.v2+json`

### Deprecation — ALWAYS announce before removal
```typescript
function deprecated(sunsetDate: string) {
  return defineEventHandler((event) => {
    setHeader(event, 'Sunset', sunsetDate)
    setHeader(event, 'Deprecation', 'true')
    setHeader(event, 'Link', '</api/v2/projects>; rel="successor-version"')
  })
}
```

Ship v2 alongside v1. Add Sunset header. Monitor traffic. After sunset return 410 Gone (not 404).

## OpenAPI / Swagger

The spec IS the source of truth. Define it before writing code.

```yaml
openapi: 3.1.0
info: { title: Projects API, version: 1.0.0 }
servers: [{ url: /api/v1 }]
paths:
  /projects:
    get:
      operationId: listProjects
      parameters:
        - { name: status, in: query, schema: { type: string, enum: [active, archived] } }
        - { name: limit, in: query, schema: { type: integer, default: 20, maximum: 100 } }
      responses:
        '200':
          content:
            application/json:
              schema:
                properties:
                  data: { type: array, items: { $ref: '#/components/schemas/Project' } }
                  meta: { $ref: '#/components/schemas/PaginationMeta' }
    post:
      operationId: createProject
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/CreateProjectInput' }
      responses:
        '201': { description: Created }
        '400': { $ref: '#/components/responses/ValidationError' }
components:
  schemas:
    Project:
      type: object
      required: [id, name, createdAt]
      properties:
        id: { type: string, format: uuid }
        name: { type: string, minLength: 1, maxLength: 100 }
        createdAt: { type: string, format: date-time }
    CreateProjectInput:
      type: object
      required: [name]
      properties:
        name: { type: string, minLength: 1, maxLength: 100 }
        description: { type: string, maxLength: 10000 }
```

### Auto-Generation (FastAPI)
```python
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Projects API", version="1.0.0")

class CreateProjectInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=10000)

@app.post("/api/v1/projects", status_code=201)
async def create_project(body: CreateProjectInput):
    return await project_service.create(body)  # OpenAPI spec auto-generated
```

### Contract Testing
```typescript
import SwaggerParser from '@apidevtools/swagger-parser'

it('response matches OpenAPI spec', async () => {
  const spec = await SwaggerParser.validate('./openapi.yaml')
  const res = await $fetch('/api/v1/projects')
  const schema = spec.paths['/projects'].get.responses['200'].content['application/json'].schema
  expect(res).toMatchSchema(schema)
})
```

## GraphQL

### Schema Design (SDL)
```graphql
type Project {
  id: ID!
  name: String!
  description: String
  status: ProjectStatus!
  tasks(first: Int = 20, after: String): TaskConnection!
  owner: User!
  createdAt: DateTime!
}

enum ProjectStatus { ACTIVE ARCHIVED DELETED }

# Relay-style connections for pagination — ALWAYS
type TaskConnection { edges: [TaskEdge!]!  pageInfo: PageInfo!  totalCount: Int! }
type TaskEdge { node: Task!  cursor: String! }
type PageInfo { hasNextPage: Boolean!  endCursor: String }

input CreateProjectInput { name: String!  description: String }
input UpdateProjectInput { name: String  description: String  status: ProjectStatus }

type Query {
  project(id: ID!): Project
  projects(status: ProjectStatus, first: Int = 20, after: String): ProjectConnection!
}
type Mutation {
  createProject(input: CreateProjectInput!): Project!
  updateProject(id: ID!, input: UpdateProjectInput!): Project!
  deleteProject(id: ID!): DeleteResult!
}
type Subscription { projectUpdated(id: ID!): Project! }
scalar DateTime
```

### Resolvers + DataLoader (N+1 Prevention)
```typescript
const resolvers = {
  Query: {
    project: async (_: any, { id }: { id: string }, ctx: Context) => {
      const p = await ctx.services.project.getById(id)
      if (!p) throw new GraphQLError('Not found', { extensions: { code: 'NOT_FOUND' } })
      return p
    },
  },
  Project: {
    owner: (p: Project, _: any, ctx: Context) => ctx.loaders.user.load(p.ownerId),
    tasks: (p: Project, args: any, ctx: Context) => ctx.services.task.listByProject(p.id, args),
  },
}

// DataLoader — batch DB calls per request. NEVER share loaders across requests.
import DataLoader from 'dataloader'
export function createLoaders(db: Database) {
  return {
    user: new DataLoader<string, User>(async (ids) => {
      const users = await db.users.findMany({ where: { id: { in: [...ids] } } })
      const map = new Map(users.map(u => [u.id, u]))
      return ids.map(id => map.get(id) || new Error(`User ${id} not found`))
    }),
  }
}
```

GraphQL errors: NEVER expose internals. Use `extensions.code` for machine-readable codes.

## gRPC

### Proto File Design
```protobuf
syntax = "proto3";
package myapi.project.v1;
option go_package = "github.com/myorg/myapi/gen/go/project/v1";
import "google/protobuf/timestamp.proto";
import "google/protobuf/field_mask.proto";

service ProjectService {
  rpc CreateProject(CreateProjectRequest) returns (Project);              // Unary
  rpc GetProject(GetProjectRequest) returns (Project);                    // Unary
  rpc ListProjects(ListProjectsRequest) returns (ListProjectsResponse);   // Unary
  rpc UpdateProject(UpdateProjectRequest) returns (Project);              // Unary
  rpc WatchProject(WatchProjectRequest) returns (stream ProjectEvent);    // Server stream
  rpc ImportTasks(stream ImportTaskRequest) returns (ImportTasksResponse); // Client stream
  rpc SyncProject(stream SyncMessage) returns (stream SyncMessage);       // Bidirectional
}

message Project {
  string id = 1;  string name = 2;  string description = 3;
  ProjectStatus status = 4;
  google.protobuf.Timestamp created_at = 5;
  google.protobuf.Timestamp updated_at = 6;
}
enum ProjectStatus {
  PROJECT_STATUS_UNSPECIFIED = 0;  PROJECT_STATUS_ACTIVE = 1;  PROJECT_STATUS_ARCHIVED = 2;
}

message CreateProjectRequest { string name = 1; string description = 2; }
message GetProjectRequest { string id = 1; }
message UpdateProjectRequest {
  string id = 1;  Project project = 2;  google.protobuf.FieldMask update_mask = 3;
}
message ListProjectsRequest { int32 page_size = 1; string page_token = 2; }
message ListProjectsResponse { repeated Project projects = 1; string next_page_token = 2; }
message WatchProjectRequest { string id = 1; }
message ProjectEvent {
  string project_id = 1;  string event_type = 2;
  google.protobuf.Timestamp timestamp = 3;  Project project = 4;
}
message ImportTaskRequest { string project_id = 1; string task_name = 2; }
message ImportTasksResponse { int32 imported_count = 1; int32 failed_count = 2; }
message SyncMessage { string project_id = 1; oneof payload { string update = 2; string cursor = 3; } }
```

### Error Codes + Streaming
```typescript
import { status } from '@grpc/grpc-js'
// NEVER use OK for errors — map to canonical gRPC codes
const GrpcErrorMap = {
  NOT_FOUND: status.NOT_FOUND, ALREADY_EXISTS: status.ALREADY_EXISTS,
  PERMISSION_DENIED: status.PERMISSION_DENIED, VALIDATION: status.INVALID_ARGUMENT,
  INTERNAL: status.INTERNAL, UNAVAILABLE: status.UNAVAILABLE,
} as const

// Server streaming
const call = client.watchProject({ id: 'proj-123' })
call.on('data', (event: ProjectEvent) => console.log(event.eventType))
call.on('error', (err) => {
  if (err.code === status.UNAVAILABLE) setTimeout(() => reconnect(), backoffMs)
})
```

## HTTP Caching

```typescript
// Immutable assets — cache aggressively
setHeader(event, 'Cache-Control', 'public, max-age=31536000, immutable')
// Dynamic — revalidate periodically
setHeader(event, 'Cache-Control', 'public, max-age=60, stale-while-revalidate=300')
// Private user data — browser only
setHeader(event, 'Cache-Control', 'private, max-age=0, must-revalidate')
// Sensitive — NEVER cache
setHeader(event, 'Cache-Control', 'no-store')
```

### ETag / If-None-Match
```typescript
const body = JSON.stringify(data)
const etag = `"${createHash('md5').update(body).digest('hex')}"`
setHeader(event, 'ETag', etag)
if (getHeader(event, 'if-none-match') === etag) { setResponseStatus(event, 304); return null }
```

ALWAYS set `Vary` when response differs by header. Use `Surrogate-Control` for CDN-specific rules. Include API version in URL so CDN caches per version. Purge CDN on writes.

## API Gateway Patterns

### AWS API Gateway (Terraform)
```hcl
resource "aws_api_gateway_rest_api" "main" {
  name = "${var.project}-api"
  endpoint_configuration { types = ["REGIONAL"] }
}

resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.prod.stage_name
  method_path = "*/*"
  settings {
    throttling_burst_limit = 500
    throttling_rate_limit  = 1000
    metrics_enabled        = true
  }
}

resource "aws_api_gateway_usage_plan" "standard" {
  name = "standard"
  api_stages { api_id = aws_api_gateway_rest_api.main.id; stage = aws_api_gateway_stage.prod.stage_name }
  throttle_settings { burst_limit = 100; rate_limit = 200 }
  quota_settings    { limit = 50000; period = "MONTH" }
}
```

### Gateway-Level Auth (Lambda Authorizer)
```typescript
export const handler = async (event: APIGatewayTokenAuthorizerEvent) => {
  const token = event.authorizationToken?.replace('Bearer ', '')
  if (!token) throw new Error('Unauthorized')
  const decoded = jwt.verify(token, process.env.JWT_SECRET!)
  return {
    principalId: decoded.sub,
    policyDocument: { Version: '2012-10-17',
      Statement: [{ Action: 'execute-api:Invoke', Effect: 'Allow', Resource: event.methodArn }] },
    context: { userId: decoded.sub, role: decoded.role },
  }
}
```

### Responsibility Split
Gateway: auth/JWT, rate limiting, CORS, request ID, compression, SSL, metrics.
Service: business logic, authorization, data access, domain validation.
The gateway is a router — NEVER put business logic in gateway transformations.

## Quality Checklist

- [ ] All inputs validated and sanitized at the boundary
- [ ] Consistent response shape across all endpoints
- [ ] Correct HTTP status codes (not everything is 200 or 500)
- [ ] Error responses include machine-readable code and human-readable message
- [ ] No internal details leaked in error responses
- [ ] Auth checked before business logic; path params validated
- [ ] Async errors caught and handled (no unhandled rejections)
- [ ] Large collections paginated; Content-Type headers correct
- [ ] API version in URL path; deprecated endpoints return Sunset headers
- [ ] OpenAPI spec exists; contract tests validate against it
- [ ] Cache-Control/ETag headers on GET responses
- [ ] Rate limit headers on all responses
- [ ] GraphQL resolvers use DataLoader; gRPC uses canonical error codes
- [ ] Service exports via port binding — self-contained, no injected server

## Anti-Patterns

- Returning 200 for errors with `{ success: false }` in the body
- Using GET for state-changing operations
- Putting sensitive data in query parameters
- Inconsistent naming (camelCase in one endpoint, snake_case in another)
- Nested resources deeper than 2 levels
- Returning entire database records including internal fields
- Using sequential integer IDs in URLs (use UUIDs or slugs)
- Versioning only in headers — impossible to debug with curl
- No deprecation warning before removing API versions
- N+1 queries in GraphQL resolvers (ALWAYS use DataLoader)
- Sharing DataLoader instances across requests
- Using `no-cache` when you mean `no-store` (they are different)
- Business logic in API gateway transformations
- Skipping contract tests — "the spec is documentation only" leads to drift
