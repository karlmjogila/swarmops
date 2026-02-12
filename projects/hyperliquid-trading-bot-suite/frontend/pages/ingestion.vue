<template>
  <div class="ingestion-page">
    <!-- SVG Noise Texture Overlay -->
    <svg class="grain-overlay">
      <filter id="grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="4" stitchTiles="stitch"/>
      </filter>
      <rect width="100%" height="100%" filter="url(#grain)"/>
    </svg>

    <!-- Hero Section -->
    <section class="hero-section reveal">
      <div class="hero-content">
        <h1 class="hero-title">Knowledge Ingestion</h1>
        <p class="hero-subtitle">Transform educational content into actionable trading strategies</p>
        <div class="stats-row">
          <div class="stat-card reveal">
            <div class="stat-value">{{ stats.totalProcessed }}</div>
            <div class="stat-label">Sources Processed</div>
          </div>
          <div class="stat-card reveal">
            <div class="stat-value">{{ stats.strategiesExtracted }}</div>
            <div class="stat-label">Strategies Extracted</div>
          </div>
          <div class="stat-card reveal">
            <div class="stat-value">{{ stats.successRate }}%</div>
            <div class="stat-label">Success Rate</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Upload Section -->
    <section class="upload-section reveal">
      <div class="section-container">
        <h2 class="section-title">Upload Content</h2>
        <p class="section-description">Upload PDFs, videos, or paste content to extract trading strategies</p>
        
        <div class="upload-tabs">
          <button 
            v-for="tab in uploadTabs" 
            :key="tab.id"
            :class="['tab-button', { active: activeTab === tab.id }]"
            @click="activeTab = tab.id"
          >
            <span class="tab-icon">{{ tab.icon }}</span>
            <span class="tab-label">{{ tab.label }}</span>
          </button>
        </div>

        <!-- PDF Upload Tab -->
        <div v-if="activeTab === 'pdf'" class="upload-panel">
          <div 
            class="drop-zone"
            :class="{ 'is-dragging': isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
          >
            <input 
              ref="fileInput"
              type="file" 
              accept=".pdf"
              multiple
              @change="handleFileSelect"
              class="file-input"
            />
            <div class="drop-zone-content">
              <div class="upload-icon">📄</div>
              <p class="drop-zone-title">Drop PDF files here or click to browse</p>
              <p class="drop-zone-subtitle">Support for multiple files • Max 50MB per file</p>
              <button class="browse-button" @click="$refs.fileInput.click()">
                Browse Files
              </button>
            </div>
          </div>

          <!-- Selected Files -->
          <div v-if="selectedFiles.length > 0" class="selected-files">
            <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
              <div class="file-icon">📄</div>
              <div class="file-info">
                <div class="file-name">{{ file.name }}</div>
                <div class="file-size">{{ formatFileSize(file.size) }}</div>
              </div>
              <button class="remove-button" @click="removeFile(index)">×</button>
            </div>
          </div>

          <!-- Tags Input -->
          <div class="tags-section">
            <label class="input-label">Tags (optional)</label>
            <input 
              v-model="tagInput"
              type="text" 
              placeholder="e.g., scalping, market-structure, supply-demand"
              class="text-input"
            />
          </div>

          <button 
            class="process-button"
            :disabled="selectedFiles.length === 0 || isProcessing"
            @click="processFiles"
          >
            {{ isProcessing ? 'Processing...' : 'Process Files' }}
          </button>
        </div>

        <!-- Video Tab -->
        <div v-if="activeTab === 'video'" class="upload-panel">
          <div class="input-group">
            <label class="input-label">Video URL</label>
            <input 
              v-model="videoUrl"
              type="url" 
              placeholder="https://youtube.com/watch?v=..."
              class="text-input"
            />
          </div>

          <div class="input-group">
            <label class="input-label">Or paste video transcript</label>
            <textarea 
              v-model="videoTranscript"
              placeholder="Paste the video transcript here..."
              rows="8"
              class="textarea-input"
            ></textarea>
          </div>

          <div class="tags-section">
            <label class="input-label">Tags (optional)</label>
            <input 
              v-model="tagInput"
              type="text" 
              placeholder="e.g., scalping, market-structure"
              class="text-input"
            />
          </div>

          <button 
            class="process-button"
            :disabled="(!videoUrl && !videoTranscript) || isProcessing"
            @click="processVideo"
          >
            {{ isProcessing ? 'Processing...' : 'Process Video' }}
          </button>
        </div>

        <!-- Text Tab -->
        <div v-if="activeTab === 'text'" class="upload-panel">
          <div class="input-group">
            <label class="input-label">Title</label>
            <input 
              v-model="textTitle"
              type="text" 
              placeholder="Strategy name or content title"
              class="text-input"
            />
          </div>

          <div class="input-group">
            <label class="input-label">Content</label>
            <textarea 
              v-model="textContent"
              placeholder="Paste trading strategy content here..."
              rows="12"
              class="textarea-input"
            ></textarea>
          </div>

          <div class="tags-section">
            <label class="input-label">Tags (optional)</label>
            <input 
              v-model="tagInput"
              type="text" 
              placeholder="e.g., breakout, confluence"
              class="text-input"
            />
          </div>

          <button 
            class="process-button"
            :disabled="!textContent || isProcessing"
            @click="processText"
          >
            {{ isProcessing ? 'Processing...' : 'Process Content' }}
          </button>
        </div>
      </div>
    </section>

    <!-- Processing Queue -->
    <section v-if="processingQueue.length > 0" class="queue-section reveal">
      <div class="section-container">
        <h2 class="section-title">Processing Queue</h2>
        <div class="queue-list">
          <div 
            v-for="item in processingQueue" 
            :key="item.id"
            class="queue-item"
            :class="item.status"
          >
            <div class="queue-icon">
              <span v-if="item.status === 'processing'">⚡</span>
              <span v-if="item.status === 'completed'">✓</span>
              <span v-if="item.status === 'error'">✗</span>
            </div>
            <div class="queue-info">
              <div class="queue-name">{{ item.name }}</div>
              <div class="queue-status">{{ item.statusText }}</div>
            </div>
            <div class="queue-progress">
              <div class="progress-bar" :style="{ width: item.progress + '%' }"></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Extracted Strategies -->
    <section class="strategies-section reveal">
      <div class="section-container">
        <h2 class="section-title">Extracted Strategies</h2>
        <p class="section-description">Recently extracted trading strategies from your content</p>
        
        <div class="strategies-grid">
          <div 
            v-for="strategy in extractedStrategies" 
            :key="strategy.id"
            class="strategy-card reveal"
          >
            <div class="strategy-header">
              <h3 class="strategy-name">{{ strategy.name }}</h3>
              <div class="confidence-badge" :class="getConfidenceClass(strategy.confidence)">
                {{ Math.round(strategy.confidence * 100) }}%
              </div>
            </div>
            <p class="strategy-description">{{ strategy.description }}</p>
            <div class="strategy-meta">
              <div class="meta-item">
                <span class="meta-label">Source:</span>
                <span class="meta-value">{{ strategy.source }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Type:</span>
                <span class="meta-value">{{ strategy.type }}</span>
              </div>
            </div>
            <div class="strategy-tags">
              <span v-for="tag in strategy.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>
            <div class="strategy-actions">
              <button class="action-button primary">View Details</button>
              <button class="action-button">Test</button>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'

// State
const activeTab = ref('pdf')
const isDragging = ref(false)
const selectedFiles = ref([])
const isProcessing = ref(false)
const videoUrl = ref('')
const videoTranscript = ref('')
const textTitle = ref('')
const textContent = ref('')
const tagInput = ref('')

const uploadTabs = [
  { id: 'pdf', label: 'PDF', icon: '📄' },
  { id: 'video', label: 'Video', icon: '🎥' },
  { id: 'text', label: 'Text', icon: '📝' }
]

const stats = reactive({
  totalProcessed: 47,
  strategiesExtracted: 142,
  successRate: 94.7
})

const processingQueue = ref([])

const extractedStrategies = ref([
  {
    id: 1,
    name: 'Liquidity Engulf Entry',
    description: 'Entry strategy based on liquidity sweeps and engulfing candles at key levels',
    source: 'Trading Guide.pdf',
    type: 'Entry Pattern',
    confidence: 0.92,
    tags: ['liquidity', 'engulf', 'entry']
  },
  {
    id: 2,
    name: 'Market Structure Break',
    description: 'Identify market structure shifts using BOS and CHoCH patterns',
    source: 'Market Structure Video',
    type: 'Analysis',
    confidence: 0.88,
    tags: ['structure', 'BOS', 'trend']
  },
  {
    id: 3,
    name: 'Supply Zone Fakeout',
    description: 'Trade fakeouts at supply/demand zones with confluence confirmation',
    source: 'Strategy Manual',
    type: 'Setup',
    confidence: 0.85,
    tags: ['supply-demand', 'fakeout', 'confluence']
  }
])

// File handling
const handleDrop = (e) => {
  isDragging.value = false
  const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf')
  selectedFiles.value.push(...files)
}

const handleFileSelect = (e) => {
  const files = Array.from(e.target.files)
  selectedFiles.value.push(...files)
}

const removeFile = (index) => {
  selectedFiles.value.splice(index, 1)
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// Processing
const processFiles = async () => {
  isProcessing.value = true
  const tags = tagInput.value.split(',').map(t => t.trim()).filter(Boolean)
  
  for (const file of selectedFiles.value) {
    const queueItem = {
      id: Date.now() + Math.random(),
      name: file.name,
      status: 'processing',
      statusText: 'Extracting content...',
      progress: 30
    }
    processingQueue.value.push(queueItem)
    
    // Simulate processing (replace with actual API call)
    setTimeout(() => {
      queueItem.statusText = 'Analyzing strategies...'
      queueItem.progress = 60
      
      setTimeout(() => {
        queueItem.statusText = 'Validating results...'
        queueItem.progress = 90
        
        setTimeout(() => {
          queueItem.status = 'completed'
          queueItem.statusText = 'Completed'
          queueItem.progress = 100
          
          // Add mock strategy
          extractedStrategies.value.unshift({
            id: Date.now(),
            name: 'New Strategy from ' + file.name,
            description: 'Extracted trading strategy with multiple entry patterns',
            source: file.name,
            type: 'Entry Pattern',
            confidence: 0.87,
            tags: tags.length > 0 ? tags : ['new', 'extracted']
          })
          
          stats.totalProcessed++
          stats.strategiesExtracted += 2
        }, 1000)
      }, 1000)
    }, 1000)
  }
  
  setTimeout(() => {
    isProcessing.value = false
    selectedFiles.value = []
    tagInput.value = ''
  }, 3500)
}

const processVideo = async () => {
  isProcessing.value = true
  const tags = tagInput.value.split(',').map(t => t.trim()).filter(Boolean)
  
  const queueItem = {
    id: Date.now(),
    name: videoUrl.value || 'Video Transcript',
    status: 'processing',
    statusText: 'Processing video content...',
    progress: 40
  }
  processingQueue.value.push(queueItem)
  
  setTimeout(() => {
    queueItem.status = 'completed'
    queueItem.statusText = 'Completed'
    queueItem.progress = 100
    isProcessing.value = false
    videoUrl.value = ''
    videoTranscript.value = ''
    tagInput.value = ''
  }, 3000)
}

const processText = async () => {
  isProcessing.value = true
  const tags = tagInput.value.split(',').map(t => t.trim()).filter(Boolean)
  
  const queueItem = {
    id: Date.now(),
    name: textTitle.value || 'Text Content',
    status: 'processing',
    statusText: 'Extracting strategies...',
    progress: 50
  }
  processingQueue.value.push(queueItem)
  
  setTimeout(() => {
    queueItem.status = 'completed'
    queueItem.statusText = 'Completed'
    queueItem.progress = 100
    isProcessing.value = false
    textTitle.value = ''
    textContent.value = ''
    tagInput.value = ''
  }, 2500)
}

const getConfidenceClass = (confidence) => {
  if (confidence >= 0.9) return 'high'
  if (confidence >= 0.7) return 'medium'
  return 'low'
}

// Animations
onMounted(() => {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => entry.target.classList.add('visible'), i * 100)
        observer.unobserve(entry.target)
      }
    })
  }, { threshold: 0.1 })
  
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el))
})
</script>

