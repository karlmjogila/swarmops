<script setup lang="ts">
const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const isMac = computed(() => {
  if (typeof navigator !== 'undefined') {
    return navigator.platform?.toLowerCase().includes('mac')
  }
  return false
})

const modKey = computed(() => isMac.value ? '⌘' : 'Ctrl')

const shortcuts = computed(() => [
  {
    category: 'Selection',
    items: [
      { keys: [`${modKey.value}+A`], description: 'Select all nodes' },
      { keys: ['Escape'], description: 'Deselect all' },
      { keys: ['Click'], description: 'Select node/edge' },
      { keys: [`${modKey.value}+Click`], description: 'Multi-select' },
    ],
  },
  {
    category: 'Edit',
    items: [
      { keys: ['Delete', 'Backspace'], description: 'Delete selected' },
      { keys: [`${modKey.value}+Z`], description: 'Undo' },
      { keys: [`${modKey.value}+Shift+Z`, `${modKey.value}+Y`], description: 'Redo' },
    ],
  },
  {
    category: 'File',
    items: [
      { keys: [`${modKey.value}+S`], description: 'Save pipeline' },
    ],
  },
  {
    category: 'View',
    items: [
      { keys: ['Scroll'], description: 'Zoom in/out' },
      { keys: ['Drag canvas'], description: 'Pan view' },
    ],
  },
])
</script>

<template>
  <UModal v-model:open="isOpen">
    <template #content>
      <div class="shortcuts-modal">
        <div class="modal-header">
          <h3 class="modal-title">
            <UIcon name="i-heroicons-command-line" class="w-5 h-5" />
            Keyboard Shortcuts
          </h3>
          <button class="close-btn" @click="isOpen = false">
            <UIcon name="i-heroicons-x-mark" class="w-5 h-5" />
          </button>
        </div>

        <div class="modal-body">
          <div
            v-for="section in shortcuts"
            :key="section.category"
            class="shortcut-section"
          >
            <h4 class="section-title">{{ section.category }}</h4>
            <div class="shortcut-list">
              <div
                v-for="(shortcut, idx) in section.items"
                :key="idx"
                class="shortcut-item"
              >
                <div class="shortcut-keys">
                  <kbd
                    v-for="(key, keyIdx) in shortcut.keys"
                    :key="keyIdx"
                    class="key"
                  >
                    {{ key }}
                  </kbd>
                </div>
                <span class="shortcut-desc">{{ shortcut.description }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <span class="hint">
            <UIcon name="i-heroicons-light-bulb" class="w-4 h-4" />
            Press <kbd class="key-inline">?</kbd> to toggle this help
          </span>
        </div>
      </div>
    </template>
  </UModal>
</template>

<style scoped>
.shortcuts-modal {
  background: var(--swarm-bg-card, var(--swarm-bg-card));
  border-radius: 12px;
  overflow: hidden;
  min-width: 400px;
  max-width: 480px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--swarm-border, var(--swarm-border));
  background: var(--swarm-bg-hover, var(--swarm-bg-primary));
}

.modal-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--swarm-text-primary, var(--swarm-text-primary));
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
  border-radius: 6px;
  color: var(--swarm-text-muted, var(--swarm-text-muted));
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
}

.close-btn:hover {
  background: var(--swarm-bg-card, var(--swarm-bg-card));
  color: var(--swarm-text-primary, var(--swarm-text-primary));
}

.modal-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.shortcut-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--swarm-text-muted, var(--swarm-text-muted));
}

.shortcut-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.shortcut-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--swarm-bg-hover, var(--swarm-bg-primary));
  border-radius: 8px;
  gap: 16px;
}

.shortcut-keys {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 500;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Mono', Monaco, 'Inconsolata', monospace;
  color: var(--swarm-text-primary, var(--swarm-text-primary));
  background: var(--swarm-bg-card, var(--swarm-bg-card));
  border: 1px solid var(--swarm-border, var(--swarm-border));
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.shortcut-desc {
  font-size: 13px;
  color: var(--swarm-text-secondary, var(--swarm-text-secondary));
  text-align: right;
}

.modal-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--swarm-border, var(--swarm-border));
  background: var(--swarm-bg-hover, var(--swarm-bg-primary));
}

.hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  color: var(--swarm-text-muted, var(--swarm-text-muted));
}

.key-inline {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 500;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Mono', Monaco, monospace;
  color: var(--swarm-text-primary, var(--swarm-text-primary));
  background: var(--swarm-bg-card, var(--swarm-bg-card));
  border: 1px solid var(--swarm-border, var(--swarm-border));
  border-radius: 3px;
}
</style>
