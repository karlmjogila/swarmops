---
name: accessibility
description: >
  Build inclusive web interfaces that work for everyone, regardless of ability.
  Covers WCAG 2.2 AA compliance, ARIA attributes, keyboard navigation, screen reader
  support, color contrast, focus management, semantic HTML, motion sensitivity,
  cognitive accessibility, inclusive design, and automated a11y testing in CI
  (axe-core, Playwright, Lighthouse, eslint-plugin-vuejs-accessibility).
  Tech stack: Nuxt, Vue 3, TypeScript.
triggers:
  - accessibility
  - a11y
  - aria
  - screen reader
  - keyboard navigation
  - wcag
  - contrast
  - focus
  - tab order
  - assistive
  - axe
  - lighthouse
  - reduced motion
  - cognitive
---

# Accessibility Excellence

Accessibility is not a feature to add later — it is a quality of well-built software. 1 in 4 adults has a disability. Build for everyone from the start.

## Core Principles (POUR)

1. **Perceivable** — Information must be presentable in ways all users can perceive.
2. **Operable** — All functionality must work via keyboard, not just mouse.
3. **Understandable** — Content and UI behavior must be predictable and readable.
4. **Robust** — Content must work with current and future assistive technologies.

## Semantic HTML — The Foundation

Semantic HTML gives you 80% of accessibility for free. Use the right elements.

```html
<!-- GOOD — semantic, accessible by default -->
<header>
  <nav aria-label="Main navigation">
    <ul><li><a href="/projects">Projects</a></li></ul>
  </nav>
</header>
<main>
  <h1>Dashboard</h1>
  <section aria-labelledby="active-heading">
    <h2 id="active-heading">Active Projects</h2>
  </section>
</main>
<footer>...</footer>

<!-- BAD — div soup, no semantics -->
<div class="header"><div class="nav-item" onclick="goto('/projects')">Projects</div></div>
```

### Element Selection Guide
```
Navigation  -> <nav>            Buttons   -> <button> (not <div onclick>)
Main        -> <main>           Links     -> <a href> (not <span onclick>)
Sections    -> <section>        Forms     -> <form>, <label>, <fieldset>, <legend>
Headings    -> <h1>-<h6>        Tables    -> <table>, <th scope="col/row">
Lists       -> <ul>/<ol>/<li>   Images    -> <img alt="description">
```

## Keyboard Navigation

### Focus Management
```css
/* GOOD — custom focus styles; NEVER remove outlines without replacement */
:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
:focus:not(:focus-visible) { outline: none; }
```

### Tab Order
```html
<!-- tabindex="0" makes non-interactive elements focusable -->
<div role="button" tabindex="0" @keydown.enter="handleClick" @click="handleClick">Custom Button</div>
<!-- tabindex="-1" for programmatic focus only (not in tab order) -->
<div ref="errorMessage" tabindex="-1" role="alert">Something went wrong</div>
<!-- NEVER use tabindex > 0 -->
```

### Keyboard Patterns
```typescript
function handleKeydown(event: KeyboardEvent) {
  switch (event.key) {
    case 'Enter': case ' ': event.preventDefault(); handleAction(); break
    case 'Escape': closeModal(); break
    case 'ArrowDown': event.preventDefault(); focusNextItem(); break
    case 'ArrowUp': event.preventDefault(); focusPreviousItem(); break
  }
}
```

### Focus Trapping (Modals/Dialogs)
```typescript
function trapFocus(container: HTMLElement) {
  const focusable = container.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )
  const first = focusable[0], last = focusable[focusable.length - 1]

  container.addEventListener('keydown', (e) => {
    if (e.key !== 'Tab') return
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
  })
  first.focus()
}
// When modal closes, return focus to the trigger element
function closeModal(triggerElement: HTMLElement) { modal.close(); triggerElement.focus() }
```

## ARIA — Use Sparingly and Correctly

First rule: **do not use ARIA if native HTML works**.

