---
name: vue-nuxt
description: >
  Build production-quality Vue 3 and Nuxt 3 applications following framework best practices.
  Covers Composition API, composables, reactivity, SSR, Nitro server routes, component patterns,
  Pinia state management, VeeValidate + Zod forms, Vitest testing, middleware, plugins, and TDD.
  Trigger for any task involving Vue components, Nuxt pages, composables, server routes,
  state management, form validation, refs, watchers, computed, or Vue/Nuxt ecosystem tooling.
triggers:
  - vue
  - nuxt
  - component
  - composable
  - ref
  - reactive
  - ssr
  - page
  - layout
  - plugin
  - nitro
  - useFetch
  - pinia
  - vee-validate
  - form validation
  - state management
---

# Vue 3 & Nuxt 3 Mastery

Write idiomatic, performant, maintainable Vue/Nuxt code. The framework has strong opinions — follow them.

## Core Philosophy

1. **Composition over options** — Always `<script setup>` + Composition API. No Options API.
2. **Reactivity is the framework** — Know when things are reactive and when they are not. #1 bug source.
3. **Let Nuxt do the work** — Auto-imports, file-based routing, server routes, built-in composables.
4. **Factor III (Config)** — Use `runtimeConfig` for all env-based configuration. Never hardcode URLs, keys, or flags.

## Component Patterns

### SFC Structure
```vue
<script setup lang="ts">
import { SomeExternalLib } from 'external-lib'

const props = defineProps<{ title: string; items: Item[]; loading?: boolean }>()
const emit = defineEmits<{ select: [item: Item]; close: [] }>()

const { data, refresh } = useFetch('/api/items')
const route = useRoute()

const searchQuery = ref('')
const filteredItems = computed(() =>
  props.items.filter(i => i.name.toLowerCase().includes(searchQuery.value.toLowerCase()))
)

watch(() => props.items, () => { /* react to prop changes */ }, { deep: true })

function handleSelect(item: Item) { emit('select', item) }
onMounted(() => { /* DOM available */ })
</script>

<template>
  <div class="component-name"><!-- template --></div>
</template>

<style scoped>
/* Always scoped unless intentionally global */
</style>
```

### Props & Defaults
```typescript
// TypeScript generics only — NEVER runtime prop validation
const props = withDefaults(defineProps<{
  id: string
  variant?: 'primary' | 'secondary'
  maxItems?: number
}>(), { variant: 'primary', maxItems: 10 })
```

### Typed Emits & v-model
```typescript
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'submit': [data: FormData]
}>()
```
```vue
<!-- Parent: <SearchInput v-model="query" v-model:filters="activeFilters" /> -->
<script setup lang="ts">
const model = defineModel<string>()              // default v-model
const filters = defineModel<string[]>('filters')  // named v-model
</script>
```

## Reactivity — Get It Right

### The Rules
```typescript
const count = ref(0)                // ref() for primitives and reassignable values
const items = ref<Item[]>([])       // ref() for arrays
const form = reactive({ email: '', password: '' }) // reactive() for mutated objects (prefer ref)

// NEVER destructure reactive — kills reactivity
const { email } = form              // BAD
const email = toRef(form, 'email')  // GOOD

// NEVER reassign reactive
form = { email: 'x' }              // BAD
Object.assign(form, { email: 'x' })// GOOD
```

### Computed & Watch
```typescript
const fullName = computed(() => `${first.value} ${last.value}`)

// Writable computed for v-model proxying
const selected = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

watch(count, (n, o) => console.log(o, '->', n))
watch([first, last], ([f, l]) => update(f, l))
watchEffect(() => { document.title = `${name.value} - App` })
```

### Common Reactivity Bugs
```typescript
const first = items.value[0]       // BAD — snapshot, not reactive
const first = computed(() => items.value[0]) // GOOD

props.items.push(newItem)          // BAD — mutating parent state
emit('add', newItem)               // GOOD — let parent handle it
```

## Nuxt-Specific Patterns

### File-Based Routing
```
pages/
├── index.vue              → /
├── projects/
│   ├── index.vue          → /projects
│   └── [name].vue         → /projects/:name
│       └── settings.vue   → /projects/:name/settings
```

### Data Fetching
```typescript
const { data, pending, error, refresh } = await useFetch<Project[]>('/api/projects')

// Reactive query params — re-fetches automatically
const page = ref(1)
const { data } = await useFetch('/api/projects', { query: { page, limit: 20 } })

// useAsyncData for custom logic
const { data } = await useAsyncData('projects', () =>
  $fetch('/api/projects', { query: { status: 'active' } })
)

// $fetch for event handlers (NOT useFetch)
async function deleteProject(id: string) {
  await $fetch(`/api/projects/${id}`, { method: 'DELETE' })
  refresh()
}
```

