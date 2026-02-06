# API Reference

SwarmOps exposes a REST API for programmatic access to all orchestration features. All endpoints return JSON.

## Base URL

```
http://localhost:3000/api
```

## Authentication

Include an API key in the `Authorization` header:

```
Authorization: Bearer <your-api-key>
```

---

## Projects

### List Projects

```http
GET /api/projects
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `archived` | boolean | Include archived projects |
| `limit` | number | Max results (default: 50) |
| `offset` | number | Pagination offset |

**Response:**

```json
{
  "projects": [
    {
      "name": "my-project",
      "status": "running",
      "taskCount": 42,
      "completedCount": 38,
      "createdAt": "2024-01-15T10:30:00Z",
      "updatedAt": "2024-01-15T12:45:00Z"
    }
  ],
  "total": 1
}
```

### Get Project

```http
GET /api/projects/:name
```

**Response:**

```json
{
  "name": "my-project",
  "status": "running",
  "config": {
    "maxWorkers": 4,
    "timeout": 300000
  },
  "stats": {
    "pending": 4,
    "running": 2,
    "completed": 38,
    "failed": 0
  },
  "createdAt": "2024-01-15T10:30:00Z"
}
```

### Create Project

```http
POST /api/projects
```

**Request Body:**

```json
{
  "name": "new-project",
  "config": {
    "maxWorkers": 4,
    "timeout": 300000,
    "retryPolicy": {
      "maxAttempts": 3,
      "backoff": "exponential"
    }
  }
}
```

### Archive Project

```http
POST /api/projects/:name/archive
```

### Unarchive Project

```http
POST /api/projects/:name/unarchive
```

---

## Tasks

### List Tasks

```http
GET /api/projects/:name/tasks
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status |
| `limit` | number | Max results |
| `before` | string | Cursor for pagination |

**Response:**

```json
{
  "tasks": [
    {
      "id": "task_abc123",
      "type": "process",
      "status": "completed",
      "input": { "data": "..." },
      "output": { "result": "..." },
      "workerId": "worker_1",
      "startedAt": "2024-01-15T12:00:00Z",
      "completedAt": "2024-01-15T12:00:45Z"
    }
  ],
  "cursor": "task_abc122"
}
```

### Submit Task

```http
POST /api/projects/:name/tasks
```

**Request Body:**

```json
{
  "type": "process",
  "input": {
    "prompt": "Analyze this data",
    "data": { ... }
  },
  "priority": "normal",
  "timeout": 60000
}
```

**Response:**

```json
{
  "id": "task_xyz789",
  "status": "pending",
  "createdAt": "2024-01-15T12:30:00Z"
}
```

### Get Task

```http
GET /api/projects/:name/tasks/:taskId
```

### Cancel Task

```http
POST /api/projects/:name/tasks/:taskId/cancel
```

---

## Workers

### List Workers

```http
GET /api/workers
```

**Response:**

```json
{
  "workers": [
    {
      "id": "worker_1",
      "name": "local-worker-1",
      "status": "online",
      "currentTask": "task_abc123",
      "capabilities": ["process", "transform"],
      "lastHeartbeat": "2024-01-15T12:45:30Z"
    }
  ]
}
```

### Get Worker

```http
GET /api/workers/:id
```

### Worker Stats

```http
GET /api/workers/:id/stats
```

**Response:**

```json
{
  "tasksCompleted": 156,
  "tasksFailed": 3,
  "avgDuration": 12500,
  "uptime": 86400000
}
```

---

## Pipelines

### List Pipelines

```http
GET /api/projects/:name/pipelines
```

### Create Pipeline

```http
POST /api/projects/:name/pipelines
```

**Request Body:**

```json
{
  "name": "data-processing",
  "steps": [
    {
      "name": "fetch",
      "action": "http_get",
      "config": {
        "url": "https://api.example.com/data"
      }
    },
    {
      "name": "transform",
      "action": "process",
      "config": {
        "input": "${{ steps.fetch.output }}"
      }
    }
  ]
}
```

### Run Pipeline

```http
POST /api/projects/:name/pipelines/:pipelineId/run
```

**Request Body:**

```json
{
  "params": {
    "startDate": "2024-01-01",
    "endDate": "2024-01-15"
  }
}
```

### Get Pipeline Run

```http
GET /api/projects/:name/pipelines/:pipelineId/runs/:runId
```

---

## Ledger

### Query Ledger

```http
GET /api/projects/:name/ledger
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `type` | string | Event type filter |
| `after` | string | After timestamp |
| `before` | string | Before timestamp |
| `limit` | number | Max entries |

**Response:**

```json
{
  "entries": [
    {
      "id": "entry_001",
      "type": "task.completed",
      "taskId": "task_abc123",
      "data": { ... },
      "timestamp": "2024-01-15T12:00:45Z"
    }
  ]
}
```

---

## WebSocket API

Connect for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:3000/ws');

ws.onmessage = (event) => {
  const { type, payload } = JSON.parse(event.data);
  
  switch (type) {
    case 'task.created':
    case 'task.updated':
    case 'task.completed':
      console.log('Task event:', payload);
      break;
    case 'worker.online':
    case 'worker.offline':
      console.log('Worker event:', payload);
      break;
  }
};

// Subscribe to project events
ws.send(JSON.stringify({
  action: 'subscribe',
  project: 'my-project'
}));
```

### Event Types

| Event | Description |
|-------|-------------|
| `task.created` | New task submitted |
| `task.assigned` | Task assigned to worker |
| `task.updated` | Task progress update |
| `task.completed` | Task finished successfully |
| `task.failed` | Task failed |
| `worker.online` | Worker connected |
| `worker.offline` | Worker disconnected |
| `pipeline.started` | Pipeline run started |
| `pipeline.completed` | Pipeline run finished |

---

## Error Responses

All errors return a consistent format:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Project 'xyz' not found",
    "details": { ... }
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `NOT_FOUND` | 404 | Resource doesn't exist |
| `BAD_REQUEST` | 400 | Invalid request data |
| `UNAUTHORIZED` | 401 | Missing/invalid auth |
| `FORBIDDEN` | 403 | Access denied |
| `CONFLICT` | 409 | Resource conflict |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Rate Limiting

API requests are rate limited:

- **Default:** 100 requests/minute
- **Authenticated:** 1000 requests/minute

Rate limit headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1705320000
```
