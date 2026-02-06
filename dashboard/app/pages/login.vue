<script setup lang="ts">
definePageMeta({
  layout: false  // No sidebar for login page
})

const router = useRouter()
const token = ref('')
const error = ref('')
const isLoading = ref(false)
const showToken = ref(false)

// Check if already authenticated
onMounted(async () => {
  try {
    const status = await $fetch<{ authenticated: boolean; authEnabled: boolean }>('/api/auth/status')
    if (status.authenticated) {
      router.push('/')
    }
  } catch {
    // Ignore errors, stay on login page
  }
})

async function handleSubmit() {
  if (!token.value.trim()) {
    error.value = 'Please enter a token'
    return
  }

  isLoading.value = true
  error.value = ''

  try {
    await $fetch('/api/auth/login', {
      method: 'POST',
      body: { token: token.value.trim() }
    })
    
    // Redirect to home on success
    router.push('/')
  } catch (e: any) {
    error.value = e.data?.statusMessage || e.message || 'Login failed'
  } finally {
    isLoading.value = false
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    handleSubmit()
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <div class="logo">
          <UIcon name="i-heroicons-cpu-chip" class="logo-icon" />
        </div>
        <h1 class="title">SwarmOps</h1>
        <p class="subtitle">Multi-agent orchestration platform</p>
      </div>

      <form class="login-form" @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="token" class="label">Gateway Token</label>
          <div class="input-wrapper">
            <input
              id="token"
              v-model="token"
              :type="showToken ? 'text' : 'password'"
              class="token-input"
              placeholder="Enter your OpenClaw gateway token"
              autocomplete="off"
              :disabled="isLoading"
              @keydown="handleKeydown"
            />
            <button
              type="button"
              class="toggle-visibility"
              @click="showToken = !showToken"
            >
              <UIcon :name="showToken ? 'i-heroicons-eye-slash' : 'i-heroicons-eye'" />
            </button>
          </div>
          <p class="hint">
            This is the same token used for OpenClaw's web UI
          </p>
        </div>

        <Transition name="error">
          <div v-if="error" class="error-message">
            <UIcon name="i-heroicons-exclamation-circle" />
            {{ error }}
          </div>
        </Transition>

        <button
          type="submit"
          class="submit-button"
          :disabled="isLoading || !token.trim()"
        >
          <UIcon v-if="isLoading" name="i-heroicons-arrow-path" class="animate-spin" />
          <span>{{ isLoading ? 'Authenticating...' : 'Sign In' }}</span>
        </button>
      </form>

      <div class="login-footer">
        <p>
          <UIcon name="i-heroicons-shield-check" />
          Secured by OpenClaw Gateway
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
  padding: 20px;
}

.login-container {
  width: 100%;
  max-width: 400px;
  background: rgba(30, 41, 59, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 20px;
  padding: 40px;
  box-shadow: 
    0 20px 60px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(148, 163, 184, 0.05);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.3);
}

.logo-icon {
  width: 32px;
  height: 32px;
  color: white;
}

.title {
  font-size: 28px;
  font-weight: 700;
  color: #f1f5f9;
  margin: 0 0 8px;
}

.subtitle {
  font-size: 14px;
  color: #94a3b8;
  margin: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.label {
  font-size: 13px;
  font-weight: 500;
  color: #cbd5e1;
}

.input-wrapper {
  position: relative;
  display: flex;
}

.token-input {
  flex: 1;
  padding: 14px 48px 14px 16px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 12px;
  color: #f1f5f9;
  font-size: 14px;
  font-family: 'SF Mono', Monaco, monospace;
  transition: all 0.2s ease;
}

.token-input::placeholder {
  color: #64748b;
  font-family: inherit;
}

.token-input:focus {
  outline: none;
  border-color: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
}

.token-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toggle-visibility {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: #64748b;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.15s ease;
}

.toggle-visibility:hover {
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.1);
}

.hint {
  font-size: 12px;
  color: #64748b;
  margin: 0;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 10px;
  color: #f87171;
  font-size: 13px;
}

.error-enter-active,
.error-leave-active {
  transition: all 0.2s ease;
}

.error-enter-from,
.error-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.submit-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 24px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
  border-radius: 12px;
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3);
}

.submit-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4);
}

.submit-button:active:not(:disabled) {
  transform: translateY(0);
}

.submit-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-footer {
  margin-top: 24px;
  text-align: center;
}

.login-footer p {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  margin: 0;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
