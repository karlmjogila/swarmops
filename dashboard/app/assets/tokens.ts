/**
 * Design Tokens - Single source of truth for SwarmOps Dashboard styling
 * 
 * These tokens define colors, typography, spacing, and radii used throughout the app.
 * Import these values in components or use the generated CSS variables.
 */

// ═══════════════════════════════════════════════════════════════════════════
// COLORS
// ═══════════════════════════════════════════════════════════════════════════

export const colors = {
  // Background colors (dark theme)
  bg: {
    primary: '#080b14',
    secondary: '#0f1420',
    tertiary: '#1a1f2e',
    card: '#12171f',
    cardHover: '#1a202d',
    elevated: '#181d28',
  },

  // Border colors
  border: {
    default: 'rgba(99, 102, 241, 0.15)',
    light: 'rgba(148, 163, 184, 0.08)',
    glow: 'rgba(99, 102, 241, 0.4)',
  },

  // Text colors
  text: {
    primary: '#f1f5f9',
    secondary: '#94a3b8',
    muted: '#64748b',
    bright: '#ffffff',
  },

  // Primary accent (indigo)
  accent: {
    default: '#6366f1',
    light: '#818cf8',
    dark: '#4f46e5',
    glow: 'rgba(99, 102, 241, 0.5)',
  },

  // Semantic colors
  success: {
    default: '#10b981',
    glow: 'rgba(16, 185, 129, 0.4)',
    dark: '#059669',
  },

  warning: {
    default: '#f59e0b',
    glow: 'rgba(245, 158, 11, 0.4)',
    dark: '#d97706',
  },

  error: {
    default: '#ef4444',
    glow: 'rgba(239, 68, 68, 0.4)',
    dark: '#dc2626',
  },

  neutral: {
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a',
    950: '#020617',
  },
} as const

// ═══════════════════════════════════════════════════════════════════════════
// GRADIENTS
// ═══════════════════════════════════════════════════════════════════════════

export const gradients = {
  primary: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%)',
  card: 'linear-gradient(180deg, rgba(99, 102, 241, 0.03) 0%, transparent 100%)',
  surface: 'linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, transparent 50%)',
  glow: 'radial-gradient(ellipse at top, rgba(99, 102, 241, 0.15) 0%, transparent 50%)',
  success: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
  warning: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
  error: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
} as const

// ═══════════════════════════════════════════════════════════════════════════
// TYPOGRAPHY
// ═══════════════════════════════════════════════════════════════════════════

export const typography = {
  fontFamily: {
    sans: 'Inter, system-ui, -apple-system, sans-serif',
    mono: "'JetBrains Mono', 'Fira Code', 'SF Mono', monospace",
  },

  fontSize: {
    xs: '0.75rem',     // 12px
    sm: '0.8125rem',   // 13px
    base: '0.875rem',  // 14px
    lg: '0.9375rem',   // 15px
    xl: '1.125rem',    // 18px
    '2xl': '1.25rem',  // 20px
    '3xl': '1.5rem',   // 24px
    '4xl': '2rem',     // 32px
  },

  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
    extrabold: '800',
  },

  lineHeight: {
    tight: '1.25',
    snug: '1.375',
    normal: '1.5',
    relaxed: '1.625',
    loose: '1.7',
  },

  letterSpacing: {
    tighter: '-0.02em',
    tight: '-0.01em',
    normal: '0',
    wide: '0.05em',
    wider: '0.12em',
  },
} as const

// ═══════════════════════════════════════════════════════════════════════════
// SPACING
// ═══════════════════════════════════════════════════════════════════════════

export const spacing = {
  px: '1px',
  0: '0',
  0.5: '0.125rem',  // 2px
  1: '0.25rem',     // 4px
  1.5: '0.375rem',  // 6px
  2: '0.5rem',      // 8px
  2.5: '0.625rem',  // 10px
  3: '0.75rem',     // 12px
  3.5: '0.875rem',  // 14px
  4: '1rem',        // 16px
  5: '1.25rem',     // 20px
  6: '1.5rem',      // 24px
  7: '1.75rem',     // 28px
  8: '2rem',        // 32px
  10: '2.5rem',     // 40px
  12: '3rem',       // 48px
  16: '4rem',       // 64px
  20: '5rem',       // 80px
} as const

// Semantic spacing aliases
export const spacingAliases = {
  xs: spacing[1],      // 4px
  sm: spacing[2],      // 8px
  md: spacing[4],      // 16px
  lg: spacing[6],      // 24px
  xl: spacing[8],      // 32px
  '2xl': spacing[10],  // 40px
} as const

// ═══════════════════════════════════════════════════════════════════════════
// BORDER RADIUS
// ═══════════════════════════════════════════════════════════════════════════

export const radii = {
  none: '0',
  sm: '0.375rem',    // 6px
  default: '0.5rem', // 8px
  md: '0.625rem',    // 10px
  lg: '0.75rem',     // 12px
  xl: '0.875rem',    // 14px
  '2xl': '1rem',     // 16px
  '3xl': '1.25rem',  // 20px
  full: '9999px',
} as const

// ═══════════════════════════════════════════════════════════════════════════
// SHADOWS
// ═══════════════════════════════════════════════════════════════════════════

export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
  default: '0 4px 12px rgba(0, 0, 0, 0.3)',
  md: '0 8px 24px rgba(0, 0, 0, 0.4)',
  lg: '0 12px 40px rgba(0, 0, 0, 0.4)',
  xl: '0 16px 48px rgba(0, 0, 0, 0.5)',
  glow: {
    accent: '0 0 20px rgba(99, 102, 241, 0.5)',
    success: '0 0 20px rgba(16, 185, 129, 0.4)',
    warning: '0 0 20px rgba(245, 158, 11, 0.4)',
    error: '0 0 20px rgba(239, 68, 68, 0.4)',
  },
  card: '0 8px 24px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(99, 102, 241, 0.1)',
  button: '0 4px 14px rgba(99, 102, 241, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.2)',
} as const

