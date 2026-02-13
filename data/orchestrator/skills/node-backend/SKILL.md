---
name: node-backend
description: >
  Build robust, production-grade Node.js backend services with proper async patterns,
  error handling, process management, file I/O, streaming, child processes, worker threads,
  queue-based job processing, observability, and resilient service architecture. This skill
  covers the full lifecycle of Node.js backend development: from event-loop-aware coding
  patterns and CPU-bound offloading via worker threads, to BullMQ job queues with retry
  semantics, OpenTelemetry tracing and metrics piped to Grafana LGTM, circuit breakers
  for external service resilience, gRPC service definitions, and graceful shutdown
  orchestrated with Kubernetes preStop hooks. All services are stateless (state lives in
  Redis, Postgres, or S3), disposable (fast startup, SIGTERM-aware), and observable (structured
  JSON logs to stdout, never to files). Trigger this skill for any task involving Node.js
  server-side code, background workers, file processing, process spawning, event-driven
  architecture, job queues, tracing, metrics, or backend service design.
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
  - bullmq
  - worker thread
  - circuit breaker
  - grpc
  - tracing
  - metrics
  - opentelemetry
---

# Node.js Backend Excellence

Node.js shines for I/O-heavy, event-driven services. Lean into its strengths — async I/O, streams, event loops — and respect its constraints. A well-built Node backend handles thousands of concurrent connections with minimal resources. Every service you build MUST be stateless (store sessions, caches, and state in Redis or Postgres, never in process memory), disposable (start fast, shut down gracefully on SIGTERM), and observable (structured JSON to stdout, never to log files).

## Core Principles

1. **Never block the event loop** — CPU-heavy work goes to worker threads or external processes. The event loop serves I/O. If a synchronous operation takes more than 1ms, it does not belong on the main thread.
2. **Handle every error** — Unhandled rejections and uncaught exceptions crash your process. Every async operation needs error handling. Every `EventEmitter` needs an `'error'` listener.
3. **Streams over buffers** — NEVER load entire files into memory. Stream them. This applies to HTTP request/response bodies, file processing, and database result sets.

## Async Patterns

### async/await — The Default
```typescript
// ALWAYS use async/await, not raw promises or callbacks
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
    logger.error('Health checks failed', { failedCount: failed.length })
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
      logger.error('Invalid JSON in config', { path, error: err.message })
      return DEFAULT_CONFIG
    }
    // Unexpected error — re-throw (programmer error)
    throw err
  }
}
```

### Global Error Handlers
```typescript
// ALWAYS install these at process startup
process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled rejection', { reason: String(reason) })
  // Log but don't exit — let the orchestrator (K8s) handle restart
})

process.on('uncaughtException', (err) => {
  logger.error('Uncaught exception', { error: err.message, stack: err.stack })
  // For uncaught exceptions, exit — state may be corrupted
  process.exit(1)
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

// Stream JSONL files line by line — NEVER load into memory
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

// ALWAYS prefer spawn — streams output, no shell injection risk
// NEVER use exec() with user-provided input
function runGitCommand(args: string[], cwd: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn('git', args, {
      cwd,
      stdio: 'pipe',
      timeout: 30_000,
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
// ALWAYS set timeouts on child processes
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

## Worker Threads

Use worker threads for CPU-bound work that would block the event loop: hashing, compression, image processing, JSON parsing of large payloads, crypto operations. NEVER use them for I/O — that is what the event loop does best.

### Worker Pool with Piscina
```typescript
// GOOD: Use Piscina for a managed worker pool
import Piscina from 'piscina'
import { resolve } from 'path'

const pool = new Piscina({
  filename: resolve(__dirname, 'workers/hash-worker.ts'),
  minThreads: 2,
  maxThreads: Math.max(4, Math.floor(require('os').cpus().length / 2)),
  idleTimeout: 30_000, // Reclaim idle threads after 30s
})

// Usage from main thread
async function hashPasswords(passwords: string[]): Promise<string[]> {
  return Promise.all(
    passwords.map(pw => pool.run(pw))
  )
}
```

```typescript
// workers/hash-worker.ts — runs in a separate thread
import { scryptSync, randomBytes } from 'crypto'

export default function hashPassword(password: string): string {
  const salt = randomBytes(16).toString('hex')
  const hash = scryptSync(password, salt, 64).toString('hex')
  return `${salt}:${hash}`
}
```

### Direct Worker Communication with SharedArrayBuffer
```typescript
// For high-throughput scenarios where structured clone is too slow
import { Worker, isMainThread, parentPort, workerData } from 'worker_threads'