<style scoped>
:root {
  /* Color System */
  --color-surface: hsl(230, 25%, 11%);
  --color-surface-elevated: hsl(230, 20%, 15%);
  --color-surface-hover: hsl(230, 20%, 18%);
  --color-accent: hsl(250, 85%, 65%);
  --color-accent-glow: hsl(250, 85%, 65%, 0.15);
  --color-accent-dim: hsl(250, 60%, 45%);
  --color-success: hsl(145, 65%, 55%);
  --color-warning: hsl(35, 85%, 60%);
  --color-error: hsl(0, 75%, 60%);
  --color-text-primary: hsl(0, 0%, 95%);
  --color-text-secondary: hsl(220, 15%, 65%);
  --color-text-dim: hsl(220, 10%, 50%);
  --color-border: hsl(230, 20%, 25%);
  --color-border-bright: hsl(250, 60%, 55%, 0.3);
  
  /* Spacing */
  --space-xs: 0.5rem;
  --space-sm: 1rem;
  --space-md: 2rem;
  --space-lg: 4rem;
  --space-xl: 6rem;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px hsl(230 25% 5% / 0.3), 0 1px 4px hsl(230 25% 5% / 0.2);
  --shadow-md: 0 4px 8px hsl(230 25% 5% / 0.3), 0 8px 20px hsl(230 25% 5% / 0.2);
  --shadow-lg: 0 8px 16px hsl(230 25% 5% / 0.4), 0 20px 40px hsl(230 25% 5% / 0.3);
  --shadow-glow: 0 0 30px var(--color-accent-glow);
  
  /* Typography */
  --font-display: 'Space Grotesk', 'Inter', sans-serif;
  --font-body: 'Inter', system-ui, sans-serif;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.ingestion-page {
  min-height: 100vh;
  background: 
    radial-gradient(ellipse at 20% 30%, hsl(250 80% 25% / 0.12) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 70%, hsl(280 70% 30% / 0.08) 0%, transparent 50%),
    var(--color-surface);
  color: var(--color-text-primary);
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  padding: var(--space-lg) 0;
}

.grain-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.03;
}

