---
name: typescript-patterns
description: >
  Write idiomatic, type-safe TypeScript that leverages the type system for correctness
  and maintainability. Covers strict typing, generics, discriminated unions, error handling,
  utility types, and patterns that prevent bugs at compile time. Trigger this skill for
  any task involving TypeScript, type definitions, interfaces, generics, or type-safe
  code architecture.
triggers:
  - typescript
  - type
  - interface
  - generic
  - enum
  - typing
  - strict
  - any
  - unknown
  - ts
---

# TypeScript Patterns

TypeScript's type system is your most powerful tool for preventing bugs. Use it to make illegal states unrepresentable, catch errors at compile time, and document your code's contracts. The goal is zero `any` — every `any` is a bug waiting to happen.

## Core Principles

1. **Make illegal states unrepresentable** — If a combination of values shouldn't exist, the type system should prevent it.
2. **Type the boundaries, infer the rest** — Define types for function signatures, API contracts, and data structures. Let TypeScript infer local variables.
3. **Never use `any`** — Use `unknown` for truly unknown values, then narrow with type guards.

## Strict Configuration

```json
// tsconfig.json — always enable strict mode
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

## Type Design

### Interfaces vs Types
```typescript
// Use interfaces for object shapes that might be extended
interface Project {
  id: string
  name: string
  status: ProjectStatus
}

// Use types for unions, intersections, and computed types
type ProjectStatus = 'active' | 'archived' | 'deleted'
type ProjectWithTasks = Project & { tasks: Task[] }
type ReadonlyProject = Readonly<Project>
```

### Discriminated Unions — The Power Tool
```typescript
// Model different states as distinct types
type TaskState =
  | { status: 'pending' }
  | { status: 'running'; startedAt: Date; workerId: string }
  | { status: 'completed'; completedAt: Date; output: string }
  | { status: 'failed'; error: string; retryCount: number }

// TypeScript narrows automatically in switch/if
function handleTask(task: TaskState) {
  switch (task.status) {
    case 'pending':
      // task is { status: 'pending' } — no startedAt, no error
      return startTask(task)
    case 'running':
      // task is { status: 'running'; startedAt: Date; workerId: string }
      return checkProgress(task.workerId)
    case 'completed':
      // task.output is available here
      return processOutput(task.output)
    case 'failed':
      // task.error and task.retryCount are available
      if (task.retryCount < 3) return retry(task)
      return escalate(task.error)
  }
}
```

### Branded Types for Safety
```typescript
// Prevent mixing up similar primitive types
type ProjectId = string & { readonly __brand: 'ProjectId' }
type TaskId = string & { readonly __brand: 'TaskId' }

function createProjectId(id: string): ProjectId {
  return id as ProjectId
}

// Now these are type errors:
function getTask(taskId: TaskId): Task { ... }
getTask(projectId)  // Error! ProjectId is not TaskId
```

### Template Literal Types
```typescript
// Enforce string patterns at the type level
type EventType = 'spawn' | 'complete' | 'error' | 'review'
type EventKey = `project:${string}:${EventType}`

function logEvent(key: EventKey, data: unknown): void { ... }
logEvent('project:my-app:spawn', {})     // OK
logEvent('project:my-app:invalid', {})   // Error!
```

## Generics

### Constrained Generics
```typescript
// Generic with constraint — T must have an id
function findById<T extends { id: string }>(items: T[], id: string): T | undefined {
  return items.find(item => item.id === id)
}

// Generic with keyof — type-safe property access
function pick<T, K extends keyof T>(obj: T, keys: K[]): Pick<T, K> {
  const result = {} as Pick<T, K>
  for (const key of keys) {
    result[key] = obj[key]
  }
  return result
}

const project = { id: '1', name: 'App', status: 'active', secret: 'xxx' }
const safe = pick(project, ['id', 'name', 'status'])  // { id, name, status }
```

### Generic Functions That Infer
```typescript
// Let the caller's usage determine the type
function createStore<T>(initial: T) {
  let value = initial
  return {
    get: () => value,
    set: (newValue: T) => { value = newValue },
  }
}

const counter = createStore(0)         // createStore<number>
counter.set('hello')                   // Error! Expected number
```

## Error Handling

### Result Type (No Exceptions for Expected Failures)
```typescript
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E }

async function parseConfig(path: string): Promise<Result<Config, string>> {
  try {
    const data = await readFile(path, 'utf-8')
    const config = JSON.parse(data)
    return { ok: true, value: config }
  } catch {
    return { ok: false, error: `Failed to parse config at ${path}` }
  }
}

