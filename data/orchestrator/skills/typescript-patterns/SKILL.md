---
name: typescript-patterns
description: >
  Write idiomatic, type-safe TypeScript that leverages the type system for correctness
  and maintainability. Covers strict typing, generics, discriminated unions, error handling,
  utility types, conditional types, mapped types, Zod inference, Vue/Nitro typing, module
  patterns, and type-level testing. Trigger this skill for any task involving TypeScript,
  type definitions, interfaces, generics, or type-safe code architecture.
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
  - conditional type
  - mapped type
  - infer
  - zod
---

# TypeScript Patterns

TypeScript's type system is your most powerful tool for preventing bugs. Use it to make illegal states unrepresentable, catch errors at compile time, and document your code's contracts. The goal is zero `any` — every `any` is a bug waiting to happen.

## Core Principles

1. **Make illegal states unrepresentable** — If a combination of values shouldn't exist, the type system should prevent it.
2. **Type the boundaries, infer the rest** — Define types for function signatures, API contracts, and data structures. Let TypeScript infer local variables.
3. **Never use `any`** — Use `unknown` for truly unknown values, then narrow with type guards.

## Strict Configuration

```json
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
// Interfaces for object shapes that might be extended
interface Project { id: string; name: string; status: ProjectStatus }

// Types for unions, intersections, and computed types
type ProjectStatus = 'active' | 'archived' | 'deleted'
type ProjectWithTasks = Project & { tasks: Task[] }
```

### Discriminated Unions
```typescript
type TaskState =
  | { status: 'pending' }
  | { status: 'running'; startedAt: Date; workerId: string }
  | { status: 'completed'; completedAt: Date; output: string }
  | { status: 'failed'; error: string; retryCount: number }

function handleTask(task: TaskState) {
  switch (task.status) {
    case 'pending':    return startTask(task)
    case 'running':    return checkProgress(task.workerId)
    case 'completed':  return processOutput(task.output)
    case 'failed':
      if (task.retryCount < 3) return retry(task)
      return escalate(task.error)
  }
}
```

### Branded Types
```typescript
type ProjectId = string & { readonly __brand: 'ProjectId' }
type TaskId = string & { readonly __brand: 'TaskId' }

function createProjectId(id: string): ProjectId { return id as ProjectId }
function getTask(taskId: TaskId): Task { /* ... */ }
getTask(projectId) // Error! ProjectId is not TaskId
```

### Template Literal Types
```typescript
type EventType = 'spawn' | 'complete' | 'error' | 'review'
type EventKey = `project:${string}:${EventType}`

function logEvent(key: EventKey, data: unknown): void { /* ... */ }
logEvent('project:my-app:spawn', {})    // OK
logEvent('project:my-app:invalid', {})  // Error!
```

## Generics

```typescript
// Constrained — T must have an id
function findById<T extends { id: string }>(items: T[], id: string): T | undefined {
  return items.find(item => item.id === id)
}

// keyof constraint — type-safe property access
function pick<T, K extends keyof T>(obj: T, keys: K[]): Pick<T, K> {
  const result = {} as Pick<T, K>
  for (const key of keys) result[key] = obj[key]
  return result
}

// Inference — caller's usage determines the type
function createStore<T>(initial: T) {
  let value = initial
  return { get: () => value, set: (next: T) => { value = next } }
}
const counter = createStore(0) // createStore<number>
counter.set('hello')           // Error! Expected number
```

## Error Handling

### Result Type
```typescript
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E }

async function parseConfig(path: string): Promise<Result<Config, string>> {
  try {
    return { ok: true, value: JSON.parse(await readFile(path, 'utf-8')) }
  } catch {
    return { ok: false, error: `Failed to parse config at ${path}` }
  }
}

const result = await parseConfig('./config.json')
if (!result.ok) { console.error(result.error); return }
// result.value is Config here
```