/* Hero Section */
.hero-section {
  text-align: center;
  padding: var(--space-xl) var(--space-md);
  max-width: 1200px;
  margin: 0 auto;
}

.hero-title {
  font-family: var(--font-display);
  font-size: clamp(3rem, 7vw, 5.5rem);
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.1;
  margin-bottom: var(--space-sm);
  background: linear-gradient(135deg, var(--color-text-primary), var(--color-accent));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: clamp(1.1rem, 2vw, 1.4rem);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-lg);
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.6;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-md);
  max-width: 800px;
  margin: 0 auto;
}

.stat-card {
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: var(--space-md);
  box-shadow: var(--shadow-md), inset 0 1px 0 hsl(0 0% 100% / 0.05);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.stat-card:hover {
  transform: translateY(-2px);
  border-color: var(--color-border-bright);
  box-shadow: var(--shadow-lg), var(--shadow-glow);
}

.stat-value {
  font-family: var(--font-display);
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--color-accent);
  margin-bottom: var(--space-xs);
}

.stat-label {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Section Styles */
.upload-section,
.queue-section,
.strategies-section {
  padding: var(--space-lg) var(--space-md);
}

.section-container {
  max-width: 1200px;
  margin: 0 auto;
}

.section-title {
  font-family: var(--font-display);
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 700;
  margin-bottom: var(--space-sm);
  letter-spacing: -0.02em;
}

.section-description {
  font-size: 1.1rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-lg);
  line-height: 1.6;
}

