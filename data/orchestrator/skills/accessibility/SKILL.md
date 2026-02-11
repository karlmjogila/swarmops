---
name: accessibility
description: >
  Build inclusive web interfaces that work for everyone, regardless of ability.
  Covers WCAG 2.1 AA compliance, ARIA attributes, keyboard navigation, screen reader
  support, color contrast, focus management, and semantic HTML. Trigger this skill
  for any task involving accessibility, a11y, ARIA, screen readers, keyboard navigation,
  or inclusive design. Also trigger for UI components that need to be accessible.
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
---

# Accessibility Excellence

Accessibility is not a feature to add later — it's a quality of well-built software. 1 in 4 adults has a disability. Build for everyone from the start, and you'll build better software for everyone.

## Core Principles

1. **Perceivable** — Information must be presentable in ways all users can perceive (not just visually).
2. **Operable** — All functionality must work via keyboard, not just mouse.
3. **Understandable** — Content and UI behavior must be predictable and readable.
4. **Robust** — Content must work with current and future assistive technologies.

## Semantic HTML — The Foundation

Semantic HTML gives you 80% of accessibility for free. Use the right elements.

```html
<!-- GOOD — semantic, accessible by default -->
<header>
  <nav aria-label="Main navigation">
    <ul>
      <li><a href="/projects">Projects</a></li>
      <li><a href="/settings">Settings</a></li>
    </ul>
  </nav>
</header>

<main>
  <h1>Dashboard</h1>
  <section aria-labelledby="active-heading">
    <h2 id="active-heading">Active Projects</h2>
    <ul>
      <li>...</li>
    </ul>
  </section>
</main>

<footer>...</footer>

<!-- BAD — div soup, no semantics -->
<div class="header">
  <div class="nav">
    <div class="nav-item" onclick="goto('/projects')">Projects</div>
  </div>
</div>
<div class="content">
  <div class="title">Dashboard</div>
</div>
```

### Element Selection Guide
```
Navigation     → <nav>
Main content   → <main> (one per page)
Sections       → <section> with aria-labelledby
Headings       → <h1>-<h6> in order (never skip levels)
Lists          → <ul>/<ol>/<li>
Buttons        → <button> (not <div onclick>)
Links          → <a href="..."> (not <span onclick>)
Forms          → <form>, <label>, <input>, <fieldset>, <legend>
Tables         → <table>, <thead>, <tbody>, <th scope="col/row">
Images         → <img alt="description">
Time           → <time datetime="2024-01-15">
```

## Keyboard Navigation

Every interactive element must be keyboard-accessible.

### Focus Management
```css
/* NEVER remove focus outlines without replacement */
/* BAD */
*:focus { outline: none; }

/* GOOD — custom focus styles */
:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: 2px;
}

/* Hide focus ring for mouse users, show for keyboard */
:focus:not(:focus-visible) {
  outline: none;
}
```

### Tab Order
```html
<!-- Natural tab order follows DOM order — arrange HTML logically -->

<!-- Use tabindex="0" to make non-interactive elements focusable (when needed) -->
<div role="button" tabindex="0" @keydown.enter="handleClick" @click="handleClick">
  Custom Button
</div>

<!-- tabindex="-1" for programmatic focus (not in tab order) -->
<div ref="errorMessage" tabindex="-1" role="alert">
  Something went wrong
</div>

<!-- NEVER use tabindex > 0 — it breaks natural flow -->
```

### Keyboard Patterns
```typescript
// All click handlers need keyboard equivalents
function handleKeydown(event: KeyboardEvent) {
  switch (event.key) {
    case 'Enter':
    case ' ':
      event.preventDefault()
      handleAction()
      break
    case 'Escape':
      closeModal()
      break
    case 'ArrowDown':
      event.preventDefault()
      focusNextItem()
      break
    case 'ArrowUp':
      event.preventDefault()
      focusPreviousItem()
      break
  }
}
```

### Focus Trapping (Modals/Dialogs)
```typescript
// When a modal opens, trap focus inside it
function trapFocus(container: HTMLElement) {
  const focusable = container.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )
  const first = focusable[0] as HTMLElement
  const last = focusable[focusable.length - 1] as HTMLElement

  container.addEventListener('keydown', (e) => {
    if (e.key !== 'Tab') return

    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault()
        last.focus()
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
  })

  first.focus()
}

// When modal closes, return focus to the trigger element
function closeModal(triggerElement: HTMLElement) {
  modal.close()
  triggerElement.focus()
}
```

## ARIA — Use Sparingly and Correctly

ARIA is a repair tool for when HTML semantics aren't enough. First rule: **don't use ARIA if native HTML works**.

### Common ARIA Patterns
```html
<!-- Live regions — announce dynamic content to screen readers -->
<div aria-live="polite" aria-atomic="true">
  {{ statusMessage }}
</div>

<!-- Loading states -->
<div aria-busy="true" aria-live="polite">
  Loading projects...
</div>

<!-- Expanded/collapsed -->
<button aria-expanded="false" aria-controls="panel-1" @click="toggle">
  Show Details
</button>
<div id="panel-1" role="region" :hidden="!isExpanded">
  Content here
</div>

<!-- Required form fields -->
<label for="email">Email <span aria-hidden="true">*</span></label>
<input id="email" type="email" required aria-required="true" />

<!-- Error messages -->
<input id="email" type="email" aria-invalid="true" aria-describedby="email-error" />
<div id="email-error" role="alert">Please enter a valid email address</div>

<!-- Progress -->
<div role="progressbar" aria-valuenow="60" aria-valuemin="0" aria-valuemax="100"
     aria-label="Build progress">
  60%
</div>
```

