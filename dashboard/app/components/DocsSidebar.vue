<script setup lang="ts">
interface DocSection {
  id: string
  label: string
  icon: string
  children?: { id: string; label: string }[]
}

const props = defineProps<{
  sections: DocSection[]
  title?: string
  icon?: string
}>()

const activeSection = defineModel<string>('activeSection', { default: '' })

const expandedSections = ref<Set<string>>(new Set())

function toggleSection(sectionId: string) {
  if (expandedSections.value.has(sectionId)) {
    expandedSections.value.delete(sectionId)
  } else {
    expandedSections.value.add(sectionId)
  }
}

function selectSection(id: string, parentId?: string) {
  activeSection.value = id
  if (parentId) {
    expandedSections.value.add(parentId)
  }
}

function isActive(sectionId: string, children?: { id: string; label: string }[]): boolean {
  if (activeSection.value === sectionId) return true
  if (children?.some(child => child.id === activeSection.value)) return true
  return false
}
</script>

<template>
  <div class="docs-sidebar">
    <div class="sidebar-header">
      <UIcon :name="icon || 'i-heroicons-book-open'" class="w-5 h-5" />
      <span>{{ title || 'Documentation' }}</span>
    </div>
    <nav class="sidebar-nav">
      <div v-for="section in sections" :key="section.id" class="nav-section">
        <button
          class="nav-item"
          :class="{ active: isActive(section.id, section.children) }"
          @click="section.children ? (toggleSection(section.id), selectSection(section.id)) : selectSection(section.id)"
        >
          <UIcon :name="section.icon" class="w-4 h-4" />
          <span class="nav-label">{{ section.label }}</span>
          <UIcon
            v-if="section.children"
            name="i-heroicons-chevron-right"
            class="w-3 h-3 expand-icon"
            :class="{ expanded: expandedSections.has(section.id) }"
          />
        </button>
        
        <div
          v-if="section.children"
          class="nav-children"
          :class="{ expanded: expandedSections.has(section.id) }"
        >
          <button
            v-for="child in section.children"
            :key="child.id"
            class="nav-child"
            :class="{ active: activeSection === child.id }"
            @click="selectSection(child.id, section.id)"
          >
            {{ child.label }}
          </button>
        </div>
      </div>
    </nav>
  </div>
</template>

<style scoped>
.docs-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: var(--swarm-bg-secondary);
  border-right: 1px solid var(--swarm-border);
  padding: 20px 0;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px 16px;
  font-size: 15px;
  font-weight: 600;
  color: var(--swarm-text-primary);
  border-bottom: 1px solid var(--swarm-border);
  margin-bottom: 12px;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 8px;
  overflow-y: auto;
  flex: 1;
}

.nav-section {
  display: flex;
  flex-direction: column;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 14px;
  color: var(--swarm-text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  width: 100%;
  transition: all 0.15s;
}

.nav-item:hover {
  background: var(--swarm-bg-hover);
  color: var(--swarm-text-primary);
}

.nav-item.active {
  background: var(--swarm-accent-bg);
  color: var(--swarm-accent);
}

.nav-label {
  flex: 1;
}

.expand-icon {
  transition: transform 0.2s;
  opacity: 0.5;
}

.expand-icon.expanded {
  transform: rotate(90deg);
}

.nav-children {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.2s;
  overflow: hidden;
}

.nav-children.expanded {
  grid-template-rows: 1fr;
}

.nav-children > div,
.nav-children > button {
  min-height: 0;
}

.nav-child {
  display: block;
  padding: 8px 12px 8px 38px;
  font-size: 13px;
  color: var(--swarm-text-muted);
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  width: 100%;
  border-radius: 6px;
  transition: all 0.15s;
}

.nav-child:hover {
  color: var(--swarm-text-secondary);
  background: var(--swarm-bg-hover);
}

.nav-child.active {
  color: var(--swarm-accent);
  background: var(--swarm-accent-bg);
}

@media (max-width: 768px) {
  .docs-sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid var(--swarm-border);
    padding: 12px 0;
  }
  
  .sidebar-header {
    padding: 0 16px 12px;
    margin-bottom: 8px;
  }
  
  .sidebar-nav {
    flex-direction: row;
    overflow-x: auto;
    padding: 0 8px;
    gap: 4px;
  }
  
  .nav-section {
    flex-shrink: 0;
  }
  
  .nav-item {
    white-space: nowrap;
    padding: 8px 12px;
  }
  
  .nav-children {
    display: none;
  }
  
  .expand-icon {
    display: none;
  }
}
</style>