### Common ARIA Patterns
```html
<!-- Live regions --> <div aria-live="polite" aria-atomic="true">{{ statusMessage }}</div>
<!-- Loading -->      <div aria-busy="true" aria-live="polite">Loading projects...</div>
<!-- Expand/collapse -->
<button aria-expanded="false" aria-controls="panel-1" @click="toggle">Show Details</button>
<div id="panel-1" role="region" :hidden="!isExpanded">Content here</div>
<!-- Error messages -->
<input id="email" type="email" aria-invalid="true" aria-describedby="email-error" />
<div id="email-error" role="alert">Please enter a valid email address</div>
<!-- Progress -->
<div role="progressbar" aria-valuenow="60" aria-valuemin="0" aria-valuemax="100" aria-label="Build progress">60%</div>
```

### ARIA Roles for Custom Widgets
```html
<!-- Tabs -->
<div role="tablist" aria-label="Project phases">
  <button role="tab" aria-selected="true" aria-controls="panel-build" id="tab-build">Build</button>
  <button role="tab" aria-selected="false" aria-controls="panel-review" id="tab-review">Review</button>
</div>
<div role="tabpanel" id="panel-build" aria-labelledby="tab-build">Build content</div>
<!-- Menu -->
<button aria-haspopup="true" aria-expanded="false" id="menu-trigger">Actions</button>
<ul role="menu" aria-labelledby="menu-trigger">
  <li role="menuitem">Edit</li>
  <li role="menuitem">Delete</li>
</ul>
```

## Advanced ARIA Patterns

### Combobox / Autocomplete
```vue
<template>
  <label id="search-label" for="search-input">Search projects</label>
  <div role="combobox" :aria-expanded="open" aria-haspopup="listbox" aria-owns="search-listbox">
    <input id="search-input" type="text" aria-autocomplete="list"
      aria-controls="search-listbox" :aria-activedescendant="activeId" @keydown="onKeydown" />
  </div>
  <ul v-show="open" id="search-listbox" role="listbox">
    <li v-for="(item, i) in results" :key="item.id" :id="`opt-${item.id}`"
      role="option" :aria-selected="i === activeIndex" @click="select(item)">{{ item.name }}</li>
  </ul>
  <div aria-live="polite" class="sr-only">{{ results.length }} results available.</div>
</template>
<script setup lang="ts">
const activeIndex = ref(-1)
const activeId = computed(() =>
  activeIndex.value >= 0 ? `opt-${results.value[activeIndex.value]?.id}` : undefined)
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowDown') { e.preventDefault(); activeIndex.value = Math.min(activeIndex.value + 1, results.value.length - 1) }
  else if (e.key === 'ArrowUp') { e.preventDefault(); activeIndex.value = Math.max(activeIndex.value - 1, 0) }
  else if (e.key === 'Enter' && activeIndex.value >= 0) select(results.value[activeIndex.value])
  else if (e.key === 'Escape') open.value = false
}
</script>
```

### Tree View
```vue
<!-- TreeNode.vue — recursive component -->
<template>
  <li role="treeitem" :aria-expanded="node.children ? expanded : undefined"
    :aria-level="level" :tabindex="isFocused ? 0 : -1" @keydown="handleKeydown">
    <span @click="toggle">{{ node.label }}</span>
    <ul v-if="node.children && expanded" role="group">
      <TreeNode v-for="child in node.children" :key="child.id" :node="child" :level="level + 1" />
    </ul>
  </li>
</template>
<script setup lang="ts">
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowRight') { if (!expanded.value) expanded.value = true; else focusFirstChild() }
  else if (e.key === 'ArrowLeft') { if (expanded.value) expanded.value = false; else focusParent() }
  else if (e.key === 'ArrowDown') focusNextVisible()
  else if (e.key === 'ArrowUp') focusPreviousVisible()
  else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle() }
}
</script>
```

