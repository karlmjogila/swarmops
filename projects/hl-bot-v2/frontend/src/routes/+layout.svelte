<script lang="ts">
	import '../app.css';
	import { page } from '$app/stores';
	import { isConnected } from '$lib/stores/websocket';
	import type { Snippet } from 'svelte';
	
	let { children }: { children: Snippet } = $props();
	
	interface NavSection {
		label: string;
		items: NavItem[];
	}
	
	interface NavItem {
		name: string;
		href: string;
		icon: string;
		badge?: string;
	}
	
	const navSections: NavSection[] = [
		{
			label: 'Overview',
			items: [
				{ name: 'Dashboard', href: '/', icon: '📊' },
			]
		},
		{
			label: 'Trading',
			items: [
				{ name: 'Backtest', href: '/backtest', icon: '⏪' },
				{ name: 'Strategies', href: '/strategies', icon: '🎯' },
				{ name: 'Trades', href: '/trades', icon: '💹' },
			]
		},
		{
			label: 'Analysis',
			items: [
				{ name: 'Journal', href: '/journal', icon: '📝' },
			]
		},
		{
			label: 'Data',
			items: [
				{ name: 'Ingest', href: '/ingest', icon: '📥' },
			]
		}
	];
	
	// Mobile sidebar state
	let sidebarOpen = $state(false);
	
	// Close sidebar when navigating
	$effect(() => {
		$page.url.pathname;
		sidebarOpen = false;
	});
	
	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}
</script>

<div class="min-h-screen flex bg-dark-900">
	<!-- Mobile Backdrop -->
	{#if sidebarOpen}
		<button
			class="fixed inset-0 bg-black/50 z-30 lg:hidden"
			onclick={toggleSidebar}
			aria-label="Close sidebar"
		></button>
	{/if}
	
	<!-- Sidebar -->
	<aside 
		class="fixed lg:static inset-y-0 left-0 z-40 w-64 bg-dark-800 border-r border-dark-700 flex flex-col transform transition-transform duration-200 lg:translate-x-0"
		class:translate-x-0={sidebarOpen}
		class:-translate-x-full={!sidebarOpen}
	>
		<!-- Header -->
		<div class="p-6 border-b border-dark-700">
			<div class="flex items-center justify-between">
				<div>
					<h1 class="text-2xl font-bold text-primary-400">HL-Bot V2</h1>
					<p class="text-sm text-gray-400 mt-1">Trading Research Platform</p>
				</div>
				<button 
					class="lg:hidden p-2 text-gray-400 hover:text-white"
					onclick={toggleSidebar}
					aria-label="Close menu"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
		</div>
		
		<!-- Navigation -->
		<nav class="flex-1 overflow-y-auto p-4">
			{#each navSections as section}
				<div class="mb-6">
					<div class="px-3 mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
						{section.label}
					</div>
					<ul class="space-y-1">
						{#each section.items as item}
							<li>
								<a 
									href={item.href}
									class="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-dark-700 transition-colors duration-150"
									class:bg-primary-900={$page.url.pathname === item.href}
									class:text-primary-400={$page.url.pathname === item.href}
									class:text-gray-300={$page.url.pathname !== item.href}
								>
									<span class="text-xl">{item.icon}</span>
									<span class="font-medium flex-1">{item.name}</span>
									{#if item.badge}
										<span class="px-2 py-0.5 text-xs font-semibold bg-primary-600 text-white rounded-full">
											{item.badge}
										</span>
									{/if}
								</a>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		</nav>
		
		<!-- Footer -->
		<div class="p-4 border-t border-dark-700">
			<!-- Connection Status -->
			<div class="flex items-center gap-2 px-3 py-2 mb-2 rounded-lg bg-dark-700">
				<div 
					class="w-2 h-2 rounded-full transition-colors duration-300"
					class:bg-green-500={$isConnected}
					class:bg-red-500={!$isConnected}
				></div>
				<span class="text-xs text-gray-400">
					{$isConnected ? 'Connected' : 'Disconnected'}
				</span>
			</div>
			
			<!-- User Info -->
			<div class="flex items-center gap-3 px-3 py-2">
				<div class="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-sm font-bold text-white shadow-lg">
					U
				</div>
				<div class="flex-1 min-w-0">
					<p class="text-sm font-medium text-gray-200 truncate">User</p>
					<p class="text-xs text-gray-400 truncate">user@example.com</p>
				</div>
			</div>
		</div>
	</aside>
	
	<!-- Main Content -->
	<div class="flex-1 flex flex-col min-w-0">
		<!-- Mobile Header -->
		<header class="lg:hidden bg-dark-800 border-b border-dark-700 p-4">
			<button
				class="flex items-center gap-2 text-gray-300 hover:text-white"
				onclick={toggleSidebar}
			>
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
				</svg>
				<span class="font-semibold">Menu</span>
			</button>
		</header>
		
		<!-- Page Content -->
		<main class="flex-1 overflow-auto">
			{@render children()}
		</main>
	</div>
</div>
