<script setup lang="ts">
import { marked } from 'marked'

useHead({
  title: 'Documentation - SwarmOps'
})

const route = useRoute()
const router = useRouter()

const docPages = [
  { slug: 'index', title: 'Overview', icon: 'i-heroicons-home' },
  { slug: 'architecture', title: 'Architecture', icon: 'i-heroicons-cube-transparent' },
  { slug: 'agent-context', title: 'Agent Context', icon: 'i-heroicons-cpu-chip' },
  { slug: 'operations', title: 'Operations', icon: 'i-heroicons-wrench-screwdriver' },
  { slug: 'resilience', title: 'Resilience', icon: 'i-heroicons-shield-check' }
]

const currentPage = computed(() => {
  const page = route.query.page as string || 'index'
  return docPages.find(p => p.slug === page) || docPages[0]
})

const content = ref('')
const loading = ref(true)
const error = ref<string | null>(null)

// Initialize Mermaid
let mermaidInitialized = false
async function initMermaid() {
  if (mermaidInitialized || typeof window === 'undefined') return
  
  const mermaid = await import('mermaid')
  mermaid.default.initialize({
    startOnLoad: false,
    theme: 'base',
    themeVariables: {
      // Light background theme
      primaryColor: '#10b981',
      primaryTextColor: '#1e293b',
      primaryBorderColor: '#10b981',
      lineColor: '#64748b',
      secondaryColor: '#f1f5f9',
      tertiaryColor: '#e2e8f0',
      background: '#ffffff',
      mainBkg: '#f8fafc',
      nodeBorder: '#cbd5e1',
      clusterBkg: '#f1f5f9',
      clusterBorder: '#e2e8f0',
      titleColor: '#1e293b',
      edgeLabelBackground: '#ffffff',
      actorBkg: '#f8fafc',
      actorBorder: '#10b981',
      actorTextColor: '#1e293b',
      // Text colors
      nodeTextColor: '#1e293b',
      textColor: '#1e293b',
    },
    flowchart: {
      curve: 'basis',
      padding: 20,
      nodeSpacing: 50,
      rankSpacing: 60,
    },
    fontSize: 18,
  })
  mermaidInitialized = true
}

// Render Mermaid diagrams in the content
async function renderMermaid() {
  if (typeof window === 'undefined') return
  
  await initMermaid()
  const mermaid = await import('mermaid')
  
  // Find all mermaid code blocks and render them
  await nextTick()
  const codeBlocks = document.querySelectorAll('.docs-article pre code.language-mermaid')
  
  for (const block of codeBlocks) {
    const pre = block.parentElement
    if (!pre) continue
    
    const code = block.textContent || ''
    const id = `mermaid-${Math.random().toString(36).slice(2, 9)}`
    
    try {
      const { svg } = await mermaid.default.render(id, code)
      const wrapper = document.createElement('div')
      wrapper.className = 'mermaid-diagram'
      wrapper.innerHTML = svg
      pre.replaceWith(wrapper)
    } catch (err) {
      console.error('Mermaid render error:', err)
    }
  }
}

async function loadDoc(slug: string) {
  loading.value = true
  error.value = null
  try {
    const res = await fetch(`/docs/${slug}.md`)
    if (!res.ok) throw new Error('Doc not found')
    const md = await res.text()
    content.value = marked.parse(md) as string
    
    // Render Mermaid diagrams after content is loaded
    await nextTick()
    renderMermaid()
  } catch (e) {
    error.value = 'Failed to load documentation'
    content.value = ''
  } finally {
    loading.value = false
  }
}

watch(() => route.query.page, () => {
  loadDoc(currentPage.value.slug)
}, { immediate: true })

function navigateTo(slug: string) {
  router.push({ path: '/docs', query: { page: slug } })
}
</script>

<template>
  <div class="docs-layout">
    <aside class="docs-sidebar">
      <div class="docs-sidebar-header">
        <h2>Documentation</h2>
      </div>
      <nav class="docs-nav">
        <button
          v-for="page in docPages"
          :key="page.slug"
          class="docs-nav-item"
          :class="{ active: currentPage.slug === page.slug }"
          @click="navigateTo(page.slug)"
        >
          <UIcon :name="page.icon" class="nav-icon" />
          <span>{{ page.title }}</span>
        </button>
      </nav>
    </aside>

    <main class="docs-content">
      <div v-if="loading" class="docs-loading">
        <UIcon name="i-heroicons-document-text" class="w-8 h-8 animate-pulse" />
        <p>Loading documentation...</p>
      </div>
      
      <div v-else-if="error" class="docs-error">
        <UIcon name="i-heroicons-exclamation-triangle" class="w-8 h-8" />
        <p>{{ error }}</p>
      </div>
      
      <article v-else class="docs-article" v-html="content" />
    </main>
  </div>
</template>

