<script lang="ts">
	import { ContentUploader } from '$lib/components';
</script>

<svelte:head>
	<title>Content Ingestion - HL-Bot V2</title>
</svelte:head>

<div class="space-y-8">
	<div>
		<h1 class="text-3xl font-bold text-white mb-2">Content Ingestion</h1>
		<p class="text-gray-400">Upload PDFs and YouTube videos for strategy extraction</p>
	</div>
	
	<ContentUploader />
	
	<!-- Info Section -->
	<div class="card p-6 bg-blue-900/10 border-blue-500/30">
		<h3 class="text-lg font-semibold text-blue-400 mb-3">How it works</h3>
		<ul class="space-y-2 text-sm text-gray-300">
			<li class="flex items-start gap-2">
				<span class="text-blue-400 mt-0.5">1.</span>
				<span><strong>YouTube:</strong> Upload educational trading videos. We'll transcribe the audio, extract key frames, and use Claude to identify strategy rules.</span>
			</li>
			<li class="flex items-start gap-2">
				<span class="text-blue-400 mt-0.5">2.</span>
				<span><strong>PDF:</strong> Upload trading books or guides. We'll extract text and analyze charts to identify patterns and rules.</span>
			</li>
			<li class="flex items-start gap-2">
				<span class="text-blue-400 mt-0.5">3.</span>
				<span><strong>Strategy Extraction:</strong> Extracted strategies are stored in your knowledge base and can be backtested immediately.</span>
			</li>
			<li class="flex items-start gap-2">
				<span class="text-blue-400 mt-0.5">4.</span>
				<span><strong>Learning Loop:</strong> As you trade, the system learns which extracted strategies work best and refines them over time.</span>
			</li>
		</ul>
	</div>
</div>
