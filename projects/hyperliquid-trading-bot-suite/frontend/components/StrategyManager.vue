<template>
  <div class="strategy-manager">
    <!-- Header Section -->
    <div class="manager-header reveal">
      <div class="header-content">
        <h1 class="title">Strategy Arsenal</h1>
        <p class="subtitle">Manage and monitor your AI-learned trading strategies</p>
      </div>
      <div class="header-actions">
        <button @click="showIngestModal = true" class="btn-primary">
          <svg class="icon" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
          Ingest New Content
        </button>
      </div>
    </div>

    <!-- Performance Overview Cards -->
    <div class="performance-overview reveal">
      <div class="stat-card">
        <div class="stat-icon success">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ activeStrategies }}</div>
          <div class="stat-label">Active Strategies</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon primary">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ overallWinRate }}%</div>
          <div class="stat-label">Overall Win Rate</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon warning">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ learningStrategies }}</div>
          <div class="stat-label">Learning Phase</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon secondary">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
            <path fill-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm9.707 5.707a1 1 0 00-1.414-1.414L9 12.586l-1.293-1.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ totalTrades }}</div>
          <div class="stat-label">Total Trades</div>
        </div>
      </div>
    </div>

    <!-- Filter Controls -->
    <div class="filter-section reveal">
      <div class="filter-group">
        <label class="filter-label">Filter by Status</label>
        <select v-model="filterStatus" class="filter-select">
          <option value="all">All Strategies</option>
          <option value="active">Active Only</option>
          <option value="inactive">Inactive Only</option>
          <option value="learning">Learning Phase</option>
        </select>
      </div>
      
      <div class="filter-group">
        <label class="filter-label">Sort by</label>
        <select v-model="sortBy" class="filter-select">
          <option value="performance">Performance</option>
          <option value="winRate">Win Rate</option>
          <option value="trades">Trade Count</option>
          <option value="recent">Recently Used</option>
        </select>
      </div>

      <div class="search-group">
        <svg class="search-icon" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
        </svg>
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Search strategies..." 
          class="search-input"
        />
      </div>
    </div>

    <!-- Strategy Cards Grid -->
    <div class="strategy-grid">
      <div 
        v-for="(strategy, index) in filteredStrategies" 
        :key="strategy.id"
        class="strategy-card reveal"
        :style="{ animationDelay: `${index * 0.1}s` }"
        @click="selectStrategy(strategy)"
      >
        <!-- Card Header -->
        <div class="card-header">
          <div class="strategy-info">
            <h3 class="strategy-name">{{ strategy.name }}</h3>
            <div class="strategy-meta">
              <span class="meta-badge" :class="strategy.source.type">
                {{ strategy.source.type === 'pdf' ? '📄 PDF' : '🎥 Video' }}
              </span>
              <span class="meta-text">{{ formatDate(strategy.createdAt) }}</span>
            </div>
          </div>
          
          <div class="strategy-toggle">
            <button 
              @click.stop="toggleStrategy(strategy)" 
              class="toggle-btn"
              :class="{ active: strategy.active }"
            >
              <span class="toggle-slider"></span>
            </button>
          </div>
        </div>

        <!-- Confidence Meter - The "One Thing" -->
        <div class="confidence-meter">
          <div class="confidence-label">
            <span>Confidence</span>
            <span class="confidence-value">{{ Math.round(strategy.confidence * 100) }}%</span>
          </div>
          <div class="confidence-bar">
            <div 
              class="confidence-fill" 
              :style="{ 
                width: `${strategy.confidence * 100}%`,
                background: getConfidenceGradient(strategy.confidence)
              }"
            >
              <div class="confidence-shimmer"></div>
            </div>
          </div>
        </div>

        <!-- Performance Metrics -->
        <div class="metrics-grid">
          <div class="metric">
            <div class="metric-label">Entry Type</div>
            <div class="metric-value">{{ formatEntryType(strategy.entryType) }}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Win Rate</div>
            <div class="metric-value" :class="getWinRateClass(strategy.winRate)">
              {{ strategy.winRate }}%
            </div>
          </div>
          <div class="metric">
            <div class="metric-label">Trades</div>
            <div class="metric-value">{{ strategy.tradeCount }}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Avg R</div>
            <div class="metric-value" :class="strategy.avgR >= 0 ? 'positive' : 'negative'">
              {{ strategy.avgR >= 0 ? '+' : '' }}{{ strategy.avgR.toFixed(2) }}R
            </div>
          </div>
        </div>

        <!-- Timeframes -->
        <div class="timeframes">
          <div class="timeframes-label">Timeframes</div>
          <div class="timeframe-badges">
            <span 
              v-for="tf in strategy.timeframes" 
              :key="tf"
              class="timeframe-badge"
            >
              {{ tf }}
            </span>
          </div>
        </div>

        <!-- Last Used -->
        <div class="last-used">
          <svg class="icon-small" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
          </svg>
          Last used {{ formatRelativeTime(strategy.lastUsed) }}
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="filteredStrategies.length === 0" class="empty-state reveal">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <h3 class="empty-title">No strategies found</h3>
        <p class="empty-text">Start by ingesting educational content to learn new trading strategies</p>
        <button @click="showIngestModal = true" class="btn-secondary">
          Ingest Content
        </button>
      </div>
    </div>

    <!-- Ingestion Modal -->
    <Teleport to="body">
      <div v-if="showIngestModal" class="modal-overlay" @click="showIngestModal = false">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h2 class="modal-title">Ingest New Content</h2>
            <button @click="showIngestModal = false" class="modal-close">
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="ingest-tabs">
              <button 
                @click="ingestTab = 'pdf'" 
                class="tab-btn"
                :class="{ active: ingestTab === 'pdf' }"
              >
                📄 PDF Document
              </button>
              <button 
                @click="ingestTab = 'video'" 
                class="tab-btn"
                :class="{ active: ingestTab === 'video' }"
              >
                🎥 YouTube Video
              </button>
            </div>

            <!-- PDF Upload -->
            <div v-if="ingestTab === 'pdf'" class="ingest-section">
              <div class="upload-area" @dragover.prevent @drop.prevent="handleFileDrop">
                <input 
                  ref="fileInput" 
                  type="file" 
                  accept=".pdf"
                  @change="handleFileSelect"
                  class="file-input"
                />
                <div class="upload-content">
                  <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <p class="upload-title">Drop PDF here or click to browse</p>
                  <p class="upload-subtitle">PDF files up to 50MB</p>
                </div>
              </div>
            </div>

            <!-- YouTube URL -->
            <div v-if="ingestTab === 'video'" class="ingest-section">
              <label class="input-label">YouTube URL</label>
              <input 
                v-model="youtubeUrl" 
                type="text" 
                placeholder="https://www.youtube.com/watch?v=..."
                class="text-input"
              />
              <div class="checkbox-group">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="extractFrames" />
                  <span>Extract chart frames from video</span>
                </label>
              </div>
            </div>

            <div class="modal-actions">
              <button @click="showIngestModal = false" class="btn-ghost">Cancel</button>
              <button @click="startIngestion" class="btn-primary">
                <svg class="icon" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                </svg>
                Start Ingestion
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- SVG Noise Texture -->
    <svg class="noise-overlay">
      <filter id="noise">
        <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="4" stitchTiles="stitch"/>
      </filter>
      <rect width="100%" height="100%" filter="url(#noise)"/>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

