/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './components/**/*.{js,vue,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './plugins/**/*.{js,ts}',
    './app.vue',
    './error.vue'
  ],
  theme: {
    extend: {
      fontFamily: {
        'display': ['Satoshi', 'ui-sans-serif', 'system-ui'],
        'body': ['General Sans', 'ui-sans-serif', 'system-ui'],
        'mono': ['SF Mono', 'Monaco', 'Cascadia Code', 'Roboto Mono', 'monospace']
      },
      colors: {
        // Custom colors from our CSS variables
        'surface': 'hsl(225, 25%, 97%)',
        'surface-elevated': 'hsl(0, 0%, 100%)',
        'surface-dark': 'hsl(225, 15%, 15%)',
        'surface-dark-elevated': 'hsl(225, 20%, 20%)',
        'accent-primary': 'hsl(210, 85%, 55%)',
        'accent-secondary': 'hsl(280, 70%, 65%)',
        'accent-success': 'hsl(145, 85%, 45%)',
        'accent-danger': 'hsl(0, 85%, 60%)',
        'accent-warning': 'hsl(35, 90%, 55%)'
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem'
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-soft': 'pulseSoft 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' }
        },
        pulseSoft: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.8' }
        }
      },
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'soft-lg': '0 10px 40px -10px rgba(0, 0, 0, 0.1)',
        'glow': '0 0 30px rgba(59, 130, 246, 0.15)',
        'glow-lg': '0 0 60px rgba(59, 130, 246, 0.2)'
      },
      backdropBlur: {
        'xs': '2px'
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography')
  ]
}