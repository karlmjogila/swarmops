---
name: vue-nuxt
description: >
  Build production-quality Vue 3 and Nuxt 3 applications following framework best practices.
  Covers Composition API, composables, reactivity, SSR considerations, Nitro server routes,
  component patterns, and state management. Trigger this skill for any task involving Vue
  components, Nuxt pages, composables, server routes, or frontend framework architecture.
  Also trigger when working with refs, reactive state, watchers, computed properties,
  or any Vue/Nuxt ecosystem tooling.
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
---

# Vue 3 & Nuxt 3 Mastery

Write Vue and Nuxt code that is idiomatic, performant, and maintainable. The framework has strong opinions — follow them. Fight the framework and you lose.

## Core Philosophy

1. **Composition over options** — Always use `<script setup>` with Composition API. No Options API.
2. **Reactivity is the framework** — Understand when things are reactive and when they're not. This is the #1 source of bugs.
3. **Let Nuxt do the work** — Auto-imports, file-based routing, server routes, built-in composables. Don't reinvent what Nuxt provides.

## Component Patterns

### Single File Component Structure
```vue
<script setup lang="ts">
// 1. Imports (auto-imported ones don't need explicit import)
import { SomeExternalLib } from 'external-lib'

// 2. Props & Emits
const props = defineProps<{
  title: string
  items: Item[]
  loading?: boolean
}>()

const emit = defineEmits<{
  select: [item: Item]
  close: []
}>()

// 3. Composables
const { data, refresh } = useFetch('/api/items')
const route = useRoute()

// 4. Reactive state
const searchQuery = ref('')
const isExpanded = ref(false)

// 5. Computed
const filteredItems = computed(() =>
  props.items.filter(item =>
    item.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
)

// 6. Watchers (use sparingly)
watch(() => props.items, (newItems) => {
  // React to prop changes
}, { deep: true })

// 7. Functions
function handleSelect(item: Item) {
  emit('select', item)
}

// 8. Lifecycle
onMounted(() => {
  // DOM is available
})
</script>

<template>
  <!-- Single root element preferred but not required in Vue 3 -->
  <div class="component-name">
    <!-- Template logic -->
  </div>
</template>

<style scoped>
/* Scoped styles — always use scoped unless intentionally global */
</style>
```

### Props — Type Them Properly
```typescript
// Use TypeScript generics — NEVER runtime prop validation
const props = defineProps<{
  // Required
  id: string
  items: TaskItem[]

  // Optional with defaults
  variant?: 'primary' | 'secondary'
  maxItems?: number
}>()

// Defaults via withDefaults
const props = withDefaults(defineProps<{
  variant?: 'primary' | 'secondary'
  maxItems?: number
}>(), {
  variant: 'primary',
  maxItems: 10,
})
```

### Events — Type Them Too
```typescript
// Typed emits with payload types
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'submit': [data: FormData]
  'delete': [id: string]
}>()
```

### v-model on Custom Components
```vue
<!-- Parent -->
<SearchInput v-model="query" v-model:filters="activeFilters" />

<!-- SearchInput.vue -->
<script setup lang="ts">
const model = defineModel<string>()           // default v-model
const filters = defineModel<string[]>('filters') // named v-model
</script>

<template>
  <input :value="model" @input="model = ($event.target as HTMLInputElement).value" />
</template>
```

## Reactivity — Get It Right

### The Rules
```typescript
// ref() for primitives and values you reassign
const count = ref(0)
const name = ref('hello')
const items = ref<Item[]>([])

// reactive() for objects you mutate (but prefer ref)
const form = reactive({
  email: '',
  password: '',
})

// NEVER destructure reactive objects — kills reactivity
const { email } = form  // BAD — email is now a plain string
const email = toRef(form, 'email')  // GOOD — preserves reactivity

// NEVER reassign a reactive object
form = { email: 'new' }  // BAD — breaks reactivity
Object.assign(form, { email: 'new' })  // GOOD
```

### Computed — The Workhorse
```typescript
// Computed values are cached and reactive
const fullName = computed(() => `${firstName.value} ${lastName.value}`)

// Writable computed (for v-model proxying)
const selected = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})
```

### Watch — Use Sparingly
```typescript
// Watch a single ref
watch(count, (newVal, oldVal) => {
  console.log(`Changed from ${oldVal} to ${newVal}`)
})

// Watch multiple sources
watch([firstName, lastName], ([newFirst, newLast]) => {
  updateFullName(newFirst, newLast)
})

// Watch with immediate (runs on creation)
watch(route, () => fetchData(), { immediate: true })

// watchEffect — auto-tracks dependencies (use for side effects)
watchEffect(() => {
  // Automatically re-runs when any ref used inside changes
  document.title = `${projectName.value} - Dashboard`
})
```

### Common Reactivity Bugs
```typescript
// BUG: Losing reactivity by extracting .value too early
const items = ref<Item[]>([])
const first = items.value[0]  // Not reactive! This is a snapshot

// FIX: Use computed or access .value in template/watchers
const first = computed(() => items.value[0])

// BUG: Async operations with stale refs
const data = ref(null)
async function load() {
  const result = await fetchData()
  data.value = result  // Fine — ref is stable across awaits
}

// BUG: Modifying props directly
props.items.push(newItem)  // BAD — mutating parent state
emit('add', newItem)       // GOOD — let parent handle it
```

