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
  import type { Strategy, StrategyStatus } from '@hl-bot/shared';

  // State
  let strategies = $state<Strategy[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let filterStatus = $state<StrategyStatus | 'all'>('all');
  let sortBy = $state<'name' | 'created' | 'updated' | 'confidence'>('updated');
  let sortOrder = $state<'asc' | 'desc'>('desc');
  
  // Modal state
  let selectedStrategy = $state<Strategy | null>(null);
  let detailsModalOpen = $state(false);
  let deleteConfirmOpen = $state(false);
  let strategyToDelete = $state<Strategy | null>(null);

  // Computed filtered and sorted strategies
  let filteredStrategies = $derived(() => {
    let result = strategies;
    
    // Filter by status
    if (filterStatus !== 'all') {
      result = result.filter(s => s.status === filterStatus);
    }
    
    // Sort
    result = [...result].sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'created':
          comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
          break;
        case 'updated':
          comparison = new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime();
          break;
        case 'confidence':
          comparison = a.confidence - b.confidence;
          break;
      }
      
      return sortOrder === 'asc' ? comparison : -comparison;
    });
    
    return result;
  });

  // Load strategies
  async function loadStrategies() {
    loading = true;
    error = null;
    
    try {
      const response = await api.strategies.list();
      strategies = response.data;
    } catch (err) {
      console.error('Failed to load strategies:', err);
      error = err instanceof Error ? err.message : 'Failed to load strategies';
    } finally {
      loading = false;
    }
  }

  // Actions
  async function activateStrategy(strategy: Strategy) {
    try {
      await api.strategies.activate(strategy.id);
      await loadStrategies();
    } catch (err) {
      console.error('Failed to activate strategy:', err);
      alert('Failed to activate strategy');
    }
  }

  async function deactivateStrategy(strategy: Strategy) {
    try {
      await api.strategies.deactivate(strategy.id);
      await loadStrategies();
    } catch (err) {
      console.error('Failed to deactivate strategy:', err);
      alert('Failed to deactivate strategy');
    }
  }

  async function archiveStrategy(strategy: Strategy) {
    try {
      await api.strategies.archive(strategy.id);
      await loadStrategies();
    } catch (err) {
      console.error('Failed to archive strategy:', err);
      alert('Failed to archive strategy');
    }
  }

  async function deleteStrategy(strategy: Strategy) {
    try {
      await api.strategies.delete(strategy.id);
      await loadStrategies();
      deleteConfirmOpen = false;
      strategyToDelete = null;
    } catch (err) {
      console.error('Failed to delete strategy:', err);
      alert('Failed to delete strategy');
    }
  }

  function openDetails(strategy: Strategy) {
    selectedStrategy = strategy;
    detailsModalOpen = true;
  }

  function openDeleteConfirm(strategy: Strategy) {
    strategyToDelete = strategy;
    deleteConfirmOpen = true;
  }

  // Status badge variant mapping
  function getStatusBadgeVariant(status: StrategyStatus): 'success' | 'warning' | 'error' | 'info' | 'default' {
    switch (status) {
      case 'approved':
        return 'success';
      case 'pending_approval':
        return 'warning';
      case 'rejected':
        return 'error';
      case 'archived':
        return 'info';
      default:
        return 'default';
    }
  }

  // Confidence badge variant
  function getConfidenceBadgeVariant(confidence: number): 'success' | 'warning' | 'error' {
    if (confidence >= 0.7) {
      return 'success';
    } else if (confidence >= 0.4) {
      return 'warning';
    } else {
      return 'error';
    }
  }

  // Confidence label
  function getConfidenceLabel(confidence: number): string {
    if (confidence >= 0.7) {
      return 'High';
    } else if (confidence >= 0.4) {
      return 'Medium';
    } else {
      return 'Low';
    }
  }

  // Format confidence percentage
  function formatConfidence(confidence: number): string {
    return `${Math.round(confidence * 100)}%`;
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

  // Load on mount
  onMount(() => {
    loadStrategies();
  });
</script>

<div class="container mx-auto p-6 space-y-6">
  <!-- Header -->
  <div class="flex justify-between items-center">
    <div>
      <h1 class="text-3xl font-bold text-text-primary">Strategies</h1>
      <p class="text-text-secondary mt-1">Manage your trading strategies</p>
    </div>
    <Button variant="primary" onclick={() => alert('Create strategy coming soon')}>
      Create Strategy
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
            <option value="draft">Draft</option>
            <option value="pending_approval">Pending Approval</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="archived">Archived</option>
          </select>
        </div>

        <div class="flex-1 min-w-[200px]">
          <label for="sort-by" class="block text-sm font-medium text-text-primary mb-1">Sort By</label>
          <select
            id="sort-by"
            bind:value={sortBy}
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="updated">Last Updated</option>
            <option value="created">Date Created</option>
            <option value="name">Name</option>
            <option value="confidence">Confidence</option>
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

        <div class="flex items-end">
          <Button variant="secondary" onclick={loadStrategies}>
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
          <p class="text-error-600 text-lg mb-4">Error loading strategies</p>
          <p class="text-text-secondary mb-4">{error}</p>
          <Button variant="primary" onclick={loadStrategies}>Try Again</Button>
        </div>
      </CardBody>
    </Card>
  {:else if filteredStrategies().length === 0}
    <Card>
      <CardBody>
        <EmptyState
          title="No strategies found"
          description={filterStatus === 'all' 
            ? "Get started by creating your first trading strategy." 
            : "No strategies match the selected filter."}
          action={{
            label: 'Create Strategy',
            onClick: () => alert('Create strategy coming soon'),
          }}
        />
      </CardBody>
    </Card>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {#each filteredStrategies() as strategy (strategy.id)}
        <Card>
          <CardHeader>
            <div class="flex justify-between items-start">
              <h3 class="text-lg font-semibold text-text-primary truncate flex-1">
                {strategy.name}
              </h3>
              <div class="flex gap-2 ml-2">
                <Badge variant={getStatusBadgeVariant(strategy.status)}>
                  {strategy.status.replace('_', ' ')}
                </Badge>
                <Badge variant={getConfidenceBadgeVariant(strategy.confidence)}>
                  {getConfidenceLabel(strategy.confidence)} ({formatConfidence(strategy.confidence)})
                </Badge>
              </div>
            </div>
          </CardHeader>
          
          <CardBody>
            <p class="text-text-secondary text-sm mb-4 line-clamp-3">
              {strategy.description}
            </p>
            
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-text-secondary">Timeframes:</span>
                <span class="text-text-primary font-medium">
                  {strategy.timeframes.join(', ')}
                </span>
              </div>
              
              <div class="flex justify-between">
                <span class="text-text-secondary">Entry Conditions:</span>
                <span class="text-text-primary font-medium">
                  {strategy.entryConditions.length}
                </span>
              </div>
              
              <div class="flex justify-between">
                <span class="text-text-secondary">Exit Conditions:</span>
                <span class="text-text-primary font-medium">
                  {strategy.exitConditions.length}
                </span>
              </div>
              
              <div class="flex justify-between">
                <span class="text-text-secondary">Risk/Reward:</span>
                <span class="text-text-primary font-medium">
                  1:{strategy.riskParameters.riskRewardRatio}
                </span>
              </div>
              
              <div class="flex justify-between text-xs pt-2 border-t border-border">
                <span class="text-text-secondary">Updated:</span>
                <span class="text-text-primary">
                  {formatDate(strategy.updatedAt)}
                </span>
              </div>
            </div>
          </CardBody>
          
          <CardFooter>
            <div class="flex gap-2 flex-wrap">
              <Button
                size="sm"
                variant="outline"
                onclick={() => openDetails(strategy)}
              >
                Details
              </Button>
              
              {#if strategy.status === 'approved'}
                <Button
                  size="sm"
                  variant="secondary"
                  onclick={() => deactivateStrategy(strategy)}
                >
                  Deactivate
                </Button>
              {:else if strategy.status === 'draft' || strategy.status === 'rejected'}
                <Button
                  size="sm"
                  variant="success"
                  onclick={() => activateStrategy(strategy)}
                >
                  Activate
                </Button>
              {/if}
              
              {#if strategy.status !== 'archived'}
                <Button
                  size="sm"
                  variant="secondary"
                  onclick={() => archiveStrategy(strategy)}
                >
                  Archive
                </Button>
              {/if}
              
              <Button
                size="sm"
                variant="danger"
                onclick={() => openDeleteConfirm(strategy)}
              >
                Delete
              </Button>
            </div>
          </CardFooter>
        </Card>
      {/each}
    </div>
  {/if}
</div>

<!-- Strategy Details Modal -->
{#if selectedStrategy}
  <Modal bind:open={detailsModalOpen} title={selectedStrategy.name} size="xl">
    <ModalBody>
      <Tabs value="overview">
        <TabList>
          <Tab value="overview">Overview</Tab>
          <Tab value="rules">Rules</Tab>
          <Tab value="conditions">Conditions</Tab>
          <Tab value="risk">Risk Parameters</Tab>
        </TabList>

        <TabPanel value="overview">
          <div class="space-y-4">
            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">Description</h4>
              <p class="text-text-secondary text-sm">{selectedStrategy.description}</p>
            </div>

            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">Reasoning</h4>
              <p class="text-text-secondary text-sm whitespace-pre-wrap">{selectedStrategy.reasoning}</p>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <h4 class="text-sm font-semibold text-text-primary mb-1">Status</h4>
                <Badge variant={getStatusBadgeVariant(selectedStrategy.status)}>
                  {selectedStrategy.status.replace('_', ' ')}
                </Badge>
              </div>

              <div>
                <h4 class="text-sm font-semibold text-text-primary mb-1">Confidence</h4>
                <Badge variant={getConfidenceBadgeVariant(selectedStrategy.confidence)}>
                  {getConfidenceLabel(selectedStrategy.confidence)} ({formatConfidence(selectedStrategy.confidence)})
                </Badge>
              </div>

              <div>
                <h4 class="text-sm font-semibold text-text-primary mb-1">Timeframes</h4>
                <p class="text-text-secondary text-sm">{selectedStrategy.timeframes.join(', ')}</p>
              </div>

              {#if selectedStrategy.requiredPatterns && selectedStrategy.requiredPatterns.length > 0}
                <div>
                  <h4 class="text-sm font-semibold text-text-primary mb-1">Required Patterns</h4>
                  <p class="text-text-secondary text-sm">{selectedStrategy.requiredPatterns.join(', ')}</p>
                </div>
              {/if}
            </div>
          </div>
        </TabPanel>

        <TabPanel value="rules">
          <div class="space-y-4">
            {#if selectedStrategy.rules.length === 0}
              <p class="text-text-secondary text-sm">No rules defined</p>
            {:else}
              {#each selectedStrategy.rules as rule, idx}
                <div class="border border-border rounded-lg p-4">
                  <div class="flex items-center gap-2 mb-2">
                    <Badge variant={rule.type === 'entry' ? 'success' : rule.type === 'exit' ? 'error' : 'info'}>
                      {rule.type}
                    </Badge>
                    <Badge variant="default">{rule.logic}</Badge>
                  </div>
                  {#if rule.description}
                    <p class="text-text-secondary text-sm mb-2">{rule.description}</p>
                  {/if}
                  <div class="space-y-1">
                    {#each rule.conditions as condition}
                      <div class="text-sm text-text-primary bg-bg-secondary rounded px-2 py-1">
                        {condition.indicator} {condition.operator} {JSON.stringify(condition.value)}
                        {#if condition.timeframe}
                          <span class="text-text-secondary">({condition.timeframe})</span>
                        {/if}
                      </div>
                    {/each}
                  </div>
                </div>
              {/each}
            {/if}
          </div>
        </TabPanel>

        <TabPanel value="conditions">
          <div class="space-y-4">
            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-2">Entry Conditions</h4>
              {#if selectedStrategy.entryConditions.length === 0}
                <p class="text-text-secondary text-sm">No entry conditions</p>
              {:else}
                <div class="space-y-1">
                  {#each selectedStrategy.entryConditions as condition}
                    <div class="text-sm text-text-primary bg-bg-secondary rounded px-3 py-2">
                      {condition.indicator} {condition.operator} {JSON.stringify(condition.value)}
                      {#if condition.timeframe}
                        <span class="text-text-secondary ml-2">({condition.timeframe})</span>
                      {/if}
                    </div>
                  {/each}
                </div>
              {/if}
            </div>

            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-2">Exit Conditions</h4>
              {#if selectedStrategy.exitConditions.length === 0}
                <p class="text-text-secondary text-sm">No exit conditions</p>
              {:else}
                <div class="space-y-1">
                  {#each selectedStrategy.exitConditions as condition}
                    <div class="text-sm text-text-primary bg-bg-secondary rounded px-3 py-2">
                      {condition.indicator} {condition.operator} {JSON.stringify(condition.value)}
                      {#if condition.timeframe}
                        <span class="text-text-secondary ml-2">({condition.timeframe})</span>
                      {/if}
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          </div>
        </TabPanel>

        <TabPanel value="risk">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">Max Position Size</h4>
              <p class="text-text-secondary">{selectedStrategy.riskParameters.maxPositionSizePct}%</p>
            </div>

            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">Default Stop Loss</h4>
              <p class="text-text-secondary">{selectedStrategy.riskParameters.defaultStopLossPct}%</p>
            </div>

            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">Default Take Profit</h4>
              <p class="text-text-secondary">{selectedStrategy.riskParameters.defaultTakeProfitPct}%</p>
            </div>

            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">Max Daily Loss</h4>
              <p class="text-text-secondary">{selectedStrategy.riskParameters.maxDailyLossPct}%</p>
            </div>

            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">Max Open Positions</h4>
              <p class="text-text-secondary">{selectedStrategy.riskParameters.maxOpenPositions}</p>
            </div>

            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">Risk/Reward Ratio</h4>
              <p class="text-text-secondary">1:{selectedStrategy.riskParameters.riskRewardRatio}</p>
            </div>
          </div>
        </TabPanel>
      </Tabs>
    </ModalBody>
    <ModalFooter>
      <Button variant="secondary" onclick={() => detailsModalOpen = false}>Close</Button>
    </ModalFooter>
  </Modal>
{/if}

<!-- Delete Confirmation Modal -->
{#if strategyToDelete}
  <Modal bind:open={deleteConfirmOpen} title="Delete Strategy">
    <ModalBody>
      <p class="text-text-secondary">
        Are you sure you want to delete the strategy <strong>{strategyToDelete.name}</strong>?
        This action cannot be undone.
      </p>
    </ModalBody>
    <ModalFooter>
      <Button variant="secondary" onclick={() => deleteConfirmOpen = false}>Cancel</Button>
      <Button variant="danger" onclick={() => deleteStrategy(strategyToDelete!)}>Delete</Button>
    </ModalFooter>
  </Modal>
{/if}

<style>
  .line-clamp-3 {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
