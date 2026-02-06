import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'happy-dom',
    include: ['tests/**/*.test.ts'],
    // Exclude CLI integration tests that run with npx tsx
    exclude: [
      'tests/pipeline-e2e.test.ts',
      'tests/conflict-resolution.test.ts',
      'tests/worktree-manager.test.ts',
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['app/**/*.ts', 'app/**/*.vue'],
    },
  },
  resolve: {
    alias: {
      '~': new URL('./app', import.meta.url).pathname,
      '@': new URL('./app', import.meta.url).pathname,
    },
  },
})
