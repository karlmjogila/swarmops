---
name: web-visuals
description: >
  Generate emotionally resonant, production-grade web pages and interfaces with
  extraordinary visual beauty. Trigger this skill when the user says "start building" a web page,
  landing page, portfolio, app UI, or any web interface where visual excellence is the primary goal.
  Also trigger on phrases like "make it beautiful", "stunning visuals", "make it look amazing",
  "gorgeous web page", or any request emphasizing visual quality of a web deliverable.
  This skill produces Nuxt/Vue/HTML artifacts with handcrafted aesthetics using Tailwind CSS
  that feel human-made, emotionally engaging, and visually unforgettable. Do NOT use for
  purely functional tools, CLIs, data scripts, or non-visual tasks.
triggers:
  - visual
  - beautiful
  - landing page
  - web design
  - ui design
  - stunning
  - gorgeous
  - responsive
  - container query
  - web performance
  - lighthouse
---

# Beautiful Web Visuals

Create web pages that make people *feel* something -- pages so beautiful they pause scrolling, lean in, and remember. Production quality at the level of Stripe, Linear, Vercel, Apple -- not generic templates.

Tech stack: **Nuxt 3, TypeScript, Tailwind CSS**.

## Philosophy

Every beautiful interface has three invisible layers:

1. **Emotional texture** -- warmth, trust, delight, wonder, calm, energy. Choose one feeling and commit.
2. **Obsessive craft** -- the 1px shadow, the 40ms ease, the letter-spacing that makes a heading sing. Details nobody notices consciously but everyone *feels*.
3. **Narrative rhythm** -- a page is a story with a hook, rising tension, rest, and a satisfying ending. Scroll should feel like turning pages of a beautiful book.

## Before Writing Any Code

Pause. State these decisions explicitly:

### 1. Emotional Target
Pick ONE dominant emotion: wonder, calm confidence, playful energy, sophisticated warmth, raw power, dreamy softness, crisp precision, organic warmth. Name it. Every choice flows from this.

### 2. Visual Identity