if (isMainThread) {
  // Main thread: create shared memory and worker
  const sharedBuffer = new SharedArrayBuffer(1024 * 1024) // 1MB shared
  const view = new Int32Array(sharedBuffer)

  const worker = new Worker(__filename, {
    workerData: { sharedBuffer },
  })

  worker.on('message', (msg) => {
    if (msg.type === 'done') {
      // Read result from shared memory
      const result = Atomics.load(view, 0)
      logger.info('Worker result', { result })
    }
  })

  // Signal the worker to start
  Atomics.store(view, 0, 42)
  Atomics.notify(view, 0)
} else {
  // Worker thread: read from shared memory
  const view = new Int32Array(workerData.sharedBuffer)
  Atomics.wait(view, 0, 0) // Wait for signal
  const input = Atomics.load(view, 0)

  // Do CPU-intensive work
  const result = heavyComputation(input)
  Atomics.store(view, 0, result)

  parentPort?.postMessage({ type: 'done' })
}
```

### When to Use What
```typescript
// BAD: Worker thread for an HTTP call (I/O — use the event loop)
const worker = new Worker('./fetch-worker.ts') // WRONG

// BAD: CPU-heavy work on the main thread
app.get('/api/report', async (req, res) => {
  const result = generatePdfSync(data) // BLOCKS EVENT LOOP
  res.send(result)
})

// GOOD: Offload CPU-bound to worker pool
app.get('/api/report', async (req, res) => {
  const result = await pool.run(data, { name: 'generatePdf' })
  res.send(result)
})
```

## Queue Systems (BullMQ)

Use BullMQ for any work that must survive process restarts, needs retry semantics, or should be processed asynchronously. The process that enqueues a job is NEVER the same process that executes it — this is how you stay stateless and disposable.

### Job Definition and Producer
```typescript
import { Queue } from 'bullmq'
import IORedis from 'ioredis'

// ALWAYS reuse the Redis connection
const connection = new IORedis(process.env.REDIS_URL!, {
  maxRetriesPerRequest: null, // Required by BullMQ
  enableReadyCheck: false,
})

const emailQueue = new Queue('email', { connection })

// Enqueue a job
async function sendWelcomeEmail(userId: string, email: string): Promise<void> {
  await emailQueue.add(
    'welcome', // Job name
    { userId, email, template: 'welcome' }, // Payload
    {
      attempts: 5,
      backoff: { type: 'exponential', delay: 2_000 }, // 2s, 4s, 8s, 16s, 32s
      removeOnComplete: { age: 24 * 3600 }, // Clean up after 24h
      removeOnFail: { age: 7 * 24 * 3600 }, // Keep failures 7 days for debugging
    }
  )
}
```

### Worker Processing
```typescript
import { Worker, Job } from 'bullmq'

const emailWorker = new Worker(
  'email',
  async (job: Job) => {
    const { userId, email, template } = job.data

    logger.info('Processing email job', {
      jobId: job.id,
      jobName: job.name,
      attempt: job.attemptsMade + 1,
    })

    // Update progress for monitoring
    await job.updateProgress(10)
    const html = await renderTemplate(template, { userId })

    await job.updateProgress(50)
    await sendEmail({ to: email, subject: 'Welcome!', html })

    await job.updateProgress(100)
    return { sentAt: new Date().toISOString() }
  },
  {
    connection,
    concurrency: 10, // Process 10 jobs in parallel
    limiter: {
      max: 100,
      duration: 60_000, // Max 100 jobs per minute (rate limit)
    },
  }
)

// ALWAYS handle worker errors
emailWorker.on('failed', (job, err) => {
  logger.error('Email job failed', {
    jobId: job?.id,
    error: err.message,
    attempt: job?.attemptsMade,
  })
})

emailWorker.on('completed', (job) => {
  logger.info('Email job completed', { jobId: job.id })
})
```

### Scheduled and Recurring Jobs
```typescript
import { Queue } from 'bullmq'

const maintenanceQueue = new Queue('maintenance', { connection })

// Recurring job — runs every hour (like cron but reliable)
await maintenanceQueue.upsertJobScheduler(
  'cleanup-expired-sessions',
  { every: 3_600_000 }, // Every hour
  {
    name: 'cleanup',
    data: { maxAge: 86_400_000 },
  }
)

// Delayed job — runs once in 30 minutes
await maintenanceQueue.add(
  'send-reminder',
  { userId: 'user-123' },
  { delay: 30 * 60 * 1_000 }
)
```

### Dead Letter Queue Pattern
```typescript
// Move permanently failed jobs to a dead letter queue for manual review
const deadLetterQueue = new Queue('dead-letter', { connection })