// State
const showIngestModal = ref(false)
const ingestTab = ref('pdf')
const filterStatus = ref('all')
const sortBy = ref('performance')
const searchQuery = ref('')
const youtubeUrl = ref('')
const extractFrames = ref(true)
const fileInput = ref<HTMLInputElement | null>(null)

// Mock data (replace with API calls)
const strategies = ref([
  {
    id: '1',
    name: 'LE Candle Breakout Strategy',
    active: true,
    confidence: 0.82,
    entryType: 'LE',
    winRate: 68,
    tradeCount: 45,
    avgR: 1.8,
    timeframes: ['4H', '1H', '15M'],
    source: { type: 'pdf', ref: 'trading_manual.pdf' },
    createdAt: new Date('2024-01-15'),
    lastUsed: new Date('2024-02-09')
  },
  {
    id: '2',
    name: 'Fakeout Reversal Play',
    active: true,
    confidence: 0.75,
    entryType: 'fakeout',
    winRate: 72,
    tradeCount: 38,
    avgR: 2.1,
    timeframes: ['1H', '30M', '15M'],
    source: { type: 'video', ref: 'youtube.com/watch?v=abc123' },
    createdAt: new Date('2024-01-20'),
    lastUsed: new Date('2024-02-10')
  },
  {
    id: '3',
    name: 'Range Onion Strategy',
    active: false,
    confidence: 0.58,
    entryType: 'onion',
    winRate: 55,
    tradeCount: 22,
    avgR: 0.9,
    timeframes: ['4H', '1H', '30M'],
    source: { type: 'pdf', ref: 'advanced_strategies.pdf' },
    createdAt: new Date('2024-01-25'),
    lastUsed: new Date('2024-02-05')
  },
  {
    id: '4',
    name: 'Small Wick Momentum',
    active: true,
    confidence: 0.88,
    entryType: 'small_wick',
    winRate: 78,
    tradeCount: 56,
    avgR: 2.4,
    timeframes: ['1H', '15M', '5M'],
    source: { type: 'video', ref: 'youtube.com/watch?v=xyz789' },
    createdAt: new Date('2024-02-01'),
    lastUsed: new Date('2024-02-10')
  }
])

