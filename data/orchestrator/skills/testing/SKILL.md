---
name: testing
description: >
  The authority on Test-Driven Development and comprehensive testing strategy. Covers TDD
  Red-Green-Refactor, the test pyramid, unit tests, integration tests, component tests,
  E2E testing, and infrastructure testing across TypeScript, Python, Go, and HCL. Trigger
  this skill for any task involving writing tests, test coverage, test-driven development,
  quality assurance, or testing strategy. Also trigger when the task mentions vitest, jest,
  playwright, cypress, pytest, go test, terratest, or any testing framework.
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
  - pytest
  - go test
  - terratest
  - smoke test
  - load test
---

# Testing Excellence

Write tests that serve as both safety net and documentation. Good tests give you confidence to refactor, catch regressions before users do, and explain *why* code exists. Bad tests are worse than no tests — they slow you down and give false confidence.

## Philosophy

1. **Test behavior, not implementation** — Verify *what* the code does, not *how*. If you refactor internals and tests break, the tests were wrong.
2. **The testing pyramid matters** — Many fast unit tests, fewer integration tests, minimal E2E tests. Unit tests catch logic errors. Integration tests catch wiring errors. E2E tests catch workflow errors.
3. **Every test answers one question** — If a test fails, you should immediately know what broke.
4. **Dev/prod parity** — Test environments must mirror production. Same OS, same database engine, same runtime version. If it passes in CI but fails in prod, your environments diverged. (12-Factor App, Factor X)
5. **Tests are a design tool** — Writing the test first forces you to think about the interface before the implementation. Hard-to-test code is hard-to-use code.

## TDD Workflow

Test-Driven Development is not about testing. It is about design. You write the test first to discover the API your code needs, then write the minimum code to satisfy it, then clean up.

### The Red-Green-Refactor Cycle

```
RED     → Write a failing test that describes the behavior you want.
GREEN   → Write the simplest code that makes the test pass. No more.
REFACTOR → Clean up without changing behavior. Tests stay green.
REPEAT  → Pick the next behavior. Write the next failing test.
```

### Complete TDD Walkthrough: Building a Rate Limiter

**Step 1 — RED: Define the interface through a test**

```typescript
import { describe, it, expect, vi } from 'vitest'
import { RateLimiter } from './rate-limiter'

describe('RateLimiter', () => {
  it('allows requests under the limit', () => {
    const limiter = new RateLimiter({ maxRequests: 3, windowMs: 1000 })
    expect(limiter.tryAcquire('user-1')).toBe(true)
  })
})
```

Run: `npx vitest run rate-limiter` — **FAILS**. `RateLimiter` does not exist. Good.

**Step 2 — GREEN: Minimum code to pass**

```typescript
interface RateLimiterConfig { maxRequests: number; windowMs: number }

export class RateLimiter {
  constructor(private config: RateLimiterConfig) {}
  tryAcquire(key: string): boolean { return true }
}
```

**PASSES**. Do not add anything else yet.

**Step 3 — RED: Rejection behavior**

```typescript
it('rejects requests over the limit', () => {
  const limiter = new RateLimiter({ maxRequests: 2, windowMs: 1000 })
  expect(limiter.tryAcquire('user-1')).toBe(true)
  expect(limiter.tryAcquire('user-1')).toBe(true)
  expect(limiter.tryAcquire('user-1')).toBe(false) // 3rd request denied
})
```

**FAILS**. `tryAcquire` always returns `true`.

**Step 4 — GREEN: Track counts**

```typescript
export class RateLimiter {
  private counts = new Map<string, number>()
  constructor(private config: RateLimiterConfig) {}

  tryAcquire(key: string): boolean {
    const current = this.counts.get(key) ?? 0
    if (current >= this.config.maxRequests) return false
    this.counts.set(key, current + 1)
    return true
  }
}
```

**PASSES**. Both tests green.

**Step 5 — RED: Window expiry**

```typescript
it('resets count after the time window expires', () => {
  vi.useFakeTimers()
  const limiter = new RateLimiter({ maxRequests: 1, windowMs: 1000 })
  expect(limiter.tryAcquire('user-1')).toBe(true)
  expect(limiter.tryAcquire('user-1')).toBe(false)
  vi.advanceTimersByTime(1001)
  expect(limiter.tryAcquire('user-1')).toBe(true) // window reset
  vi.useRealTimers()
})
```