### Server Routes (Nitro)
```typescript
// server/api/projects/index.get.ts
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const id = getRouterParam(event, 'id')
  return { data: projects }
})
```

### Composables
```typescript
// composables/useProject.ts
export function useProject(name: MaybeRef<string>) {
  const projectName = toRef(name)
  const { data: project, pending, refresh } = useFetch(() => `/api/projects/${projectName.value}`)
  const isActive = computed(() => project.value?.status === 'running')

  async function archive() {
    await $fetch(`/api/projects/${projectName.value}/archive`, { method: 'POST' })
    await refresh()
  }

  return { project, pending, isActive, archive, refresh }
}
```

### Runtime Config (Factor III)
```typescript
// nuxt.config.ts — all config from env, never hardcoded
export default defineNuxtConfig({
  runtimeConfig: {
    secretKey: process.env.SECRET_KEY,        // server-only
    dbUrl: process.env.DATABASE_URL,
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || '/api',  // client-accessible
    }
  }
})

// Usage: useRuntimeConfig().secretKey (server) / useRuntimeConfig().public.apiBase (client)
// In K8s/EKS: env vars via ConfigMap/Secrets — NUXT_PUBLIC_* auto-maps to runtimeConfig
```

## State Management (Pinia)

### Setup Store (Preferred)
```typescript
// stores/useProjectStore.ts
export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const activeId = ref<string | null>(null)
  const loading = ref(false)

  const activeProject = computed(() => projects.value.find(p => p.id === activeId.value))

  async function fetchProjects() {
    loading.value = true
    try { projects.value = await $fetch<Project[]>('/api/projects') }
    finally { loading.value = false }
  }

  return { projects, activeId, loading, activeProject, fetchProjects }
})
```

### Composable vs Store Decision
```
COMPOSABLE: scoped to component tree, per-instance data, no cross-route sharing
STORE:      global/shared state, survives navigation, multiple unrelated consumers
```

### Persisted State
```typescript
export const usePrefsStore = defineStore('prefs', () => {
  const theme = ref<'light' | 'dark'>('light')
  return { theme }
}, {
  persist: { storage: piniaPluginPersistedstate.localStorage(), pick: ['theme'] },
})
```

### Store Testing
```typescript
import { setActivePinia, createPinia } from 'pinia'

describe('useProjectStore', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('finds active project by id', () => {
    const store = useProjectStore()
    store.projects = [{ id: '1', name: 'Alpha' }, { id: '2', name: 'Beta' }]
    store.activeId = '2'
    expect(store.activeProject?.name).toBe('Beta')
  })
})
```

## Form Handling

### VeeValidate + Zod (Shared Schema)
```typescript
// schemas/project.ts — used by BOTH client and server
import { z } from 'zod'
export const projectSchema = z.object({
  name: z.string().min(3, 'Min 3 characters'),
  budget: z.number().positive('Must be positive'),
  status: z.enum(['draft', 'active', 'archived']),
})
export type ProjectFormData = z.infer<typeof projectSchema>
```

```vue
<!-- components/ProjectForm.vue -->
<script setup lang="ts">
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { projectSchema, type ProjectFormData } from '~/schemas/project'

const emit = defineEmits<{ submit: [data: ProjectFormData] }>()
const { handleSubmit, errors, defineField, setErrors } = useForm({
  validationSchema: toTypedSchema(projectSchema),
  initialValues: { name: '', budget: 0, status: 'draft' as const },
})
const [name, nameAttrs] = defineField('name')
const [budget, budgetAttrs] = defineField('budget')

const onSubmit = handleSubmit(async (values) => {
  try { emit('submit', values) }
  catch (err: any) { if (err.data?.fieldErrors) setErrors(err.data.fieldErrors) }
})
</script>

<template>
  <form @submit.prevent="onSubmit">
    <input v-model="name" v-bind="nameAttrs" />
    <span v-if="errors.name" class="error">{{ errors.name }}</span>
    <input v-model.number="budget" v-bind="budgetAttrs" type="number" />
    <span v-if="errors.budget" class="error">{{ errors.budget }}</span>
    <button type="submit">Save</button>
  </form>
</template>
```

### Form Composable
```typescript
// composables/useFormSubmit.ts
export function useFormSubmit<T>(url: string, method = 'POST') {
  const submitting = ref(false)
  const serverError = ref<string | null>(null)

  async function submit(data: T) {
    submitting.value = true; serverError.value = null
    try { return await $fetch(url, { method, body: data }) }
    catch (e: any) { serverError.value = e.data?.message ?? 'Failed'; throw e }
    finally { submitting.value = false }
  }
  return { submit, submitting, serverError }
}
```