const worker = new Worker(
  'critical-jobs',
  async (job: Job) => {
    await processCriticalJob(job.data)
  },
  {
    connection,
    settings: {
      backoffStrategy: (attemptsMade: number) => {
        return Math.min(Math.pow(2, attemptsMade) * 1000, 60_000)
      },
    },
  }
)

worker.on('failed', async (job, err) => {
  if (job && job.attemptsMade >= job.opts.attempts!) {
    // All retries exhausted — move to dead letter queue
    await deadLetterQueue.add('failed-job', {
      originalQueue: 'critical-jobs',
      originalJobId: job.id,
      payload: job.data,
      error: err.message,
      failedAt: new Date().toISOString(),
    })
    logger.error('Job moved to dead letter queue', { jobId: job.id })
  }
})
```

## Observability (OpenTelemetry)

Every service MUST emit traces, metrics, and structured logs. Use OpenTelemetry as the single instrumentation layer — it exports to Grafana Tempo (traces), Prometheus/Mimir (metrics), and your logs go to stdout as JSON for Loki to scrape.

### SDK Setup and Auto-Instrumentation
```typescript
// instrumentation.ts — MUST be imported BEFORE any other module
import { NodeSDK } from '@opentelemetry/sdk-node'
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-grpc'
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-grpc'
import { PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics'
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node'
import { Resource } from '@opentelemetry/resources'
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from '@opentelemetry/semantic-conventions'

const sdk = new NodeSDK({
  resource: new Resource({
    [ATTR_SERVICE_NAME]: process.env.OTEL_SERVICE_NAME || 'my-service',
    [ATTR_SERVICE_VERSION]: process.env.npm_package_version || '0.0.0',
    'deployment.environment': process.env.NODE_ENV || 'development',
  }),
  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://otel-collector:4317',
  }),
  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter({
      url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://otel-collector:4317',
    }),
    exportIntervalMillis: 15_000,
  }),
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-http': { enabled: true },
      '@opentelemetry/instrumentation-express': { enabled: true },
      '@opentelemetry/instrumentation-pg': { enabled: true },
      '@opentelemetry/instrumentation-ioredis': { enabled: true },
    }),
  ],
})

sdk.start()

// Graceful shutdown of telemetry pipeline
process.on('SIGTERM', async () => {
  await sdk.shutdown()
})
```

### Custom Spans for Business Logic
```typescript
import { trace, SpanStatusCode, context, propagation } from '@opentelemetry/api'

const tracer = trace.getTracer('order-service')

async function processOrder(order: Order): Promise<OrderResult> {
  return tracer.startActiveSpan('processOrder', async (span) => {
    try {
      span.setAttribute('order.id', order.id)
      span.setAttribute('order.amount', order.amount)
      span.setAttribute('order.currency', order.currency)

      // Child span for validation
      const validated = await tracer.startActiveSpan('validateOrder', async (valSpan) => {
        const result = await validateOrder(order)
        valSpan.setAttribute('validation.passed', result.valid)
        valSpan.end()
        return result
      })

      if (!validated.valid) {
        span.setStatus({ code: SpanStatusCode.ERROR, message: 'Validation failed' })
        throw new AppError('Order validation failed', 'VALIDATION_ERROR', 400)
      }

      const result = await executeOrder(order)
      span.setStatus({ code: SpanStatusCode.OK })
      return result
    } catch (err) {
      span.recordException(err as Error)
      span.setStatus({ code: SpanStatusCode.ERROR, message: (err as Error).message })
      throw err
    } finally {
      span.end()
    }
  })
}
```

### Custom Metrics
```typescript
import { metrics } from '@opentelemetry/api'

const meter = metrics.getMeter('order-service')

// Counter — tracks totals
const ordersProcessed = meter.createCounter('orders.processed', {
  description: 'Total orders processed',
  unit: '1',
})

// Histogram — tracks distributions (latency, sizes)
const orderLatency = meter.createHistogram('orders.processing_duration', {
  description: 'Order processing duration in milliseconds',
  unit: 'ms',
})

// UpDownCounter — tracks current value (active connections, queue depth)
const activeConnections = meter.createUpDownCounter('connections.active', {
  description: 'Current number of active connections',
})

