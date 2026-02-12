<template>
  <div class="replay-controls-container">
    <div class="replay-controls">
      <!-- Left Section: Playback Controls -->
      <div class="controls-section controls-left">
        <!-- Play/Pause Button -->
        <button
          @click="togglePlayPause"
          class="control-btn control-btn-primary"
          :disabled="!canPlay"
          :title="isPlaying ? 'Pause' : 'Play'"
        >
          <svg v-if="!isPlaying" class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z"/>
          </svg>
          <svg v-else class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
          </svg>
        </button>

        <!-- Step Backward -->
        <button
          @click="stepBackward"
          class="control-btn"
          :disabled="currentIndex <= 0"
          title="Step Backward"
        >
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z"/>
          </svg>
        </button>

        <!-- Step Forward -->
        <button
          @click="stepForward"
          class="control-btn"
          :disabled="currentIndex >= totalPoints - 1"
          title="Step Forward"
        >
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z"/>
          </svg>
        </button>

        <!-- Reset Button -->
        <button
          @click="reset"
          class="control-btn"
          :disabled="currentIndex === 0 && !isPlaying"
          title="Reset to Start"
        >
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
          </svg>
        </button>

        <!-- Speed Control -->
        <div class="speed-selector">
          <button
            @click="toggleSpeedMenu"
            class="control-btn control-btn-speed"
            title="Playback Speed"
          >
            {{ speedLabel }}
          </button>
          
          <div v-if="showSpeedMenu" class="speed-menu" @click.stop>
            <button
              v-for="speed in availableSpeeds"
              :key="speed"
              @click="changeSpeed(speed)"
              class="speed-option"
              :class="{ active: playbackSpeed === speed }"
            >
              {{ speed }}x
            </button>
          </div>
        </div>
      </div>

      <!-- Center Section: Timeline -->
      <div class="controls-section controls-center">
        <!-- Current Time Display -->
        <div class="time-display">
          <span class="time-current">{{ formattedCurrentTime }}</span>
          <span class="time-separator">/</span>
          <span class="time-total">{{ formattedTotalTime }}</span>
        </div>

        <!-- Timeline Slider -->
        <div class="timeline-container">
          <input
            v-model.number="currentIndex"
            type="range"
            min="0"
            :max="totalPoints - 1"
            step="1"
            class="timeline-slider"
            :disabled="!canPlay"
            @input="handleTimelineChange"
            @mousedown="handleTimelineDragStart"
            @mouseup="handleTimelineDragEnd"
          />
          
          <!-- Progress Bar Fill -->
          <div class="timeline-fill" :style="{ width: progressPercentage + '%' }"></div>

          <!-- Timeline Markers (Optional: for trade events, etc.) -->
          <div v-if="markers.length > 0" class="timeline-markers">
            <div
              v-for="marker in markers"
              :key="marker.id"
              class="timeline-marker"
              :class="`marker-${marker.type}`"
              :style="{ left: markerPosition(marker.time) + '%' }"
              :title="`${marker.type}: ${formatPrice(marker.price)}`"
            ></div>
          </div>
        </div>

        <!-- Progress Percentage -->
        <div class="progress-text">
          {{ progressPercentage.toFixed(1) }}%
        </div>
      </div>

      <!-- Right Section: Additional Controls -->
      <div class="controls-section controls-right">
        <!-- Frame Rate Display -->
        <div v-if="showStats" class="stat-display" title="Current Frame">
          <svg class="w-3 h-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
          </svg>
          <span class="stat-value">{{ currentIndex + 1 }} / {{ totalPoints }}</span>
        </div>

        <!-- Loop Toggle -->
        <button
          @click="toggleLoop"
          class="control-btn"
          :class="{ active: isLooping }"
          title="Loop Replay"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
        </button>

        <!-- Settings/Options -->
        <button
          @click="$emit('settings')"
          class="control-btn"
          title="Replay Settings"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Status Bar (Optional: Shows current date, price, etc.) -->
    <div v-if="showStatusBar" class="status-bar">
      <div class="status-item">
        <span class="status-label">Date:</span>
        <span class="status-value">{{ formattedDate }}</span>
      </div>
      <div v-if="currentPrice !== null" class="status-item">
        <span class="status-label">Price:</span>
        <span class="status-value">{{ formatPrice(currentPrice) }}</span>
      </div>
      <div v-if="currentVolume !== null" class="status-item">
        <span class="status-label">Volume:</span>
        <span class="status-value">{{ formatVolume(currentVolume) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ReplayControls - Historical data replay controls for backtesting
 * 
 * Provides VCR-like controls for stepping through historical market data
 */

import type { CandleData, TradeMarker, Timeframe } from '~/types/chart'

// Props
const props = withDefaults(defineProps<{
  symbol?: string
  timeframe?: Timeframe
  totalPoints?: number
  currentTime?: number
  startTime?: number
  endTime?: number
  markers?: TradeMarker[]
  showStatusBar?: boolean
  showStats?: boolean
  disabled?: boolean
  currentPrice?: number | null
  currentVolume?: number | null
}>(), {
  symbol: 'ETH/USD',
  timeframe: '15m',
  totalPoints: 0,
  currentTime: 0,
  startTime: 0,
  endTime: 0,
  markers: () => [],
  showStatusBar: false,
  showStats: true,
  disabled: false,
  currentPrice: null,
  currentVolume: null,
})

// Emits
const emit = defineEmits<{
  play: []
  pause: []
  seek: [index: number]
  step: [direction: 'forward' | 'backward']
  reset: []
  speedChange: [speed: number]
  settings: []
  'markers-update': [markers: TradeMarker[]]
  'overlays-update': [overlays: any[]]
}>()

// State
const isPlaying = ref(false)
const currentIndex = ref(0)
const playbackSpeed = ref(1)
const isLooping = ref(false)
const showSpeedMenu = ref(false)
const isDraggingTimeline = ref(false)

// Available playback speeds
const availableSpeeds = [0.25, 0.5, 1, 2, 4, 8, 16]

// Computed
const canPlay = computed(() => {
  return props.totalPoints > 0 && !props.disabled
})

const progressPercentage = computed(() => {
  if (props.totalPoints === 0) return 0
  return (currentIndex.value / (props.totalPoints - 1)) * 100
})

const speedLabel = computed(() => {
  return `${playbackSpeed.value}x`
})

const formattedCurrentTime = computed(() => {
  if (!props.currentTime) return '00:00:00'
  return formatTimestamp(props.currentTime)
})

const formattedTotalTime = computed(() => {
  if (!props.endTime) return '00:00:00'
  return formatTimestamp(props.endTime)
})

const formattedDate = computed(() => {
  if (!props.currentTime) return 'N/A'
  return new Date(props.currentTime * 1000).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
})

// Playback interval ref
let playbackInterval: NodeJS.Timeout | null = null

// Methods
function togglePlayPause() {
  if (isPlaying.value) {
    pause()
  } else {
    play()
  }
}

function play() {
  if (!canPlay.value) return
  
  // If at the end, restart
  if (currentIndex.value >= props.totalPoints - 1) {
    if (isLooping.value) {
      currentIndex.value = 0
      emit('seek', 0)
    } else {
      return
    }
  }

  isPlaying.value = true
  emit('play')

  // Calculate interval based on speed (assuming 1 candle per second at 1x)
  const baseInterval = 1000 // 1 second per candle at 1x speed
  const interval = baseInterval / playbackSpeed.value

  playbackInterval = setInterval(() => {
    if (currentIndex.value < props.totalPoints - 1) {
      currentIndex.value++
      emit('seek', currentIndex.value)
    } else {
      // Reached the end
      if (isLooping.value) {
        currentIndex.value = 0
        emit('seek', 0)
      } else {
        pause()
      }
    }
  }, interval)
}

function pause() {
  isPlaying.value = false
  emit('pause')
  
  if (playbackInterval) {
    clearInterval(playbackInterval)
    playbackInterval = null
  }
}

function stepForward() {
  if (currentIndex.value < props.totalPoints - 1) {
    currentIndex.value++
    emit('seek', currentIndex.value)
    emit('step', 'forward')
  }
}

function stepBackward() {
  if (currentIndex.value > 0) {
    currentIndex.value--
    emit('seek', currentIndex.value)
    emit('step', 'backward')
  }
}

function reset() {
  pause()
  currentIndex.value = 0
  emit('seek', 0)
  emit('reset')
}

function changeSpeed(speed: number) {
  const wasPlaying = isPlaying.value
  pause()
  
  playbackSpeed.value = speed
  showSpeedMenu.value = false
  emit('speedChange', speed)

  if (wasPlaying) {
    // Resume playing with new speed
    nextTick(() => play())
  }
}

function toggleSpeedMenu() {
  showSpeedMenu.value = !showSpeedMenu.value
}

function toggleLoop() {
  isLooping.value = !isLooping.value
}

function handleTimelineChange() {
  emit('seek', currentIndex.value)
}

function handleTimelineDragStart() {
  isDraggingTimeline.value = true
  if (isPlaying.value) {
    pause()
  }
}

function handleTimelineDragEnd() {
  isDraggingTimeline.value = false
}

function markerPosition(time: number): number {
  if (!props.startTime || !props.endTime) return 0
  const totalDuration = props.endTime - props.startTime
  const markerOffset = time - props.startTime
  return (markerOffset / totalDuration) * 100
}

function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const seconds = date.getSeconds().toString().padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
}

function formatPrice(price: number): string {
  return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatVolume(volume: number): string {
  if (volume >= 1000000) {
    return `${(volume / 1000000).toFixed(2)}M`
  } else if (volume >= 1000) {
    return `${(volume / 1000).toFixed(2)}K`
  }
  return volume.toFixed(2)
}

// Cleanup
onBeforeUnmount(() => {
  if (playbackInterval) {
    clearInterval(playbackInterval)
  }
})

// Close speed menu when clicking outside
onMounted(() => {
  const handleClickOutside = (event: MouseEvent) => {
    const target = event.target as HTMLElement
    if (!target.closest('.speed-selector')) {
      showSpeedMenu.value = false
    }
  }
  
  document.addEventListener('click', handleClickOutside)
  
  onBeforeUnmount(() => {
    document.removeEventListener('click', handleClickOutside)
  })
})

// Watch for external index changes
watch(() => props.currentTime, (newTime) => {
  if (!props.startTime || !props.endTime || isDraggingTimeline.value) return
  
  // Calculate index from timestamp
  const totalDuration = props.endTime - props.startTime
  const offset = newTime - props.startTime
  const calculatedIndex = Math.floor((offset / totalDuration) * props.totalPoints)
  
  if (calculatedIndex !== currentIndex.value) {
    currentIndex.value = Math.max(0, Math.min(calculatedIndex, props.totalPoints - 1))
  }
})
</script>

<style scoped>
.replay-controls-container {
  background: linear-gradient(to bottom, 
    rgba(249, 250, 251, 0.95), 
    rgba(255, 255, 255, 0.95)
  );
  border: 1px solid rgba(229, 231, 235, 0.8);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

:global(.dark) .replay-controls-container {
  background: linear-gradient(to bottom,
    rgba(31, 41, 55, 0.95),
    rgba(17, 24, 39, 0.95)
  );
  border-color: rgba(55, 65, 81, 0.8);
}

.replay-controls {
  display: flex;
  align-items: center;
  gap: 24px;
}

.controls-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.controls-left {
  flex-shrink: 0;
}

.controls-center {
  flex: 1;
  min-width: 0;
  gap: 12px;
}

.controls-right {
  flex-shrink: 0;
}

/* Control Buttons */
.control-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid rgb(229, 231, 235);
  border-radius: 8px;
  background: white;
  color: rgb(75, 85, 99);
  cursor: pointer;
  transition: all 0.2s ease;
}

.control-btn:hover:not(:disabled) {
  background: rgb(249, 250, 251);
  border-color: rgb(209, 213, 219);
  color: rgb(17, 24, 39);
}

.control-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.control-btn.active {
  background: rgb(59, 130, 246);
  border-color: rgb(59, 130, 246);
  color: white;
}

:global(.dark) .control-btn {
  background: rgb(31, 41, 55);
  border-color: rgb(55, 65, 81);
  color: rgb(209, 213, 219);
}

:global(.dark) .control-btn:hover:not(:disabled) {
  background: rgb(55, 65, 81);
  border-color: rgb(75, 85, 99);
  color: rgb(243, 244, 246);
}

:global(.dark) .control-btn.active {
  background: rgb(37, 99, 235);
  border-color: rgb(37, 99, 235);
}

.control-btn-primary {
  width: 44px;
  height: 44px;
  background: rgb(59, 130, 246);
  border-color: rgb(59, 130, 246);
  color: white;
}

.control-btn-primary:hover:not(:disabled) {
  background: rgb(37, 99, 235);
  border-color: rgb(37, 99, 235);
}

:global(.dark) .control-btn-primary {
  background: rgb(37, 99, 235);
  border-color: rgb(37, 99, 235);
}

:global(.dark) .control-btn-primary:hover:not(:disabled) {
  background: rgb(29, 78, 216);
  border-color: rgb(29, 78, 216);
}

/* Speed Selector */
.speed-selector {
  position: relative;
}

.control-btn-speed {
  width: auto;
  min-width: 48px;
  padding: 0 12px;
  font-size: 0.875rem;
  font-weight: 500;
}

.speed-menu {
  position: absolute;
  bottom: 100%;
  left: 0;
  margin-bottom: 8px;
  background: white;
  border: 1px solid rgb(229, 231, 235);
  border-radius: 8px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  padding: 4px;
  z-index: 10;
  min-width: 80px;
}

:global(.dark) .speed-menu {
  background: rgb(31, 41, 55);
  border-color: rgb(55, 65, 81);
}

.speed-option {
  display: block;
  width: 100%;
  padding: 8px 12px;
  text-align: left;
  font-size: 0.875rem;
  border: none;
  background: transparent;
  color: rgb(75, 85, 99);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.speed-option:hover {
  background: rgb(243, 244, 246);
  color: rgb(17, 24, 39);
}

.speed-option.active {
  background: rgb(59, 130, 246);
  color: white;
}

:global(.dark) .speed-option {
  color: rgb(209, 213, 219);
}

:global(.dark) .speed-option:hover {
  background: rgb(55, 65, 81);
  color: rgb(243, 244, 246);
}

:global(.dark) .speed-option.active {
  background: rgb(37, 99, 235);
}

/* Time Display */
.time-display {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
  color: rgb(75, 85, 99);
}

:global(.dark) .time-display {
  color: rgb(209, 213, 219);
}

.time-current {
  color: rgb(17, 24, 39);
}

:global(.dark) .time-current {
  color: rgb(243, 244, 246);
}

.time-separator {
  color: rgb(156, 163, 175);
  margin: 0 2px;
}

.time-total {
  color: rgb(107, 114, 128);
}

:global(.dark) .time-total {
  color: rgb(156, 163, 175);
}

/* Timeline */
.timeline-container {
  position: relative;
  flex: 1;
  height: 32px;
  display: flex;
  align-items: center;
}

.timeline-slider {
  position: absolute;
  width: 100%;
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
  outline: none;
  cursor: pointer;
  z-index: 2;
}

.timeline-slider::-webkit-slider-track {
  width: 100%;
  height: 4px;
  background: transparent;
  border-radius: 2px;
}

.timeline-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  background: rgb(59, 130, 246);
  border: 2px solid white;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: all 0.15s ease;
}

.timeline-slider::-webkit-slider-thumb:hover {
  transform: scale(1.15);
}

.timeline-slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: rgb(59, 130, 246);
  border: 2px solid white;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: all 0.15s ease;
}

.timeline-slider::-moz-range-thumb:hover {
  transform: scale(1.15);
}

:global(.dark) .timeline-slider::-webkit-slider-thumb {
  background: rgb(37, 99, 235);
  border-color: rgb(31, 41, 55);
}

:global(.dark) .timeline-slider::-moz-range-thumb {
  background: rgb(37, 99, 235);
  border-color: rgb(31, 41, 55);
}

.timeline-fill {
  position: absolute;
  left: 0;
  height: 4px;
  background: linear-gradient(to right, rgb(59, 130, 246), rgb(37, 99, 235));
  border-radius: 2px;
  pointer-events: none;
  transition: width 0.1s linear;
  z-index: 1;
}

.timeline-slider:disabled + .timeline-fill {
  background: rgb(209, 213, 219);
}

:global(.dark) .timeline-fill {
  background: linear-gradient(to right, rgb(37, 99, 235), rgb(29, 78, 216));
}

:global(.dark) .timeline-slider:disabled + .timeline-fill {
  background: rgb(55, 65, 81);
}

/* Timeline base track */
.timeline-container::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  height: 4px;
  background: rgb(229, 231, 235);
  border-radius: 2px;
  pointer-events: none;
}