### Exhaustive Checks
```typescript
function assertNever(x: never): never { throw new Error(`Unexpected value: ${x}`) }

type Phase = 'interview' | 'spec' | 'build' | 'review' | 'complete'
function getPhaseColor(phase: Phase): string {
  switch (phase) {
    case 'interview': return 'blue'
    case 'spec':      return 'purple'
    case 'build':     return 'yellow'
    case 'review':    return 'orange'
    case 'complete':  return 'green'
    default: return assertNever(phase) // Compile error if case missed
  }
}
```

## Utility Types

```typescript
function updateProject(id: string, updates: Partial<Project>) { /* ... */ }
type CompleteProject = Required<Project>
type ProjectSummary = Pick<Project, 'id' | 'name' | 'status'>
type NewProject = Omit<Project, 'id' | 'createdAt'>
type PhaseConfig = Record<Phase, { model: string; thinking: string }>
type ActiveStatuses = Extract<ProjectStatus, 'active' | 'running'>
type InactiveStatuses = Exclude<ProjectStatus, 'active'>
type FetchResult = ReturnType<typeof fetchProjects>
type Projects = Awaited<ReturnType<typeof fetchProjects>>
```

## Type Guards

```typescript
function isProject(value: unknown): value is Project {
  return typeof value === 'object' && value !== null && 'id' in value && 'name' in value
}

if (isProject(data)) console.log(data.name) // data is Project

// Assertion function — throws if invalid
function assertProject(value: unknown): asserts value is Project {
  if (!isProject(value)) throw new Error('Invalid project data')
}
```

## Common Patterns

### Builder Pattern
```typescript
class QueryBuilder<T> {
  private filters: Array<(item: T) => boolean> = []
  private sortKey?: keyof T

  where(fn: (item: T) => boolean): this { this.filters.push(fn); return this }
  orderBy(key: keyof T): this { this.sortKey = key; return this }
  execute(items: T[]): T[] {
    let result = items.filter(i => this.filters.every(f => f(i)))
    if (this.sortKey) result.sort((a, b) => a[this.sortKey!] > b[this.sortKey!] ? 1 : -1)
    return result
  }
}
```

### Readonly by Default
```typescript
interface Config { readonly port: number; readonly host: string; readonly features: readonly string[] }
const PHASES = ['interview', 'spec', 'build', 'review', 'complete'] as const
type Phase = typeof PHASES[number]
```

## Advanced Type Patterns

### Conditional Types
```typescript
type IsString<T> = T extends string ? true : false
type UnwrapPromise<T> = T extends Promise<infer R> ? R : T // Project[] from Promise<Project[]>
type NonNullable<T> = T extends null | undefined ? never : T // distributive over unions

// Nested conditional for response shaping
type ApiResponse<T> = T extends undefined ? { status: 'empty' }
  : T extends Error ? { status: 'error'; message: string }
  : { status: 'ok'; data: T }
```

### Mapped Types with Key Remapping
```typescript
// Generate getters — remap keys with `as` clause
type Getters<T> = { [K in keyof T as `get${Capitalize<string & K>}`]: () => T[K] }
// Getters<{ id: string; priority: number }> = { getId: () => string; getPriority: () => number }

// Filter properties by value type — exclude non-matching keys with never
type StringKeysOf<T> = { [K in keyof T as T[K] extends string ? K : never]: T[K] }

// Make specific keys optional
type OptionalKeys<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>
```

### The `infer` Keyword
```typescript
type ElementOf<T> = T extends readonly (infer E)[] ? E : never
type FirstArg<T> = T extends (a: infer A, ...r: unknown[]) => unknown ? A : never

// Parse route params from template literal — combines infer with recursion
type ExtractRouteParams<T extends string> =
  T extends `${string}:${infer P}/${infer Rest}`
    ? { [K in P | keyof ExtractRouteParams<Rest>]: string }
    : T extends `${string}:${infer P}` ? { [K in P]: string } : Record<string, never>
// ExtractRouteParams<'/api/:projectId/tasks/:taskId'> = { projectId: string; taskId: string }
```