// Usage in request handler
async function handleOrder(order: Order): Promise<void> {
  const start = performance.now()
  try {
    await processOrder(order)
    ordersProcessed.add(1, { status: 'success', type: order.type })
  } catch (err) {
    ordersProcessed.add(1, { status: 'error', type: order.type })
    throw err
  } finally {
    orderLatency.record(performance.now() - start, { type: order.type })
  }
}
```

### Structured JSON Logging to stdout (for Loki)
```typescript
// ALWAYS log to stdout as JSON. NEVER write to log files.
// Loki/Fluentd/Vector scrapes stdout from the container.

import { context, trace } from '@opentelemetry/api'

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

function log(level: LogLevel, message: string, meta?: Record<string, unknown>): void {
  // Extract trace context so logs correlate with traces in Grafana
  const activeSpan = trace.getActiveSpan()
  const spanContext = activeSpan?.spanContext()

  const entry = {
    timestamp: new Date().toISOString(),
    level,
    message,
    service: process.env.OTEL_SERVICE_NAME || 'unknown',
    ...(spanContext && {
      traceId: spanContext.traceId,
      spanId: spanContext.spanId,
    }),
    ...meta,
  }

  // stdout for info/debug/warn, stderr for error
  const output = level === 'error' ? process.stderr : process.stdout
  output.write(JSON.stringify(entry) + '\n')
}

// Convenience wrappers
const logger = {
  debug: (msg: string, meta?: Record<string, unknown>) => log('debug', msg, meta),
  info: (msg: string, meta?: Record<string, unknown>) => log('info', msg, meta),
  warn: (msg: string, meta?: Record<string, unknown>) => log('warn', msg, meta),
  error: (msg: string, meta?: Record<string, unknown>) => log('error', msg, meta),
}

// Usage — trace IDs are injected automatically
logger.info('Order created', { orderId: 'ord-123', userId: 'usr-456' })
// => {"timestamp":"...","level":"info","message":"Order created","traceId":"abc...","orderId":"ord-123",...}
```

## Circuit Breakers

Wrap every external service call with a circuit breaker. When a dependency fails repeatedly, the circuit opens and fast-fails requests instead of piling up timeouts that cascade across your system.

### Implementation Pattern
```typescript
enum CircuitState {
  CLOSED = 'CLOSED',     // Normal — requests flow through
  OPEN = 'OPEN',         // Failing — requests rejected immediately
  HALF_OPEN = 'HALF_OPEN', // Testing — single request allowed through
}

interface CircuitBreakerOptions {
  failureThreshold: number   // Failures before opening (default: 5)
  resetTimeoutMs: number     // Time in OPEN before trying HALF_OPEN (default: 30s)
  halfOpenMaxAttempts: number // Successes in HALF_OPEN to close (default: 3)
}

class CircuitBreaker {
  private state = CircuitState.CLOSED
  private failures = 0
  private successes = 0
  private lastFailureTime = 0

  constructor(
    private readonly name: string,
    private readonly options: CircuitBreakerOptions = {
      failureThreshold: 5,
      resetTimeoutMs: 30_000,
      halfOpenMaxAttempts: 3,
    }
  ) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      if (Date.now() - this.lastFailureTime >= this.options.resetTimeoutMs) {
        this.state = CircuitState.HALF_OPEN
        this.successes = 0
        logger.info('Circuit half-open', { circuit: this.name })
      } else {
        throw new AppError(
          `Circuit breaker '${this.name}' is OPEN`,
          'CIRCUIT_OPEN',
          503
        )
      }
    }

    try {
      const result = await fn()
      this.onSuccess()
      return result
    } catch (err) {
      this.onFailure()
      throw err
    }
  }

  private onSuccess(): void {
    if (this.state === CircuitState.HALF_OPEN) {
      this.successes++
      if (this.successes >= this.options.halfOpenMaxAttempts) {
        this.state = CircuitState.CLOSED
        this.failures = 0
        logger.info('Circuit closed', { circuit: this.name })
      }
    } else {
      this.failures = 0
    }
  }

  private onFailure(): void {
    this.failures++
    this.lastFailureTime = Date.now()

    if (this.failures >= this.options.failureThreshold) {
      this.state = CircuitState.OPEN
      logger.warn('Circuit opened', {
        circuit: this.name,
        failures: this.failures,
      })
    }
  }

  getState(): CircuitState {
    return this.state
  }
}
```

### Integration with HTTP Client
```typescript
// Combine circuit breaker with fetch retries
const paymentCircuit = new CircuitBreaker('payment-api', {
  failureThreshold: 3,
  resetTimeoutMs: 60_000,
  halfOpenMaxAttempts: 2,
})

