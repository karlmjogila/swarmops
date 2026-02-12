# Hyperliquid Trading Bot Suite - Frontend

A beautiful, high-performance trading dashboard built with Nuxt 3 and TradingView Lightweight Charts.

## 🎨 Design Philosophy

This frontend follows a "Beautiful Web Visuals" approach with:

### Emotional Target: **Calm Confidence**
- Professional sophistication meets approachable warmth
- Clean lines with subtle depth and atmosphere
- Purposeful animations that enhance rather than distract

### Visual Identity
- **Colors**: Sophisticated blue-purple gradient with warm off-white surfaces
- **Typography**: Playfair Display for headings (personality), Sora for body text (clarity)
- **Depth**: Layered backgrounds, soft realistic shadows, subtle glassmorphism
- **Motion**: Staggered reveals, smooth micro-interactions, thoughtful hover states

## 🚀 Features

### Core Dashboard
- **Real-time TradingView Charts** - Lightweight Charts integration with custom themes
- **Live Price Feeds** - WebSocket connections to real-time market data
- **Position Management** - Quick trade panel with leverage controls
- **Strategy Status** - Active strategies with performance metrics
- **Trade History** - Recent trades with P&L visualization

### Technical Features
- **Responsive Design** - Mobile-first approach with fluid layouts
- **Dark/Light Mode** - System preference detection with manual override
- **Performance Optimized** - Code splitting, lazy loading, optimized charts
- **Type Safety** - Full TypeScript support with strict checking
- **Modern Stack** - Vue 3, Nuxt 3, Pinia, Tailwind CSS

## 🛠️ Tech Stack

### Core Framework
- **Nuxt 3.8+** - Vue.js meta-framework with SSR/SPA modes
- **Vue 3** - Composition API with `<script setup>`
- **TypeScript** - Strict type checking enabled

### UI & Styling
- **Tailwind CSS** - Utility-first with custom design tokens
- **HeadlessUI** - Accessible component primitives
- **Heroicons** - Beautiful SVG icons
- **Google Fonts** - Playfair Display + Sora typography

### Charts & Data
- **Lightweight Charts** - TradingView's performant charting library
- **Chart.js + Vue-ChartJS** - Additional chart types
- **Date-fns** - Date manipulation utilities

### State & Utils
- **Pinia** - Vue 3 state management
- **VueUse** - Composition utilities
- **Vue Toastification** - Toast notifications

## 📁 Project Structure

```
frontend/
├── components/           # Vue components
│   └── TradingViewChart.vue  # Main chart component
├── pages/               # Route pages
│   └── index.vue       # Dashboard homepage
├── layouts/            # Page layouts
│   └── default.vue     # Main app layout
├── assets/            # Static assets
│   └── css/           # Stylesheets
│       ├── main.css   # Custom CSS variables & utilities
│       └── tailwind.css # Tailwind imports
├── composables/       # Vue composables (state, utilities)
├── plugins/          # Nuxt plugins
├── types/           # TypeScript definitions
├── app.vue         # Root app component
├── nuxt.config.ts  # Nuxt configuration
└── tailwind.config.js # Tailwind configuration
```

## 🎯 Component Architecture

### TradingViewChart.vue
- Lightweight Charts integration
- Theme-aware (light/dark mode)
- Responsive sizing
- Real-time data updates
- Error handling & loading states

### Layout System
- **Header**: Logo, navigation, theme toggle, connection status
- **Main**: Chart area + trading panel + strategy sidebar
- **Footer**: Minimal branding

## 🎨 Design System

### Color Palette
```css
/* Brand Colors */
--primary: hsl(250, 75%, 60%)      /* Signature blue-purple */
--surface: hsl(220, 20%, 97%)      /* Warm off-white */
--surface-elevated: hsl(0, 0%, 100%) /* Pure white cards */

/* Trading Colors */
--profit: #10b981                  /* Success green */
--loss: #ef4444                    /* Warning red */
--neutral: #6b7280                 /* Neutral gray */
```

### Typography Scale
```css
/* Display Font - Playfair Display */
h1: clamp(2.5rem, 5vw, 4rem)      /* Hero headings */
h2: clamp(2rem, 4vw, 3rem)        /* Section headings */
h3: clamp(1.5rem, 3vw, 2rem)      /* Card headings */

/* Body Font - Sora */
body: 18px / 1.6                   /* Comfortable reading */
small: 14px / 1.5                  /* UI elements */
```

### Animation Philosophy
- **Page entrance**: Staggered reveals (100ms delays)
- **Scroll-driven**: Intersection Observer triggers
- **Micro-interactions**: Hover states (scale 1.02, shadow lift)
- **Timing**: cubic-bezier(0.16, 1, 0.3, 1) for natural feel

## 🚀 Development

### Setup
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables
```bash
# API Configuration
NUXT_PUBLIC_API_BASE_URL=http://localhost:8000
NUXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## 📱 Responsive Breakpoints

```javascript
sm: '640px',   // Mobile landscape
md: '768px',   // Tablet
lg: '1024px',  // Desktop
xl: '1280px',  // Large desktop
2xl: '1536px', // Extra large
```

### Dashboard Layout
- **Mobile**: Single column, collapsible panels
- **Tablet**: Chart + sidebar stacked
- **Desktop**: Full three-column layout (chart + trading + strategies)

## 🔧 Configuration

### Nuxt Config Highlights
```typescript
// nuxt.config.ts
export default defineNuxtConfig({
  // Modules
  modules: ['@nuxtjs/tailwindcss', '@pinia/nuxt', '@vueuse/nuxt'],
  
  // TradingView Charts
  build: {
    transpile: ['lightweight-charts'],
  },
  
  // Vite optimization
  vite: {
    optimizeDeps: {
      include: ['lightweight-charts'],
    },
  },
})
```

### Performance Optimizations
- **Code Splitting**: Route-based chunks
- **Tree Shaking**: Unused code elimination
- **Asset Optimization**: Image compression, font loading
- **Bundle Analysis**: `npm run analyze`

## 🎭 Customization

### Adding New Chart Types
1. Create component in `components/charts/`
2. Import required chart libraries
3. Add to main dashboard layout
4. Update TypeScript definitions

### Extending Color Palette
```javascript
// tailwind.config.js
theme: {
  extend: {
    colors: {
      'custom-blue': {
        500: '#your-color-here'
      }
    }
  }
}
```

### Custom Animations
```css
/* assets/css/main.css */
@keyframes yourAnimation {
  from { /* start state */ }
  to { /* end state */ }
}

.your-class {
  animation: yourAnimation 0.5s ease-out;
}
```

## 🚦 Status

### ✅ Completed Features
- [x] Nuxt 3 project setup with TradingView integration
- [x] Responsive dashboard layout
- [x] TradingView Lightweight Charts component
- [x] Dark/light theme system
- [x] Beautiful design system with custom CSS variables
- [x] TypeScript configuration
- [x] Performance optimizations

### 🔄 Next Steps
- [ ] Real WebSocket integration for live data
- [ ] Chart overlay components (indicators, drawings)
- [ ] Advanced trading panel features
- [ ] Strategy management interface
- [ ] Backtesting visualization components

## 🤝 Contributing

1. Follow the established design system
2. Maintain TypeScript strict mode
3. Add proper component documentation
4. Test responsive behavior
5. Ensure accessibility standards

---

Built with ❤️ using Nuxt 3, Vue 3, and TradingView Lightweight Charts