**FAILS**. No window logic yet.

**Step 6 — GREEN: Add timestamps**

```typescript
export class RateLimiter {
  private windows = new Map<string, { count: number; start: number }>()
  constructor(private config: RateLimiterConfig) {}

  tryAcquire(key: string): boolean {
    const now = Date.now()
    const window = this.windows.get(key)
    if (!window || now - window.start >= this.config.windowMs) {
      this.windows.set(key, { count: 1, start: now })
      return true
    }
    if (window.count >= this.config.maxRequests) return false
    window.count++
    return true
  }
}
```

**PASSES**. All tests green. Step 7: add key isolation test — passes immediately (design already handles it). Step 8: **REFACTOR** — extract window lookup, rename internals, add JSDoc. Tests guard the refactor.

### TDD Rules of Thumb

- **Never write production code without a failing test.** If you cannot articulate what test would fail, you do not know what you are building.
- **Write the simplest failing test.** One behavior at a time.
- **Make it pass stupidly first.** Hardcode a value. The next test forces the real implementation.
- **Refactor only when green.** Never change behavior and structure simultaneously.
- **Listen to the tests.** Hard-to-test code is poorly designed code. Fix the design.

## Test Structure (AAA Pattern)

Every test follows Arrange, Act, Assert:

```typescript
describe('calculateTotal', () => {
  it('applies discount to items over $100', () => {
    // Arrange
    const items = [{ name: 'Widget', price: 150 }, { name: 'Gadget', price: 50 }]
    // Act
    const total = calculateTotal(items, 0.1)
    // Assert
    expect(total).toBe(185) // 150 * 0.9 + 50
  })
})
```

### Naming — Tests Read Like Requirements
```typescript
it('returns empty array when no projects match the filter')  // GOOD
it('throws 401 when auth token is missing')                  // GOOD
it('calls the database')                                     // BAD — describes implementation
it('works correctly')                                        // BAD — says nothing
```

## Unit Testing

### Mocking — Only When Necessary
```typescript
import { vi } from 'vitest'
vi.mock('fs/promises', () => ({ readFile: vi.fn(), writeFile: vi.fn() }))
import { readFile } from 'fs/promises'

describe('loadConfig', () => {
  beforeEach(() => vi.clearAllMocks())

  it('parses valid JSON config', async () => {
    vi.mocked(readFile).mockResolvedValue('{"port": 3000}')
    const config = await loadConfig('/path/to/config.json')
    expect(config.port).toBe(3000)
  })

  it('returns defaults when file not found', async () => {
    vi.mocked(readFile).mockRejectedValue(Object.assign(new Error('ENOENT'), { code: 'ENOENT' }))
    const config = await loadConfig('/missing.json')
    expect(config).toEqual(DEFAULT_CONFIG)
  })
})
```

### When to Mock vs. Integrate

| Mock when... | Integrate when... |
|---|---|
| External service you do not control (Stripe, AWS) | Your own database with testcontainers |
| Non-deterministic (time, randomness, UUIDs) | File system in integration tests |
| Slow resource (network calls > 100ms) | In-memory stores (SQLite, Redis mock) |
| Flaky third-party API | Service-to-service within your monorepo |

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
  })

  it('rejects duplicate project names', async () => {
    await $fetch('/api/projects', { method: 'POST', body: { name: 'dupe-test' } })
    await expect(
      $fetch('/api/projects', { method: 'POST', body: { name: 'dupe-test' } })
    ).rejects.toMatchObject({ statusCode: 409 })
  })
})
```

### Database Integration with Testcontainers
```typescript
import { PostgreSqlContainer } from '@testcontainers/postgresql'

describe('UserRepository', () => {
  let container: StartedPostgreSqlContainer
  let db: Pool

  beforeAll(async () => {
    container = await new PostgreSqlContainer('postgres:16-alpine').start()
    db = new Pool({ connectionString: container.getConnectionUri() })
    await runMigrations(db)
  }, 30_000)

  afterAll(async () => { await db.end(); await container.stop() })

  it('creates and retrieves user', async () => {
    const repo = new UserRepository(db)
    const created = await repo.create({ email: 'test@example.com', name: 'Test' })
    const found = await repo.findById(created.id)
    expect(found.email).toBe('test@example.com')
  })
})
```

## Component Testing (Vue/Nuxt)

```typescript
import { mount } from '@vue/test-utils'
import ProjectCard from './ProjectCard.vue'