<style scoped>
.docs-layout {
  display: flex;
  min-height: 100%;
}

.docs-sidebar {
  width: 220px;
  flex-shrink: 0;
  background: var(--swarm-bg-secondary);
  border-right: 1px solid var(--swarm-border);
  height: calc(100vh - 60px);
  position: sticky;
  top: 0;
}

@media (max-width: 768px) {
  .docs-layout {
    flex-direction: column;
  }
  
  .docs-sidebar {
    width: 100%;
    height: auto;
    position: relative;
    border-right: none;
    border-bottom: 1px solid var(--swarm-border);
  }
}

.docs-sidebar-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--swarm-border);
}

.docs-sidebar-header h2 {
  font-size: 14px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  margin: 0;
}

.docs-nav {
  padding: 8px;
}

.docs-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 6px;
  border: none;
  background: none;
  color: var(--swarm-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
  font-family: inherit;
}

.docs-nav-item:hover {
  background: var(--swarm-bg-hover);
  color: var(--swarm-text-primary);
}

.docs-nav-item.active {
  background: var(--swarm-accent-bg);
  color: var(--swarm-accent);
}

.docs-nav-item .nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.docs-content {
  flex: 1;
  min-width: 0;
  padding: 32px 40px;
  max-width: 900px;
}

@media (max-width: 768px) {
  .docs-content {
    padding: 20px 16px;
  }
}

.docs-loading,
.docs-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 20px;
  color: var(--swarm-text-muted);
}

.docs-error {
  color: var(--swarm-error);
}

.docs-article {
  color: var(--swarm-text-primary);
  line-height: 1.7;
}

.docs-article :deep(h1) {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 8px 0;
  color: var(--swarm-text-primary);
}

.docs-article :deep(h2) {
  font-size: 20px;
  font-weight: 600;
  margin: 32px 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--swarm-border);
  color: var(--swarm-text-primary);
}

.docs-article :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  margin: 24px 0 12px 0;
  color: var(--swarm-text-primary);
}

.docs-article :deep(p) {
  margin: 0 0 16px 0;
  color: var(--swarm-text-secondary);
}

.docs-article :deep(ul),
.docs-article :deep(ol) {
  margin: 0 0 16px 0;
  padding-left: 24px;
  color: var(--swarm-text-secondary);
}

.docs-article :deep(li) {
  margin-bottom: 6px;
}

.docs-article :deep(code) {
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  font-size: 13px;
  background: var(--swarm-bg-tertiary);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--swarm-accent);
}

.docs-article :deep(pre) {
  background: var(--swarm-bg-tertiary);
  border: 1px solid var(--swarm-border);
  border-radius: 8px;
  padding: 16px;
  margin: 0 0 20px 0;
  overflow-x: auto;
}

.docs-article :deep(pre code) {
  background: none;
  padding: 0;
  color: var(--swarm-text-primary);
  font-size: 13px;
  line-height: 1.6;
}

.docs-article :deep(a) {
  color: var(--swarm-accent);
  text-decoration: none;
}

.docs-article :deep(a:hover) {
  text-decoration: underline;
}

.docs-article :deep(blockquote) {
  border-left: 3px solid var(--swarm-accent);
  margin: 0 0 16px 0;
  padding: 12px 16px;
  background: var(--swarm-accent-bg);
  border-radius: 0 6px 6px 0;
}

.docs-article :deep(blockquote p) {
  margin: 0;
}

.docs-article :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 20px 0;
}

.docs-article :deep(th),
.docs-article :deep(td) {
  padding: 10px 12px;
  border: 1px solid var(--swarm-border);
  text-align: left;
}

.docs-article :deep(th) {
  background: var(--swarm-bg-secondary);
  font-weight: 600;
}

.docs-article :deep(hr) {
  border: none;
  border-top: 1px solid var(--swarm-border);
  margin: 32px 0;
}

/* Mermaid diagrams - light background for readability */
.docs-article :deep(.mermaid-diagram) {
  margin: 24px 0;
  padding: 24px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow-x: auto;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.docs-article :deep(.mermaid-diagram svg) {
  display: block;
  margin: 0 auto;
  max-width: 100%;
  height: auto;
  min-height: 200px;
}

/* Ensure text is dark on light background */
.docs-article :deep(.mermaid-diagram .nodeLabel),
.docs-article :deep(.mermaid-diagram .label),
.docs-article :deep(.mermaid-diagram text) {
  fill: #1e293b !important;
  color: #1e293b !important;
}

.docs-article :deep(.mermaid-diagram .edgeLabel) {
  background: #ffffff !important;
  color: #475569 !important;
}

/* Node styling */
.docs-article :deep(.mermaid-diagram .node rect),
.docs-article :deep(.mermaid-diagram .node circle),
.docs-article :deep(.mermaid-diagram .node polygon) {
  stroke-width: 2px;
}
</style>