### Data Grid with Sortable Columns
```vue
<template>
  <table role="grid" aria-label="Project list">
    <thead><tr>
      <th v-for="col in columns" :key="col.key" scope="col"
        :aria-sort="sortKey === col.key ? sortDir : 'none'">
        <button @click="sortBy(col.key)">{{ col.label }}</button>
      </th>
    </tr></thead>
    <tbody>
      <tr v-for="row in sortedRows" :key="row.id">
        <td v-for="col in columns" :key="col.key" role="gridcell">{{ row[col.key] }}</td>
      </tr>
    </tbody>
  </table>
  <div aria-live="polite" class="sr-only">Sorted by {{ sortLabel }}, {{ sortDir }}.</div>
</template>
<script setup lang="ts">
const sortDir = ref<'ascending' | 'descending'>('ascending')
function sortBy(key: string) {
  if (sortKey.value === key) sortDir.value = sortDir.value === 'ascending' ? 'descending' : 'ascending'
  else { sortKey.value = key; sortDir.value = 'ascending' }
}
</script>
```

## Color & Contrast

```
Normal text (< 18px):                 4.5:1 contrast ratio minimum
Large text (>= 18px bold / >= 24px):  3:1 minimum
UI components & graphics:             3:1 minimum
```
```css
:root {
  --text-primary: hsl(220, 25%, 12%);   /* 15:1 on light bg */
  --text-secondary: hsl(220, 15%, 40%); /* 5.5:1 on light bg */
  --color-error: hsl(0, 70%, 40%);      /* dark enough for text */
  --color-success: hsl(140, 60%, 30%);
}
/* Never rely on color alone — add icon/text */
.status-active { color: var(--color-success); }
.status-active::before { content: "\2713 "; }
.status-error { color: var(--color-error); }
.status-error::before { content: "\2717 "; }
```

## Images & Media

```html
<img src="chart.png" alt="Build progress: 7 of 10 tasks complete, 70% done" />
<img src="divider.svg" alt="" role="presentation" />   <!-- decorative -->
<figure>
  <img src="arch.png" alt="System architecture diagram" aria-describedby="arch-desc" />
  <figcaption id="arch-desc">Three layers: Vue/Nuxt frontend, Nitro server, Claude agents.</figcaption>
</figure>
<button aria-label="Delete project"><TrashIcon aria-hidden="true" /></button>
```

## Forms

```html
<form @submit.prevent="handleSubmit">
  <label for="project-name">Project Name</label>
  <input id="project-name" type="text" required aria-required="true"
    :aria-invalid="!!errors.name" :aria-describedby="errors.name ? 'name-error' : undefined" />
  <div v-if="errors.name" id="name-error" role="alert" class="error">{{ errors.name }}</div>

  <fieldset>
    <legend>Project Settings</legend>
    <input type="checkbox" id="auto-review" />
    <label for="auto-review">Enable automatic code review</label>
  </fieldset>

  <button type="submit" :disabled="submitting" :aria-busy="submitting">
    {{ submitting ? 'Creating...' : 'Create Project' }}
  </button>
</form>
```

## Motion Sensitivity

Respect OS preferences and provide manual controls for users who experience nausea or seizures from animation.

### prefers-reduced-motion
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

### Safe Animation Patterns in Vue
```vue
<template>
  <Transition :name="motionSafe ? 'slide-fade' : 'instant'">
    <div v-if="visible" class="panel">Content</div>
  </Transition>
</template>
<script setup lang="ts">
function useMotionPreference(): Ref<boolean> {
  const safe = ref(true)
  if (typeof window !== 'undefined') {
    const mql = window.matchMedia('(prefers-reduced-motion: reduce)')
    safe.value = !mql.matches
    mql.addEventListener('change', (e) => { safe.value = !e.matches })
  }
  return safe
}
const motionSafe = useMotionPreference()
</script>
<style scoped>
.slide-fade-enter-active, .slide-fade-leave-active { transition: transform 0.3s ease, opacity 0.3s ease; }
.slide-fade-enter-from { opacity: 0; transform: translateY(10px); }
.slide-fade-leave-to   { opacity: 0; transform: translateY(-10px); }
.instant-enter-active, .instant-leave-active { transition: none; }
</style>
```