describe('ProjectCard', () => {
  it('renders project name and status', () => {
    const wrapper = mount(ProjectCard, {
      props: { name: 'my-project', status: 'running', phase: 'build' },
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
  })
})
```

Nuxt-specific with `@nuxt/test-utils`:
```typescript
import { mountSuspended } from '@nuxt/test-utils/runtime'
import DashboardPage from '~/pages/dashboard.vue'

it('renders project list', async () => {
  const wrapper = await mountSuspended(DashboardPage)
  expect(wrapper.findAll('[data-testid="project-row"]').length).toBeGreaterThan(0)
})
```

## E2E Testing (Playwright)

### Page Object Model
```typescript
import { type Page, type Locator } from '@playwright/test'

export class LoginPage {
  readonly emailInput: Locator
  readonly passwordInput: Locator
  readonly submitButton: Locator

  constructor(private page: Page) {
    this.emailInput = page.getByLabel('Email')
    this.passwordInput = page.getByLabel('Password')
    this.submitButton = page.getByRole('button', { name: 'Sign in' })
  }

  async goto() { await this.page.goto('/login') }

  async login(email: string, password: string) {
    await this.emailInput.fill(email)
    await this.passwordInput.fill(password)
    await this.submitButton.click()
  }
}
```

### Test Isolation and Visual Regression
```typescript
import { test, expect } from '@playwright/test'
import { LoginPage } from '../pages/LoginPage'

test.describe('Project Management', () => {
  test.beforeEach(async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.goto()
    await loginPage.login('admin@test.com', 'test-password')
    await page.waitForURL('/dashboard')
  })

  test('creates a new project', async ({ page }) => {
    await page.getByRole('button', { name: 'New Project' }).click()
    await page.getByLabel('Project name').fill(`e2e-${Date.now()}`)
    await page.getByRole('button', { name: 'Create' }).click()
    await expect(page).toHaveURL(/\/projects\//)
  })

  test('dashboard matches visual snapshot', async ({ page }) => {
    await page.waitForLoadState('networkidle')
    await expect(page).toHaveScreenshot('dashboard.png', { maxDiffPixelRatio: 0.01 })
  })
})
```

### Playwright Configuration
```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e/tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 4 : undefined,
  reporter: process.env.CI ? [['html'], ['junit', { outputFile: 'results/e2e.xml' }]] : 'html',
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
})
```

## Python Testing (pytest)

### Fixtures and conftest
```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_app

@pytest.fixture
def app():
    return create_app(testing=True)

@pytest.fixture
async def client(app) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def sample_project():
    def _factory(**overrides):
        return {"name": "test-project", "status": "active", "owner": "test-user", **overrides}
    return _factory
```

### Parametrized Tests
```python
import pytest
from app.validators import validate_slug

@pytest.mark.parametrize("input_val,expected", [
    ("hello-world", True),
    ("UPPERCASE", False),
    ("has spaces", False),
    ("trailing-", False),
    ("a" * 64, False),
    ("valid-123", True),
    ("", False),
])
def test_validate_slug(input_val: str, expected: bool):
    assert validate_slug(input_val) == expected
```

### Async Testing with pytest-asyncio
```python
@pytest.mark.asyncio
async def test_create_project(client, sample_project):
    payload = sample_project(name="async-test")
    response = await client.post("/api/projects", json=payload)
    assert response.status_code == 201
    assert response.json()["name"] == "async-test"
```

### Markers for Organization
```python
# pyproject.toml: [tool.pytest.ini_options]
# markers = ["slow", "integration", "smoke"]

@pytest.mark.slow
def test_full_data_pipeline(): ...

@pytest.mark.smoke
def test_health_endpoint(client):
    assert client.get("/health").status_code == 200
