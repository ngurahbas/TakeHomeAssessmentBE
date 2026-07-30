<script lang="ts">
	import { CircleAlert } from 'lucide-svelte';
	import type { Snippet } from 'svelte';

	let {
		data,
		children
	}: { data: { isAdmin: boolean }; children: Snippet } = $props();
</script>

{#if data.isAdmin}
	{@render children()}
{:else}
	<section class="card preset-filled-surface-100-900 mx-auto max-w-2xl space-y-4 p-8 text-center">
		<span
			class="bg-warning-500/15 text-warning-500 mx-auto grid h-12 w-12 place-items-center rounded-full"
		>
			<CircleAlert size={22} strokeWidth={1.75} />
		</span>
		<div class="space-y-1">
			<h1 class="h3">Admin only</h1>
			<p class="opacity-70 text-sm">
				AI escalations are restricted to administrators. Reach out to your account owner if you need
				access.
			</p>
		</div>
		<a href="/dashboard" class="btn preset-tonal-surface mx-auto">Back to dashboard</a>
	</section>
{/if}