### ARIA Roles for Custom Widgets
```html
<!-- Tabs -->
<div role="tablist" aria-label="Project phases">
  <button role="tab" aria-selected="true" aria-controls="panel-build" id="tab-build">
    Build
  </button>
  <button role="tab" aria-selected="false" aria-controls="panel-review" id="tab-review">
    Review
  </button>
</div>
<div role="tabpanel" id="panel-build" aria-labelledby="tab-build">
  Build content
</div>

<!-- Menu -->
<button aria-haspopup="true" aria-expanded="false" id="menu-trigger">
  Actions
</button>
<ul role="menu" aria-labelledby="menu-trigger">
  <li role="menuitem">Edit</li>
  <li role="menuitem">Delete</li>
</ul>
```

## Color & Contrast

### WCAG AA Requirements
```
Normal text (< 18px):     4.5:1 contrast ratio minimum
Large text (>= 18px bold or >= 24px):  3:1 minimum
UI components & graphics:  3:1 minimum
```

### Implementation
```css
/* Define accessible color pairs */
:root {
  --text-primary: hsl(220, 25%, 12%);      /* On light bg: 15:1 ratio */
  --text-secondary: hsl(220, 15%, 40%);     /* On light bg: 5.5:1 ratio */
  --bg-surface: hsl(220, 20%, 97%);

  /* Error/success colors must also meet contrast */
  --color-error: hsl(0, 70%, 40%);          /* Not bright red — too low contrast */
  --color-success: hsl(140, 60%, 30%);      /* Dark enough for text */
}

/* Never rely on color alone to convey information */
/* BAD — colorblind users can't distinguish */
.status-active { color: green; }
.status-error { color: red; }

/* GOOD — color + icon/text */
.status-active { color: var(--color-success); }
.status-active::before { content: "✓ "; }
.status-error { color: var(--color-error); }
.status-error::before { content: "✗ "; }
```

## Images & Media

```html
<!-- Informative images: descriptive alt text -->
<img src="chart.png" alt="Build progress: 7 of 10 tasks complete, 70% done" />

<!-- Decorative images: empty alt -->
<img src="divider.svg" alt="" role="presentation" />

<!-- Complex images: longer description -->
<figure>
  <img src="architecture.png" alt="System architecture diagram" aria-describedby="arch-desc" />
  <figcaption id="arch-desc">
    The system consists of three layers: the dashboard frontend (Vue/Nuxt),
    the orchestration server (Nitro), and the worker agents (Claude sessions).
  </figcaption>
</figure>

<!-- Icons with meaning need labels -->
<button aria-label="Delete project">
  <TrashIcon aria-hidden="true" />
</button>

<!-- Decorative icons should be hidden -->
<span aria-hidden="true">🚀</span> Deploying...
```

## Forms

```html
<form @submit.prevent="handleSubmit">
  <!-- Every input needs a label -->
  <div>
    <label for="project-name">Project Name</label>
    <input
      id="project-name"
      type="text"
      required
      aria-required="true"
      :aria-invalid="!!errors.name"
      :aria-describedby="errors.name ? 'name-error' : undefined"
    />
    <div v-if="errors.name" id="name-error" role="alert" class="error">
      {{ errors.name }}
    </div>
  </div>

  <!-- Group related fields -->
  <fieldset>
    <legend>Project Settings</legend>
    <div>
      <input type="checkbox" id="auto-review" />
      <label for="auto-review">Enable automatic code review</label>
    </div>
  </fieldset>

  <!-- Submit button with loading state -->
  <button type="submit" :disabled="submitting" :aria-busy="submitting">
    {{ submitting ? 'Creating...' : 'Create Project' }}
  </button>
</form>
```

## Testing Accessibility

### Automated Checks
```typescript
// Use axe-core in tests
import { axe } from 'vitest-axe'

it('has no accessibility violations', async () => {
  const wrapper = mount(ProjectCard, { props: { ... } })
  const results = await axe(wrapper.element)
  expect(results.violations).toHaveLength(0)
})
```

### Manual Testing Checklist
```
1. Tab through the entire page — can you reach everything?
2. Use Enter/Space on every interactive element
3. Use Escape to close modals/dropdowns
4. Use arrow keys in menus/tabs/lists
5. Zoom to 200% — is everything still usable?
6. Turn off CSS — does the content still make sense?
7. Use a screen reader (VoiceOver/NVDA) — is the experience coherent?
```

## Quality Checklist

- [ ] All interactive elements keyboard-accessible
- [ ] Focus visible on all focusable elements
- [ ] Heading hierarchy correct (h1 → h2 → h3, no skipping)
- [ ] All images have appropriate alt text
- [ ] Color contrast meets WCAG AA (4.5:1 text, 3:1 UI)
- [ ] Information not conveyed by color alone
- [ ] Form inputs have associated labels
- [ ] Error messages linked to inputs via aria-describedby
- [ ] Dynamic content announced via aria-live regions
- [ ] Modal dialogs trap focus and return focus on close
- [ ] No keyboard traps (user can always tab away)
- [ ] Page has a single h1 and landmarks (main, nav, footer)

## Anti-Patterns

- Removing :focus outlines without visible replacement
- Using div/span for buttons and links
- Relying on hover-only interactions (no keyboard equivalent)
- Using placeholder as the only label for inputs
- Auto-playing media without user control
- Moving focus unexpectedly (focus should follow user intent)
- Using tabindex > 0 (breaks natural tab order)
- ARIA overload — adding roles/attributes to elements that already have semantics
- "Click here" link text (screen readers read links out of context)
- Disabled buttons with no explanation of why they're disabled
