<script setup lang="ts">
const props = defineProps<{
  projectName: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  'pipeline-started': [result: any]
  'pipeline-error': [error: Error]
}>()

const toast = useToast()
const loading = ref(false)
const lastResult = ref<any>(null)

async function runPipeline() {
  if (loading.value) return
  
  loading.value = true
  lastResult.value = null
  
  try {
    const result = await $fetch(`/api/projects/${props.projectName}/orchestrate`, {
      method: 'POST',
      body: { action: 'start' }
    })
    
    lastResult.value = result
    
    if (result.status === 'complete') {
      toast.add({
        title: 'Pipeline Complete',
        description: 'All tasks have been completed!',
        icon: 'i-heroicons-check-circle',
        color: 'success',
        duration: 5000
      })
    } else if (result.status === 'blocked') {
      toast.add({
        title: 'Pipeline Blocked',
        description: result.message,
        icon: 'i-heroicons-exclamation-triangle',
        color: 'warning',
        duration: 5000
      })
    } else if (result.spawned?.length > 0) {
      toast.add({
        title: 'Pipeline Running',
        description: `Spawned ${result.spawned.length} worker${result.spawned.length > 1 ? 's' : ''}`,
        icon: 'i-heroicons-rocket-launch',
        color: 'success',
        duration: 4000
      })
    }
    
    emit('pipeline-started', result)
  } catch (error) {
    const err = error instanceof Error ? error : new Error('Unknown error')
    toast.add({
      title: 'Pipeline Failed',
      description: err.message,
      icon: 'i-heroicons-x-circle',
      color: 'error',
      duration: 5000
    })
    emit('pipeline-error', err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <button
    class="run-pipeline-btn"
    :class="{ loading }"
    :disabled="disabled || loading"
    @click="runPipeline"
  >
    <UIcon 
      v-if="loading" 
      name="i-heroicons-arrow-path" 
      class="w-5 h-5 animate-spin" 
    />
    <UIcon 
      v-else 
      name="i-heroicons-play" 
      class="w-5 h-5" 
    />
    <span>{{ loading ? 'Starting...' : 'Run Pipeline' }}</span>
  </button>
</template>

<style scoped>
.run-pipeline-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.run-pipeline-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
}

.run-pipeline-btn:active:not(:disabled) {
  transform: translateY(0);
}

.run-pipeline-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.run-pipeline-btn.loading {
  background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
  box-shadow: 0 2px 8px rgba(107, 114, 128, 0.3);
}
</style>
