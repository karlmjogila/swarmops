<script lang="ts">
	/**
	 * App Layout
	 * 
	 * Shared layout for all authenticated app pages.
	 * Includes AuthGuard and AppHeader for consistent navigation.
	 */
	import { AuthGuard } from '$lib/components/guards';
	import { AppHeader } from '$lib/components/layout';

	let { children } = $props();
</script>

<AuthGuard>
	<AppHeader />
	{@render children()}
</AuthGuard>