async function chargeCustomer(customerId: string, amount: number): Promise<ChargeResult> {
  return paymentCircuit.execute(async () => {
    const response = await fetchWithRetry(
      `${PAYMENT_API_URL}/charges`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customerId, amount }),
      },
      2, // Only 2 retries inside the circuit
      5_000 // 5s timeout
    )

    if (!response.ok) {
      throw new AppError(`Payment failed: ${response.status}`, 'PAYMENT_ERROR', 502)
    }

    return response.json()
  })
}
```

## gRPC Services

Use gRPC for internal service-to-service communication where you need strong typing, streaming, and performance. Use REST/HTTP for external-facing APIs.

### Proto Definition
```protobuf
// proto/order_service.proto
syntax = "proto3";

package orderservice;

service OrderService {
  rpc CreateOrder (CreateOrderRequest) returns (OrderResponse);
  rpc GetOrder (GetOrderRequest) returns (OrderResponse);
  rpc StreamOrderUpdates (StreamOrdersRequest) returns (stream OrderUpdate);
}

message CreateOrderRequest {
  string symbol = 1;
  string side = 2;      // "buy" | "sell"
  double quantity = 3;
  double price = 4;     // 0 for market orders
}

message GetOrderRequest {
  string order_id = 1;
}

message OrderResponse {
  string id = 1;
  string symbol = 2;
  string side = 3;
  string status = 4;
  double quantity = 5;
  double price = 6;
  string created_at = 7;
}

message StreamOrdersRequest {
  string user_id = 1;
}

message OrderUpdate {
  string order_id = 1;
  string status = 2;
  double filled_quantity = 3;
  string updated_at = 4;
}
```

### Server Implementation
```typescript
import * as grpc from '@grpc/grpc-js'
import * as protoLoader from '@grpc/proto-loader'
import { resolve } from 'path'

const PROTO_PATH = resolve(__dirname, '../proto/order_service.proto')
const packageDef = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
})
const proto = grpc.loadPackageDefinition(packageDef).orderservice as any

function createGrpcServer(): grpc.Server {
  const server = new grpc.Server({
    'grpc.max_receive_message_length': 4 * 1024 * 1024, // 4MB
    'grpc.keepalive_time_ms': 15_000,
  })

  server.addService(proto.OrderService.service, {
    createOrder: async (
      call: grpc.ServerUnaryCall<any, any>,
      callback: grpc.sendUnaryData<any>
    ) => {
      try {
        const order = await orderService.create(call.request)
        callback(null, order)
      } catch (err) {
        callback({
          code: grpc.status.INTERNAL,
          message: (err as Error).message,
        })
      }
    },

    getOrder: async (
      call: grpc.ServerUnaryCall<any, any>,
      callback: grpc.sendUnaryData<any>
    ) => {
      try {
        const order = await orderService.get(call.request.order_id)
        if (!order) {
          callback({ code: grpc.status.NOT_FOUND, message: 'Order not found' })
          return
        }
        callback(null, order)
      } catch (err) {
        callback({ code: grpc.status.INTERNAL, message: (err as Error).message })
      }
    },

    // Server-side streaming
    streamOrderUpdates: (call: grpc.ServerWritableStream<any, any>) => {
      const userId = call.request.user_id
      const unsubscribe = orderEvents.subscribe(userId, (update) => {
        call.write(update)
      })

      call.on('cancelled', () => {
        unsubscribe()
      })
    },
  })

  return server
}

// Start gRPC server
const grpcServer = createGrpcServer()
grpcServer.bindAsync(
  `0.0.0.0:${process.env.GRPC_PORT || 50051}`,
  grpc.ServerCredentials.createInsecure(),
  (err, port) => {
    if (err) throw err
    logger.info('gRPC server started', { port })
  }
)
```

### Client Usage
```typescript
import * as grpc from '@grpc/grpc-js'
import * as protoLoader from '@grpc/proto-loader'