// Caller handles both cases explicitly
const result = await parseConfig('./config.json')
if (!result.ok) {
  console.error(result.error)
  return
}
// result.value is Config here — TypeScript knows
```

### Exhaustive Checks
```typescript
// Ensure all union cases are handled
function assertNever(x: never): never {
  throw new Error(`Unexpected value: ${x}`)
}

type Phase = 'interview' | 'spec' | 'build' | 'review' | 'complete'

function getPhaseColor(phase: Phase): string {
  switch (phase) {
    case 'interview': return 'blue'
    case 'spec': return 'purple'
    case 'build': return 'yellow'
    case 'review': return 'orange'
    case 'complete': return 'green'
    default: return assertNever(phase)  // Compile error if case missed
  }
}
```

## Utility Types — Know Them

```typescript
// Partial<T> — all properties optional
function updateProject(id: string, updates: Partial<Project>) { ... }

// Required<T> — all properties required
type CompleteProject = Required<Project>

// Pick<T, K> — select specific properties
type ProjectSummary = Pick<Project, 'id' | 'name' | 'status'>

// Omit<T, K> — exclude properties
type NewProject = Omit<Project, 'id' | 'createdAt'>

// Record<K, V> — typed dictionary
type PhaseConfig = Record<Phase, { model: string; thinking: string }>

// Extract / Exclude — filter union types
type ActiveStatuses = Extract<ProjectStatus, 'active' | 'running'>  // 'active' | 'running'
type InactiveStatuses = Exclude<ProjectStatus, 'active'>  // 'archived' | 'deleted'

// ReturnType<T> — extract return type
type FetchResult = ReturnType<typeof fetchProjects>  // Promise<Project[]>

// Awaited<T> — unwrap Promise
type Projects = Awaited<ReturnType<typeof fetchProjects>>  // Project[]
```

## Type Guards

```typescript
// Custom type guard with 'is' predicate
function isProject(value: unknown): value is Project {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'name' in value &&
    typeof (value as any).id === 'string'
  )
}

// Use in conditionals
const data: unknown = JSON.parse(input)
if (isProject(data)) {
  // data is Project here
  console.log(data.name)
}

// Assertion function (throws if not valid)
function assertProject(value: unknown): asserts value is Project {
  if (!isProject(value)) {
    throw new Error('Invalid project data')
  }
}
```

## Common Patterns

### Builder Pattern with Types
```typescript
class QueryBuilder<T> {
  private filters: Array<(item: T) => boolean> = []
  private sortKey?: keyof T
  private limitCount?: number

  where(predicate: (item: T) => boolean): this {
    this.filters.push(predicate)
    return this
  }

  orderBy(key: keyof T): this {
    this.sortKey = key
    return this
  }

  limit(count: number): this {
    this.limitCount = count
    return this
  }

  execute(items: T[]): T[] {
    let result = items.filter(item => this.filters.every(f => f(item)))
    if (this.sortKey) result.sort((a, b) => a[this.sortKey!] > b[this.sortKey!] ? 1 : -1)
    if (this.limitCount) result = result.slice(0, this.limitCount)
    return result
  }
}
```

### Readonly by Default
```typescript
// Prefer readonly to prevent accidental mutation
interface Config {
  readonly port: number
  readonly host: string
  readonly features: readonly string[]
}

// Use as const for literal types
const PHASES = ['interview', 'spec', 'build', 'review', 'complete'] as const
type Phase = typeof PHASES[number]  // 'interview' | 'spec' | 'build' | 'review' | 'complete'
```

## Quality Checklist

- [ ] Zero `any` types (use `unknown` + type guards instead)
- [ ] Function parameters and return types are explicitly typed
- [ ] Union types used for values with fixed options (not string/number)
- [ ] Discriminated unions for state modeling
- [ ] All switch/if-else chains handle every case (exhaustive checks)
- [ ] Generic constraints are specific (not just `<T>`)
- [ ] Errors are handled with Result types or explicit try/catch
- [ ] No type assertions (`as`) without preceding validation
- [ ] Interfaces for extensible shapes, types for unions/computed
- [ ] tsconfig strict mode enabled

## Anti-Patterns

- Using `any` to "make it compile" — fix the actual type issue
- Type assertions (`as Type`) without validation — lying to the compiler
- Using `enum` — prefer `as const` objects or union types
- Non-exhaustive switch statements on union types
- `object` type — too broad, use specific interfaces
- Optional chaining as a substitute for proper null checks
- `!` non-null assertion — if you need it, your types are wrong
- Exporting everything — export only what consumers need
- Complex conditional types when simpler solutions exist
- Index signatures (`[key: string]: any`) — use Map or specific interfaces
