<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/utils/api';
	import type { 
		StrategyRule, 
		StrategyListResponse,
		MarketPhase,
		Timeframe 
	} from '$lib/types';
	import StrategyCard from '$lib/components/StrategyCard.svelte';
	import StrategyDetails from '$lib/components/StrategyDetails.svelte';

	// State
	let strategies: readonly StrategyRule[] = [];
	let filteredStrategies: readonly StrategyRule[] = [];
	let selectedStrategy: StrategyRule | null = null;
	let isLoading = true;
	let error: string | null = null;
	let showDetails = false;
	let showCreateModal = false;

	// Filter state
	let searchQuery = '';
	let filterPhase: MarketPhase | 'all' = 'all';
	let filterEnabled: 'all' | 'enabled' | 'disabled' = 'all';
	let sortBy: 'name' | 'effectiveness' | 'trades' | 'winrate' = 'effectiveness';

	// Load strategies from API
	async function loadStrategies() {
		isLoading = true;
		error = null;
		
		const result = await api.get<StrategyListResponse>('/api/v1/strategies');
		
		if (result.success && result.data) {
			strategies = result.data.strategies;
			applyFilters();
		} else {
			error = result.error || 'Failed to load strategies';
		}
		
		isLoading = false;
	}

	// Apply filters and sorting
	function applyFilters() {
		let filtered = [...strategies];

		// Search filter
		if (searchQuery) {
			const query = searchQuery.toLowerCase();
			filtered = filtered.filter(s => 
				s.name.toLowerCase().includes(query) ||
				s.description.toLowerCase().includes(query)
			);
		}

		// Phase filter
		if (filterPhase !== 'all') {
			filtered = filtered.filter(s => s.market_phase === filterPhase);
		}

		// Enabled filter
		if (filterEnabled !== 'all') {
			filtered = filtered.filter(s => 
				filterEnabled === 'enabled' ? s.enabled : !s.enabled
			);
		}

		// Sort
		filtered.sort((a, b) => {
			switch (sortBy) {
				case 'name':
					return a.name.localeCompare(b.name);
				case 'effectiveness':
					return b.effectiveness_score - a.effectiveness_score;
				case 'trades':
					return b.total_trades - a.total_trades;
				case 'winrate':
					const aWinRate = a.total_trades > 0 ? a.winning_trades / a.total_trades : 0;
					const bWinRate = b.total_trades > 0 ? b.winning_trades / b.total_trades : 0;
					return bWinRate - aWinRate;
				default:
					return 0;
			}
		});

		filteredStrategies = filtered;
	}

	// Toggle strategy enabled status
	async function toggleStrategy(strategyId: string, enabled: boolean) {
		const result = await api.patch(`/api/v1/strategies/${strategyId}`, { enabled });
		
		if (result.success) {
			// Update local state
			strategies = strategies.map(s => 
				s.id === strategyId ? { ...s, enabled } as StrategyRule : s
			);
			applyFilters();
		} else {
			error = result.error || 'Failed to update strategy';
		}
	}

	// View strategy details
	function viewStrategy(strategy: StrategyRule) {
		selectedStrategy = strategy;
		showDetails = true;
	}

	// Close details panel
	function closeDetails() {
		showDetails = false;
		selectedStrategy = null;
	}

	// Delete strategy
	async function deleteStrategy(strategyId: string) {
		if (!confirm('Are you sure you want to delete this strategy?')) {
			return;
		}

		const result = await api.delete(`/api/v1/strategies/${strategyId}`);
		
		if (result.success) {
			strategies = strategies.filter(s => s.id !== strategyId);
			applyFilters();
			closeDetails();
		} else {
			error = result.error || 'Failed to delete strategy';
		}
	}

	// Safe toggle handler that captures the current strategy ID
	function handleStrategyToggle(strategyId: string, enabled: boolean) {
		toggleStrategy(strategyId, enabled);
	}

	// Reactive statements
	$: {
		searchQuery;
		filterPhase;
		filterEnabled;
		sortBy;
		applyFilters();
	}

	// Calculate summary stats
	$: enabledCount = strategies.filter(s => s.enabled).length;
	$: avgEffectiveness = strategies.length > 0 
		? strategies.reduce((sum, s) => sum + s.effectiveness_score, 0) / strategies.length 
		: 0;
	$: totalTrades = strategies.reduce((sum, s) => sum + s.total_trades, 0);
	$: totalWinRate = totalTrades > 0 
		? strategies.reduce((sum, s) => sum + s.winning_trades, 0) / totalTrades
		: 0;

	onMount(() => {
		loadStrategies();
	});
</script>

<svelte:head>
	<title>Strategies - HL-Bot V2</title>
</svelte:head>