### Recursive Types
```typescript
type DeepReadonly<T> = T extends Function ? T
  : T extends object ? { readonly [K in keyof T]: DeepReadonly<T[K]> } : T

type DeepPartial<T> = T extends object ? { [K in keyof T]?: DeepPartial<T[K]> } : T

type JsonValue = string | number | boolean | null | JsonValue[] | { [k: string]: JsonValue }

// Flatten nested keys into dot-notation
type FlattenKeys<T, Prefix extends string = ''> = T extends object
  ? { [K in keyof T & string]: T[K] extends object
        ? FlattenKeys<T[K], `${Prefix}${K}.`> : `${Prefix}${K}` }[keyof T & string]
  : never
// FlattenKeys<{ server: { host: string; port: number } }> = 'server.host' | 'server.port'
```

### Variadic Tuple Types
```typescript
type Concat<A extends readonly unknown[], B extends readonly unknown[]> = [...A, ...B]

// Type-safe event emitter using labeled tuple elements
type EventMap = {
  'task:start': [taskId: string, workerId: string]
  'task:complete': [taskId: string, output: string]
  'error': [error: Error]
}
function emit<K extends keyof EventMap>(event: K, ...args: EventMap[K]): void { /* ... */ }
emit('task:start', 'task-1', 'worker-a') // OK
emit('task:start', 'task-1')             // Error — missing workerId
```

## Framework-Specific Typing

### Nitro/H3 Middleware
```typescript
import { defineEventHandler, readBody } from 'h3'

interface CreateProjectBody { name: string; goal: string; template?: string }
export default defineEventHandler(async (event) => {
  const body = await readBody<CreateProjectBody>(event)
  return { id: (await createProject(body.name, body.goal)).id, status: 'created' as const }
})

// Augment H3 context with typed user
declare module 'h3' {
  interface H3EventContext { user?: { id: string; role: 'admin' | 'user' } }
}
```

### Vue Component Props
```typescript
<script setup lang="ts">
const props = withDefaults(defineProps<{
  items: Project[]; selected?: string; loading?: boolean
}>(), { loading: false })

const emit = defineEmits<{ select: [id: string]; delete: [id: string, confirm: boolean] }>()
defineSlots<{
  default: (props: { item: Project; index: number }) => unknown
  empty: () => unknown
}>()
</script>
```

### Zod Schema Inference
```typescript
import { z } from 'zod'

const ProjectSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  status: z.enum(['active', 'archived', 'deleted']),
  tags: z.array(z.string()).default([]),
  config: z.object({ model: z.string(), maxTokens: z.number().positive() }),
  createdAt: z.coerce.date(),
})

type Project = z.infer<typeof ProjectSchema> // single source of truth
const ProjectUpdateSchema = ProjectSchema.partial().omit({ id: true, createdAt: true })
type ProjectUpdate = z.infer<typeof ProjectUpdateSchema>

// Generic paginated wrapper
const PaginatedSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.object({ items: z.array(itemSchema), total: z.number(), page: z.number() })
type PaginatedProjects = z.infer<ReturnType<typeof PaginatedSchema<typeof ProjectSchema>>>
```

### Type-Safe API Routes
```typescript
interface ApiRoutes {
  'GET /api/projects': { query: { status?: ProjectStatus }; response: PaginatedProjects }
  'POST /api/projects': { body: CreateProjectBody; response: Project }
  'PUT /api/projects/:id': { params: { id: string }; body: ProjectUpdate; response: Project }
}

async function apiFetch<K extends keyof ApiRoutes>(
  route: K, options: Omit<ApiRoutes[K], 'response'>,
): Promise<ApiRoutes[K]['response']> {
  const [method, path] = (route as string).split(' ')
  return (await fetch(path, { method })).json()
}
const projects = await apiFetch('GET /api/projects', { query: { status: 'active' } })
```

## Module Patterns

### Barrel Exports
```typescript
// src/models/index.ts — public API only
export type { Project, ProjectStatus, ProjectUpdate } from './project'
export type { Task, TaskState } from './task'
export { ProjectSchema, TaskSchema } from './schemas'
// AVOID barrels for: internal utils, circular deps, large monorepos (defeats tree-shaking)
```