### Motion Toggle Control
```vue
<template>
  <button @click="toggleMotion" :aria-pressed="String(motionEnabled)">
    {{ motionEnabled ? 'Disable animations' : 'Enable animations' }}
  </button>
</template>
<script setup lang="ts">
const motionEnabled = useState('motion-enabled', () =>
  typeof window === 'undefined' ? true : !window.matchMedia('(prefers-reduced-motion: reduce)').matches)
function toggleMotion() {
  motionEnabled.value = !motionEnabled.value
  document.documentElement.classList.toggle('reduce-motion', !motionEnabled.value)
}
</script>
```

## Inclusive Design

### Motor Impairment Patterns
```css
/* WCAG 2.2 Target Size: minimum 44x44px for interactive elements */
button, a, [role="button"] { min-height: 44px; min-width: 44px; }
.action-bar button + button { margin-left: 8px; } /* adequate spacing */
```
```vue
<!-- Drag interactions MUST have keyboard/button alternatives -->
<template>
  <ul role="list" aria-label="Task list">
    <li v-for="(task, i) in tasks" :key="task.id">
      {{ task.name }}
      <button :aria-label="`Move ${task.name} up`" :disabled="i === 0" @click="moveUp(i)">Up</button>
      <button :aria-label="`Move ${task.name} down`" :disabled="i === tasks.length - 1" @click="moveDown(i)">Down</button>
    </li>
  </ul>
</template>
```

### Cognitive Accessibility
```
- Use plain language; avoid jargon unless defined
- Keep sentences short (< 25 words)
- Consistent navigation across all pages
- Group related actions; separate destructive from constructive
- Show progress indicators for multi-step flows
- Provide undo instead of "Are you sure?" dialogs
- Never auto-advance timed content without user control
```
```vue
<!-- Multi-step wizard with visible progress -->
<nav aria-label="Form progress">
  <ol>
    <li v-for="(step, i) in steps" :key="step.id" :aria-current="i === current ? 'step' : undefined">
      {{ step.label }}
    </li>
  </ol>
</nav>
<p>Step {{ current + 1 }} of {{ steps.length }}: {{ steps[current].label }}</p>
```

### Internationalization Considerations
```html
<html lang="en" dir="ltr">
<p>The project name is <span lang="fr">Architecte</span>.</p>
<style>
/* Use logical properties for RTL support */
.sidebar { margin-inline-start: 1rem; padding-inline-end: 0.5rem; }
</style>
```

## Testing Accessibility

### TDD: Write the Assertion First
```typescript
// Step 1: Write the FAILING test before building the component
import { mount } from '@vue/test-utils'
import { axe, toHaveNoViolations } from 'vitest-axe'
expect.extend(toHaveNoViolations)

describe('ProjectCard', () => {
  it('has no accessibility violations', async () => {
    const wrapper = mount(ProjectCard, { props: { name: 'SwarmOps', status: 'active' } })
    expect(await axe(wrapper.element)).toHaveNoViolations()
  })
  it('announces status to screen readers', () => {
    const wrapper = mount(ProjectCard, { props: { name: 'SwarmOps', status: 'error' } })
    expect(wrapper.find('[role="status"]').text()).toContain('error')
  })
})
// Step 2: Build the component to make the test pass
// Step 3: Refactor while keeping tests green
```

### Reusable axe Helper for Vitest
```typescript
// test/utils/a11y.ts
import { axe, toHaveNoViolations } from 'vitest-axe'
import type { VueWrapper } from '@vue/test-utils'
expect.extend(toHaveNoViolations)

export async function expectAccessible(wrapper: VueWrapper) {
  const results = await axe(wrapper.element, { rules: { region: { enabled: false } } })
  expect(results).toHaveNoViolations()
}

// Usage: await expectAccessible(mount(LoginForm))
```