// Computed
const filteredStrategies = computed(() => {
  let result = strategies.value

  // Filter by status
  if (filterStatus.value !== 'all') {
    if (filterStatus.value === 'active') {
      result = result.filter(s => s.active)
    } else if (filterStatus.value === 'inactive') {
      result = result.filter(s => !s.active)
    } else if (filterStatus.value === 'learning') {
      result = result.filter(s => s.confidence < 0.7)
    }
  }

  // Search
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(s => 
      s.name.toLowerCase().includes(query) || 
      s.entryType.toLowerCase().includes(query)
    )
  }

  // Sort
  result = [...result].sort((a, b) => {
    switch (sortBy.value) {
      case 'performance':
        return (b.avgR * b.confidence) - (a.avgR * a.confidence)
      case 'winRate':
        return b.winRate - a.winRate
      case 'trades':
        return b.tradeCount - a.tradeCount
      case 'recent':
        return b.lastUsed.getTime() - a.lastUsed.getTime()
      default:
        return 0
    }
  })

  return result
})

const activeStrategies = computed(() => 
  strategies.value.filter(s => s.active).length
)

const overallWinRate = computed(() => {
  const total = strategies.value.reduce((sum, s) => sum + (s.winRate * s.tradeCount), 0)
  const count = strategies.value.reduce((sum, s) => sum + s.tradeCount, 0)
  return count > 0 ? Math.round(total / count) : 0
})

const learningStrategies = computed(() =>
  strategies.value.filter(s => s.confidence < 0.7).length
)

const totalTrades = computed(() =>
  strategies.value.reduce((sum, s) => sum + s.tradeCount, 0)
)

// Methods
const toggleStrategy = (strategy: any) => {
  strategy.active = !strategy.active
  // TODO: Call API to update strategy status
}

const selectStrategy = (strategy: any) => {
  console.log('Selected strategy:', strategy)
  // TODO: Navigate to strategy detail view or open detail modal
}

const formatEntryType = (type: string) => {
  const types: Record<string, string> = {
    'LE': 'LE Candle',
    'small_wick': 'Small Wick',
    'steeper_wick': 'Steeper Wick',
    'celery': 'Celery Play',
    'breakout': 'Breakout',
    'fakeout': 'Fakeout',
    'onion': 'Onion'
  }
  return types[type] || type
}

