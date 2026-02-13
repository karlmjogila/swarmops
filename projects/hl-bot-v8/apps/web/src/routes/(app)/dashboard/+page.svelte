<script lang="ts">
	import { onMount } from 'svelte';
	import { strategies, signals, trades } from '$lib/stores';
	import Card from '$lib/components/ui/Card.svelte';
	import CardHeader from '$lib/components/ui/CardHeader.svelte';
	import CardBody from '$lib/components/ui/CardBody.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import LoadingState from '$lib/components/layout/LoadingState.svelte';
	import EmptyState from '$lib/components/layout/EmptyState.svelte';
	import type { Trade, Signal, Strategy } from '@hl-bot/shared';

	// Local state
	let loading = true;
	let error: Error | null = null;

	// Computed values
	$: activeStrategies = $strategies.items.filter((s: Strategy) => s.status === 'active');
	$: activeSignals = $signals.items.filter((s: Signal) => s.status === 'active');
	$: openTrades = $trades.items.filter((t: Trade) => t.status === 'open');
	$: closedTrades = $trades.items.filter((t: Trade) => t.status === 'closed');

	// Calculate metrics
	$: totalPnL = closedTrades.reduce((sum, t) => sum + (t.realizedPnl || 0), 0);
	$: winningTrades = closedTrades.filter((t) => (t.realizedPnl || 0) > 0);
	$: losingTrades = closedTrades.filter((t) => (t.realizedPnl || 0) < 0);
	$: winRate = closedTrades.length > 0 
		? (winningTrades.length / closedTrades.length) * 100 
		: 0;
	$: averageWin = winningTrades.length > 0
		? winningTrades.reduce((sum, t) => sum + (t.realizedPnl || 0), 0) / winningTrades.length
		: 0;
	$: averageLoss = losingTrades.length > 0
		? losingTrades.reduce((sum, t) => sum + (t.realizedPnl || 0), 0) / losingTrades.length
		: 0;
	$: profitFactor = averageLoss !== 0 ? Math.abs(averageWin / averageLoss) : 0;

	// Load initial data
	onMount(async () => {
		try {
			loading = true;
			await Promise.all([
				strategies.load({ status: 'active' }),
				signals.loadActive(),
				trades.load({ limit: 50 })
			]);
			await trades.loadStats();
		} catch (err) {
			error = err instanceof Error ? err : new Error('Failed to load dashboard data');
			console.error('Dashboard load error:', err);
		} finally {
			loading = false;
		}
	});

	// Format currency
	function formatCurrency(value: number): string {
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD',
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		}).format(value);
	}

	// Format percentage
	function formatPercent(value: number): string {
		return `${value.toFixed(2)}%`;
	}

	// Format date
	function formatDate(date: Date | string): string {
		return new Date(date).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	// Get badge variant for signal status
	function getSignalBadgeVariant(status: string): 'success' | 'warning' | 'error' | 'default' {
		switch (status) {
			case 'active': return 'success';
			case 'pending': return 'warning';
			case 'cancelled': return 'error';
			default: return 'default';
		}
	}

	// Get badge variant for trade status
	function getTradeBadgeVariant(status: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
		switch (status) {
			case 'open': return 'info';
			case 'closed': return 'success';
			case 'cancelled': return 'error';
			default: return 'default';
		}
	}

	// Get direction badge variant
	function getDirectionBadgeVariant(direction: string): 'long' | 'short' {
		return direction === 'long' ? 'long' : 'short';
	}
</script>

<div class="min-h-screen bg-bg-primary p-6">
	<div class="max-w-7xl mx-auto space-y-6">
		<!-- Header -->
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-3xl font-bold text-text-primary">Dashboard</h1>
				<p class="text-text-secondary mt-1">Monitor your trading activity and performance</p>
			</div>
			<div class="flex gap-3">
				<Button variant="outlined" href="/strategies">Strategies</Button>
				<Button variant="outlined" href="/signals">Signals</Button>
				<Button variant="primary" href="/backtest">Run Backtest</Button>
			</div>
		</div>

		{#if loading}
			<LoadingState message="Loading dashboard..." />
		{:else if error}
			<Card variant="elevated" padding="lg">
				<div class="text-center">
					<p class="text-error text-lg font-semibold mb-2">Failed to Load Dashboard</p>
					<p class="text-text-secondary">{error.message}</p>
					<Button 
						variant="primary" 
						class="mt-4"
						onclick={() => window.location.reload()}
					>
						Retry
					</Button>
				</div>
			</Card>
		{:else}
			<!-- Key Metrics -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
				<!-- Total PnL -->
				<Card variant="elevated" padding="md">
					<div class="space-y-2">
						<p class="text-text-secondary text-sm font-medium">Total PnL</p>
						<p class={`text-2xl font-bold ${totalPnL >= 0 ? 'text-long-green' : 'text-short-red'}`}>
							{formatCurrency(totalPnL)}
						</p>
						<p class="text-text-tertiary text-xs">
							{closedTrades.length} closed trades
						</p>
					</div>
				</Card>

				<!-- Win Rate -->
				<Card variant="elevated" padding="md">
					<div class="space-y-2">
						<p class="text-text-secondary text-sm font-medium">Win Rate</p>
						<p class={`text-2xl font-bold ${winRate >= 50 ? 'text-long-green' : 'text-short-red'}`}>
							{formatPercent(winRate)}
						</p>
						<p class="text-text-tertiary text-xs">
							{winningTrades.length}W / {losingTrades.length}L
						</p>
					</div>
				</Card>

				<!-- Active Strategies -->
				<Card variant="elevated" padding="md">
					<div class="space-y-2">
						<p class="text-text-secondary text-sm font-medium">Active Strategies</p>
						<p class="text-2xl font-bold text-text-primary">
							{activeStrategies.length}
						</p>
						<p class="text-text-tertiary text-xs">
							{$strategies.items.length} total
						</p>
					</div>
				</Card>

				<!-- Open Trades -->
				<Card variant="elevated" padding="md">
					<div class="space-y-2">
						<p class="text-text-secondary text-sm font-medium">Open Trades</p>
						<p class="text-2xl font-bold text-info">
							{openTrades.length}
						</p>
						<p class="text-text-tertiary text-xs">
							{activeSignals.length} active signals
						</p>
					</div>
				</Card>
			</div>

			<!-- Additional Metrics Row -->
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<!-- Profit Factor -->
				<Card variant="default" padding="md">
					<div class="space-y-2">
						<p class="text-text-secondary text-sm font-medium">Profit Factor</p>
						<p class={`text-xl font-bold ${profitFactor >= 1.5 ? 'text-long-green' : profitFactor >= 1 ? 'text-warning' : 'text-short-red'}`}>
							{profitFactor.toFixed(2)}
						</p>
					</div>
				</Card>

				<!-- Average Win -->
				<Card variant="default" padding="md">
					<div class="space-y-2">
						<p class="text-text-secondary text-sm font-medium">Average Win</p>
						<p class="text-xl font-bold text-long-green">
							{formatCurrency(averageWin)}
						</p>
					</div>
				</Card>

				<!-- Average Loss -->
				<Card variant="default" padding="md">
					<div class="space-y-2">
						<p class="text-text-secondary text-sm font-medium">Average Loss</p>
						<p class="text-xl font-bold text-short-red">
							{formatCurrency(averageLoss)}
						</p>
					</div>
				</Card>
			</div>

			<!-- Main Content Grid -->
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<!-- Active Signals -->
				<Card variant="elevated">
					<CardHeader>
						<div class="flex items-center justify-between">
							<h2 class="text-xl font-semibold text-text-primary">Active Signals</h2>
							<Badge variant="info" dot>{activeSignals.length}</Badge>
						</div>
					</CardHeader>
					<CardBody>
						{#if activeSignals.length === 0}
							<EmptyState 
								title="No Active Signals"
								description="Signals will appear here when your strategies generate them"
							/>
						{:else}
							<div class="space-y-3">
								{#each activeSignals.slice(0, 5) as signal}
									<div class="flex items-center justify-between p-3 bg-bg-tertiary rounded-lg hover:bg-bg-hover transition-colors">
										<div class="flex-1">
											<div class="flex items-center gap-2 mb-1">
												<Badge variant={getDirectionBadgeVariant(signal.direction)} size="sm">
													{signal.direction.toUpperCase()}
												</Badge>
												<span class="font-medium text-text-primary">{signal.symbol}</span>
												<Badge variant={getSignalBadgeVariant(signal.status)} size="sm">
													{signal.status}
												</Badge>
											</div>
											<p class="text-sm text-text-secondary">
												Entry: {formatCurrency(signal.entryPrice)} • 
												Confidence: {formatPercent(signal.confidence * 100)}
											</p>
										</div>
										<div class="text-right">
											<p class="text-xs text-text-tertiary">
												{formatDate(signal.createdAt)}
											</p>
										</div>
									</div>
								{/each}
								{#if activeSignals.length > 5}
									<div class="text-center pt-2">
										<Button variant="ghost" size="sm" href="/signals">
											View All {activeSignals.length} Signals
										</Button>
									</div>
								{/if}
							</div>
						{/if}
					</CardBody>
				</Card>

				<!-- Open Trades -->
				<Card variant="elevated">
					<CardHeader>
						<div class="flex items-center justify-between">
							<h2 class="text-xl font-semibold text-text-primary">Open Trades</h2>
							<Badge variant="info" dot>{openTrades.length}</Badge>
						</div>
					</CardHeader>
					<CardBody>
						{#if openTrades.length === 0}
							<EmptyState 
								title="No Open Trades"
								description="Your active trades will be displayed here"
							/>
						{:else}
							<div class="space-y-3">
								{#each openTrades.slice(0, 5) as trade}
									<div class="flex items-center justify-between p-3 bg-bg-tertiary rounded-lg hover:bg-bg-hover transition-colors">
										<div class="flex-1">
											<div class="flex items-center gap-2 mb-1">
												<Badge variant={getDirectionBadgeVariant(trade.direction)} size="sm">
													{trade.direction.toUpperCase()}
												</Badge>
												<span class="font-medium text-text-primary">{trade.symbol}</span>
												<Badge variant={getTradeBadgeVariant(trade.status)} size="sm">
													{trade.status}
												</Badge>
											</div>
											<p class="text-sm text-text-secondary">
												Entry: {formatCurrency(trade.entryPrice)} • 
												Size: {trade.size}
											</p>
										</div>
										<div class="text-right">
											<p class={`text-sm font-semibold ${(trade.unrealizedPnl || 0) >= 0 ? 'text-long-green' : 'text-short-red'}`}>
												{formatCurrency(trade.unrealizedPnl || 0)}
											</p>
											<p class="text-xs text-text-tertiary">
												{formatDate(trade.createdAt)}
											</p>
										</div>
									</div>
								{/each}
								{#if openTrades.length > 5}
									<div class="text-center pt-2">
										<Button variant="ghost" size="sm" href="/journal">
											View All {openTrades.length} Trades
										</Button>
									</div>
								{/if}
							</div>
						{/if}
					</CardBody>
				</Card>
			</div>

			<!-- Active Strategies -->
			<Card variant="elevated">
				<CardHeader>
					<div class="flex items-center justify-between">
						<h2 class="text-xl font-semibold text-text-primary">Active Strategies</h2>
						<Badge variant="success" dot>{activeStrategies.length}</Badge>
					</div>
				</CardHeader>
				<CardBody>
					{#if activeStrategies.length === 0}
						<EmptyState 
							title="No Active Strategies"
							description="Activate or create strategies to start generating signals"
						>
							<Button variant="primary" href="/strategies" class="mt-4">
								Browse Strategies
							</Button>
						</EmptyState>
					{:else}
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
							{#each activeStrategies as strategy}
								<div class="p-4 bg-bg-tertiary rounded-lg hover:bg-bg-hover transition-colors cursor-pointer">
									<div class="flex items-start justify-between mb-2">
										<h3 class="font-semibold text-text-primary">{strategy.name}</h3>
										<Badge variant="success" size="sm" dot>Active</Badge>
									</div>
									{#if strategy.description}
										<p class="text-sm text-text-secondary mb-3 line-clamp-2">
											{strategy.description}
										</p>
									{/if}
									<div class="flex items-center justify-between text-xs text-text-tertiary">
										<span>Updated {formatDate(strategy.updatedAt)}</span>
									</div>
								</div>
							{/each}
						</div>
						<div class="text-center pt-4">
							<Button variant="ghost" href="/strategies">
								View All Strategies
							</Button>
						</div>
					{/if}
				</CardBody>
			</Card>

			<!-- Recent Activity -->
			<Card variant="elevated">
				<CardHeader>
					<h2 class="text-xl font-semibold text-text-primary">Recent Activity</h2>
				</CardHeader>
				<CardBody>
					{#if closedTrades.length === 0}
						<EmptyState 
							title="No Recent Activity"
							description="Your trading history will appear here"
						/>
					{:else}
						<div class="space-y-2">
							{#each closedTrades.slice(0, 10) as trade}
								<div class="flex items-center justify-between p-3 bg-bg-tertiary rounded-lg hover:bg-bg-hover transition-colors">
									<div class="flex items-center gap-3">
										<Badge variant={getDirectionBadgeVariant(trade.direction)} size="sm">
											{trade.direction.toUpperCase()}
										</Badge>
										<div>
											<p class="font-medium text-text-primary">{trade.symbol}</p>
											<p class="text-xs text-text-tertiary">{formatDate(trade.closedAt || trade.createdAt)}</p>
										</div>
									</div>
									<div class="text-right">
										<p class={`font-semibold ${(trade.realizedPnl || 0) >= 0 ? 'text-long-green' : 'text-short-red'}`}>
											{formatCurrency(trade.realizedPnl || 0)}
										</p>
										<p class="text-xs text-text-tertiary">
											{trade.exitPrice ? formatCurrency(trade.exitPrice) : 'N/A'}
										</p>
									</div>
								</div>
							{/each}
							{#if closedTrades.length > 10}
								<div class="text-center pt-2">
									<Button variant="ghost" size="sm" href="/journal">
										View Full History
									</Button>
								</div>
							{/if}
						</div>
					{/if}
				</CardBody>
			</Card>
		{/if}
	</div>
</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
