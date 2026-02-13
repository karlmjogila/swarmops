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
  } from '$lib/components/ui';
  import { LoadingState, EmptyState } from '$lib/components/layout';
  import { api } from '$lib/api';
  import type { Signal, SignalStatus } from '@hl-bot/shared';

  // State
  let signals = $state<Signal[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let filterStatus = $state<SignalStatus | 'all'>('all');
  let sortBy = $state<'created' | 'strength' | 'symbol'>('created');
  let sortOrder = $state<'asc' | 'desc'>('desc');
  
  // Modal state
  let selectedSignal = $state<Signal | null>(null);
  let detailsModalOpen = $state(false);

  // Computed filtered and sorted signals
  let filteredSignals = $derived(() => {
    let result = signals;
    
    // Filter by status
    if (filterStatus !== 'all') {
      result = result.filter(s => s.status === filterStatus);
    }
    
    // Sort
    result = [...result].sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case 'symbol':
          comparison = a.symbol.localeCompare(b.symbol);
          break;
        case 'created':
          comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
          break;
        case 'strength':
          comparison = a.strength - b.strength;
          break;
      }
      
      return sortOrder === 'asc' ? comparison : -comparison;
    });
    
    return result;
  });

  // Load signals
  async function loadSignals() {
    loading = true;
    error = null;
    
    try {
      const response = await api.signals.list();
      signals = response.data;
    } catch (err) {
      console.error('Failed to load signals:', err);
      error = err instanceof Error ? err.message : 'Failed to load signals';
    } finally {
      loading = false;
    }
  }

  // Actions
  async function dismissSignal(signal: Signal) {
    try {
      await api.signals.dismiss(signal.id);
      await loadSignals();
    } catch (err) {
      console.error('Failed to dismiss signal:', err);
      alert('Failed to dismiss signal');
    }
  }

  async function executeSignal(signal: Signal) {
    try {
      await api.signals.execute(signal.id);
      await loadSignals();
    } catch (err) {
      console.error('Failed to execute signal:', err);
      alert('Failed to execute signal');
    }
  }

  function openDetails(signal: Signal) {
    selectedSignal = signal;
    detailsModalOpen = true;
  }

  // Status badge variant mapping
  function getStatusBadgeVariant(status: SignalStatus): 'success' | 'warning' | 'error' | 'info' | 'default' {
    switch (status) {
      case 'active':
        return 'success';
      case 'pending':
        return 'warning';
      case 'executed':
        return 'info';
      case 'expired':
      case 'dismissed':
        return 'default';
      default:
        return 'default';
    }
  }

  // Direction badge variant
  function getDirectionBadgeVariant(direction: 'long' | 'short'): 'success' | 'error' {
    return direction === 'long' ? 'success' : 'error';
  }

  // Strength badge variant
  function getStrengthBadgeVariant(strength: number): 'success' | 'warning' | 'error' {
    if (strength >= 0.7) return 'success';
    if (strength >= 0.4) return 'warning';
    return 'error';
  }

  // Format date
  function formatDate(date: Date | string): string {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  // Format price
  function formatPrice(price: number): string {
    return price.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 6,
    });
  }

  // Format percentage
  function formatPercent(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
  }

  // Load on mount
  onMount(() => {
    loadSignals();
  });
</script>