### Multi-Step Forms
```vue
<script setup lang="ts">
const step = ref(1)
const formData = reactive({ name: '', email: '', plan: 'free' as const })
</script>
<template>
  <form @submit.prevent="handleSubmit">
    <StepOne v-if="step === 1" v-model:name="formData.name" v-model:email="formData.email" />
    <StepTwo v-if="step === 2" v-model:plan="formData.plan" />
    <button v-if="step > 1" type="button" @click="step--">Back</button>
    <button v-if="step < 2" type="button" @click="step++">Next</button>
    <button v-else type="submit">Submit</button>
  </form>
</template>
```

### Server-Side Validation
```typescript
// server/api/projects/index.post.ts — validate with same Zod schema
import { projectSchema } from '~/schemas/project'

export default defineEventHandler(async (event) => {
  const result = projectSchema.safeParse(await readBody(event))
  if (!result.success) {
    throw createError({ statusCode: 422, data: { fieldErrors: result.error.flatten().fieldErrors } })
  }
  return await createProject(result.data)
})
```

## Middleware Deep Dive

### Global vs Route Middleware
```typescript
// middleware/auth.global.ts — .global suffix = every route
export default defineNuxtRouteMiddleware((to) => {
  const { authenticated } = useAuth()
  if (!authenticated.value && !['/login', '/signup'].includes(to.path)) {
    return navigateTo('/login')
  }
})

// middleware/admin.ts — named, opt-in per page
export default defineNuxtRouteMiddleware(() => {
  const { user } = useAuth()
  if (user.value?.role !== 'admin') return abortNavigation({ statusCode: 403 })
})

// Usage: definePageMeta({ middleware: ['admin'] })
```

### Server Middleware (Nitro)
```typescript
// server/middleware/auth.ts — runs on every server request
export default defineEventHandler(async (event) => {
  if (!event.path.startsWith('/api') || event.path.startsWith('/api/auth')) return
  const token = getHeader(event, 'authorization')?.replace('Bearer ', '')
  if (!token) throw createError({ statusCode: 401, message: 'Unauthorized' })
  event.context.user = await verifyToken(token)
})
```

### Auth Composable
```typescript
export function useAuth() {
  const user = useState<User | null>('auth-user', () => null)
  const authenticated = computed(() => !!user.value)

  async function login(creds: { email: string; password: string }) {
    user.value = await $fetch('/api/auth/login', { method: 'POST', body: creds })
  }
  async function logout() {
    await $fetch('/api/auth/logout', { method: 'POST' })
    user.value = null
    navigateTo('/login')
  }
  return { user, authenticated, login, logout }
}
```

## Plugin System

### Client-Only / Server-Only
```typescript
// plugins/analytics.client.ts — .client = browser only
export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig()
  if (config.public.analyticsId) initAnalytics(config.public.analyticsId)
})

// plugins/db.server.ts — .server = server only
export default defineNuxtPlugin(() => {
  return { provide: { db: createDbConnection(useRuntimeConfig().dbUrl) } }
})
```

### Providing Globals
```typescript
// plugins/api.ts — both client and server
export default defineNuxtPlugin(() => {
  const api = $fetch.create({
    baseURL: useRuntimeConfig().public.apiBase,
    onRequest({ options }) {
      const token = useCookie('auth-token')
      if (token.value) options.headers.set('Authorization', `Bearer ${token.value}`)
    },
    onResponseError({ response }) {
      if (response.status === 401) navigateTo('/login')
    },
  })
  return { provide: { api } } // useNuxtApp().$api('/projects')
})
```

### Third-Party Integration
```typescript
// plugins/sentry.client.ts
import * as Sentry from '@sentry/vue'

export default defineNuxtPlugin((nuxtApp) => {
  Sentry.init({
    app: nuxtApp.vueApp,
    dsn: useRuntimeConfig().public.sentryDsn,
    integrations: [Sentry.browserTracingIntegration({ router: useRouter() })],
  })
})
```

## Testing Patterns

### Component Testing (Vitest + Vue Test Utils)
```typescript
import { mountSuspended } from '@nuxt/test-utils/runtime'
import ProjectCard from '~/components/ProjectCard.vue'

describe('ProjectCard', () => {
  it('renders name and emits archive', async () => {
    const wrapper = await mountSuspended(ProjectCard, {
      props: { project: { id: '1', name: 'Alpha', status: 'active' } },
    })
    expect(wrapper.text()).toContain('Alpha')

    await wrapper.find('[data-testid="archive-btn"]').trigger('click')
    expect(wrapper.emitted('archive')![0]).toEqual(['1'])
  })
})
```

### Composable Testing
```typescript
describe('useCounter', () => {
  it('increments and decrements', () => {
    const { count, increment, decrement } = useCounter(5)
    increment(); expect(count.value).toBe(6)
    decrement(); decrement(); expect(count.value).toBe(4)
  })
})
```