function createOrderClient(address: string) {
  const packageDef = protoLoader.loadSync(PROTO_PATH)
  const proto = grpc.loadPackageDefinition(packageDef).orderservice as any

  const client = new proto.OrderService(
    address,
    grpc.credentials.createInsecure(),
    {
      'grpc.keepalive_time_ms': 15_000,
      'grpc.initial_reconnect_backoff_ms': 1_000,
      'grpc.max_reconnect_backoff_ms': 10_000,
    }
  )

  // Promisify for async/await usage
  return {
    createOrder(req: CreateOrderRequest): Promise<OrderResponse> {
      return new Promise((resolve, reject) => {
        client.createOrder(req, (err: grpc.ServiceError | null, res: any) => {
          if (err) reject(err)
          else resolve(res)
        })
      })
    },

    streamOrderUpdates(userId: string): AsyncIterable<OrderUpdate> {
      const call = client.streamOrderUpdates({ user_id: userId })

      return {
        [Symbol.asyncIterator]() {
          return {
            next(): Promise<IteratorResult<OrderUpdate>> {
              return new Promise((resolve, reject) => {
                call.once('data', (data: OrderUpdate) => {
                  resolve({ value: data, done: false })
                })
                call.once('end', () => {
                  resolve({ value: undefined, done: true })
                })
                call.once('error', reject)
              })
            },
          }
        },
      }
    },
  }
}
```

## Periodic Tasks

### setInterval with Error Handling
```typescript
// Wrap periodic tasks with error handling and overlap guard
function startPeriodicTask(
  name: string,
  fn: () => Promise<void>,
  intervalMs: number
): () => void {
  let running = false

  const timer = setInterval(async () => {
    if (running) {
      logger.warn('Skipping periodic task — previous run active', { task: name })
      return
    }

    running = true
    const start = Date.now()

    try {
      await fn()
      logger.info('Periodic task completed', { task: name, durationMs: Date.now() - start })
    } catch (err) {
      logger.error('Periodic task failed', { task: name, error: (err as Error).message })
    } finally {
      running = false
    }
  }, intervalMs)

  // Return cleanup function
  return () => clearInterval(timer)
}

// Usage
const stopWatchdog = startPeriodicTask('watchdog', runWatchdog, 5 * 60 * 1000)
```

## HTTP Client Patterns

### fetch with Retries and Timeouts
```typescript
async function fetchWithRetry(
  url: string,
  options: RequestInit,
  maxRetries = 3,
  timeoutMs = 10_000
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
        const delay = Math.min(1000 * Math.pow(2, attempt), 10_000)
        logger.warn('HTTP retry', { url, attempt: attempt + 1, maxRetries, delayMs: delay })
        await new Promise(resolve => setTimeout(resolve, delay))
        continue
      }

      return response
    } catch (err: any) {
      if (attempt === maxRetries) throw err
      if (err.name === 'AbortError') {
        logger.warn('HTTP timeout, retrying', { url, timeoutMs })
      }
    }
  }

  throw new Error('Unreachable')
}
```

## Graceful Shutdown

Every Node.js service running in Kubernetes MUST handle SIGTERM and drain cleanly. K8s sends SIGTERM, waits `terminationGracePeriodSeconds` (default 30s), then sends SIGKILL. Your service must finish in-flight work within that window.

### Full Shutdown Orchestration
```typescript
import { Server } from 'http'

class GracefulShutdown {
  private shuttingDown = false
  private readonly cleanupFns: Array<{ name: string; fn: () => Promise<void> }> = []

  constructor(private readonly timeoutMs: number = 25_000) {} // Under K8s 30s grace

  register(name: string, fn: () => Promise<void>): void {
    this.cleanupFns.push({ name, fn })
  }

  isShuttingDown(): boolean {
    return this.shuttingDown
  }

  async shutdown(signal: string): Promise<void> {
    if (this.shuttingDown) return
    this.shuttingDown = true

    logger.info('Shutdown initiated', { signal, registeredCleanups: this.cleanupFns.length })

    // Force exit if cleanup takes too long
    const forceTimer = setTimeout(() => {
      logger.error('Shutdown timeout exceeded, forcing exit')
      process.exit(1)
    }, this.timeoutMs)
    forceTimer.unref()

    // Run all cleanups in order (reverse registration = LIFO)
    for (const { name, fn } of [...this.cleanupFns].reverse()) {
      try {
        logger.info('Running cleanup', { name })
        await fn()
        logger.info('Cleanup completed', { name })
      } catch (err) {
        logger.error('Cleanup failed', { name, error: (err as Error).message })
      }
    }

    clearTimeout(forceTimer)
    logger.info('Shutdown complete')
    process.exit(0)
  }
}

// Usage — wire everything together at startup
const shutdown = new GracefulShutdown()
const httpServer: Server = app.listen(PORT)

// 1. Stop accepting new connections
shutdown.register('http-server', async () => {
  await new Promise<void>((resolve, reject) => {
    httpServer.close((err) => (err ? reject(err) : resolve()))
  })
})

// 2. Close gRPC server
shutdown.register('grpc-server', async () => {
  await new Promise<void>((resolve) => {
    grpcServer.tryShutdown(() => resolve())
  })
})

// 3. Drain BullMQ workers (finish in-flight jobs)
shutdown.register('bullmq-workers', async () => {
  await emailWorker.close()
})

