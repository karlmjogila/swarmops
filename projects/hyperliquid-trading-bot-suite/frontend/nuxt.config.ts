// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: true },
  
  // Modules
  modules: [
    '@nuxtjs/tailwindcss',
    '@pinia/nuxt',
    '@vueuse/nuxt',
  ],

  // CSS
  css: [
    '~/assets/css/tailwind.css',
  ],

  // Runtime config
  runtimeConfig: {
    // Private keys (only available on server-side)
    // apiSecret: '123',
    
    // Public keys (exposed to client-side)
    public: {
      apiBaseUrl: process.env.NUXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
      // SECURITY: Use wss:// for production, ws:// only for local development
      // Set NUXT_PUBLIC_WS_URL in production to wss://your-domain.com/ws
      wsUrl: process.env.NUXT_PUBLIC_WS_URL || (
        process.env.NODE_ENV === 'production' 
          ? 'wss://localhost:8000/ws'  // Production default: secure WebSocket
          : 'ws://localhost:8000/ws'   // Development default: plain WebSocket
      ),
      // Flag to enforce secure WebSocket in production
      enforceSecureWs: process.env.NODE_ENV === 'production',
    }
  },

  // App config
  app: {
    head: {
      title: 'Hyperliquid Trading Bot Suite',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { 
          name: 'description', 
          content: 'AI-powered trading system that learns strategies from educational content' 
        },
      ],
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
        // Google Fonts
        { 
          rel: 'preconnect', 
          href: 'https://fonts.googleapis.com' 
        },
        { 
          rel: 'preconnect', 
          href: 'https://fonts.gstatic.com', 
          crossorigin: '' 
        },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Satoshi:wght@300;400;500;600;700;900&family=General+Sans:wght@300;400;500;600;700&display=swap'
        }
      ],
    },
  },

  // Tailwind CSS
  tailwindcss: {
    cssPath: '~/assets/css/tailwind.css',
    configPath: 'tailwind.config.js',
  },

  // Pinia - autoImports are enabled by default
  pinia: {
    storesDirs: ['./stores/**'],
  },

  // TypeScript
  typescript: {
    strict: true,
    typeCheck: true,
  },

  // Build
  build: {
    transpile: ['lightweight-charts'],
  },

  // Server-side rendering
  ssr: true,

  // Nitro config for production
  nitro: {
    compressPublicAssets: true,
  },

  // Dev server config - bind to localhost only
  devServer: {
    host: '127.0.0.1',
    port: 3000,
  },

  // Vite config
  vite: {
    define: {
      global: 'globalThis',
    },
    optimizeDeps: {
      include: ['lightweight-charts'],
    },
  },
})