### Mocking useFetch
```typescript
import { mountSuspended, mockNuxtImport } from '@nuxt/test-utils/runtime'

mockNuxtImport('useFetch', () => () => ({
  data: ref([{ id: '1', name: 'Alpha' }]),
  pending: ref(false), error: ref(null), refresh: vi.fn(),
}))

describe('ProjectList', () => {
  it('renders fetched projects', async () => {
    const wrapper = await mountSuspended(ProjectList)
    expect(wrapper.findAll('[data-testid="project-item"]')).toHaveLength(1)
  })
})
```

### Vitest Config
```typescript
// vitest.config.ts
import { defineVitestConfig } from '@nuxt/test-utils/config'
export default defineVitestConfig({ test: { environment: 'nuxt', globals: true } })
```

## TDD Example — Test First, Then Implement

### Step 1: Write the failing test (Red)
```typescript
// components/__tests__/StatusBadge.test.ts
import { mountSuspended } from '@nuxt/test-utils/runtime'
import StatusBadge from '~/components/StatusBadge.vue'

describe('StatusBadge', () => {
  it('renders capitalized status text', async () => {
    const w = await mountSuspended(StatusBadge, { props: { status: 'active' } })
    expect(w.text()).toBe('Active')
  })

  it('applies status-specific CSS class', async () => {
    const w = await mountSuspended(StatusBadge, { props: { status: 'failed' } })
    expect(w.find('span').classes()).toContain('badge--failed')
  })

  it('defaults to unknown for unrecognized status', async () => {
    const w = await mountSuspended(StatusBadge, { props: { status: 'xyz' as any } })
    expect(w.text()).toBe('Unknown')
    expect(w.find('span').classes()).toContain('badge--unknown')
  })
})
```

### Step 2: Implement minimal component to pass (Green)
```vue
<!-- components/StatusBadge.vue -->
<script setup lang="ts">
const props = defineProps<{ status: string }>()
const LABELS: Record<string, string> = { active: 'Active', pending: 'Pending', failed: 'Failed', archived: 'Archived' }
const label = computed(() => LABELS[props.status] ?? 'Unknown')
const cssClass = computed(() => `badge--${LABELS[props.status] ? props.status : 'unknown'}`)
</script>

<template>
  <span class="badge" :class="cssClass">{{ label }}</span>
</template>

<style scoped>
.badge { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }
.badge--active { background: #d1fae5; color: #065f46; }
.badge--failed { background: #fee2e2; color: #991b1b; }
.badge--unknown { background: #f3f4f6; color: #6b7280; }
</style>
```

### Step 3: Tests pass. Refactor with confidence.

## Performance Patterns

```vue
<LazyHeavyChart v-if="showChart" :data="chartData" />  <!-- lazy-load heavy components -->
<Panel v-show="isOpen" />       <!-- v-show for frequent toggles -->
<AdminTools v-if="isAdmin" />   <!-- v-if for rare toggles -->

<!-- Always :key with unique ID, NEVER index -->
<div v-for="item in items" :key="item.id">{{ item.name }}</div>
```
```typescript
// Static data does NOT need ref/reactive
const COLUMNS = ['Name', 'Status', 'Date']
const selectedColumn = ref(COLUMNS[0]) // only wrap what changes
```

## Quality Checklist

- [ ] All components use `<script setup lang="ts">`
- [ ] Props and emits typed with TypeScript generics
- [ ] Reactive state uses `ref()` (not `reactive()` unless needed)
- [ ] No destructuring of reactive objects without `toRef`/`toRefs`
- [ ] `useFetch`/`useAsyncData` in setup; `$fetch` in event handlers
- [ ] `:key` with unique IDs on `v-for` (never array index)
- [ ] Scoped styles on all components
- [ ] Composables extract reusable logic
- [ ] Server routes validate inputs with Zod
- [ ] `runtimeConfig` for all env-dependent values (Factor III)
- [ ] Shared Zod schemas between client forms and server validation
- [ ] Pinia stores use setup syntax and are tested
- [ ] Tests written before or alongside components (TDD)

## Anti-Patterns

- Options API (`data()`, `methods:`, `computed:` as object)
- `useFetch` in click handlers (use `$fetch`)
- Direct prop mutation instead of emitting
- Array index as `:key`
- Business logic in components instead of composables
- Destructuring `reactive()` (kills reactivity)
- Importing auto-imported Vue utilities (`ref`, `computed`, `watch`)
- `window`/`document` without SSR guard (`if (process.client)`)
- Deep watchers on large objects
- Refs for values that never change
- Hardcoded URLs/secrets instead of `runtimeConfig`
- Local state when multiple components need the same data (use Pinia)
- Skipping server validation because client validates
- Writing components before writing tests
