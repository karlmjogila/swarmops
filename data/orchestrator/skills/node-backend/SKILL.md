---
name: node-backend
description: >
  Build robust, production-grade Node.js backend services with proper async patterns,
  error handling, process management, file I/O, streaming, child processes, and
  service architecture. Trigger this skill for any task involving Node.js server-side
  code, background workers, file processing, process spawning, event-driven architecture,
  or backend service design.
triggers:
  - node
  - nodejs
  - server
  - backend
  - worker
  - process
  - spawn
  - child process
  - stream
  - buffer
  - event
  - cron
  - queue
  - job
  - service
  - daemon
---

# Node.js Backend Excellence

Node.js shines for I/O-heavy, event-driven services. Lean into its strengths — async I/O, streams, event loops — and respect its constraints. A well-built Node backend handles thousands of concurrent connections with minimal resources.

## Core Principles

1. **Never block the event loop** — CPU-heavy work goes to worker threads or external processes. The event loop serves I/O.
2. **Handle every error** — Unhandled rejections and uncaught exceptions crash your process. Every async operation needs error handling.
3. **Streams over buffers** — Don't load entire files into memory. Stream them.

## Async Patterns

### async/await — The Default
```typescript
// Always use async/await, not raw promises or callbacks
async function loadProject(name: string): Promise<Project> {
  const statePath = join(projectsDir, name, 'state.json')
  const data = await readFile(statePath, 'utf-8')
  return JSON.parse(data)
}

// Parallel execution when operations are independent
async function loadProjectWithActivity(name: string) {
  const [state, activity] = await Promise.all([
    readFile(join(projectsDir, name, 'state.json'), 'utf-8'),
    readFile(join(projectsDir, name, 'activity.jsonl'), 'utf-8').catch(() => ''),
  ])

  return {
    state: JSON.parse(state),
    activity: activity.split('\n').filter(Boolean).map(line => JSON.parse(line)),
  }
}

// Sequential when order matters
async function advancePhases(projects: string[]) {
  const results = []
  for (const name of projects) {
    const result = await checkAndAdvancePhase(name)
    results.push(result)
  }
  return results
}
```

### Promise.allSettled for Fault Tolerance
```typescript
// When some operations can fail without killing the batch
async function checkAllProjects(names: string[]) {
  const results = await Promise.allSettled(
    names.map(name => checkProjectHealth(name))
  )

  const healthy = results
    .filter((r): r is PromiseFulfilledResult<HealthCheck> => r.status === 'fulfilled')
    .map(r => r.value)

  const failed = results
    .filter((r): r is PromiseRejectedResult => r.status === 'rejected')
    .map(r => r.reason)

  if (failed.length > 0) {
    console.error(`${failed.length} health checks failed:`, failed)
  }

  return { healthy, failed }
}
```

### Concurrency Control
```typescript
// Limit concurrent operations to avoid overwhelming resources
async function processWithLimit<T, R>(
  items: T[],
  fn: (item: T) => Promise<R>,
  concurrency: number
): Promise<R[]> {
  const results: R[] = []
  const executing = new Set<Promise<void>>()

  for (const item of items) {
    const promise = fn(item).then(result => {
      results.push(result)
      executing.delete(promise)
    })
    executing.add(promise)

    if (executing.size >= concurrency) {
      await Promise.race(executing)
    }
  }

  await Promise.all(executing)
  return results
}

// Usage: spawn max 5 workers at a time
await processWithLimit(tasks, spawnWorker, 5)
```

## Error Handling

### Operational vs Programmer Errors
```typescript
// Operational errors: expected failures, handle gracefully
async function loadConfig(path: string): Promise<Config> {
  try {
    const data = await readFile(path, 'utf-8')
    return JSON.parse(data)
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === 'ENOENT') {
      // File not found — return defaults (operational error)
      return DEFAULT_CONFIG
    }
    if (err instanceof SyntaxError) {
      // Invalid JSON — log and return defaults
      console.error(`[config] Invalid JSON in ${path}:`, err.message)
      return DEFAULT_CONFIG
    }
    // Unexpected error — re-throw (programmer error)
    throw err
  }
}
```