const formatDate = (date: Date) => {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const formatRelativeTime = (date: Date) => {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 7) return `${days} days ago`
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`
  return `${Math.floor(days / 30)} months ago`
}

const getWinRateClass = (winRate: number) => {
  if (winRate >= 70) return 'excellent'
  if (winRate >= 60) return 'good'
  if (winRate >= 50) return 'neutral'
  return 'poor'
}

const getConfidenceGradient = (confidence: number) => {
  if (confidence >= 0.8) {
    return 'linear-gradient(90deg, hsl(145, 85%, 45%), hsl(145, 85%, 55%))'
  } else if (confidence >= 0.6) {
    return 'linear-gradient(90deg, hsl(210, 85%, 55%), hsl(210, 85%, 65%))'
  } else {
    return 'linear-gradient(90deg, hsl(35, 90%, 55%), hsl(35, 90%, 65%))'
  }
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    console.log('File selected:', target.files[0].name)
    // TODO: Upload file to backend
  }
}

const handleFileDrop = (event: DragEvent) => {
  if (event.dataTransfer?.files) {
    console.log('File dropped:', event.dataTransfer.files[0].name)
    // TODO: Upload file to backend
  }
}

const startIngestion = () => {
  console.log('Starting ingestion:', { ingestTab: ingestTab.value, youtubeUrl: youtubeUrl.value })
  // TODO: Call ingestion API
  showIngestModal.value = false
}

// Animation reveal on mount
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
.strategy-manager {
  position: relative;
  width: 100%;
  min-height: 100vh;
  padding: clamp(2rem, 5vw, 4rem);
  background: 
    radial-gradient(ellipse at 20% 10%, hsl(210 85% 55% / 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 70%, hsl(280 70% 65% / 0.06) 0%, transparent 50%),
    hsl(225, 25%, 97%);
}

/* Header */
.manager-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 3rem;
  gap: 2rem;
}

.header-content {
  flex: 1;
}

.title {
  font-family: 'Satoshi', sans-serif;
  font-size: clamp(2.5rem, 5vw, 4rem);
  font-weight: 700;
  background: linear-gradient(135deg, hsl(225, 25%, 12%), hsl(210, 85%, 55%));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 0.5rem;
  line-height: 1.1;
}

.subtitle {
  font-family: 'General Sans', sans-serif;
  font-size: 1.125rem;
  color: hsl(225, 15%, 45%);
  line-height: 1.6;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

/* Buttons */
.btn-primary, .btn-secondary, .btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  border-radius: 0.75rem;
  font-family: 'General Sans', sans-serif;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  border: none;
  outline: none;
}

.btn-primary {
  background: linear-gradient(135deg, hsl(210, 85%, 55%), hsl(210, 85%, 65%));
  color: white;
  box-shadow: 0 4px 12px hsl(210 85% 55% / 0.3), inset 0 1px 0 hsl(0 0% 100% / 0.2);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px hsl(210 85% 55% / 0.4), inset 0 1px 0 hsl(0 0% 100% / 0.2);
}

.btn-secondary {
  background: white;
  color: hsl(210, 85%, 55%);
  box-shadow: 0 2px 8px hsl(220 20% 20% / 0.08), inset 0 1px 0 hsl(0 0% 100% / 0.8);
  border: 1px solid hsl(220, 20%, 90%);
}

.btn-secondary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px hsl(220 20% 20% / 0.12);
}

.btn-ghost {
  background: transparent;
  color: hsl(225, 15%, 45%);
  border: 1px solid hsl(220, 20%, 85%);
}

.btn-ghost:hover {
  background: hsl(220, 20%, 96%);
}

.icon {
  width: 1.125rem;
  height: 1.125rem;
}

/* Performance Overview */
.performance-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1.75rem;
  background: white;
  border-radius: 1.25rem;
  box-shadow: 
    0 4px 6px hsl(220 20% 20% / 0.04), 
    0 8px 20px hsl(220 20% 20% / 0.06),
    inset 0 1px 0 hsl(0 0% 100% / 0.8);
  border: 1px solid hsl(220, 20%, 92%);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 
    0 8px 16px hsl(220 20% 20% / 0.06), 
    0 20px 40px hsl(220 20% 20% / 0.08);
}

.stat-icon {
  flex-shrink: 0;
  width: 3rem;
  height: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 1rem;
}

.stat-icon svg {
  width: 1.75rem;
  height: 1.75rem;
}

.stat-icon.success {
  background: linear-gradient(135deg, hsl(145, 85%, 45% / 0.15), hsl(145, 85%, 55% / 0.15));
  color: hsl(145, 85%, 45%);
}

.stat-icon.primary {
  background: linear-gradient(135deg, hsl(210, 85%, 55% / 0.15), hsl(210, 85%, 65% / 0.15));
  color: hsl(210, 85%, 55%);
}

.stat-icon.warning {
  background: linear-gradient(135deg, hsl(35, 90%, 55% / 0.15), hsl(35, 90%, 65% / 0.15));
  color: hsl(35, 90%, 55%);
}

.stat-icon.secondary {
  background: linear-gradient(135deg, hsl(280, 70%, 65% / 0.15), hsl(280, 70%, 75% / 0.15));
  color: hsl(280, 70%, 65%);
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: hsl(225, 25%, 12%);
  line-height: 1;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.875rem;
  color: hsl(225, 15%, 45%);
  font-weight: 500;
}

/* Filter Section */
.filter-section {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  align-items: flex-end;
}

.filter-group, .search-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(225, 25%, 12%);
}

.filter-select {
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid hsl(220, 20%, 85%);
  background: white;
  color: hsl(225, 25%, 12%);
  font-family: 'General Sans', sans-serif;
  font-size: 0.9375rem;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 180px;
}

.filter-select:hover {
  border-color: hsl(210, 85%, 55%);
}

.filter-select:focus {
  outline: none;
  border-color: hsl(210, 85%, 55%);
  box-shadow: 0 0 0 3px hsl(210 85% 55% / 0.1);
}

.search-group {
  position: relative;
  flex: 1;
  max-width: 400px;
}

.search-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  width: 1.25rem;
  height: 1.25rem;
  color: hsl(225, 15%, 45%);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 0.75rem 1rem 0.75rem 3rem;
  border-radius: 0.75rem;
  border: 1px solid hsl(220, 20%, 85%);
  background: white;
  color: hsl(225, 25%, 12%);
  font-family: 'General Sans', sans-serif;
  font-size: 0.9375rem;
  transition: all 0.2s ease;
}

.search-input:focus {
  outline: none;
  border-color: hsl(210, 85%, 55%);
  box-shadow: 0 0 0 3px hsl(210 85% 55% / 0.1);
}

/* Strategy Grid */
.strategy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 2rem;
}

.strategy-card {
  background: white;
  border-radius: 1.25rem;
  padding: 1.75rem;
  border: 1px solid hsl(220, 20%, 92%);
  box-shadow: 
    0 4px 6px hsl(220 20% 20% / 0.04), 
    0 8px 20px hsl(220 20% 20% / 0.06),
    inset 0 1px 0 hsl(0 0% 100% / 0.8);
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.strategy-card:hover {
  transform: translateY(-6px);
  box-shadow: 
    0 12px 24px hsl(220 20% 20% / 0.08), 
    0 24px 48px hsl(220 20% 20% / 0.1),
    0 0 30px hsl(210 85% 55% / 0.12);
  border-color: hsl(210, 85%, 55% / 0.3);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  gap: 1rem;
}

.strategy-info {
  flex: 1;
}

.strategy-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: hsl(225, 25%, 12%);
  margin-bottom: 0.5rem;
  line-height: 1.3;
}

.strategy-meta {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.meta-badge {
  padding: 0.25rem 0.625rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  background: hsl(220, 20%, 96%);
  color: hsl(225, 15%, 45%);
}

.meta-badge.pdf {
  background: hsl(210, 85%, 55% / 0.1);
  color: hsl(210, 85%, 45%);
}

.meta-badge.video {
  background: hsl(0, 85%, 60% / 0.1);
  color: hsl(0, 85%, 50%);
}

.meta-text {
  font-size: 0.875rem;
  color: hsl(225, 15%, 45%);
}

/* Toggle Button */
.strategy-toggle {
  flex-shrink: 0;
}

.toggle-btn {
  position: relative;
  width: 3rem;
  height: 1.75rem;
  border-radius: 1rem;
  background: hsl(220, 20%, 85%);
  border: none;
  cursor: pointer;
  transition: all 0.3s ease;
  padding: 0;
}

.toggle-btn.active {
  background: linear-gradient(135deg, hsl(145, 85%, 45%), hsl(145, 85%, 55%));
}

.toggle-slider {
  position: absolute;
  top: 0.125rem;
  left: 0.125rem;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  background: white;
  box-shadow: 0 2px 4px hsl(220 20% 20% / 0.2);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.toggle-btn.active .toggle-slider {
  transform: translateX(1.25rem);
}

/* Confidence Meter - The "One Thing" */
.confidence-meter {
  margin-bottom: 1.5rem;
}

.confidence-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(225, 25%, 12%);
}

.confidence-value {
  font-size: 1.125rem;
  font-weight: 700;
}

.confidence-bar {
  position: relative;
  height: 0.75rem;
  background: hsl(220, 20%, 93%);
  border-radius: 0.5rem;
  overflow: hidden;
}

.confidence-fill {
  position: relative;
  height: 100%;
  border-radius: 0.5rem;
  transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
}

.confidence-shimmer {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.3),
    transparent
  );
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  100% {
    left: 100%;
  }
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.metric-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: hsl(225, 15%, 45%);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.metric-value {
  font-size: 1.125rem;
  font-weight: 700;
  color: hsl(225, 25%, 12%);
}

.metric-value.excellent {
  color: hsl(145, 85%, 45%);
}

.metric-value.good {
  color: hsl(210, 85%, 55%);
}

.metric-value.neutral {
  color: hsl(35, 90%, 55%);
}

.metric-value.poor {
  color: hsl(0, 85%, 60%);
}

.metric-value.positive {
  color: hsl(145, 85%, 45%);
}

.metric-value.negative {
  color: hsl(0, 85%, 60%);
}

/* Timeframes */
.timeframes {
  margin-bottom: 1rem;
}

.timeframes-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: hsl(225, 15%, 45%);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.timeframe-badges {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.timeframe-badge {
  padding: 0.375rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.8125rem;
  font-weight: 600;
  background: hsl(210, 85%, 55% / 0.1);
  color: hsl(210, 85%, 45%);
  border: 1px solid hsl(210, 85%, 55% / 0.2);
}

/* Last Used */
.last-used {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: hsl(225, 15%, 45%);
  padding-top: 1rem;
  border-top: 1px solid hsl(220, 20%, 92%);
}

.icon-small {
  width: 1rem;
  height: 1rem;
}

/* Empty State */
.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
}

.empty-icon {
  width: 5rem;
  height: 5rem;
  margin-bottom: 1.5rem;
  color: hsl(225, 15%, 70%);
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

.empty-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: hsl(225, 25%, 12%);
  margin-bottom: 0.5rem;
}

.empty-text {
  font-size: 1rem;
  color: hsl(225, 15%, 45%);
  margin-bottom: 2rem;
  max-width: 400px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: hsl(225 25% 12% / 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
  animation: fadeIn 0.3s ease;
}

.modal-content {
  background: white;
  border-radius: 1.5rem;
  max-width: 600px;
  width: 100%;
  box-shadow: 0 20px 60px hsl(220 20% 20% / 0.3);
  animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem;
  border-bottom: 1px solid hsl(220, 20%, 92%);
}

.modal-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: hsl(225, 25%, 12%);
}

.modal-close {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.75rem;
  background: transparent;
  border: none;
  color: hsl(225, 15%, 45%);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close:hover {
  background: hsl(220, 20%, 96%);
  color: hsl(225, 25%, 12%);
}

.modal-close svg {
  width: 1.5rem;
  height: 1.5rem;
}

.modal-body {
  padding: 2rem;
}

/* Ingest Tabs */
.ingest-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  padding: 0.5rem;
  background: hsl(220, 20%, 96%);
  border-radius: 0.75rem;
}

.tab-btn {
  flex: 1;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background: transparent;
  color: hsl(225, 15%, 45%);
  font-family: 'General Sans', sans-serif;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn.active {
  background: white;
  color: hsl(225, 25%, 12%);
  box-shadow: 0 2px 4px hsl(220 20% 20% / 0.06);
}

/* Ingest Section */
.ingest-section {
  margin-bottom: 2rem;
}

.upload-area {
  position: relative;
  border: 2px dashed hsl(220, 20%, 85%);
  border-radius: 1rem;
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-area:hover {
  border-color: hsl(210, 85%, 55%);
  background: hsl(210, 85%, 55% / 0.03);
}

.file-input {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  opacity: 0;
  cursor: pointer;
}

.upload-content {
  pointer-events: none;
}

.upload-icon {
  width: 3rem;
  height: 3rem;
  margin: 0 auto 1rem;
  color: hsl(210, 85%, 55%);
}

.upload-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: hsl(225, 25%, 12%);
  margin-bottom: 0.25rem;
}

.upload-subtitle {
  font-size: 0.875rem;
  color: hsl(225, 15%, 45%);
}

/* Input */
.input-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(225, 25%, 12%);
  margin-bottom: 0.5rem;
}

.text-input {
  width: 100%;
  padding: 0.875rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid hsl(220, 20%, 85%);
  background: white;
  color: hsl(225, 25%, 12%);
  font-family: 'General Sans', sans-serif;
  font-size: 0.9375rem;
  transition: all 0.2s ease;
}

.text-input:focus {
  outline: none;
  border-color: hsl(210, 85%, 55%);
  box-shadow: 0 0 0 3px hsl(210 85% 55% / 0.1);
}

/* Checkbox */
.checkbox-group {
  margin-top: 1rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  font-size: 0.9375rem;
  color: hsl(225, 25%, 12%);
}

.checkbox-label input[type="checkbox"] {
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 0.375rem;
  cursor: pointer;
}

/* Modal Actions */
.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

/* Noise Overlay */
.noise-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.03;
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
  .strategy-manager {
    padding: 1.5rem;
  }

  .manager-header {
    flex-direction: column;
  }

  .title {
    font-size: 2.5rem;
  }

  .performance-overview {
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1rem;
  }

  .stat-card {
    flex-direction: column;
    text-align: center;
  }

  .filter-section {
    flex-direction: column;
    align-items: stretch;
  }

  .search-group {
    max-width: none;
  }

  .strategy-grid {
    grid-template-columns: 1fr;
  }
}
</style>