**Color Strategy** -- A signature color (one hue that owns the page). A spatial color system (layered backgrounds, gradient fog, glowing accents). Light behavior (above? behind? ambient? directional?). Never use flat white (#fff) -- use warm off-whites (hsl(40,20%,97%)) or cool grays (hsl(220,15%,96%)).

**Typography as Voice** -- A display font with REAL personality (Playfair Display, Fraunces, Instrument Serif, Clash Display, Cabinet Grotesk, Satoshi, Sora, Plus Jakarta Sans). NEVER Inter/Roboto/Arial as display. A body font that complements. Hero text enormous (clamp(3rem, 8vw, 7rem)), body comfortable (18-20px), generous line-height (1.6-1.8).

**Spatial Design** -- Generous padding (80-120px vertical sections). Asymmetric layouts that feel composed. Strategic overlap and layering. Negative space is a design element.

**Depth & Atmosphere** -- Layered backgrounds (stacked gradients, mesh gradients, noise textures). Multi-layer colored shadows. Glassmorphism, grain, blur with restraint.

### 3. Motion Philosophy
- **Page entrance**: Staggered reveals (animation-delay: 0.1s increments). Fade + translate(20px) baseline; better with scale, blur-to-sharp, or clip-path.
- **Scroll-driven**: Intersection Observer or VueUse `useIntersectionObserver`. Elements *arrive*, not just appear.
- **Micro-interactions**: Hover scale (1.02-1.05), color shifts, shadow lifts. Buttons feel pressable (translateY, deeper shadow).
- **Timing**: cubic-bezier(0.16, 1, 0.3, 1). 300-600ms reveals, 150-250ms hovers. CSS-first always.

### 4. The "One Thing"
What single visual moment will someone screenshot and share? Design it first, build around it.

## Implementation Standards

### CSS Craft
```css
:root {
  --color-surface: hsl(220, 20%, 97%);
  --color-surface-elevated: hsl(0, 0%, 100%);
  --color-accent: hsl(250, 75%, 60%);
  --color-accent-glow: hsl(250, 75%, 60%, 0.15);
  --color-text-primary: hsl(220, 25%, 12%);
  --color-text-secondary: hsl(220, 15%, 45%);
  --space-xs: 0.5rem; --space-sm: 1rem; --space-md: 2rem;
  --space-lg: 4rem; --space-xl: 8rem; --space-2xl: 12rem;
  --font-display: 'Your Display Font', serif;
  --font-body: 'Your Body Font', sans-serif;
  --shadow-sm: 0 1px 2px hsl(220 20% 20% / 0.04), 0 1px 3px hsl(220 20% 20% / 0.06);
  --shadow-md: 0 4px 6px hsl(220 20% 20% / 0.04), 0 8px 20px hsl(220 20% 20% / 0.06);
  --shadow-lg: 0 8px 16px hsl(220 20% 20% / 0.04), 0 20px 50px hsl(220 20% 20% / 0.08);
  --shadow-glow: 0 0 30px var(--color-accent-glow);
}
html { scroll-behavior: smooth; }
body { -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; }
```

Wire into `tailwind.config.ts`:
```ts
export default {
  theme: {
    extend: {
      colors: { surface: 'var(--color-surface)', accent: 'var(--color-accent)' },
      fontFamily: { display: ['var(--font-display)'], body: ['var(--font-body)'] },
      boxShadow: { glow: 'var(--shadow-glow)' },
    },
  },
}
```

### Visual Techniques Library

**Mesh gradient background:**
```css
.hero {
  background:
    radial-gradient(ellipse at 20% 50%, hsl(250 80% 65% / 0.15) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, hsl(330 70% 60% / 0.1) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 80%, hsl(200 80% 55% / 0.08) 0%, transparent 50%),
    var(--color-surface);
}
```

**SVG noise overlay:**
```html
<svg class="fixed inset-0 w-full h-full pointer-events-none z-[9999] opacity-[0.03]">
  <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="4" stitchTiles="stitch"/></filter>
  <rect width="100%" height="100%" filter="url(#grain)"/>
</svg>
```

**Staggered reveal:**
```css
.reveal { opacity: 0; transform: translateY(20px);
  transition: opacity 0.7s cubic-bezier(0.16,1,0.3,1), transform 0.7s cubic-bezier(0.16,1,0.3,1); }
.reveal.visible { opacity: 1; transform: translateY(0); }
```
```ts
// composables/useReveal.ts
export function useReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => entry.target.classList.add('visible'), i * 100)
        observer.unobserve(entry.target)
      }
    })
  }, { threshold: 0.1 })
  onMounted(() => document.querySelectorAll('.reveal').forEach(el => observer.observe(el)))
  onUnmounted(() => observer.disconnect())
}
```

**Glowing card borders:**
```css
.card { border: 1px solid hsl(250 60% 70% / 0.2);
  box-shadow: var(--shadow-md), inset 0 1px 0 hsl(0 0% 100% / 0.5);
  transition: box-shadow 0.3s ease, border-color 0.3s ease; }
.card:hover { border-color: hsl(250 60% 70% / 0.4);
  box-shadow: var(--shadow-lg), var(--shadow-glow); }
```

## Responsive Design

Mobile-first is not a suggestion -- it is the workflow. Start from the smallest screen, then enhance.

### Fluid Typography
```css
h1 { font-size: clamp(2.25rem, 5vw + 1rem, 5rem); }
h2 { font-size: clamp(1.5rem, 3vw + 0.5rem, 3rem); }
p  { font-size: clamp(1rem, 0.5vw + 0.875rem, 1.25rem); }
```
In Tailwind: `text-[clamp(2.25rem,5vw+1rem,5rem)]`.

### Breakpoints and Container Queries
Use Tailwind defaults (`sm:640`, `md:768`, `lg:1024`, `xl:1280`) but think in *content* breakpoints. Use container queries when a component must adapt to its container, not the viewport:
```css
.card-wrapper { container-type: inline-size; }
@container (min-width: 400px) { .card-inner { flex-direction: row; } }
@container (max-width: 399px) { .card-inner { flex-direction: column; } }
```

### Touch Targets and Fluid Spacing
All interactive elements: 44px minimum tap target. Section padding scales with viewport:
```vue
<template>
  <button class="min-h-[44px] min-w-[44px] px-6 py-3">Get Started</button>
</template>
```
```css
section { padding-block: clamp(3rem, 8vw, 8rem); padding-inline: clamp(1rem, 5vw, 4rem); }
```

## Accessibility Integration

Visual excellence and accessibility are complementary, never competing.

### Color Contrast (WCAG AA)
- Normal text (< 18pt): 4.5:1 ratio. Large text (>= 18pt bold): 3:1. UI components: 3:1.
- Never rely on color alone. Pair with icons, patterns, or text labels.

### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```
```ts
// composables/useReducedMotion.ts
export function useReducedMotion() {
  const prefersReduced = ref(false)
  onMounted(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    prefersReduced.value = mq.matches
    mq.addEventListener('change', (e) => { prefersReduced.value = e.matches })
  })
  return { prefersReduced }
}
```

### Screen Readers and Semantic HTML
Decorative elements: `aria-hidden="true"`. Meaningful images: descriptive `alt`. Icon buttons: `aria-label`. Use `sr-only` for visually hidden context. Visual layouts still need semantic structure:
```vue
<template>
  <main>
    <section aria-labelledby="hero-heading">
      <h1 id="hero-heading">Ship faster, sleep better</h1>
    </section>
    <section aria-labelledby="features-heading">
      <h2 id="features-heading">Features</h2>
      <ul role="list" class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <li v-for="f in features" :key="f.id"><article><h3>{{ f.title }}</h3></article></li>
      </ul>
    </section>
  </main>
</template>
```

## Asset Optimization

A beautiful page that loads in 8 seconds is an ugly page. Performance is a visual feature.

### Image Formats
WebP for photos (30-50% smaller than JPEG). AVIF where supported (50-70% smaller). SVG for icons/logos. Use `@nuxt/image`:
```vue
<NuxtImg src="/images/hero.jpg" format="avif,webp" sizes="100vw md:80vw lg:1200px"
  :placeholder="[20, 10, 75, 5]" alt="Abstract gradient landscape" loading="lazy" />
```
Never lazy-load the hero/LCP image -- use `loading="eager" fetchpriority="high"`.

### Font Loading
Preload critical fonts. Always use `font-display: swap`:
```ts
// nuxt.config.ts
export default defineNuxtConfig({
  app: {
    head: {
      link: [{ rel: 'preload', href: '/fonts/ClashDisplay-Bold.woff2',
        as: 'font', type: 'font/woff2', crossorigin: '' }],
    },
  },
})
```

### Critical CSS
Nuxt SSR handles critical CSS extraction automatically. Defer heavy visuals with `<ClientOnly>`:
```vue
<template>
  <HeroSection />
  <ClientOnly>
    <ParticleCanvas />
    <template #fallback>
      <div class="h-full bg-gradient-to-b from-accent/5 to-transparent" />
    </template>
  </ClientOnly>
</template>
```

## Nuxt/Vue Visual Patterns

### Component Architecture
```
components/
  landing/
    LandingHero.vue          # Hero with animation
    LandingFeatures.vue      # Feature grid
    LandingCTA.vue           # Call to action
  ui/
    GradientBlob.vue         # Reusable decorative gradient
    GlowCard.vue             # Card with hover glow
    TextReveal.vue           # Scroll-triggered text reveal
```

### Tailwind + TypeScript Props
```vue
<script setup lang="ts">
const props = withDefaults(defineProps<{ variant?: 'primary' | 'ghost'; glow?: boolean }>(),
  { variant: 'primary', glow: false })

const classes = computed(() => [
  'inline-flex items-center justify-center rounded-xl px-6 py-3 min-h-[44px]',
  'font-medium transition-all duration-200 ease-out',
  { 'bg-accent text-white shadow-md hover:shadow-lg hover:-translate-y-0.5': props.variant === 'primary',
    'bg-transparent text-accent hover:bg-accent/5': props.variant === 'ghost',
    'shadow-glow': props.glow },
])
</script>
<template><button :class="classes"><slot /></button></template>
```

### CSS Variables with Vue Reactivity
```vue
<script setup lang="ts">
const mouseX = ref(50)
const mouseY = ref(50)
function handleMouseMove(e: MouseEvent) {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  mouseX.value = ((e.clientX - rect.left) / rect.width) * 100
  mouseY.value = ((e.clientY - rect.top) / rect.height) * 100
}
const gradientStyle = computed(() => ({ '--mx': `${mouseX.value}%`, '--my': `${mouseY.value}%` }))
</script>
<template>
  <section :style="gradientStyle" class="relative min-h-screen overflow-hidden" @mousemove="handleMouseMove">
    <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_var(--mx)_var(--my),_hsl(250_80%_65%/0.2),_transparent_60%)]" />
    <div class="relative z-10"><slot /></div>
  </section>
</template>
```

### NuxtImage Config
```ts
// nuxt.config.ts
export default defineNuxtConfig({
  modules: ['@nuxt/image'],
  image: { quality: 80, formats: ['avif', 'webp'],
    screens: { xs: 320, sm: 640, md: 768, lg: 1024, xl: 1280, xxl: 1536 } },
})
```

## Quality Checklist

- [ ] Emotional target stated and consistently executed
- [ ] No flat white backgrounds -- all surfaces have warmth/depth
- [ ] Typography loaded with font-display: swap, display font has personality
- [ ] Hero text large, confident, beautifully spaced
- [ ] Color system uses HSL with intentional relationships
- [ ] Shadows multi-layered and colored (not pure black)
- [ ] Page entrance has staggered animation
- [ ] Hover states on all interactive elements
- [ ] Generous spacing (sections: 80-120px+ vertical padding)
- [ ] At least one "screenshot-worthy" visual moment
- [ ] Responsive: mobile-first, fluid clamp() type, touch targets >= 44px
- [ ] Accessibility: WCAG AA contrast, prefers-reduced-motion, semantic HTML
- [ ] Images via NuxtImg/NuxtPicture (AVIF/WebP), hero loading="eager"
- [ ] Fonts preloaded, heavy visuals deferred with ClientOnly
- [ ] No generic/template aesthetic -- handcrafted for THIS page

## Anti-Patterns (never do these)

- Plain white background with blue links
- System fonts or Inter/Roboto as display font
- Cookie-cutter card grids with no visual hierarchy
- Uniform spacing with no rhythm variation
- Animations that all fire simultaneously (no stagger)
- Stock-photo hero with centered text overlay (the "startup template" look)
- Purple-gradient-on-white (the "AI product" cliche)
- Drop shadows that are pure black (rgba(0,0,0,x))
- Ignoring prefers-reduced-motion (animated pages that cannot be stilled)
- Text over images with no contrast overlay (fails WCAG)
- Uncompressed PNG/JPEG hero images (kills LCP)
- Loading 6+ font weights when 2-3 suffice
- Viewport units without clamp() (breaks on extreme screen sizes)

## Delivering the Output

For Nuxt/Vue projects: output Vue SFC components organized by visual section. Use Tailwind utilities, CSS custom properties for theming, and `@nuxt/image` for raster images. Configure fonts and head metadata in `nuxt.config.ts`.

For standalone pages: output a single HTML file with all CSS in `<style>` and JS in `<script>`. Use CDN links for Google Fonts. Immediately openable and production-ready.

Always take a second pass to refine and polish. Ask: "Would I screenshot this?" If not, elevate it.
