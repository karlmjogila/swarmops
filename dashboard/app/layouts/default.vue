<script setup lang="ts">
// Mobile sidebar state
const sidebarOpen = ref(false)

// Close sidebar when route changes
const route = useRoute()
watch(() => route.path, () => {
  sidebarOpen.value = false
})

provide('toggleSidebar', () => {
  sidebarOpen.value = !sidebarOpen.value
})

// Auth
const { isAuthEnabled, logout } = useAuth()
</script>

<template>
  <div class="app-layout">
    <!-- Mobile backdrop -->
    <Transition
      enter-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="sidebarOpen"
        class="mobile-backdrop"
        @click="sidebarOpen = false"
      />
    </Transition>

    <!-- Sidebar -->
    <aside
      class="sidebar"
      :class="{ 'sidebar-open': sidebarOpen }"
    >
      <!-- Logo -->
      <div class="sidebar-header">
        <div class="logo">
          <div class="logo-icon">
            <UIcon name="i-heroicons-cube-transparent" class="w-5 h-5" />
          </div>
          <span class="logo-text">SwarmOps</span>
        </div>
        <button class="sidebar-close" @click="sidebarOpen = false">
          <UIcon name="i-heroicons-x-mark" class="w-5 h-5" />
        </button>
      </div>
      
      <!-- Nav sections -->
      <nav class="sidebar-nav">
        <div class="nav-section">
          <div class="nav-label">Main</div>
          <NuxtLink to="/" class="nav-item">
            <UIcon name="i-heroicons-home" class="nav-icon" />
            <span>Dashboard</span>
          </NuxtLink>
          <NuxtLink to="/docs" class="nav-item">
            <UIcon name="i-heroicons-book-open" class="nav-icon" />
            <span>Documentation</span>
          </NuxtLink>
        </div>
        
        <div class="nav-section">
          <div class="nav-label">Projects</div>
          <ProjectList />
          <NuxtLink to="/archived" class="nav-item archived-link">
            <UIcon name="i-heroicons-archive-box" class="nav-icon" />
            <span>Archived</span>
          </NuxtLink>
        </div>

        <div class="nav-section">
          <div class="nav-label">Orchestrator</div>
          <NuxtLink to="/workers" class="nav-item">
            <UIcon name="i-heroicons-cpu-chip" class="nav-icon" />
            <span>Workers</span>
          </NuxtLink>
          <NuxtLink to="/ledger" class="nav-item">
            <UIcon name="i-heroicons-document-text" class="nav-icon" />
            <span>Ledger</span>
          </NuxtLink>
          <!-- Pipeline hidden until orchestration is implemented
          <NuxtLink to="/pipelines" class="nav-item">
            <UIcon name="i-heroicons-queue-list" class="nav-icon" />
            <span>Pipelines</span>
          </NuxtLink>
          -->
          <NuxtLink to="/roles" class="nav-item">
            <UIcon name="i-heroicons-user-group" class="nav-icon" />
            <span>Roles</span>
          </NuxtLink>
        </div>
      </nav>
      
      <!-- Footer -->
      <div class="sidebar-footer">
        <ClientOnly>
          <div class="footer-row">
            <ConnectionStatus />
            <button 
              v-if="isAuthEnabled" 
              class="logout-btn"
              title="Sign out"
              @click="logout"
            >
              <UIcon name="i-heroicons-arrow-right-start-on-rectangle" />
            </button>
          </div>
        </ClientOnly>
      </div>
    </aside>

    <!-- Main content -->
    <main class="main-content">
      <!-- Mobile header -->
      <header class="mobile-header">
        <button class="menu-btn" @click="sidebarOpen = true">
          <UIcon name="i-heroicons-bars-3" class="w-5 h-5" />
        </button>
        <div class="mobile-logo">
          <div class="logo-icon small">
            <UIcon name="i-heroicons-cube-transparent" class="w-4 h-4" />
          </div>
          <span class="logo-text">SwarmOps</span>
        </div>
      </header>
      
      <div class="content-area">
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--swarm-bg-page);
}

.mobile-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 40;
}

/* Sidebar */
.sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--swarm-bg-secondary);
  border-right: 1px solid var(--swarm-border);
  height: 100%;
}

@media (max-width: 1023px) {
  .sidebar {
    position: fixed;
    inset-y: 0;
    left: 0;
    z-index: 50;
    transform: translateX(-100%);
    transition: transform 0.2s ease;
  }
  
  .sidebar.sidebar-open {
    transform: translateX(0);
  }
}

@media (min-width: 1024px) {
  .mobile-backdrop {
    display: none !important;
  }
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px;
  border-bottom: 1px solid var(--swarm-border);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--swarm-accent);
  color: white;
}

.logo-icon.small {
  width: 28px;
  height: 28px;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--swarm-text-primary);
}

.sidebar-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  color: var(--swarm-text-muted);
  cursor: pointer;
}

.sidebar-close:hover {
  background: var(--swarm-bg-hover);
  color: var(--swarm-text-primary);
}

@media (min-width: 1024px) {
  .sidebar-close {
    display: none;
  }
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.nav-section {
  margin-bottom: 8px;
}

.nav-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--swarm-text-muted);
  padding: 8px 20px 6px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  margin: 2px 8px;
  border-radius: 6px;
  color: var(--swarm-text-secondary);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
}

.nav-item:hover {
  background: var(--swarm-bg-hover);
  color: var(--swarm-text-primary);
}

.nav-item.router-link-active {
  background: var(--swarm-accent-bg);
  color: var(--swarm-accent);
}

.nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.archived-link {
  margin-top: 4px;
  opacity: 0.7;
}

.archived-link:hover {
  opacity: 1;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--swarm-border);
}

.footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.logout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  color: var(--swarm-text-muted);
  cursor: pointer;
  transition: all 0.15s;
}

.logout-btn:hover {
  background: var(--swarm-bg-hover);
  color: var(--swarm-text-primary);
}

/* Main content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.mobile-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--swarm-bg-secondary);
  border-bottom: 1px solid var(--swarm-border);
}

@media (min-width: 1024px) {
  .mobile-header {
    display: none;
  }
}

.menu-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: var(--swarm-text-secondary);
  cursor: pointer;
}

.menu-btn:hover {
  background: var(--swarm-bg-hover);
}

.mobile-logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.content-area {
  flex: 1;
  overflow: auto;
}
</style>
