---
name: web-visuals
description: >
  Generate emotionally resonant, production-grade web pages and interfaces with
  extraordinary visual beauty. Trigger this skill when the user says "start building" a web page,
  landing page, portfolio, app UI, or any web interface where visual excellence is the primary goal.
  Also trigger on phrases like "make it beautiful", "stunning visuals", "make it look amazing", 
  "gorgeous web page", or any request emphasizing visual quality of a web deliverable.
  This skill produces HTML/CSS/JS or React artifacts with handcrafted aesthetics that feel human-made,
  emotionally engaging, and visually unforgettable. Do NOT use for purely functional tools, CLIs,
  data scripts, or non-visual tasks.
---

# Beautiful Web Visuals

Create web pages that make people *feel* something — pages so beautiful they pause scrolling, lean in, and remember. This skill produces web interfaces at the level of award-winning studios like Stripe, Linear, Vercel, Apple, and Pentagram — not generic templates.

## Philosophy

Every beautiful interface has three invisible layers:

1. **Emotional texture** — warmth, trust, delight, wonder, calm, energy. Choose one feeling and commit.
2. **Obsessive craft** — the 1px shadow, the 40ms ease, the letter-spacing that makes a heading sing. Details nobody notices consciously but everyone *feels*.
3. **Narrative rhythm** — a page is a story. It has a hook, rising tension, moments of rest, and a satisfying ending. Scroll should feel like turning pages of a beautiful book.

## Before Writing Any Code

Pause. Think through these decisions and state them explicitly:

### 1. Emotional Target
Pick ONE dominant emotion: wonder, calm confidence, playful energy, sophisticated warmth, raw power, dreamy softness, crisp precision, organic warmth. Name it. Every choice flows from this.

### 2. Visual Identity (commit to ALL of these)

