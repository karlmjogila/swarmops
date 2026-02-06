<script setup lang="ts">
// Get sidebar toggle from parent layout
const toggleSidebar = inject<() => void>('toggleSidebar', () => {})

// Auth state
const { isAuthEnabled, logout } = useAuth()

async function handleLogout() {
  await logout()
}
</script>

<template>
  <aside class="sidebar">
    <header class="sidebar-header">
      <div class="brand">
        <div class="brand-logo">
          <UIcon name="i-heroicons-cube" class="brand-icon" />
        </div>
        <div>
          <h1 class="brand-title">SwarmOps</h1>
          <p class="brand-subtitle">Dashboard</p>
        </div>
      </div>
      <!-- Mobile close button -->
      <button class="mobile-close" @click="toggleSidebar">
        <UIcon name="i-heroicons-x-mark" class="w-5 h-5" />
      </button>
    </header>
    <div class="sidebar-content">
      <div class="section-label">
        Projects
      </div>
      <slot />
    </div>
    <!-- Footer with connection status and logout -->
    <footer class="sidebar-footer">
      <ClientOnly>
        <ConnectionStatus />
      </ClientOnly>
      <button 
        v-if="isAuthEnabled" 
        class="logout-btn"
        @click="handleLogout"
      >
        <UIcon name="i-heroicons-arrow-right-start-on-rectangle" />
        <span>Sign Out</span>
      </button>
    </footer>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 300px;
  display: flex;
  flex-direction: column;
  background: var(--swarm-bg-secondary);
  border-right: 1px solid var(--swarm-border);
  height: 100%;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  border-bottom: 1px solid var(--swarm-border);
}

.brand {
  display: flex;
  align-items: center;
  gap: 16px;
}

.brand-logo {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--swarm-accent), var(--swarm-accent-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px var(--swarm-accent-glow);
}

.brand-icon {
  width: 20px;
  height: 20px;
  color: white;
}

.brand-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--swarm-text-primary);
  letter-spacing: -0.01em;
}

.brand-subtitle {
  font-size: 12px;
  color: var(--swarm-text-muted);
}

.mobile-close {
  display: none;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  color: var(--swarm-text-muted);
}
.mobile-close:hover {
  background: var(--swarm-bg-hover);
  color: var(--swarm-text-primary);
}

@media (max-width: 1024px) {
  .mobile-close {
    display: flex;
  }
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--swarm-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0 12px;
  margin-bottom: 12px;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--swarm-border);
  background: var(--swarm-bg-page);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 14px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid var(--swarm-border);
  color: var(--swarm-text-muted);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.logout-btn:hover {
  background: var(--swarm-bg-hover);
  color: var(--swarm-text-primary);
  border-color: var(--swarm-border);
}
</style>