// 4. Close database pools
shutdown.register('database', async () => {
  await dbPool.end()
})

// 5. Close Redis connections
shutdown.register('redis', async () => {
  await connection.quit()
})

// 6. Flush telemetry
shutdown.register('telemetry', async () => {
  await sdk.shutdown()
})

// Listen for signals
process.on('SIGTERM', () => shutdown.shutdown('SIGTERM'))
process.on('SIGINT', () => shutdown.shutdown('SIGINT'))
```

### Kubernetes preStop Hook Coordination
```yaml
# In your Kubernetes deployment manifest
spec:
  terminationGracePeriodSeconds: 35
  containers:
    - name: my-service
      lifecycle:
        preStop:
          # Sleep gives the load balancer time to remove the pod from endpoints
          # BEFORE SIGTERM is sent. Without this, traffic arrives after shutdown starts.
          exec:
            command: ["sh", "-c", "sleep 5"]
      readinessProbe:
        httpGet:
          path: /health/ready
          port: 3000
        periodSeconds: 5
        failureThreshold: 1
```

```typescript
// Readiness probe returns 503 during shutdown so K8s stops routing traffic
app.get('/health/ready', (req, res) => {
  if (shutdown.isShuttingDown()) {
    res.status(503).json({ status: 'shutting_down' })
    return
  }
  res.json({ status: 'ready' })
})

// Liveness probe always returns 200 unless the process is truly stuck
app.get('/health/live', (req, res) => {
  res.json({ status: 'alive', uptime: process.uptime() })
})
```

## TDD Example: Building a Rate Limiter

Write the test FIRST, then implement. This is how every feature should be developed.

### Step 1: Write the Failing Test
```typescript
// __tests__/rate-limiter.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { SlidingWindowRateLimiter } from '../src/rate-limiter'

describe('SlidingWindowRateLimiter', () => {
  let limiter: SlidingWindowRateLimiter

  beforeEach(() => {
    vi.useFakeTimers()
    limiter = new SlidingWindowRateLimiter({
      maxRequests: 3,
      windowMs: 10_000, // 10 seconds
    })
  })

  it('allows requests under the limit', () => {
    expect(limiter.tryConsume('user-1')).toBe(true)
    expect(limiter.tryConsume('user-1')).toBe(true)
    expect(limiter.tryConsume('user-1')).toBe(true)
  })

  it('rejects requests over the limit', () => {
    limiter.tryConsume('user-1')
    limiter.tryConsume('user-1')
    limiter.tryConsume('user-1')
    expect(limiter.tryConsume('user-1')).toBe(false) // 4th request rejected
  })

  it('tracks limits per key independently', () => {
    limiter.tryConsume('user-1')
    limiter.tryConsume('user-1')
    limiter.tryConsume('user-1')
    expect(limiter.tryConsume('user-2')).toBe(true) // Different user, fresh window
  })

  it('resets after the window expires', () => {
    limiter.tryConsume('user-1')
    limiter.tryConsume('user-1')
    limiter.tryConsume('user-1')

    vi.advanceTimersByTime(10_001) // Window expired

    expect(limiter.tryConsume('user-1')).toBe(true) // Allowed again
  })

  it('returns remaining count', () => {
    limiter.tryConsume('user-1')
    expect(limiter.remaining('user-1')).toBe(2)
    limiter.tryConsume('user-1')
    expect(limiter.remaining('user-1')).toBe(1)
  })
})
```

### Step 2: Implement to Make Tests Pass
```typescript
// src/rate-limiter.ts
interface RateLimiterOptions {
  maxRequests: number
  windowMs: number
}

interface WindowEntry {
  timestamps: number[]
}

export class SlidingWindowRateLimiter {
  private windows = new Map<string, WindowEntry>()

  constructor(private readonly options: RateLimiterOptions) {}

  tryConsume(key: string): boolean {
    const now = Date.now()
    const windowStart = now - this.options.windowMs

    // Get or create entry
    let entry = this.windows.get(key)
    if (!entry) {
      entry = { timestamps: [] }
      this.windows.set(key, entry)
    }

    // Evict expired timestamps
    entry.timestamps = entry.timestamps.filter(ts => ts > windowStart)

    // Check limit
    if (entry.timestamps.length >= this.options.maxRequests) {
      return false
    }

    entry.timestamps.push(now)
    return true
  }