### Ambient Declarations
```typescript
// env.d.ts — type environment variables
declare namespace NodeJS {
  interface ProcessEnv {
    NODE_ENV: 'development' | 'production' | 'test'
    DATABASE_URL: string
    PORT?: string
  }
}
declare module 'legacy-lib' { export function doThing(input: string): Promise<unknown> }
export {} // required — makes this a module, not a script
```

### Declaration Merging and Module Augmentation
```typescript
declare module 'nuxt/schema' {
  interface RuntimeConfig { apiSecret: string }
  interface PublicRuntimeConfig { apiBase: string }
}
declare module 'vue' {
  interface ComponentCustomProperties { $api: ApiClient }
}
```

## Type-Level Testing

### Negative Tests with @ts-expect-error
```typescript
// Place in .test-d.ts files — verified by tsc, not at runtime
// @ts-expect-error — invalid currency rejected
const invalid: Currency = 'MONOPOLY_MONEY'
// @ts-expect-error — branded types not interchangeable
const taskId: TaskId = createProjectId('abc')
// @ts-expect-error — readonly rejects mutation
const phases: readonly string[] = ['a', 'b']; phases.push('c')
```

### expectTypeOf from Vitest
```typescript
import { describe, it, expectTypeOf } from 'vitest'

describe('type-level tests', () => {
  it('Result narrows correctly', () => {
    type Success = Extract<Result<string>, { ok: true }>
    expectTypeOf<Success>().toMatchTypeOf<{ ok: true; value: string }>()
  })

  it('branded types are not interchangeable', () => {
    expectTypeOf<ProjectId>().not.toMatchTypeOf<TaskId>()
  })

  it('pick returns correct subset', () => {
    const result = pick({ id: '1', name: 'App', secret: 'x' }, ['id', 'name'])
    expectTypeOf(result).toEqualTypeOf<{ id: string; name: string }>()
  })

  it('Zod schema infers correct shape', () => {
    type Inferred = z.infer<typeof ProjectSchema>
    expectTypeOf<Inferred['status']>().toEqualTypeOf<'active' | 'archived' | 'deleted'>()
  })
})
```

### Testing Complex Generics
```typescript
import { it, expectTypeOf } from 'vitest'

it('Getters produces correct accessor names', () => {
  type G = Getters<{ name: string; age: number }>
  expectTypeOf<G['getName']>().toEqualTypeOf<() => string>()
})

it('FlattenKeys produces dot-notation paths', () => {
  type Keys = FlattenKeys<{ a: { b: string; c: number }; d: string }>
  expectTypeOf<Keys>().toEqualTypeOf<'a.b' | 'a.c' | 'd'>()
})

it('ExtractRouteParams extracts named params', () => {
  type P = ExtractRouteParams<'/api/:orgId/projects/:projectId'>
  expectTypeOf<P>().toEqualTypeOf<{ orgId: string; projectId: string }>()
})
```

## Quality Checklist

- [ ] Zero `any` types (use `unknown` + type guards instead)
- [ ] Function parameters and return types explicitly typed
- [ ] Union types for fixed-option values (not bare string/number)
- [ ] Discriminated unions for state modeling
- [ ] All switch/if-else chains exhaustively checked
- [ ] Generic constraints are specific (not just `<T>`)
- [ ] Errors handled with Result types or explicit try/catch
- [ ] No type assertions (`as`) without preceding validation
- [ ] Interfaces for extensible shapes, types for unions/computed
- [ ] tsconfig strict mode enabled
- [ ] Zod schemas as single source of truth for shared types
- [ ] Type-level tests cover custom utilities and branded types
- [ ] Module augmentations in dedicated .d.ts files

## Anti-Patterns

- `any` to "make it compile" — fix the actual type issue
- `as Type` without validation — lying to the compiler
- `enum` — prefer `as const` objects or union types
- Non-exhaustive switch on union types
- `object` type — too broad, use specific interfaces
- `!` non-null assertion — if you need it, your types are wrong
- Exporting everything — export only what consumers need
- `[key: string]: any` — use Map or specific interfaces
- Duplicating types that Zod can infer — single source of truth
- Barrel files that re-export entire modules — defeats tree-shaking
- Forgetting `export {}` in .d.ts files — makes them scripts not modules
