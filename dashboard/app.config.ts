export default defineAppConfig({
  ui: {
    colors: {
      primary: 'indigo',
      success: 'emerald',
      warning: 'amber',
      error: 'red',
      neutral: 'slate'
    },
    // Force dark theme
    theme: {
      colors: ['primary', 'success', 'warning', 'error', 'neutral']
    }
  }
})