## Nuxt-Specific Patterns

### File-Based Routing
```
pages/
├── index.vue              → /
├── about.vue              → /about
├── projects/
│   ├── index.vue          → /projects
│   └── [name].vue         → /projects/:name
│   └── [name]/
│       └── settings.vue   → /projects/:name/settings
```

### Data Fetching
```typescript
// useFetch — SSR-friendly, cached, auto-refreshes
const { data, pending, error, refresh } = await useFetch('/api/projects')

// With typing
const { data } = await useFetch<Project[]>('/api/projects')

// With query params (reactive — re-fetches when params change)
const page = ref(1)
const { data } = await useFetch('/api/projects', {
  query: { page, limit: 20 }
})

// useAsyncData — for custom async logic
const { data } = await useAsyncData('projects', () =>
  $fetch('/api/projects', { query: { status: 'active' } })
)

// $fetch — for event handlers (not SSR, no caching)
async function deleteProject(id: string) {
  await $fetch(`/api/projects/${id}`, { method: 'DELETE' })
  refresh()  // Re-fetch the list
}

// IMPORTANT: useFetch/useAsyncData are for setup context only
// In event handlers, onClick etc., use $fetch
```

### Server Routes (Nitro)
```typescript
// server/api/projects/index.get.ts
export default defineEventHandler(async (event) => {
  const query = getQuery(event)       // Query params
  const body = await readBody(event)  // POST/PUT body
  const id = getRouterParam(event, 'id')  // Path params

  return { data: projects }  // Auto-serialized to JSON
})

// server/api/projects/[name].get.ts — dynamic params
export default defineEventHandler(async (event) => {
  const name = getRouterParam(event, 'name')
  // ...
})
```

### Middleware
```typescript
// middleware/auth.ts — runs on every route change
export default defineNuxtRouteMiddleware((to, from) => {
  const { authenticated } = useAuth()

  if (!authenticated.value && to.path !== '/login') {
    return navigateTo('/login')
  }
})

// Page-level middleware
definePageMeta({
  middleware: 'auth'
})
```

### Composables
```typescript
// composables/useProject.ts
export function useProject(name: MaybeRef<string>) {
  const projectName = toRef(name)

  const { data: project, pending, refresh } = useFetch(
    () => `/api/projects/${projectName.value}`
  )

  const isActive = computed(() =>
    project.value?.status === 'running'
  )

  async function archive() {
    await $fetch(`/api/projects/${projectName.value}/archive`, {
      method: 'POST'
    })
    await refresh()
  }

  return {
    project,
    pending,
    isActive,
    archive,
    refresh,
  }
}
```

### Runtime Config
```typescript
// nuxt.config.ts
export default defineNuxtConfig({
  runtimeConfig: {
    // Server-only (never exposed to client)
    secretKey: process.env.SECRET_KEY,

    // Client-accessible
    public: {
      apiBase: process.env.API_BASE || '/api',
    }
  }
})

// In server code
const config = useRuntimeConfig()
config.secretKey  // Server-only value

// In client code
const config = useRuntimeConfig()
config.public.apiBase  // Public value only
```

## Performance Patterns

### Lazy Components
```vue
<!-- Only load when visible -->
<LazyHeavyChart v-if="showChart" :data="chartData" />
```

### Conditional Rendering
```vue
<!-- v-show for frequent toggling (keeps DOM, toggles display) -->
<Panel v-show="isOpen" />

<!-- v-if for rare toggling (adds/removes DOM) -->
<AdminTools v-if="isAdmin" />
```

### List Rendering
```vue
<!-- Always use :key with unique identifier, NEVER use index -->
<div v-for="item in items" :key="item.id">
  {{ item.name }}
</div>
```

### Avoid Unnecessary Reactivity
```typescript
// Static data doesn't need ref/reactive
const COLUMNS = ['Name', 'Status', 'Date']  // Plain const is fine
const API_BASE = '/api/v1'                   // Not reactive

// Only wrap in ref what actually changes
const selectedColumn = ref(COLUMNS[0])
```

## Quality Checklist

- [ ] All components use `<script setup lang="ts">`
- [ ] Props and emits are typed with TypeScript generics
- [ ] No Options API usage (data, methods, computed as options)
- [ ] Reactive state uses ref() (not reactive() unless needed)
- [ ] No destructuring of reactive objects without toRef/toRefs
- [ ] useFetch/useAsyncData for data loading (not raw fetch in setup)
- [ ] $fetch used in event handlers, not useFetch
- [ ] List rendering uses :key with unique IDs (not array index)
- [ ] Scoped styles on components
- [ ] Composables extract reusable logic (not massive components)
- [ ] Server routes validate all inputs
- [ ] No direct prop mutation

## Anti-Patterns

- Using Options API (`data()`, `methods:`, `computed:` as object)
- Calling useFetch inside onClick handlers (use $fetch instead)
- Mutating props directly instead of emitting events
- Using array index as :key in v-for
- Putting business logic in components instead of composables
- Using reactive() and then destructuring it (kills reactivity)
- Importing Vue utilities that Nuxt auto-imports (ref, computed, watch, etc.)
- Using window/document without checking for SSR (`if (process.client)`)
- Deep watchers on large objects (prefer specific property watches)
- Creating refs for values that never change
