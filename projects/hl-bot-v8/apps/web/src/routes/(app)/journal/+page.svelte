<script lang="ts">
  import { onMount } from 'svelte';
  import {
    Button,
    Card,
    CardHeader,
    CardBody,
    CardFooter,
    Badge,
    Modal,
    ModalHeader,
    ModalBody,
    ModalFooter,
    Tabs,
    TabList,
    Tab,
    TabPanel,
  } from '$lib/components/ui';
  import { LoadingState, EmptyState } from '$lib/components/layout';
  import { api } from '$lib/api';

  // Journal Entry Type
  interface JournalEntry {
    id: string;
    tradeId?: string;
    type: 'trade_review' | 'market_observation' | 'strategy_note' | 'lesson_learned';
    title: string;
    content: string;
    tags: string[];
    sentiment?: 'positive' | 'negative' | 'neutral';
    metrics?: {
      pnl?: number;
      riskRewardActual?: number;
      emotionalState?: string;
    };
    createdAt: Date;
    updatedAt: Date;
  }

  // State
  let entries = $state<JournalEntry[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let filterType = $state<JournalEntry['type'] | 'all'>('all');
  let searchQuery = $state('');
  let sortOrder = $state<'asc' | 'desc'>('desc');
  
  // Create/Edit modal state
  let editModalOpen = $state(false);
  let editEntry = $state<Partial<JournalEntry>>({});
  let isCreating = $state(false);
  let saving = $state(false);
  
  // Details modal state
  let selectedEntry = $state<JournalEntry | null>(null);
  let detailsModalOpen = $state(false);

  // Computed filtered entries
  let filteredEntries = $derived(() => {
    let result = entries;
    
    // Filter by type
    if (filterType !== 'all') {
      result = result.filter(e => e.type === filterType);
    }
    
    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(e => 
        e.title.toLowerCase().includes(query) ||
        e.content.toLowerCase().includes(query) ||
        e.tags.some(t => t.toLowerCase().includes(query))
      );
    }
    
    // Sort by date
    result = [...result].sort((a, b) => {
      const dateA = new Date(a.createdAt).getTime();
      const dateB = new Date(b.createdAt).getTime();
      return sortOrder === 'desc' ? dateB - dateA : dateA - dateB;
    });
    
    return result;
  });

  // Statistics
  let stats = $derived(() => {
    const total = entries.length;
    const tradeReviews = entries.filter(e => e.type === 'trade_review').length;
    const lessonsLearned = entries.filter(e => e.type === 'lesson_learned').length;
    const thisWeek = entries.filter(e => {
      const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
      return new Date(e.createdAt).getTime() > weekAgo;
    }).length;
    
    return { total, tradeReviews, lessonsLearned, thisWeek };
  });

  // Load journal entries
  async function loadEntries() {
    loading = true;
    error = null;
    
    try {
      // For now, use mock data since the learning API isn't implemented yet
      // In production: const response = await api.learning.listJournalEntries();
      entries = getMockEntries();
    } catch (err) {
      console.error('Failed to load journal entries:', err);
      error = err instanceof Error ? err.message : 'Failed to load journal entries';
    } finally {
      loading = false;
    }
  }

  // Mock data for development
  function getMockEntries(): JournalEntry[] {
    return [
      {
        id: '1',
        type: 'trade_review',
        title: 'BTC Long - Successful breakout trade',
        content: 'Entered on the 4H breakout above 65k resistance. The setup had 3 confluence factors: bullish market structure, RSI divergence, and volume confirmation. Managed position well, scaled out at 1.5R and 2R targets.',
        tags: ['BTC', 'breakout', 'successful'],
        sentiment: 'positive',
        metrics: {
          pnl: 1250,
          riskRewardActual: 2.1,
          emotionalState: 'Calm and focused',
        },
        createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
        updatedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
      },
      {
        id: '2',
        type: 'lesson_learned',
        title: 'Importance of waiting for confirmation',
        content: 'After reviewing my last 5 losing trades, I noticed a pattern: I was entering before price confirmed the pattern. Moving forward, I will wait for candle close confirmation before entry.',
        tags: ['discipline', 'patience', 'entry-timing'],
        sentiment: 'neutral',
        createdAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
        updatedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
      },
      {
        id: '3',
        type: 'market_observation',
        title: 'ETH showing accumulation pattern',
        content: 'ETH has been consolidating in a tight range between 3400-3600 for the past week. Volume profile suggests accumulation. Watch for breakout above 3650 with volume confirmation.',
        tags: ['ETH', 'accumulation', 'watchlist'],
        sentiment: 'positive',
        createdAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
        updatedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
      },
      {
        id: '4',
        type: 'trade_review',
        title: 'SOL Short - Stop loss hit',
        content: 'Shorted SOL on what looked like a double top, but the rejection wasn\'t clean. Got stopped out at -1R. In hindsight, should have waited for more bearish confirmation before entering.',
        tags: ['SOL', 'short', 'loss'],
        sentiment: 'negative',
        metrics: {
          pnl: -420,
          riskRewardActual: -1,
          emotionalState: 'Frustrated but learning',
        },
        createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
        updatedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
      },
    ];
  }

  // Create new entry
  function openCreateModal() {
    isCreating = true;
    editEntry = {
      type: 'trade_review',
      title: '',
      content: '',
      tags: [],
    };
    editModalOpen = true;
  }

  // Edit entry
  function openEditModal(entry: JournalEntry) {
    isCreating = false;
    editEntry = { ...entry };
    editModalOpen = true;
  }

  // Save entry
  async function saveEntry() {
    if (!editEntry.title || !editEntry.content) {
      alert('Title and content are required');
      return;
    }
    
    saving = true;
    
    try {
      // In production: await api.learning.saveJournalEntry(editEntry);
      // For now, just update local state
      if (isCreating) {
        const newEntry: JournalEntry = {
          id: Date.now().toString(),
          type: editEntry.type || 'trade_review',
          title: editEntry.title || '',
          content: editEntry.content || '',
          tags: editEntry.tags || [],
          sentiment: editEntry.sentiment,
          metrics: editEntry.metrics,
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        entries = [newEntry, ...entries];
      } else {
        entries = entries.map(e => 
          e.id === editEntry.id 
            ? { ...e, ...editEntry, updatedAt: new Date() } as JournalEntry
            : e
        );
      }
      
      editModalOpen = false;
    } catch (err) {
      console.error('Failed to save entry:', err);
      alert('Failed to save entry');
    } finally {
      saving = false;
    }
  }

  // Delete entry
  async function deleteEntry(entry: JournalEntry) {
    if (!confirm(`Are you sure you want to delete "${entry.title}"?`)) return;
    
    try {
      // In production: await api.learning.deleteJournalEntry(entry.id);
      entries = entries.filter(e => e.id !== entry.id);
    } catch (err) {
      console.error('Failed to delete entry:', err);
      alert('Failed to delete entry');
    }
  }

  function openDetails(entry: JournalEntry) {
    selectedEntry = entry;
    detailsModalOpen = true;
  }

  // Type badge variant mapping
  function getTypeBadgeVariant(type: JournalEntry['type']): 'success' | 'warning' | 'error' | 'info' | 'default' {
    switch (type) {
      case 'trade_review':
        return 'info';
      case 'lesson_learned':
        return 'success';
      case 'market_observation':
        return 'warning';
      case 'strategy_note':
        return 'default';
      default:
        return 'default';
    }
  }

  // Sentiment badge
  function getSentimentBadgeVariant(sentiment?: 'positive' | 'negative' | 'neutral'): 'success' | 'error' | 'default' {
    switch (sentiment) {
      case 'positive':
        return 'success';
      case 'negative':
        return 'error';
      default:
        return 'default';
    }
  }

  // Format date
  function formatDate(date: Date | string): string {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }

  // Format PnL
  function formatPnL(pnl?: number): string {
    if (pnl === undefined) return 'N/A';
    const sign = pnl >= 0 ? '+' : '';
    return `${sign}$${pnl.toLocaleString()}`;
  }

  // Get type label
  function getTypeLabel(type: JournalEntry['type']): string {
    switch (type) {
      case 'trade_review':
        return 'Trade Review';
      case 'lesson_learned':
        return 'Lesson Learned';
      case 'market_observation':
        return 'Market Observation';
      case 'strategy_note':
        return 'Strategy Note';
      default:
        return type;
    }
  }

  // Get type icon
  function getTypeIcon(type: JournalEntry['type']): string {
    switch (type) {
      case 'trade_review':
        return '📊';
      case 'lesson_learned':
        return '💡';
      case 'market_observation':
        return '👁️';
      case 'strategy_note':
        return '📝';
      default:
        return '📄';
    }
  }

  // Load on mount
  onMount(() => {
    loadEntries();
  });
</script>

<div class="container mx-auto p-6 space-y-6">
  <!-- Header -->
  <div class="flex justify-between items-center">
    <div>
      <h1 class="text-3xl font-bold text-text-primary">Trading Journal</h1>
      <p class="text-text-secondary mt-1">Track your trades, insights, and lessons learned</p>
    </div>
    <Button variant="primary" onclick={openCreateModal}>
      New Entry
    </Button>
  </div>

  <!-- Stats Cards -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
    <Card>
      <CardBody>
        <div class="text-center">
          <div class="text-3xl font-bold text-text-primary">{stats().total}</div>
          <div class="text-sm text-text-secondary">Total Entries</div>
        </div>
      </CardBody>
    </Card>
    <Card>
      <CardBody>
        <div class="text-center">
          <div class="text-3xl font-bold text-text-primary">{stats().tradeReviews}</div>
          <div class="text-sm text-text-secondary">Trade Reviews</div>
        </div>
      </CardBody>
    </Card>
    <Card>
      <CardBody>
        <div class="text-center">
          <div class="text-3xl font-bold text-text-primary">{stats().lessonsLearned}</div>
          <div class="text-sm text-text-secondary">Lessons Learned</div>
        </div>
      </CardBody>
    </Card>
    <Card>
      <CardBody>
        <div class="text-center">
          <div class="text-3xl font-bold text-text-primary">{stats().thisWeek}</div>
          <div class="text-sm text-text-secondary">This Week</div>
        </div>
      </CardBody>
    </Card>
  </div>

  <!-- Filters -->
  <Card>
    <CardBody>
      <div class="flex flex-wrap gap-4 items-center">
        <div class="flex-1 min-w-[200px]">
          <label for="search" class="block text-sm font-medium text-text-primary mb-1">Search</label>
          <input
            id="search"
            type="text"
            placeholder="Search entries..."
            bind:value={searchQuery}
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        <div class="flex-1 min-w-[200px]">
          <label for="filter-type" class="block text-sm font-medium text-text-primary mb-1">Entry Type</label>
          <select
            id="filter-type"
            bind:value={filterType}
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Types</option>
            <option value="trade_review">Trade Reviews</option>
            <option value="lesson_learned">Lessons Learned</option>
            <option value="market_observation">Market Observations</option>
            <option value="strategy_note">Strategy Notes</option>
          </select>
        </div>

        <div class="flex-1 min-w-[200px]">
          <label for="sort-order" class="block text-sm font-medium text-text-primary mb-1">Sort Order</label>
          <select
            id="sort-order"
            bind:value={sortOrder}
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="desc">Newest First</option>
            <option value="asc">Oldest First</option>
          </select>
        </div>

        <div class="flex items-end">
          <Button variant="secondary" onclick={loadEntries}>
            Refresh
          </Button>
        </div>
      </div>
    </CardBody>
  </Card>

  <!-- Content -->
  {#if loading}
    <div class="flex justify-center items-center py-12">
      <LoadingState type="spinner" size="lg" />
    </div>
  {:else if error}
    <Card>
      <CardBody>
        <div class="text-center py-8">
          <p class="text-error-600 text-lg mb-4">Error loading journal entries</p>
          <p class="text-text-secondary mb-4">{error}</p>
          <Button variant="primary" onclick={loadEntries}>Try Again</Button>
        </div>
      </CardBody>
    </Card>
  {:else if filteredEntries().length === 0}
    <Card>
      <CardBody>
        <EmptyState
          title="No journal entries found"
          description={filterType === 'all' && !searchQuery
            ? "Start documenting your trading journey by creating your first journal entry."
            : "No entries match your current filters."}
          action={{
            label: 'New Entry',
            onClick: openCreateModal,
          }}
        />
      </CardBody>
    </Card>
  {:else}
    <div class="space-y-4">
      {#each filteredEntries() as entry (entry.id)}
        <Card>
          <CardBody>
            <div class="flex gap-4">
              <div class="text-3xl flex-shrink-0">
                {getTypeIcon(entry.type)}
              </div>
              
              <div class="flex-1 min-w-0">
                <div class="flex items-start justify-between gap-4 mb-2">
                  <div>
                    <h3 class="text-lg font-semibold text-text-primary">
                      {entry.title}
                    </h3>
                    <div class="flex gap-2 mt-1">
                      <Badge variant={getTypeBadgeVariant(entry.type)}>
                        {getTypeLabel(entry.type)}
                      </Badge>
                      {#if entry.sentiment}
                        <Badge variant={getSentimentBadgeVariant(entry.sentiment)}>
                          {entry.sentiment}
                        </Badge>
                      {/if}
                    </div>
                  </div>
                  <span class="text-sm text-text-secondary flex-shrink-0">
                    {formatDate(entry.createdAt)}
                  </span>
                </div>
                
                <p class="text-text-secondary text-sm line-clamp-2 mb-3">
                  {entry.content}
                </p>
                
                {#if entry.metrics?.pnl !== undefined}
                  <div class="flex items-center gap-4 text-sm mb-3">
                    <span class="font-medium" class:text-green-500={entry.metrics.pnl >= 0} class:text-red-500={entry.metrics.pnl < 0}>
                      {formatPnL(entry.metrics.pnl)}
                    </span>
                    {#if entry.metrics.riskRewardActual}
                      <span class="text-text-secondary">
                        R:R {entry.metrics.riskRewardActual.toFixed(1)}
                      </span>
                    {/if}
                  </div>
                {/if}
                
                {#if entry.tags.length > 0}
                  <div class="flex flex-wrap gap-1">
                    {#each entry.tags as tag}
                      <span class="px-2 py-0.5 bg-bg-secondary text-text-secondary text-xs rounded">
                        #{tag}
                      </span>
                    {/each}
                  </div>
                {/if}
              </div>
              
              <div class="flex flex-col gap-2 flex-shrink-0">
                <Button size="sm" variant="outline" onclick={() => openDetails(entry)}>
                  View
                </Button>
                <Button size="sm" variant="secondary" onclick={() => openEditModal(entry)}>
                  Edit
                </Button>
                <Button size="sm" variant="danger" onclick={() => deleteEntry(entry)}>
                  Delete
                </Button>
              </div>
            </div>
          </CardBody>
        </Card>
      {/each}
    </div>
  {/if}
</div>

<!-- Entry Details Modal -->
{#if selectedEntry}
  <Modal bind:open={detailsModalOpen} title={selectedEntry.title} size="xl">
    <ModalBody>
      <div class="space-y-4">
        <!-- Type and Sentiment -->
        <div class="flex gap-4">
          <div class="flex-1">
            <h4 class="text-sm font-semibold text-text-primary mb-1">Type</h4>
            <Badge variant={getTypeBadgeVariant(selectedEntry.type)}>
              {getTypeLabel(selectedEntry.type)}
            </Badge>
          </div>
          {#if selectedEntry.sentiment}
            <div class="flex-1">
              <h4 class="text-sm font-semibold text-text-primary mb-1">Sentiment</h4>
              <Badge variant={getSentimentBadgeVariant(selectedEntry.sentiment)}>
                {selectedEntry.sentiment}
              </Badge>
            </div>
          {/if}
        </div>

        <!-- Content -->
        <div>
          <h4 class="text-sm font-semibold text-text-primary mb-2">Content</h4>
          <div class="p-3 bg-bg-secondary rounded border border-border">
            <p class="text-text-secondary text-sm whitespace-pre-wrap">
              {selectedEntry.content}
            </p>
          </div>
        </div>

        <!-- Metrics -->
        {#if selectedEntry.metrics}
          <div>
            <h4 class="text-sm font-semibold text-text-primary mb-2">Metrics</h4>
            <div class="grid grid-cols-3 gap-4">
              {#if selectedEntry.metrics.pnl !== undefined}
                <div>
                  <span class="text-text-secondary text-sm">P&L</span>
                  <p class="font-semibold" class:text-green-500={selectedEntry.metrics.pnl >= 0} class:text-red-500={selectedEntry.metrics.pnl < 0}>
                    {formatPnL(selectedEntry.metrics.pnl)}
                  </p>
                </div>
              {/if}
              {#if selectedEntry.metrics.riskRewardActual}
                <div>
                  <span class="text-text-secondary text-sm">Risk/Reward</span>
                  <p class="font-semibold text-text-primary">{selectedEntry.metrics.riskRewardActual.toFixed(2)}</p>
                </div>
              {/if}
              {#if selectedEntry.metrics.emotionalState}
                <div>
                  <span class="text-text-secondary text-sm">Emotional State</span>
                  <p class="text-text-primary">{selectedEntry.metrics.emotionalState}</p>
                </div>
              {/if}
            </div>
          </div>
        {/if}

        <!-- Tags -->
        {#if selectedEntry.tags.length > 0}
          <div>
            <h4 class="text-sm font-semibold text-text-primary mb-2">Tags</h4>
            <div class="flex flex-wrap gap-2">
              {#each selectedEntry.tags as tag}
                <span class="px-2 py-1 bg-bg-secondary text-text-secondary text-sm rounded">
                  #{tag}
                </span>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Timestamps -->
        <div class="grid grid-cols-2 gap-4 pt-4 border-t border-border text-xs">
          <div>
            <span class="text-text-secondary">Created:</span>
            <p class="text-text-primary">{formatDate(selectedEntry.createdAt)}</p>
          </div>
          <div>
            <span class="text-text-secondary">Updated:</span>
            <p class="text-text-primary">{formatDate(selectedEntry.updatedAt)}</p>
          </div>
        </div>
      </div>
    </ModalBody>
    <ModalFooter>
      <Button variant="secondary" onclick={() => detailsModalOpen = false}>Close</Button>
      <Button variant="primary" onclick={() => { openEditModal(selectedEntry!); detailsModalOpen = false; }}>
        Edit
      </Button>
    </ModalFooter>
  </Modal>
{/if}

<!-- Create/Edit Entry Modal -->
<Modal bind:open={editModalOpen} title={isCreating ? 'New Journal Entry' : 'Edit Entry'} size="lg">
  <ModalBody>
    <div class="space-y-4">
      <div>
        <label for="entry-type" class="block text-sm font-medium text-text-primary mb-1">Type</label>
        <select
          id="entry-type"
          bind:value={editEntry.type}
          class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="trade_review">Trade Review</option>
          <option value="lesson_learned">Lesson Learned</option>
          <option value="market_observation">Market Observation</option>
          <option value="strategy_note">Strategy Note</option>
        </select>
      </div>

      <div>
        <label for="entry-title" class="block text-sm font-medium text-text-primary mb-1">Title</label>
        <input
          id="entry-title"
          type="text"
          placeholder="Enter a title for your entry"
          bind:value={editEntry.title}
          class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      <div>
        <label for="entry-content" class="block text-sm font-medium text-text-primary mb-1">Content</label>
        <textarea
          id="entry-content"
          rows="8"
          placeholder="Write your journal entry..."
          bind:value={editEntry.content}
          class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500 resize-y"
        ></textarea>
      </div>

      <div>
        <label for="entry-sentiment" class="block text-sm font-medium text-text-primary mb-1">Sentiment</label>
        <select
          id="entry-sentiment"
          bind:value={editEntry.sentiment}
          class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value={undefined}>None</option>
          <option value="positive">Positive</option>
          <option value="neutral">Neutral</option>
          <option value="negative">Negative</option>
        </select>
      </div>

      <div>
        <label for="entry-tags" class="block text-sm font-medium text-text-primary mb-1">Tags (comma-separated)</label>
        <input
          id="entry-tags"
          type="text"
          placeholder="BTC, breakout, successful"
          value={editEntry.tags?.join(', ') || ''}
          oninput={(e) => editEntry.tags = (e.target as HTMLInputElement).value.split(',').map(t => t.trim()).filter(Boolean)}
          class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>
    </div>
  </ModalBody>
  <ModalFooter>
    <Button variant="secondary" onclick={() => editModalOpen = false} disabled={saving}>
      Cancel
    </Button>
    <Button variant="primary" onclick={saveEntry} disabled={saving}>
      {saving ? 'Saving...' : isCreating ? 'Create' : 'Save'}
    </Button>
  </ModalFooter>
</Modal>

<style>
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