:global(.dark) .timeline-container::before {
  background: rgb(55, 65, 81);
}

/* Timeline Markers */
.timeline-markers {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.timeline-marker {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.marker-buy {
  background: rgb(34, 197, 94);
}

.marker-sell {
  background: rgb(239, 68, 68);
}

:global(.dark) .timeline-marker {
  border-color: rgb(31, 41, 55);
}

/* Progress Text */
.progress-text {
  font-size: 0.75rem;
  font-weight: 500;
  color: rgb(107, 114, 128);
  white-space: nowrap;
}

:global(.dark) .progress-text {
  color: rgb(156, 163, 175);
}

/* Stat Display */
.stat-display {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgb(243, 244, 246);
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 500;
  color: rgb(75, 85, 99);
}

:global(.dark) .stat-display {
  background: rgb(55, 65, 81);
  color: rgb(209, 213, 219);
}

.stat-value {
  font-family: ui-monospace, monospace;
}

/* Status Bar */
.status-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgb(229, 231, 235);
}

:global(.dark) .status-bar {
  border-top-color: rgb(55, 65, 81);
}

.status-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 0.875rem;
}

.status-label {
  font-weight: 500;
  color: rgb(107, 114, 128);
}

:global(.dark) .status-label {
  color: rgb(156, 163, 175);
}

.status-value {
  font-weight: 600;
  color: rgb(17, 24, 39);
  font-family: ui-monospace, monospace;
}

:global(.dark) .status-value {
  color: rgb(243, 244, 246);
}

/* Responsive */
@media (max-width: 768px) {
  .replay-controls {
    flex-wrap: wrap;
    gap: 16px;
  }

  .controls-center {
    order: 3;
    flex-basis: 100%;
  }

  .time-display {
    font-size: 0.75rem;
  }

  .control-btn {
    width: 32px;
    height: 32px;
  }

  .control-btn-primary {
    width: 40px;
    height: 40px;
  }

  .status-bar {
    flex-wrap: wrap;
    gap: 12px;
  }
}
</style>