<div class="container mx-auto p-6 space-y-6">
  <!-- Header -->
  <div class="flex justify-between items-center">
    <div>
      <h1 class="text-3xl font-bold text-text-primary">Signals</h1>
      <p class="text-text-secondary mt-1">View and manage trading signals</p>
    </div>
    <Button variant="secondary" onclick={loadSignals}>
      Refresh
    </Button>
  </div>

  <!-- Filters -->
  <Card>
    <CardBody>
      <div class="flex flex-wrap gap-4 items-center">
        <div class="flex-1 min-w-[200px]">
          <label for="filter-status" class="block text-sm font-medium text-text-primary mb-1">Filter by Status</label>
          <select
            id="filter-status"
            bind:value={filterStatus}
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="pending">Pending</option>
            <option value="executed">Executed</option>
            <option value="expired">Expired</option>
            <option value="dismissed">Dismissed</option>
          </select>
        </div>

        <div class="flex-1 min-w-[200px]">
          <label for="sort-by" class="block text-sm font-medium text-text-primary mb-1">Sort By</label>
          <select
            id="sort-by"
            bind:value={sortBy}
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="created">Date Created</option>
            <option value="strength">Signal Strength</option>
            <option value="symbol">Symbol</option>
          </select>
        </div>

        <div class="flex-1 min-w-[200px]">
          <label for="sort-order" class="block text-sm font-medium text-text-primary mb-1">Order</label>
          <select
            id="sort-order"
            bind:value={sortOrder}
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
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
          <p class="text-error-600 text-lg mb-4">Error loading signals</p>
          <p class="text-text-secondary mb-4">{error}</p>
          <Button variant="primary" onclick={loadSignals}>Try Again</Button>
        </div>
      </CardBody>
    </Card>
  {:else if filteredSignals().length === 0}
    <Card>
      <CardBody>
        <EmptyState
          title="No signals found"
          description={filterStatus === 'all' 
            ? "No trading signals have been generated yet. Signals are created when strategies detect opportunities." 
            : "No signals match the selected filter."}
        />
      </CardBody>
    </Card>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {#each filteredSignals() as signal (signal.id)}
        <Card>
          <CardHeader>
            <div class="flex justify-between items-start">
              <div class="flex items-center gap-2">
                <h3 class="text-lg font-semibold text-text-primary">
                  {signal.symbol}
                </h3>
                <Badge variant={getDirectionBadgeVariant(signal.direction)}>
                  {signal.direction.toUpperCase()}
                </Badge>
              </div>
              <Badge variant={getStatusBadgeVariant(signal.status)}>
                {signal.status}
              </Badge>
            </div>
          </CardHeader>
          
          <CardBody>
            <div class="space-y-3 text-sm">
              <div class="flex justify-between items-center">
                <span class="text-text-secondary">Strength:</span>
                <Badge variant={getStrengthBadgeVariant(signal.strength)}>
                  {formatPercent(signal.strength)}
                </Badge>
              </div>
              
              <div class="flex justify-between">
                <span class="text-text-secondary">Entry Price:</span>
                <span class="text-text-primary font-medium font-mono">
                  ${formatPrice(signal.entryPrice)}
                </span>
              </div>
              
              {#if signal.stopLoss}
                <div class="flex justify-between">
                  <span class="text-text-secondary">Stop Loss:</span>
                  <span class="text-red-500 font-medium font-mono">
                    ${formatPrice(signal.stopLoss)}
                  </span>
                </div>
              {/if}
              
              {#if signal.takeProfit}
                <div class="flex justify-between">
                  <span class="text-text-secondary">Take Profit:</span>
                  <span class="text-green-500 font-medium font-mono">
                    ${formatPrice(signal.takeProfit)}
                  </span>
                </div>
              {/if}
              
              <div class="flex justify-between">
                <span class="text-text-secondary">Timeframe:</span>
                <span class="text-text-primary font-medium">
                  {signal.timeframe}
                </span>
              </div>
              
              <div class="flex justify-between text-xs pt-2 border-t border-border">
                <span class="text-text-secondary">Created:</span>
                <span class="text-text-primary">
                  {formatDate(signal.createdAt)}
                </span>
              </div>
            </div>
          </CardBody>
          
          <CardFooter>
            <div class="flex gap-2 flex-wrap">
              <Button
                size="sm"
                variant="outline"
                onclick={() => openDetails(signal)}
              >
                Details
              </Button>
              
              {#if signal.status === 'active'}
                <Button
                  size="sm"
                  variant="success"
                  onclick={() => executeSignal(signal)}
                >
                  Execute
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onclick={() => dismissSignal(signal)}
                >
                  Dismiss
                </Button>
              {/if}
            </div>
          </CardFooter>
        </Card>
      {/each}
    </div>
  {/if}
</div>

<!-- Signal Details Modal -->
{#if selectedSignal}
  <Modal bind:open={detailsModalOpen} title={`${selectedSignal.symbol} Signal`} size="lg">
    <ModalBody>
      <div class="space-y-4">
        <!-- Status and Direction -->
        <div class="flex gap-4">
          <div class="flex-1">
            <h4 class="text-sm font-semibold text-text-primary mb-1">Status</h4>
            <Badge variant={getStatusBadgeVariant(selectedSignal.status)}>
              {selectedSignal.status}
            </Badge>
          </div>
          <div class="flex-1">
            <h4 class="text-sm font-semibold text-text-primary mb-1">Direction</h4>
            <Badge variant={getDirectionBadgeVariant(selectedSignal.direction)}>
              {selectedSignal.direction.toUpperCase()}
            </Badge>
          </div>
          <div class="flex-1">
            <h4 class="text-sm font-semibold text-text-primary mb-1">Strength</h4>
            <Badge variant={getStrengthBadgeVariant(selectedSignal.strength)}>
              {formatPercent(selectedSignal.strength)}
            </Badge>
          </div>
        </div>

        <!-- Price Levels -->
        <div class="grid grid-cols-3 gap-4">
          <div>
            <h4 class="text-sm font-semibold text-text-primary mb-1">Entry Price</h4>
            <p class="text-text-secondary font-mono">${formatPrice(selectedSignal.entryPrice)}</p>
          </div>
          {#if selectedSignal.stopLoss}
            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">Stop Loss</h4>
              <p class="text-red-500 font-mono">${formatPrice(selectedSignal.stopLoss)}</p>
            </div>
          {/if}
          {#if selectedSignal.takeProfit}
            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">Take Profit</h4>
              <p class="text-green-500 font-mono">${formatPrice(selectedSignal.takeProfit)}</p>
            </div>
          {/if}
        </div>

        <!-- Reasoning -->
        {#if selectedSignal.reasoning}
          <div>
            <h4 class="text-sm font-semibold text-text-primary mb-2">Reasoning</h4>
            <div class="p-3 bg-bg-secondary rounded border border-border">
              <p class="text-text-secondary text-sm whitespace-pre-wrap">
                {selectedSignal.reasoning}
              </p>
            </div>
          </div>
        {/if}

        <!-- Confluence Factors -->
        {#if selectedSignal.confluenceFactors && selectedSignal.confluenceFactors.length > 0}
          <div>
            <h4 class="text-sm font-semibold text-text-primary mb-2">Confluence Factors</h4>
            <div class="space-y-1">
              {#each selectedSignal.confluenceFactors as factor}
                <div class="flex items-center gap-2 text-sm">
                  <span class="text-green-500">✓</span>
                  <span class="text-text-secondary">{factor}</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Timestamps -->
        <div class="grid grid-cols-2 gap-4 pt-4 border-t border-border text-xs">
          <div>
            <span class="text-text-secondary">Created:</span>
            <p class="text-text-primary">{formatDate(selectedSignal.createdAt)}</p>
          </div>
          {#if selectedSignal.expiresAt}
            <div>
              <span class="text-text-secondary">Expires:</span>
              <p class="text-text-primary">{formatDate(selectedSignal.expiresAt)}</p>
            </div>
          {/if}
        </div>
      </div>
    </ModalBody>
    <ModalFooter>
      <Button variant="secondary" onclick={() => detailsModalOpen = false}>Close</Button>
      {#if selectedSignal.status === 'active'}
        <Button variant="success" onclick={() => { executeSignal(selectedSignal!); detailsModalOpen = false; }}>
          Execute Trade
        </Button>
      {/if}
    </ModalFooter>
  </Modal>
{/if}
