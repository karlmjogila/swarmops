---
name: testing
description: >
  Write comprehensive, maintainable tests that actually catch bugs. Covers unit tests,
  integration tests, component tests, and end-to-end testing patterns. Trigger this skill
  for any task involving writing tests, test coverage, test-driven development, or quality
  assurance automation. Also trigger when the task mentions vitest, jest, playwright,
  cypress, or any testing framework.
triggers:
  - test
  - spec
  - coverage
  - jest
  - vitest
  - playwright
  - cypress
  - e2e
  - unit test
  - integration test
  - tdd
  - assertion
---

# Testing Excellence

Write tests that serve as both safety net and documentation. Good tests give you confidence to refactor, catch regressions before users do, and explain *why* code exists. Bad tests are worse than no tests — they slow you down and give false confidence.

## Philosophy

1. **Test behavior, not implementation** — Tests should verify *what* the code does, not *how* it does it. If you refactor internals and tests break, the tests were wrong.
2. **The testing pyramid matters** — Many fast unit tests, fewer integration tests, minimal E2E tests. Each level catches different bugs.
3. **Every test answers one question** — If a test fails, you should immediately know what broke. No test should check 10 things.

## Test Structure

### The AAA Pattern
Every test follows Arrange, Act, Assert:

```typescript
describe('calculateTotal', () => {
  it('applies discount to items over $100', () => {
    // Arrange — set up the scenario
    const items = [
      { name: 'Widget', price: 150 },
      { name: 'Gadget', price: 50 },
    ]
    const discount = 0.1

    // Act — do the thing
    const total = calculateTotal(items, discount)

    // Assert — verify the outcome
    expect(total).toBe(185) // 150 * 0.9 + 50
  })
})
```

### Naming Convention
Test names should read like requirements:

```typescript
// GOOD — describes the behavior and condition
it('returns empty array when no projects match the filter')
it('throws 401 when auth token is missing')
it('retries failed requests up to 3 times')
it('marks task complete and advances phase when all tasks done')

// BAD — describes implementation
it('calls the database')
it('works correctly')
it('test for bug #123')
```

### Describe Blocks — Group by Behavior
```typescript
describe('ProjectService', () => {
  describe('create', () => {
    it('creates project with valid input')
    it('throws when name already exists')
    it('generates unique slug from name')
  })

  describe('archive', () => {
    it('sets status to archived')
    it('throws when project has running tasks')
    it('preserves all project data')
  })
})
```

## Unit Testing

### Pure Functions — The Easy Wins
```typescript
// Function
function parseTaskAnnotations(line: string): { id?: string, role?: string, depends?: string[] } {
  // ...
}

// Tests
describe('parseTaskAnnotations', () => {
  it('extracts @id annotation', () => {
    const result = parseTaskAnnotations('- [ ] Build API @id(api-1)')
    expect(result.id).toBe('api-1')
  })

  it('extracts @role annotation', () => {
    const result = parseTaskAnnotations('- [ ] Review code @role(reviewer)')
    expect(result.role).toBe('reviewer')
  })

  it('extracts multiple @depends', () => {
    const result = parseTaskAnnotations('- [ ] Deploy @depends(build,test)')
    expect(result.depends).toEqual(['build', 'test'])
  })

  it('returns empty object for plain task', () => {
    const result = parseTaskAnnotations('- [ ] Simple task')
    expect(result).toEqual({})
  })

  it('handles malformed annotations gracefully', () => {
    const result = parseTaskAnnotations('- [ ] Bad @id() @role()')
    expect(result.id).toBeUndefined()
  })
})
```

### Testing Async Code
```typescript
describe('fetchProject', () => {
  it('returns project data for valid name', async () => {
    const project = await fetchProject('my-app')
    expect(project).toMatchObject({
      name: 'my-app',
      status: expect.stringMatching(/active|archived/),
    })
  })

  it('throws NotFoundError for missing project', async () => {
    await expect(fetchProject('nonexistent'))
      .rejects
      .toThrow('not found')
  })
})
```

### Mocking — Only When Necessary
```typescript
import { vi } from 'vitest'

// Mock external dependencies, not your own code
vi.mock('fs/promises', () => ({
  readFile: vi.fn(),
  writeFile: vi.fn(),
}))

import { readFile, writeFile } from 'fs/promises'

describe('loadConfig', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('parses valid JSON config', async () => {
    vi.mocked(readFile).mockResolvedValue('{"port": 3000}')

    const config = await loadConfig('/path/to/config.json')
    expect(config.port).toBe(3000)
    expect(readFile).toHaveBeenCalledWith('/path/to/config.json', 'utf-8')
  })

  it('returns defaults when file not found', async () => {
    vi.mocked(readFile).mockRejectedValue(
      Object.assign(new Error('ENOENT'), { code: 'ENOENT' })
    )

    const config = await loadConfig('/missing.json')
    expect(config).toEqual(DEFAULT_CONFIG)
  })
})
```