**Color Strategy** — Go beyond "pick a palette." Decide:
- A signature color (one hue that owns the page)
- A spatial color system (how color creates depth: layered backgrounds, gradient fog, glowing accents)
- Light behavior (does light come from above? behind? is it ambient or directional?)
- Never use flat white (#fff) backgrounds. Use warm off-whites (hsl(40,20%,97%)), cool grays (hsl(220,15%,96%)), or tinted surfaces.

**Typography as Voice** — Load from Google Fonts. Choose:
- A display/heading font with REAL personality (e.g., Playfair Display, Fraunces, Instrument Serif, Clash Display, Cabinet Grotesk, Satoshi, General Sans, Sora, Plus Jakarta Sans). NEVER use Inter, Roboto, Arial, system-ui as primary fonts.
- A body font that complements but doesn't compete.
- Establish a type scale with intentional rhythm: hero text should be enormous (clamp(3rem, 8vw, 7rem)), body text comfortable (18-20px), with generous line-height (1.6-1.8).

**Spatial Design** — Beautiful pages breathe:
- Generous padding (80-120px vertical sections minimum)
- Asymmetric layouts that feel composed, not random
- Strategic overlap and layering (elements that break grid boundaries)
- Negative space is a design element, not emptiness

**Depth & Atmosphere** — Create a sense of place:
- Layered backgrounds (stacked gradients, mesh gradients, noise textures via SVG filters)
- Soft, realistic shadows (multiple shadow layers, colored shadows matching nearby hues)
- Glassmorphism, grain, blur — used with restraint and purpose
- Subtle background patterns or shapes that add texture without distraction

### 3. Motion Philosophy
Animation makes the difference between "nice" and "beautiful":
- **Page entrance**: Staggered reveals — elements appear in choreographed sequence (use animation-delay: 0.1s increments). Fade + slight translate (20px) is the baseline; better pages add scale, blur-to-sharp, or clip-path reveals.
- **Scroll-driven**: Use Intersection Observer for scroll-triggered animations. Elements should feel like they're *arriving*, not just *appearing*.
- **Micro-interactions**: Hover states that reward curiosity — subtle scale (1.02-1.05), color shifts, shadow lifts, underline animations on links. Buttons should feel pressable (slight translateY on hover, deeper shadow).
- **Timing**: Use cubic-bezier(0.16, 1, 0.3, 1) for natural-feeling ease. Duration 300-600ms for reveals, 150-250ms for hover states.
- **CSS-first**: Prefer CSS animations/transitions. Use @keyframes for complex sequences. JS only when CSS can't achieve it.

### 4. The "One Thing"
What's the single visual moment someone will screenshot and share? A hero animation? A color transition on scroll? A beautifully typeset quote? An unexpected layout shift? Design this moment first, then build the page around it.

## Implementation Standards

### HTML Structure
- Use semantic HTML5 (section, article, header, nav, figure).
- Everything in a single file (HTML + CSS in `<style>` + JS in `<script>`).
- Include `<meta name="viewport" content="width=device-width, initial-scale=1.0">`.
- Load Google Fonts via `<link>` with `display=swap`.

### CSS Craft
```css
/* Always define a design system at the root */
:root {
  /* Named colors that tell a story */
  --color-surface: hsl(220, 20%, 97%);
  --color-surface-elevated: hsl(0, 0%, 100%);
  --color-accent: hsl(250, 75%, 60%);
  --color-accent-glow: hsl(250, 75%, 60%, 0.15);
  --color-text-primary: hsl(220, 25%, 12%);
  --color-text-secondary: hsl(220, 15%, 45%);

  /* Spacing scale */
  --space-xs: 0.5rem;
  --space-sm: 1rem;
  --space-md: 2rem;
  --space-lg: 4rem;
  --space-xl: 8rem;
  --space-2xl: 12rem;

  /* Typography */
  --font-display: 'Your Display Font', serif;
  --font-body: 'Your Body Font', sans-serif;

  /* Shadows that feel real */
  --shadow-sm: 0 1px 2px hsl(220 20% 20% / 0.04), 0 1px 3px hsl(220 20% 20% / 0.06);
  --shadow-md: 0 4px 6px hsl(220 20% 20% / 0.04), 0 8px 20px hsl(220 20% 20% / 0.06);
  --shadow-lg: 0 8px 16px hsl(220 20% 20% / 0.04), 0 20px 50px hsl(220 20% 20% / 0.08);
  --shadow-glow: 0 0 30px var(--color-accent-glow);
}

/* Smooth scroll for the whole page */
html { scroll-behavior: smooth; }

/* Beautiful text rendering */
body {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
```

### Visual Techniques Library

**Mesh/gradient backgrounds:**
```css
.hero {
  background:
    radial-gradient(ellipse at 20% 50%, hsl(250 80% 65% / 0.15) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, hsl(330 70% 60% / 0.1) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 80%, hsl(200 80% 55% / 0.08) 0%, transparent 50%),
    var(--color-surface);
}
```

**SVG noise texture overlay:**
```html
<svg style="position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;opacity:0.03">
  <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="4" stitchTiles="stitch"/></filter>
  <rect width="100%" height="100%" filter="url(#grain)"/>
</svg>
```

**Staggered reveal animation:**
```css
.reveal { opacity: 0; transform: translateY(20px); transition: opacity 0.7s cubic-bezier(0.16,1,0.3,1), transform 0.7s cubic-bezier(0.16,1,0.3,1); }
.reveal.visible { opacity: 1; transform: translateY(0); }
```
```js
const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      setTimeout(() => entry.target.classList.add('visible'), i * 100);
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.1 });
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
```

**Glowing accent borders:**
```css
.card {
  border: 1px solid hsl(250 60% 70% / 0.2);
  box-shadow: var(--shadow-md), inset 0 1px 0 hsl(0 0% 100% / 0.5);
  transition: box-shadow 0.3s ease, border-color 0.3s ease;
}
.card:hover {
  border-color: hsl(250 60% 70% / 0.4);
  box-shadow: var(--shadow-lg), var(--shadow-glow);
}
```

## Quality Checklist (verify before delivering)

- [ ] Emotional target stated and consistently executed
- [ ] No flat white backgrounds — all surfaces have warmth/depth
- [ ] Typography loaded from Google Fonts, display font has personality
- [ ] Hero text is large, confident, beautifully spaced
- [ ] Color system uses HSL with intentional relationships
- [ ] Shadows are multi-layered and colored (not pure black)
- [ ] Page entrance has staggered animation
- [ ] Hover states on all interactive elements
- [ ] Generous spacing (sections: 80-120px+ vertical padding)
- [ ] At least one "screenshot-worthy" visual moment
- [ ] SVG noise/grain overlay for texture (when appropriate)
- [ ] Responsive (clamp() for type, fluid padding, mobile-considered)
- [ ] No generic/template aesthetic — this feels handcrafted for THIS page

## Anti-Patterns (never do these)

- Plain white background with blue links
- System fonts or Inter/Roboto as display font
- Cookie-cutter card grids with no visual hierarchy
- Uniform spacing with no rhythm variation
- Black text on white with no color accent
- Animations that all fire simultaneously (no stagger)
- Stock-photo hero with centered text overlay (the "startup template" look)
- Purple-gradient-on-white (the "AI product" cliché)
- Using opacity:0.5 as a lazy way to create visual hierarchy
- Drop shadows that are pure black (rgba(0,0,0,x))

## Delivering the Output

Output a single HTML file. Include all CSS in a `<style>` block and all JS in a `<script>` block. Use CDN links for Google Fonts. The file should be immediately openable in a browser and look production-ready.

For React: output a single `.jsx` file using Tailwind utility classes and inline styles for custom properties. Import Google Fonts in a style block within the component.

Always take a second pass through the code to refine and polish. Ask: "Would I screenshot this?" If not, elevate it.