### Playwright Accessibility Tests
```typescript
// e2e/accessibility.spec.ts
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('dashboard has no a11y violations', async ({ page }) => {
  await page.goto('/dashboard')
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag22aa'])
    .analyze()
  expect(results.violations).toEqual([])
})

test('modal traps focus', async ({ page }) => {
  await page.goto('/projects')
  await page.getByRole('button', { name: 'New project' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  for (let i = 0; i < 20; i++) await page.keyboard.press('Tab')
  expect(await page.locator(':focus').evaluate(
    (el) => el.closest('[role="dialog"]') !== null)).toBe(true)
})
```

### Lighthouse CI Integration
```yaml
# .github/workflows/lighthouse.yml
name: Lighthouse CI
on: [pull_request]
jobs:
  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci && npm run build
      - uses: treosh/lighthouse-ci-action@v12
        with: { uploadArtifacts: true, configPath: ./lighthouserc.json }
```
```json
{
  "ci": {
    "assert": {
      "assertions": {
        "categories:accessibility": ["error", { "minScore": 0.95 }],
        "color-contrast": "error", "heading-order": "error",
        "image-alt": "error", "label": "error", "button-name": "error"
      }
    },
    "collect": {
      "startServerCommand": "npm run preview",
      "url": ["http://localhost:3000/", "http://localhost:3000/projects"]
    }
  }
}
```

### eslint-plugin-vuejs-accessibility
```javascript
// eslint.config.mjs
import pluginVueA11y from 'eslint-plugin-vuejs-accessibility'
export default [
  ...pluginVueA11y.configs['flat/recommended'],
  { rules: {
    'vuejs-accessibility/alt-text': 'error',
    'vuejs-accessibility/click-events-have-key-events': 'error',
    'vuejs-accessibility/form-control-has-label': 'error',
    'vuejs-accessibility/label-has-for': 'error',
    'vuejs-accessibility/mouse-events-have-key-events': 'error',
    'vuejs-accessibility/no-autofocus': 'warn',
    'vuejs-accessibility/tabindex-no-positive': 'error',
  }},
]
```

### Manual Testing Checklist
```
1. Tab through entire page — can you reach everything?
2. Enter/Space on every interactive element
3. Escape to close modals/dropdowns
4. Arrow keys in menus/tabs/lists
5. Zoom to 200% — still usable?
6. Turn off CSS — content still makes sense?
7. Screen reader (VoiceOver/NVDA) — coherent experience?
8. Enable prefers-reduced-motion — animations stop?
9. Voice control — all targets labeled?
```

## Quality Checklist

- [ ] All interactive elements keyboard-accessible
- [ ] Focus visible on all focusable elements
- [ ] Heading hierarchy correct (h1 > h2 > h3, no skipping)
- [ ] All images have appropriate alt text
- [ ] Color contrast meets WCAG AA (4.5:1 text, 3:1 UI)
- [ ] Information not conveyed by color alone
- [ ] Form inputs have associated labels
- [ ] Error messages linked via aria-describedby
- [ ] Dynamic content announced via aria-live regions
- [ ] Modals trap focus and return focus on close
- [ ] No keyboard traps
- [ ] Page has single h1 and landmarks (main, nav, footer)
- [ ] Touch/click targets at least 44x44px
- [ ] Animations respect prefers-reduced-motion
- [ ] eslint-plugin-vuejs-accessibility passing
- [ ] axe-core tests pass in CI
- [ ] Lighthouse accessibility score >= 95

## Anti-Patterns

- Removing :focus outlines without visible replacement
- Using div/span for buttons and links
- Hover-only interactions with no keyboard equivalent
- Placeholder as the only label for inputs
- Auto-playing media without user control
- Moving focus unexpectedly
- tabindex > 0 (breaks natural tab order)
- ARIA overload on elements that already have semantics
- "Click here" link text
- Disabled buttons with no explanation
- Animations that cannot be paused or disabled
- Drag-only interactions with no keyboard alternative
- Click targets below 44x44px
- Time limits without extension or override