<div class="space-y-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-3xl font-bold text-white mb-2">Strategy Manager</h1>
			<p class="text-gray-400">Manage and monitor trading strategies</p>
		</div>
		<button 
			class="btn-primary flex items-center gap-2"
			onclick={() => showCreateModal = true}
		>
			<span>➕</span>
			<span>Create Strategy</span>
		</button>
	</div>

	{#if error}
		<div class="alert-error">
			<span class="text-xl">⚠️</span>
			<span>{error}</span>
			<button 
				class="ml-auto text-red-300 hover:text-white"
				onclick={() => error = null}
			>
				✕
			</button>
		</div>
	{/if}

	<!-- Summary Stats -->
	<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
		<div class="card p-4">
			<div class="text-sm text-gray-400 mb-1">Total Strategies</div>
			<div class="text-2xl font-bold text-white">{strategies.length}</div>
		</div>
		<div class="card p-4">
			<div class="text-sm text-gray-400 mb-1">Enabled</div>
			<div class="text-2xl font-bold text-green-400">{enabledCount}</div>
		</div>
		<div class="card p-4">
			<div class="text-sm text-gray-400 mb-1">Avg Effectiveness</div>
			<div class="text-2xl font-bold text-blue-400">{(avgEffectiveness * 100).toFixed(1)}%</div>
		</div>
		<div class="card p-4">
			<div class="text-sm text-gray-400 mb-1">Overall Win Rate</div>
			<div class="text-2xl font-bold text-primary-400">{(totalWinRate * 100).toFixed(1)}%</div>
		</div>
	</div>

	<!-- Filters & Search -->
	<div class="card p-6">
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
			<!-- Search -->
			<div class="lg:col-span-2">
				<label for="search-strategies" class="block text-sm font-medium text-gray-300 mb-2">
					Search
				</label>
				<input 
					id="search-strategies"
					type="text" 
					bind:value={searchQuery}
					placeholder="Search strategies..."
					class="input w-full"
				/>
			</div>

			<!-- Phase Filter -->
			<div>
				<label for="filter-phase" class="block text-sm font-medium text-gray-300 mb-2">
					Market Phase
				</label>
				<select id="filter-phase" bind:value={filterPhase} class="select w-full">
					<option value="all">All Phases</option>
					<option value="drive">Drive</option>
					<option value="range">Range</option>
					<option value="liquidity">Liquidity</option>
				</select>
			</div>

			<!-- Status Filter -->
			<div>
				<label for="filter-status" class="block text-sm font-medium text-gray-300 mb-2">
					Status
				</label>
				<select id="filter-status" bind:value={filterEnabled} class="select w-full">
					<option value="all">All</option>
					<option value="enabled">Enabled</option>
					<option value="disabled">Disabled</option>
				</select>
			</div>

			<!-- Sort By -->
			<div>
				<label for="sort-by" class="block text-sm font-medium text-gray-300 mb-2">
					Sort By
				</label>
				<select id="sort-by" bind:value={sortBy} class="select w-full">
					<option value="effectiveness">Effectiveness</option>
					<option value="name">Name</option>
					<option value="trades">Total Trades</option>
					<option value="winrate">Win Rate</option>
				</select>
			</div>
		</div>
	</div>

	<!-- Strategy List -->
	{#if isLoading}
		<div class="card p-12">
			<div class="flex flex-col items-center justify-center text-gray-400">
				<div class="animate-spin text-4xl mb-4">⚙️</div>
				<p>Loading strategies...</p>
			</div>
		</div>
	{:else if filteredStrategies.length === 0}
		<div class="card p-12">
			<div class="text-center text-gray-400">
				<div class="text-6xl mb-4">🔍</div>
				<p class="text-lg mb-2">No strategies found</p>
				{#if searchQuery || filterPhase !== 'all' || filterEnabled !== 'all'}
					<p class="text-sm">Try adjusting your filters</p>
				{:else}
					<p class="text-sm">Create your first strategy to get started</p>
				{/if}
			</div>
		</div>
	{:else}
		<div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
			{#each filteredStrategies as strategy (strategy.id)}
				<StrategyCard 
					{strategy}
					on:toggle={(e) => toggleStrategy(strategy.id, e.detail.enabled)}
					on:view={() => viewStrategy(strategy)}
				/>
			{/each}
		</div>
	{/if}
</div>

<!-- Strategy Details Sidebar -->
{#if showDetails && selectedStrategy}
	{@const currentStrategyId = selectedStrategy.id}
	<StrategyDetails 
		strategy={selectedStrategy}
		on:close={closeDetails}
		on:delete={(e) => deleteStrategy(e.detail.id)}
		on:toggle={(e) => handleStrategyToggle(currentStrategyId, e.detail.enabled)}
	/>
{/if}

<!-- Create Strategy Modal (placeholder) -->
{#if showCreateModal}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div 
		class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" 
		onclick={() => showCreateModal = false}
		role="dialog"
		aria-modal="true"
		aria-labelledby="create-modal-title"
		tabindex="-1"
	>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div class="card p-8 max-w-2xl w-full mx-4" onclick={(e) => e.stopPropagation()}>
			<h2 id="create-modal-title" class="text-2xl font-bold text-white mb-4">Create Strategy</h2>
			<p class="text-gray-400 mb-6">
				Strategy creation via manual input coming soon. 
				Use the Content Ingestion feature to extract strategies from YouTube videos or PDFs.
			</p>
			<div class="flex justify-end gap-3">
				<button class="btn-secondary" onclick={() => showCreateModal = false}>
					Close
				</button>
				<a href="/ingest" class="btn-primary">
					Go to Ingest
				</a>
			</div>
		</div>
	</div>
{/if}

<style lang="postcss">
	.btn-primary {
		@apply px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors duration-200;
	}

	.btn-secondary {
		@apply px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white font-medium rounded-lg transition-colors duration-200;
	}

	.card {
		@apply bg-dark-800 border border-dark-700 rounded-lg;
	}

	.input {
		@apply bg-dark-700 border border-dark-600 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500;
	}

	.select {
		@apply bg-dark-700 border border-dark-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500;
	}

	.alert-error {
		@apply bg-red-900/20 border border-red-700 rounded-lg p-4 flex items-center gap-3 text-red-300;
	}
</style>