  remaining(key: string): number {
    const now = Date.now()
    const windowStart = now - this.options.windowMs
    const entry = this.windows.get(key)

    if (!entry) return this.options.maxRequests

    const active = entry.timestamps.filter(ts => ts > windowStart).length
    return Math.max(0, this.options.maxRequests - active)
  }
}
```

### Step 3: Run Tests, Confirm Green, Refactor
```bash
# Run tests — all 5 should pass
npx vitest run __tests__/rate-limiter.test.ts
```

## Memory Management

```typescript
// Avoid memory leaks in long-running services

// 1. Clean up event listeners
const handler = () => { /* ... */ }
emitter.on('event', handler)
// Later:
emitter.off('event', handler)

// 2. Use WeakMap/WeakSet for caches tied to object lifetime
const cache = new WeakMap<object, ComputedResult>()

// 3. Limit collection sizes — NEVER let Maps/Arrays grow unbounded
const recentEvents = new Map<string, Event>()
function addEvent(id: string, event: Event) {
  recentEvents.set(id, event)
  if (recentEvents.size > 1000) {
    const oldest = recentEvents.keys().next().value
    if (oldest) recentEvents.delete(oldest)
  }
}

// 4. Clear intervals on shutdown (registered via GracefulShutdown)
const intervals: NodeJS.Timeout[] = []
intervals.push(setInterval(healthCheck, 30_000))

// 5. Monitor memory in production
setInterval(() => {
  const usage = process.memoryUsage()
  if (usage.heapUsed > 400 * 1024 * 1024) { // 400MB threshold
    logger.warn('High memory usage', {
      heapUsedMb: Math.round(usage.heapUsed / 1024 / 1024),
      rss: Math.round(usage.rss / 1024 / 1024),
    })
  }
}, 60_000)
```

## Configuration from Environment

ALWAYS read configuration from environment variables, validate at startup, and fail fast if anything is missing. NEVER scatter `process.env` reads throughout your codebase.

```typescript
// config.ts — single source of truth, loaded once at startup
import { z } from 'zod'

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'staging', 'production']).default('development'),
  PORT: z.coerce.number().int().min(1024).max(65535).default(3000),
  REDIS_URL: z.string().url(),
  DATABASE_URL: z.string().url(),
  OTEL_SERVICE_NAME: z.string().min(1),
  OTEL_EXPORTER_OTLP_ENDPOINT: z.string().url().optional(),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
})

export type Config = z.infer<typeof envSchema>

let _config: Config | null = null

export function getConfig(): Config {
  if (!_config) {
    const result = envSchema.safeParse(process.env)
    if (!result.success) {
      console.error('Invalid environment configuration:')
      console.error(result.error.format())
      process.exit(1) // Fail fast — do not start with bad config
    }
    _config = result.data
  }
  return _config
}
```

## Quality Checklist

- [ ] All async operations have error handling (`try/catch` or `.catch()`)
- [ ] No unhandled promise rejections possible (`process.on('unhandledRejection')`)
- [ ] Child processes have timeouts (ALWAYS)
- [ ] File writes are atomic (write-to-temp + rename)
- [ ] Large files read via streams, not `readFile`
- [ ] Graceful shutdown handler drains HTTP, gRPC, queues, DB pools, and telemetry
- [ ] Periodic tasks guard against overlapping execution
- [ ] HTTP requests have timeouts, retry logic, and circuit breakers
- [ ] Event listeners are cleaned up (no memory leaks)
- [ ] Process is stateless (no in-process sessions, caches backed by Redis)
- [ ] Logs are structured JSON to stdout (never to files)
- [ ] Config validated at startup with Zod, fail-fast on missing vars

## Anti-Patterns

- **readFileSync in handlers** — Blocks the event loop for every request. Use async `readFile` or streams.
- **Fire-and-forget promises** — Promises without `.catch()` become unhandled rejections that crash your process.
- **Buffering large files** — `readFile` on a 500MB file kills your container. ALWAYS stream.
- **exec with user input** — Shell injection. Use `spawn` with argument arrays.
- **No timeouts** — HTTP requests, child processes, and gRPC calls without timeouts hang forever and leak resources.
- **Unbounded collections** — Maps and arrays that grow forever are memory leaks. Set hard caps.
- **process.exit without cleanup** — Kills in-flight requests, corrupts writes. Use the GracefulShutdown class.
- **In-process state** — Sessions, caches, or locks stored in memory die when the pod restarts. Use Redis.
- **Console.log to files** — Log rotation, disk pressure, and you lose logs on container restart. Write JSON to stdout and let the platform (Loki) handle it.
- **CPU work on event loop** — JSON.parse on a 50MB payload, crypto operations, image processing. Offload to worker threads via Piscina.
