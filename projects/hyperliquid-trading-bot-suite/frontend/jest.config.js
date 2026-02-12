module.exports = {
  preset: '@nuxt/test-utils/jest',
  testEnvironment: 'jsdom',
  transform: {
    '^.+\\.(t|j)sx?$': ['@swc/jest', {
      jsc: {
        parser: {
          syntax: 'typescript',
          tsx: true,
          decorators: true,
        },
        transform: {
          react: {
            runtime: 'automatic',
          },
        },
      },
    }],
    '^.+\\.vue$': '@vue/vue3-jest',
  },
  moduleFileExtensions: ['js', 'ts', 'vue', 'json'],
  collectCoverage: true,
  collectCoverageFrom: [
    '<rootDir>/components/**/*.vue',
    '<rootDir>/pages/**/*.vue',
    '<rootDir>/composables/**/*.ts',
    '<rootDir>/utils/**/*.ts',
    '<rootDir>/stores/**/*.ts',
  ],
  testMatch: [
    '<rootDir>/tests/**/*.test.{js,ts}',
    '<rootDir>/components/**/*.test.{js,ts}',
    '<rootDir>/pages/**/*.test.{js,ts}',
  ],
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/$1',
    '^~/(.*)$': '<rootDir>/$1',
  },
}