import { ref, watch, onUnmounted } from 'vue'
import type { Ref, WatchSource } from 'vue'

export interface AutoSaveOptions<T> {
  /** Data source to watch */
  source: WatchSource<T>
  /** Save function that performs the actual save */
  onSave: (data: T) => Promise<void>
  /** Debounce delay in milliseconds (default: 2000) */
  debounceMs?: number
  /** Whether auto-save is enabled (default: true) */
  enabled?: Ref<boolean> | boolean
  /** Called when save starts */
  onSaveStart?: () => void
  /** Called when save succeeds */
  onSaveSuccess?: () => void
  /** Called when save fails */
  onSaveError?: (error: unknown) => void
}

export interface AutoSaveReturn {
  /** Current saving state */
  saving: Ref<boolean>
  /** Last save error (null if none) */
  error: Ref<string | null>
  /** Time of last successful save */
  lastSaved: Ref<Date | null>
  /** Whether there are unsaved changes */
  hasUnsavedChanges: Ref<boolean>
  /** Force save immediately */
  saveNow: () => Promise<void>
  /** Cancel pending save */
  cancel: () => void
}

export function useAutoSave<T>(options: AutoSaveOptions<T>): AutoSaveReturn {
  const {
    source,
    onSave,
    debounceMs = 2000,
    enabled = true,
    onSaveStart,
    onSaveSuccess,
    onSaveError,
  } = options

  const saving = ref(false)
  const error = ref<string | null>(null)
  const lastSaved = ref<Date | null>(null)
  const hasUnsavedChanges = ref(false)

  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let pendingData: T | null = null

  const isEnabled = () => {
    if (typeof enabled === 'boolean') return enabled
    return enabled.value
  }

  const cancel = () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
  }

  const performSave = async (data: T) => {
    if (saving.value) {
      pendingData = data
      return
    }

    saving.value = true
    error.value = null
    onSaveStart?.()

    try {
      await onSave(data)
      lastSaved.value = new Date()
      hasUnsavedChanges.value = false
      onSaveSuccess?.()

      if (pendingData !== null) {
        const nextData = pendingData
        pendingData = null
        await performSave(nextData)
      }
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : 'Failed to save'
      error.value = errorMessage
      onSaveError?.(e)
    } finally {
      saving.value = false
    }
  }

  const saveNow = async () => {
    cancel()
    const currentValue = typeof source === 'function' 
      ? (source as () => T)() 
      : (source as Ref<T>).value
    await performSave(currentValue)
  }

  const scheduleSave = (data: T) => {
    if (!isEnabled()) return
    
    hasUnsavedChanges.value = true
    cancel()
    
    debounceTimer = setTimeout(() => {
      performSave(data)
    }, debounceMs)
  }

  const stopWatch = watch(
    source,
    (newValue) => {
      scheduleSave(newValue as T)
    },
    { deep: true }
  )

  onUnmounted(() => {
    cancel()
    stopWatch()
  })

  return {
    saving,
    error,
    lastSaved,
    hasUnsavedChanges,
    saveNow,
    cancel,
  }
}