// ═══════════════════════════════════════════════════════════════════════════
// TRANSITIONS
// ═══════════════════════════════════════════════════════════════════════════

export const transitions = {
  duration: {
    fast: '150ms',
    default: '200ms',
    slow: '300ms',
    slower: '400ms',
  },
  timing: {
    default: 'cubic-bezier(0.4, 0, 0.2, 1)',
    in: 'cubic-bezier(0.4, 0, 1, 1)',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  },
} as const

// ═══════════════════════════════════════════════════════════════════════════
// Z-INDEX
// ═══════════════════════════════════════════════════════════════════════════

export const zIndex = {
  base: 0,
  dropdown: 10,
  sticky: 20,
  fixed: 30,
  overlay: 40,
  modal: 50,
  popover: 60,
  tooltip: 70,
} as const

// ═══════════════════════════════════════════════════════════════════════════
// BREAKPOINTS
// ═══════════════════════════════════════════════════════════════════════════

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const

// ═══════════════════════════════════════════════════════════════════════════
// COMPONENT TOKENS (pre-composed)
// ═══════════════════════════════════════════════════════════════════════════

export const components = {
  card: {
    bg: colors.bg.card,
    bgHover: colors.bg.cardHover,
    border: colors.border.light,
    borderHover: colors.border.default,
    radius: radii['2xl'],
    padding: spacing[5],
    shadow: shadows.default,
    shadowHover: shadows.card,
  },

  button: {
    paddingX: spacing[5],
    paddingY: spacing[2.5],
    radius: radii.md,
    fontWeight: typography.fontWeight.semibold,
    fontSize: typography.fontSize.sm,
    transition: `all ${transitions.duration.default} ${transitions.timing.default}`,
  },

  badge: {
    paddingX: spacing[3],
    paddingY: spacing[1.5],
    radius: radii.full,
    fontSize: typography.fontSize.xs,
    fontWeight: typography.fontWeight.bold,
    letterSpacing: typography.letterSpacing.wide,
  },

  input: {
    bg: colors.bg.tertiary,
    border: colors.border.light,
    borderFocus: colors.accent.default,
    radius: radii.lg,
    paddingX: spacing[4],
    paddingY: spacing[2.5],
  },

  section: {
    bg: colors.bg.secondary,
    border: colors.border.light,
    radius: radii['2xl'],
    padding: spacing[6],
    gap: spacing[5],
  },

  sidebar: {
    width: '300px',
    bg: colors.bg.secondary,
    border: colors.border.light,
  },
} as const

// ═══════════════════════════════════════════════════════════════════════════
// CSS VARIABLE GENERATION
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Generates CSS custom properties from the design tokens.
 * Use this to inject tokens as CSS variables.
 */
export function generateCSSVariables(): string {
  return `
:root {
  /* Background Colors */
  --color-bg-primary: ${colors.bg.primary};
  --color-bg-secondary: ${colors.bg.secondary};
  --color-bg-tertiary: ${colors.bg.tertiary};
  --color-bg-card: ${colors.bg.card};
  --color-bg-card-hover: ${colors.bg.cardHover};
  --color-bg-elevated: ${colors.bg.elevated};

  /* Border Colors */
  --color-border: ${colors.border.default};
  --color-border-light: ${colors.border.light};
  --color-border-glow: ${colors.border.glow};

  /* Text Colors */
  --color-text-primary: ${colors.text.primary};
  --color-text-secondary: ${colors.text.secondary};
  --color-text-muted: ${colors.text.muted};
  --color-text-bright: ${colors.text.bright};

  /* Accent Colors */
  --color-accent: ${colors.accent.default};
  --color-accent-light: ${colors.accent.light};
  --color-accent-dark: ${colors.accent.dark};
  --color-accent-glow: ${colors.accent.glow};

  /* Semantic Colors */
  --color-success: ${colors.success.default};
  --color-success-glow: ${colors.success.glow};
  --color-warning: ${colors.warning.default};
  --color-warning-glow: ${colors.warning.glow};
  --color-error: ${colors.error.default};
  --color-error-glow: ${colors.error.glow};

  /* Gradients */
  --gradient-primary: ${gradients.primary};
  --gradient-card: ${gradients.card};
  --gradient-surface: ${gradients.surface};

  /* Typography */
  --font-sans: ${typography.fontFamily.sans};
  --font-mono: ${typography.fontFamily.mono};

  /* Spacing */
  --space-xs: ${spacingAliases.xs};
  --space-sm: ${spacingAliases.sm};
  --space-md: ${spacingAliases.md};
  --space-lg: ${spacingAliases.lg};
  --space-xl: ${spacingAliases.xl};

  /* Border Radius */
  --radius-sm: ${radii.sm};
  --radius-default: ${radii.default};
  --radius-md: ${radii.md};
  --radius-lg: ${radii.lg};
  --radius-xl: ${radii.xl};
  --radius-2xl: ${radii['2xl']};
  --radius-full: ${radii.full};

  /* Transitions */
  --transition-fast: ${transitions.duration.fast};
  --transition-default: ${transitions.duration.default};
  --transition-slow: ${transitions.duration.slow};
  --transition-timing: ${transitions.timing.default};
}
`.trim()
}

// Default export for convenience
export default {
  colors,
  gradients,
  typography,
  spacing,
  spacingAliases,
  radii,
  shadows,
  transitions,
  zIndex,
  breakpoints,
  components,
  generateCSSVariables,
}