### Global Error Handlers
```typescript
// Catch unhandled errors at process level
process.on('unhandledRejection', (reason, promise) => {
  console.error('[FATAL] Unhandled rejection:', reason)
  // Log but don't exit — let the process manager (systemd) handle restart
})

process.on('uncaughtException', (err) => {
  console.error('[FATAL] Uncaught exception:', err)
  // For uncaught exceptions, exit — state may be corrupted
  process.exit(1)
})

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('[shutdown] SIGTERM received, shutting down gracefully...')
  // Close server, finish in-flight requests, flush logs
  await server.close()
  await flushLogs()
  process.exit(0)
})
```

### Error Wrapping
```typescript
// Add context to errors as they propagate
class AppError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 500,
    public cause?: Error
  ) {
    super(message)
    this.name = 'AppError'
  }
}

async function getProject(name: string): Promise<Project> {
  try {
    return await loadFromDisk(name)
  } catch (err) {
    throw new AppError(
      `Failed to load project '${name}'`,
      'PROJECT_LOAD_FAILED',
      404,
      err as Error
    )
  }
}
```

## File I/O

### Atomic Writes
```typescript
// Write to temp file, then rename (atomic on same filesystem)
import { writeFile, rename } from 'fs/promises'
import { join, dirname } from 'path'
import { randomUUID } from 'crypto'

async function atomicWrite(filePath: string, data: string): Promise<void> {
  const tempPath = join(dirname(filePath), `.${randomUUID()}.tmp`)
  await writeFile(tempPath, data)
  await rename(tempPath, filePath)
}

// Usage
await atomicWrite(statePath, JSON.stringify(state, null, 2))
```

### JSONL Append Pattern
```typescript
// Append-only log files — safe for concurrent writes
import { appendFile } from 'fs/promises'

async function logActivity(projectPath: string, event: ActivityEvent): Promise<void> {
  const line = JSON.stringify({
    ...event,
    id: randomUUID(),
    timestamp: new Date().toISOString(),
  }) + '\n'

  await appendFile(join(projectPath, 'activity.jsonl'), line)
}
```

### Reading Large Files
```typescript
import { createReadStream } from 'fs'
import { createInterface } from 'readline'

// Stream JSONL files line by line — don't load into memory
async function* readActivityLog(path: string): AsyncGenerator<ActivityEvent> {
  const stream = createReadStream(path, { encoding: 'utf-8' })
  const rl = createInterface({ input: stream, crlfDelay: Infinity })

  for await (const line of rl) {
    if (line.trim()) {
      try {
        yield JSON.parse(line)
      } catch {
        // Skip malformed lines
      }
    }
  }
}

// Usage
for await (const event of readActivityLog(activityPath)) {
  if (event.type === 'spawn') spawnCount++
}
```

### File Watching
```typescript
import { watch } from 'fs'

// Watch for changes with debounce
function watchFile(path: string, callback: () => void, debounceMs = 500) {
  let timeout: NodeJS.Timeout | null = null

  const watcher = watch(path, () => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(callback, debounceMs)
  })

  return () => {
    watcher.close()
    if (timeout) clearTimeout(timeout)
  }
}
```

## Child Processes

### spawn vs exec
```typescript
import { spawn } from 'child_process'

// PREFER spawn — streams output, no shell injection risk
function runGitCommand(args: string[], cwd: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn('git', args, {
      cwd,
      stdio: 'pipe',
      timeout: 30000,
    })

    let stdout = ''
    let stderr = ''

    child.stdout.on('data', (data) => { stdout += data })
    child.stderr.on('data', (data) => { stderr += data })

    child.on('close', (code) => {
      if (code === 0) resolve(stdout.trim())
      else reject(new Error(`git ${args[0]} failed (${code}): ${stderr}`))
    })

    child.on('error', reject)
  })
}

// Usage
const branch = await runGitCommand(['branch', '--show-current'], projectPath)
const log = await runGitCommand(['log', '--oneline', '-10'], projectPath)
```

### Process Timeouts
```typescript
// Always set timeouts on child processes
function spawnWithTimeout(cmd: string, args: string[], timeoutMs: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { stdio: 'pipe' })
    let stdout = ''

    const timer = setTimeout(() => {
      child.kill('SIGTERM')
      reject(new Error(`Process timed out after ${timeoutMs}ms`))
    }, timeoutMs)

    child.stdout.on('data', (data) => { stdout += data })

    child.on('close', (code) => {
      clearTimeout(timer)
      if (code === 0) resolve(stdout)
      else reject(new Error(`Process exited with code ${code}`))
    })

    child.on('error', (err) => {
      clearTimeout(timer)
      reject(err)
    })
  })
}
```