/* Tabs */
.upload-tabs {
  display: flex;
  gap: var(--space-sm);
  margin-bottom: var(--space-lg);
  flex-wrap: wrap;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-sm) var(--space-md);
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  color: var(--color-text-secondary);
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.tab-button:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-border-bright);
  transform: translateY(-1px);
}

.tab-button.active {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: white;
  box-shadow: var(--shadow-glow);
}

.tab-icon {
  font-size: 1.3rem;
}

/* Upload Panel */
.upload-panel {
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  padding: var(--space-lg);
  box-shadow: var(--shadow-md);
}

.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: 16px;
  padding: var(--space-xl);
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
}

.drop-zone:hover {
  border-color: var(--color-accent);
  background: hsl(250 85% 65% / 0.02);
}

.drop-zone.is-dragging {
  border-color: var(--color-accent);
  background: hsl(250 85% 65% / 0.05);
  border-width: 3px;
}

.file-input {
  display: none;
}

.upload-icon {
  font-size: 4rem;
  margin-bottom: var(--space-md);
}

.drop-zone-title {
  font-size: 1.3rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--space-xs);
}

.drop-zone-subtitle {
  font-size: 0.95rem;
  color: var(--color-text-dim);
  margin-bottom: var(--space-md);
}

.browse-button {
  padding: var(--space-sm) var(--space-lg);
  background: var(--color-accent);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
}

.browse-button:hover {
  background: hsl(250, 85%, 70%);
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow);
}

/* Selected Files */
.selected-files {
  margin-top: var(--space-md);
}

.file-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  margin-bottom: var(--space-sm);
}

.file-icon {
  font-size: 1.5rem;
}

