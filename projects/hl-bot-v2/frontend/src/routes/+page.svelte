<script lang="ts">
	import { onMount } from 'svelte';
	import { isConnected } from '$lib/stores/websocket';
	import { backtestState } from '$lib/stores/backtest';
	
	interface StatCard {
		label: string;
		value: string;
		change: string;
		trend: 'up' | 'down' | 'neutral';
		icon: string;
	}
	
	interface QuickAction {
		title: string;
		description: string;
		href: string;
		icon: string;
		primary?: boolean;
	}
	
	const stats: StatCard[] = [
		{ label: 'Total Trades', value: '0', change: '0%', trend: 'neutral', icon: '💹' },
		{ label: 'Win Rate', value: '0%', change: '0%', trend: 'neutral', icon: '🎯' },
		{ label: 'Total P&L', value: '$0.00', change: '0%', trend: 'neutral', icon: '💰' },
		{ label: 'Sharpe Ratio', value: '0.00', change: '0%', trend: 'neutral', icon: '📈' }
	];
	
	const quickActions: QuickAction[] = [
		{
			title: 'Start Backtest',
			description: 'Run visual replay with pattern detection',
			href: '/backtest',
			icon: '⏪',
			primary: true
		},
		{
			title: 'Manage Strategies',
			description: 'View and configure trading strategies',
			href: '/strategies',
			icon: '🎯'
		},
		{
			title: 'View Journal',
			description: 'Review trading decisions and outcomes',
			href: '/journal',
			icon: '📝'
		},
		{
			title: 'Ingest Content',
			description: 'Upload videos and PDFs for AI analysis',
			href: '/ingest',
			icon: '📥'
		}
	];
	
	function getTrendColor(trend: 'up' | 'down' | 'neutral'): string {
		switch (trend) {
			case 'up':
				return 'text-green-400';
			case 'down':
				return 'text-red-400';
			default:
				return 'text-gray-400';
		}
	}
	
	function getTrendIcon(trend: 'up' | 'down' | 'neutral'): string {
		switch (trend) {
			case 'up':
				return '↑';
			case 'down':
				return '↓';
			default:
				return '→';
		}
	}
	
	// Check backend health
	let apiStatus = $state<'checking' | 'connected' | 'error'>('checking');
	let dbStatus = $state<'checking' | 'connected' | 'error'>('checking');
	
	onMount(async () => {
		// Check API health
		try {
			const response = await fetch('/api/health');
			apiStatus = response.ok ? 'connected' : 'error';
		} catch (error) {
			apiStatus = 'error';
		}
		
		// Check DB health (via API)
		try {
			const response = await fetch('/api/health/db');
			dbStatus = response.ok ? 'connected' : 'error';
		} catch (error) {
			dbStatus = 'error';
		}
	});
	
	function getStatusColor(status: typeof apiStatus) {
		switch (status) {
			case 'connected': return 'bg-green-500';
			case 'error': return 'bg-red-500';
			default: return 'bg-yellow-400 animate-pulse';
		}
	}
	
	function getStatusText(status: typeof apiStatus) {
		switch (status) {
			case 'connected': return 'Connected';
			case 'error': return 'Error';
			default: return 'Checking...';
		}
	}
</script>

<svelte:head>
	<title>Dashboard - HL-Bot V2</title>
</svelte:head>

