module.exports = {
  root: true,
  extends: ['@nuxt/eslint-config'],
  rules: {
    // Add custom rules here
    'vue/multi-word-component-names': 'off',
    'vue/no-multiple-template-root': 'off',
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    'prefer-const': 'error',
    'no-var': 'error',
    'object-shorthand': 'error',
    'prefer-template': 'error',
  },
}