```

## Go Testing

### Table-Driven Tests
```go
func TestHashPassword(t *testing.T) {
    tests := []struct {
        name     string
        password string
        wantErr  bool
    }{
        {name: "valid", password: "secure123!", wantErr: false},
        {name: "empty", password: "", wantErr: true},
        {name: "long", password: string(make([]byte, 1024)), wantErr: false},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            hash, err := HashPassword(tt.password)
            if tt.wantErr {
                if err == nil { t.Fatal("expected error") }
                return
            }
            if err != nil { t.Fatalf("unexpected error: %v", err) }
            if len(hash) == 0 { t.Fatal("expected non-empty hash") }
        })
    }
}
```

### Mocking with Interfaces
```go
type ProjectStore interface {
    Save(ctx context.Context, p *Project) error
    FindByID(ctx context.Context, id string) (*Project, error)
}

type MockProjectStore struct {
    SaveFunc     func(ctx context.Context, p *Project) error
    FindByIDFunc func(ctx context.Context, id string) (*Project, error)
}
func (m *MockProjectStore) Save(ctx context.Context, p *Project) error {
    return m.SaveFunc(ctx, p)
}
func (m *MockProjectStore) FindByID(ctx context.Context, id string) (*Project, error) {
    return m.FindByIDFunc(ctx, id)
}

func TestProjectCreation(t *testing.T) {
    var saved *Project
    store := &MockProjectStore{
        SaveFunc: func(_ context.Context, p *Project) error { saved = p; return nil },
    }
    svc := NewProjectService(store)
    _, err := svc.Create(context.Background(), CreateProjectInput{Name: "test"})
    if err != nil { t.Fatalf("unexpected error: %v", err) }
    if saved == nil || saved.Name != "test" { t.Fatal("project not saved correctly") }
}
```

### Benchmarks
```go
func BenchmarkHashPassword(b *testing.B) {
    for i := 0; i < b.N; i++ {
        _, _ = HashPassword("benchmark-password")
    }
}
```

Run: `go test -bench=. -benchmem ./...`

## Infrastructure Testing (Terratest)

### Testing Terraform Modules
```go
func TestVpcModule(t *testing.T) {
    t.Parallel()
    opts := &terraform.Options{
        TerraformDir: "../modules/vpc",
        Vars: map[string]interface{}{
            "environment":     "test",
            "vpc_cidr":        "10.99.0.0/16",
            "azs":             []string{"us-east-1a", "us-east-1b"},
            "private_subnets": []string{"10.99.1.0/24", "10.99.2.0/24"},
            "public_subnets":  []string{"10.99.101.0/24", "10.99.102.0/24"},
        },
        TerraformBinary: "terragrunt",
    }
    defer terraform.Destroy(t, opts)
    terraform.InitAndApply(t, opts)

    vpcId := terraform.Output(t, opts, "vpc_id")
    assert.Regexp(t, `^vpc-[a-z0-9]+$`, vpcId)
    assert.Len(t, terraform.OutputList(t, opts, "private_subnet_ids"), 2)
}
```

### Validating EKS Deployments
```go
func TestAppDeploymentRollout(t *testing.T) {
    t.Parallel()
    kubectlOptions := k8s.NewKubectlOptions("", "../kubeconfig-test.yaml", "apps")

    k8s.KubectlApply(t, kubectlOptions, "../k8s/manifests/app-deployment.yaml")
    k8s.WaitUntilDeploymentAvailable(t, kubectlOptions, "api-server", 60, 5*time.Second)

    service := k8s.GetService(t, kubectlOptions, "api-server")
    require.Equal(t, int32(80), service.Spec.Ports[0].Port)

    // In-cluster smoke test
    output, err := k8s.RunKubectlAndGetOutputE(t, kubectlOptions,
        "run", "smoke-test", "--rm", "-i", "--restart=Never",
        "--image=curlimages/curl", "--",
        "curl", "-sf", "http://api-server.apps.svc.cluster.local/health",
    )
    require.NoError(t, err)
    require.Contains(t, output, `"status":"ok"`)
}
```

### Post-Deploy Smoke Tests
```go
func TestSmokePostDeploy(t *testing.T) {
    baseURL := os.Getenv("DEPLOY_URL")
    if baseURL == "" { t.Skip("DEPLOY_URL not set") }

    t.Run("health", func(t *testing.T) {
        resp, err := http.Get(baseURL + "/health")
        require.NoError(t, err)
        defer resp.Body.Close()
        assert.Equal(t, 200, resp.StatusCode)
    })
    t.Run("static assets", func(t *testing.T) {
        resp, err := http.Get(baseURL + "/_nuxt/entry.js")
        require.NoError(t, err)
        defer resp.Body.Close()
        assert.Equal(t, 200, resp.StatusCode)
    })
}
```

## CI Pipeline Integration

### Pipeline Design — Fast Checks First
```yaml
# .github/workflows/test.yml
name: Test Suite
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
concurrency:
  group: test-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint-and-typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci && npm run lint && npm run typecheck

  unit-tests:
    needs: lint-and-typecheck
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci
      - run: npx vitest run --reporter=junit --outputFile=results/unit.xml --shard=${{ matrix.shard }}/4
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: "unit-results-${{ matrix.shard }}", path: results/ }

  integration-tests:
    needs: unit-tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_DB: test, POSTGRES_PASSWORD: test }
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci
      - run: npx vitest run --config vitest.integration.config.ts
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/test

  e2e-tests:
    needs: integration-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci
      - run: npx playwright install --with-deps chromium
      - run: npx playwright test
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: playwright-report, path: playwright-report/ }

  coverage-gate:
    needs: [unit-tests, integration-tests]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci && npx vitest run --coverage
      - name: Enforce thresholds
        run: |
          node -e "
            const r = require('./coverage/coverage-summary.json').total;
            const t = 80;
            if (r.lines.pct < t || r.branches.pct < t)
              { console.error('Coverage below ' + t + '%'); process.exit(1); }
          "