## Periodic Tasks

### setInterval with Error Handling
```typescript
// Wrap periodic tasks with error handling and jitter
function startPeriodicTask(
  name: string,
  fn: () => Promise<void>,
  intervalMs: number
): () => void {
  let running = false

  const timer = setInterval(async () => {
    if (running) {
      console.log(`[${name}] Skipping — previous run still active`)
      return
    }

    running = true
    const start = Date.now()

    try {
      await fn()
      console.log(`[${name}] Completed in ${Date.now() - start}ms`)
    } catch (err) {
      console.error(`[${name}] Failed:`, err)
    } finally {
      running = false
    }
  }, intervalMs)

  // Return cleanup function
  return () => clearInterval(timer)
}

// Usage
const stopWatchdog = startPeriodicTask('watchdog', runWatchdog, 5 * 60 * 1000)

// On shutdown
process.on('SIGTERM', () => {
  stopWatchdog()
})
```

## HTTP Client Patterns

### fetch with Retries and Timeouts
```typescript
async function fetchWithRetry(
  url: string,
  options: RequestInit,
  maxRetries = 3,
  timeoutMs = 10000
): Promise<Response> {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), timeoutMs)

      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      })

      clearTimeout(timer)

      // Don't retry client errors (4xx)
      if (response.status >= 400 && response.status < 500) {
        return response
      }

      // Retry server errors (5xx)
      if (!response.ok && attempt < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, attempt), 10000)
        console.log(`[fetch] Retry ${attempt + 1}/${maxRetries} after ${delay}ms`)
        await new Promise(resolve => setTimeout(resolve, delay))
        continue
      }

      return response
    } catch (err: any) {
      if (attempt === maxRetries) throw err
      if (err.name === 'AbortError') {
        console.error(`[fetch] Timeout after ${timeoutMs}ms, retrying...`)
      }
    }
  }

  throw new Error('Unreachable')
}
```

## Memory Management

```typescript
// Avoid memory leaks in long-running services

// 1. Clean up event listeners
const handler = () => { ... }
emitter.on('event', handler)
// Later:
emitter.off('event', handler)

// 2. Use WeakMap/WeakSet for caches tied to object lifetime
const cache = new WeakMap<object, ComputedResult>()

// 3. Limit collection sizes
const recentEvents = new Map<string, Event>()
function addEvent(id: string, event: Event) {
  recentEvents.set(id, event)
  // Evict old entries
  if (recentEvents.size > 1000) {
    const oldest = recentEvents.keys().next().value
    recentEvents.delete(oldest)
  }
}

// 4. Clear intervals on shutdown
const intervals: NodeJS.Timeout[] = []
intervals.push(setInterval(healthCheck, 30000))
// On shutdown: intervals.forEach(clearInterval)
```

## Quality Checklist

- [ ] All async operations have error handling
- [ ] No unhandled promise rejections possible
- [ ] Child processes have timeouts
- [ ] File writes are atomic (write-to-temp + rename)
- [ ] Large files read via streams, not readFile
- [ ] Graceful shutdown handler (SIGTERM)
- [ ] Periodic tasks guard against overlapping execution
- [ ] HTTP requests have timeouts and retry logic
- [ ] Event listeners are cleaned up (no memory leaks)
- [ ] Process-level error handlers installed
- [ ] No synchronous I/O in request handlers (use async versions)
- [ ] Collections have size limits (no unbounded growth)

## Anti-Patterns

- Using `fs.readFileSync` in request handlers (blocks event loop)
- Fire-and-forget promises without `.catch()` (unhandled rejections)
- Loading entire large files into memory (`readFile` on 500MB file)
- Using `exec()` with user input (shell injection)
- No timeout on child processes or HTTP requests (hang forever)
- `setInterval` without checking if previous run completed
- Storing unbounded data in Maps/Arrays (memory leak)
- Using `process.exit()` without cleanup
- Catching errors and silently ignoring them
- Spawning unlimited concurrent child processes
