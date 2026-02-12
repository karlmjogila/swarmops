<script lang="ts">
import { TradeLog, EquityCurve } from '$lib/components';
</script>

<svelte:head>
	<title>Trades - HL-Bot V2</title>
</svelte:head>

<div class="space-y-8">
	<div>
		<h1 class="text-3xl font-bold text-white mb-2">Trade History</h1>
		<p class="text-gray-400">Complete audit trail of all trades with full context</p>
	</div>
	
	<!-- Equity Curve Chart -->
	<div>
		<h2 class="text-xl font-semibold text-white mb-4">Equity Curve</h2>
		<EquityCurve height={400} initialBalance={10000} />
	</div>
	
	<!-- Trade Log -->
	<div>
		<h2 class="text-xl font-semibold text-white mb-4">Trade Log</h2>
		<TradeLog />
	</div>
</div>