```

### Flaky Test Management

Flaky tests erode trust. Quarantine, do not ignore.

```typescript
// Quarantined: intermittent timeout — tracked in JIRA-1234
it.skipIf(process.env.CI)('reconnects after server restart', async () => { ... })
```

Rules: (1) Never ignore. Every flaky test has a root cause. (2) Quarantine immediately — do not block deploys. (3) Fix within one sprint or delete it.

### Test Reporting
```yaml
- name: Publish Results
  uses: dorny/test-reporter@v1
  if: always()
  with: { name: Test Results, path: "results/**/*.xml", reporter: jest-junit }
- name: Coverage Comment
  uses: davelosert/vitest-coverage-report-action@v2
  if: always()
```

## Edge Cases to Always Test

```typescript
// Empty/null          // Boundaries               // Errors
it('handles empty []') it('handles zero')          it('handles network timeout')
it('handles null')     it('handles negative nums') it('handles malformed JSON')
it('handles ""')       it('handles max length')    it('handles permission errors')
```

## Test Configuration (Vitest)

```typescript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['**/*.{test,spec}.{ts,js}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json-summary'],
      exclude: ['node_modules', 'test/fixtures', '**/*.d.ts'],
      thresholds: { lines: 80, branches: 75, functions: 80 },
    },
    setupFiles: ['./test/setup.ts'],
    testTimeout: 10_000,
  },
})
```

## Quality Checklist

- [ ] Tests are independent — no test depends on another running first
- [ ] Tests are deterministic — same result every run
- [ ] Each test verifies one behavior
- [ ] Test names describe expected behavior
- [ ] Mocks are minimal — only external dependencies
- [ ] Edge cases covered (empty, null, boundary, errors)
- [ ] Setup/teardown cleans up properly
- [ ] Tests run fast (< 10s for unit suite)
- [ ] Coverage is meaningful — branch coverage, not just lines
- [ ] Dev/prod parity — test DB matches production engine and version
- [ ] CI pipeline fails the build on test failure

## Anti-Patterns

- Testing implementation details (private methods, internal state)
- Snapshot tests for complex objects (approved blindly)
- Mocking everything (testing your mocks, not your code)
- One giant test that checks 15 things
- Copy-pasting tests instead of using helpers/fixtures
- Ignoring async timing (missing await)
- Different DB engines in test vs production (SQLite in test, Postgres in prod)
- Skipping tests in CI instead of fixing them
- No coverage gates — coverage only trends down without enforcement