.file-info {
  flex: 1;
}

.file-name {
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: 0.2rem;
}

.file-size {
  font-size: 0.85rem;
  color: var(--color-text-dim);
}

.remove-button {
  width: 32px;
  height: 32px;
  border: none;
  background: hsl(0, 75%, 50%, 0.1);
  color: var(--color-error);
  border-radius: 8px;
  font-size: 1.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.remove-button:hover {
  background: var(--color-error);
  color: white;
}

/* Input Groups */
.input-group,
.tags-section {
  margin-top: var(--space-md);
}

.input-label {
  display: block;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--space-xs);
  font-size: 0.95rem;
}

.text-input,
.textarea-input {
  width: 100%;
  padding: var(--space-sm) var(--space-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  color: var(--color-text-primary);
  font-size: 1rem;
  font-family: var(--font-body);
  transition: all 0.25s ease;
}

.text-input:focus,
.textarea-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-glow);
}

.textarea-input {
  resize: vertical;
  line-height: 1.6;
}

.process-button {
  width: 100%;
  margin-top: var(--space-md);
  padding: var(--space-md);
  background: var(--color-accent);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.process-button:hover:not(:disabled) {
  background: hsl(250, 85%, 70%);
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg), var(--shadow-glow);
}

.process-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Queue */
.queue-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.queue-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  transition: all 0.3s ease;
}

.queue-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
  border-radius: 10px;
  font-size: 1.5rem;
}

.queue-item.processing .queue-icon {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.queue-item.completed {
  border-color: var(--color-success);
}

.queue-item.completed .queue-icon {
  background: hsl(145, 65%, 55%, 0.1);
  color: var(--color-success);
}

.queue-item.error {
  border-color: var(--color-error);
}

.queue-item.error .queue-icon {
  background: hsl(0, 75%, 60%, 0.1);
  color: var(--color-error);
}

.queue-name {
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 0.3rem;
}

.queue-status {
  font-size: 0.9rem;
  color: var(--color-text-dim);
}

.queue-progress {
  width: 200px;
  height: 6px;
  background: var(--color-surface);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--color-accent);
  transition: width 0.5s ease;
}

/* Strategies Grid */
.strategies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: var(--space-md);
}

.strategy-card {
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: var(--space-md);
  box-shadow: var(--shadow-md), inset 0 1px 0 hsl(0 0% 100% / 0.03);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.strategy-card:hover {
  transform: translateY(-4px);
  border-color: var(--color-border-bright);
  box-shadow: var(--shadow-lg), var(--shadow-glow);
}

.strategy-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-sm);
  gap: var(--space-sm);
}

.strategy-name {
  font-family: var(--font-display);
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.confidence-badge {
  padding: 0.3rem 0.7rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  flex-shrink: 0;
}

.confidence-badge.high {
  background: hsl(145, 65%, 55%, 0.15);
  color: var(--color-success);
}

.confidence-badge.medium {
  background: hsl(35, 85%, 60%, 0.15);
  color: var(--color-warning);
}

.confidence-badge.low {
  background: hsl(0, 75%, 60%, 0.15);
  color: var(--color-error);
}

.strategy-description {
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-md);
}

.strategy-meta {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: var(--space-md);
}

.meta-item {
  display: flex;
  gap: var(--space-xs);
  font-size: 0.9rem;
}

.meta-label {
  color: var(--color-text-dim);
  font-weight: 500;
}

.meta-value {
  color: var(--color-text-secondary);
}

.strategy-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
  margin-bottom: var(--space-md);
}

.tag {
  padding: 0.3rem 0.7rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 0.8rem;
  color: var(--color-text-dim);
}

.strategy-actions {
  display: flex;
  gap: var(--space-sm);
}

.action-button {
  flex: 1;
  padding: var(--space-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-button:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-border-bright);
  color: var(--color-text-primary);
}

.action-button.primary {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: white;
}

.action-button.primary:hover {
  background: hsl(250, 85%, 70%);
}

/* Reveal Animation */
.reveal {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.7s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);
}

.reveal.visible {
  opacity: 1;
  transform: translateY(0);
}

/* Responsive */
@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
  
  .strategies-grid {
    grid-template-columns: 1fr;
  }
  
  .queue-item {
    grid-template-columns: auto 1fr;
    grid-template-rows: auto auto;
  }
  
  .queue-progress {
    grid-column: 1 / -1;
    width: 100%;
    margin-top: var(--space-sm);
  }
}
</style>