<div class="min-h-screen bg-dark-900">
	<div class="max-w-7xl mx-auto p-6 lg:p-8 space-y-8">
		<!-- Header -->
		<div class="mb-8">
			<h1 class="text-4xl font-bold text-white mb-3 bg-gradient-to-r from-primary-400 to-primary-600 bg-clip-text text-transparent">
				Dashboard
			</h1>
			<p class="text-gray-400 text-lg">AI-Powered Trading Research & Execution System</p>
		</div>
		
		<!-- Stats Grid -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
			{#each stats as stat}
				<div class="card p-6 hover:border-primary-600/30 transition-colors duration-200">
					<div class="flex items-start justify-between mb-4">
						<span class="text-3xl">{stat.icon}</span>
						<span class={`text-lg font-bold ${getTrendColor(stat.trend)}`}>
							{getTrendIcon(stat.trend)}
						</span>
					</div>
					<p class="text-sm text-gray-400 mb-2">{stat.label}</p>
					<p class="text-3xl font-bold text-white mb-2">{stat.value}</p>
					<p class={`text-sm ${getTrendColor(stat.trend)}`}>
						{stat.change} vs last period
					</p>
				</div>
			{/each}
		</div>
		
		<!-- Quick Actions -->
		<div class="card p-6">
			<h2 class="text-2xl font-bold text-white mb-6 flex items-center gap-2">
				<span>⚡</span>
				Quick Actions
			</h2>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				{#each quickActions as action}
					<a 
						href={action.href}
						class="group p-6 rounded-xl border-2 transition-all duration-200 {action.primary 
							? 'border-primary-600 bg-primary-900/20 hover:bg-primary-900/30' 
							: 'border-dark-600 hover:border-primary-600/50 hover:bg-dark-700/50'}"
					>
						<div class="flex items-start gap-4">
							<span class="text-4xl group-hover:scale-110 transition-transform duration-200">
								{action.icon}
							</span>
							<div class="flex-1">
								<h3 class="text-lg font-bold text-white mb-1 group-hover:text-primary-400 transition-colors">
									{action.title}
								</h3>
								<p class="text-sm text-gray-400">
									{action.description}
								</p>
							</div>
							<svg class="w-5 h-5 text-gray-600 group-hover:text-primary-400 group-hover:translate-x-1 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
							</svg>
						</div>
					</a>
				{/each}
			</div>
		</div>
		
		<!-- System Status Grid -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
			<!-- System Status -->
			<div class="card p-6">
				<h3 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
					<span>🔧</span>
					System Status
				</h3>
				<div class="space-y-4">
					<div class="flex justify-between items-center p-3 bg-dark-700/50 rounded-lg">
						<span class="text-gray-300 font-medium">Backend API</span>
						<span class="flex items-center gap-2">
							<span class={`w-2.5 h-2.5 rounded-full ${getStatusColor(apiStatus)}`}></span>
							<span class="text-sm text-gray-300 font-medium">{getStatusText(apiStatus)}</span>
						</span>
					</div>
					<div class="flex justify-between items-center p-3 bg-dark-700/50 rounded-lg">
						<span class="text-gray-300 font-medium">Database</span>
						<span class="flex items-center gap-2">
							<span class={`w-2.5 h-2.5 rounded-full ${getStatusColor(dbStatus)}`}></span>
							<span class="text-sm text-gray-300 font-medium">{getStatusText(dbStatus)}</span>
						</span>
					</div>
					<div class="flex justify-between items-center p-3 bg-dark-700/50 rounded-lg">
						<span class="text-gray-300 font-medium">WebSocket</span>
						<span class="flex items-center gap-2">
							<span class={`w-2.5 h-2.5 rounded-full ${$isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
							<span class="text-sm text-gray-300 font-medium">
								{$isConnected ? 'Connected' : 'Disconnected'}
							</span>
						</span>
					</div>
				</div>
			</div>
			
			<!-- Strategy Engine -->
			<div class="card p-6">
				<h3 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
					<span>🧠</span>
					Strategy Engine
				</h3>
				<div class="space-y-4">
					<div class="flex justify-between items-center p-3 bg-dark-700/50 rounded-lg">
						<span class="text-gray-300 font-medium">Active Strategies</span>
						<span class="text-white font-bold text-lg">0</span>
					</div>
					<div class="flex justify-between items-center p-3 bg-dark-700/50 rounded-lg">
						<span class="text-gray-300 font-medium">Loaded Patterns</span>
						<span class="text-white font-bold text-lg">0</span>
					</div>
					<div class="flex justify-between items-center p-3 bg-dark-700/50 rounded-lg">
						<span class="text-gray-300 font-medium">Data Points</span>
						<span class="text-white font-bold text-lg">0</span>
					</div>
				</div>
			</div>
		</div>
		
		<!-- Recent Activity -->
		<div class="card p-6">
			<h2 class="text-2xl font-bold text-white mb-6 flex items-center gap-2">
				<span>📋</span>
				Recent Activity
			</h2>
			<div class="text-center py-16 text-gray-400">
				<div class="text-6xl mb-4">📊</div>
				<p class="text-lg font-medium mb-2">No recent activity</p>
				<p class="text-sm mb-6">Start a backtest or ingest content to get started</p>
				<a href="/backtest" class="btn btn-primary inline-flex items-center gap-2">
					<span>⏪</span>
					<span>Start Your First Backtest</span>
				</a>
			</div>
		</div>
	</div>
</div>