### When NOT to Mock
```typescript
// DON'T mock the thing you're testing
// DON'T mock simple utility functions
// DON'T mock data structures
// DO mock: filesystem, network, databases, time, randomness
```

## Integration Testing

### API Endpoint Tests
```typescript
describe('POST /api/projects', () => {
  it('creates a new project', async () => {
    const response = await $fetch('/api/projects', {
      method: 'POST',
      body: { name: 'test-project', goal: 'Build a thing' },
    })

    expect(response.status).toBe('created')
    expect(response.project.name).toBe('test-project')

    // Verify side effects
    const state = await readFile(join(projectsDir, 'test-project', 'state.json'), 'utf-8')
    expect(JSON.parse(state).phase).toBe('interview')
  })

  it('rejects duplicate project names', async () => {
    // Create first
    await $fetch('/api/projects', {
      method: 'POST',
      body: { name: 'dupe-test' },
    })

    // Try duplicate
    await expect(
      $fetch('/api/projects', {
        method: 'POST',
        body: { name: 'dupe-test' },
      })
    ).rejects.toMatchObject({ statusCode: 409 })
  })

  it('validates required fields', async () => {
    await expect(
      $fetch('/api/projects', {
        method: 'POST',
        body: {},
      })
    ).rejects.toMatchObject({ statusCode: 400 })
  })
})
```

### Testing with Fixtures
```typescript
// test/fixtures/projects.ts
export function createTestProject(overrides = {}) {
  return {
    name: `test-${Date.now()}`,
    phase: 'build',
    status: 'running',
    startedAt: new Date().toISOString(),
    ...overrides,
  }
}

// In tests
const project = createTestProject({ phase: 'review' })
```

## Component Testing

### Vue Component Tests (with Vitest + Vue Test Utils)
```typescript
import { mount } from '@vue/test-utils'
import ProjectCard from './ProjectCard.vue'

describe('ProjectCard', () => {
  it('renders project name and status', () => {
    const wrapper = mount(ProjectCard, {
      props: {
        name: 'my-project',
        status: 'running',
        phase: 'build',
      },
    })

    expect(wrapper.text()).toContain('my-project')
    expect(wrapper.find('[data-testid="status"]').text()).toBe('running')
  })

  it('emits select event on click', async () => {
    const wrapper = mount(ProjectCard, {
      props: { name: 'test', status: 'ready', phase: 'build' },
    })

    await wrapper.trigger('click')
    expect(wrapper.emitted('select')).toHaveLength(1)
    expect(wrapper.emitted('select')![0]).toEqual(['test'])
  })

  it('shows loading state when pending', () => {
    const wrapper = mount(ProjectCard, {
      props: { name: 'test', status: 'running', phase: 'build', loading: true },
    })

    expect(wrapper.find('[data-testid="spinner"]').exists()).toBe(true)
  })
})
```

## Edge Cases to Always Test

```typescript
// Empty inputs
it('handles empty array', () => { ... })
it('handles empty string', () => { ... })
it('handles null/undefined', () => { ... })

// Boundaries
it('handles zero', () => { ... })
it('handles negative numbers', () => { ... })
it('handles maximum length input', () => { ... })

// Concurrency
it('handles simultaneous requests', () => { ... })
it('handles rapid successive calls', () => { ... })

// Error conditions
it('handles network timeout', () => { ... })
it('handles malformed JSON', () => { ... })
it('handles filesystem permission errors', () => { ... })
```

## Test Configuration (Vitest)
```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',           // or 'jsdom' for component tests
    include: ['**/*.{test,spec}.{ts,js}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['node_modules', 'test/fixtures'],
    },
    setupFiles: ['./test/setup.ts'],
  },
})
```

## Quality Checklist

- [ ] Tests are independent — no test depends on another test running first
- [ ] Tests are deterministic — same result every run (no random, no real time)
- [ ] Each test verifies one behavior
- [ ] Test names describe the expected behavior
- [ ] Mocks are minimal — only external dependencies
- [ ] Edge cases covered (empty, null, boundary values, errors)
- [ ] Setup/teardown cleans up properly (no leaked state)
- [ ] Tests run fast (< 10 seconds for unit suite)
- [ ] No console.log left in tests
- [ ] Coverage is meaningful (not just line coverage — branch coverage matters)

## Anti-Patterns

- Testing implementation details (private methods, internal state)
- Snapshot tests for complex objects (they always get approved blindly)
- Tests that pass when the code is broken (false positives)
- Tests that fail randomly (flaky tests destroy trust)
- Mocking everything (you're testing your mocks, not your code)
- One giant test that checks 15 things
- Copy-pasting test code instead of using helpers/fixtures
- Testing framework behavior (don't test that Vue renders a div)
- Ignoring async timing (missing await, not waiting for DOM updates)
- Writing tests after the fact that just assert current behavior without understanding intent
