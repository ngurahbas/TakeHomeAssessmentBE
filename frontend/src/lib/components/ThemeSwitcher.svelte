<script lang="ts">
	import { Monitor, Moon, Sun } from 'lucide-svelte';
	import { cycle, getMode, type ColorMode } from '$lib/theme.svelte';

	const labels: Record<ColorMode, string> = {
		system: 'System',
		light: 'Light',
		dark: 'Dark'
	};
</script>

<button
	type="button"
	class="btn-icon btn preset-tonal-surface"
	aria-label={`Color mode: ${labels[getMode()]}`}
	title={`Color mode: ${labels[getMode()]} (click to cycle)`}
	onclick={cycle}
>
	{#if getMode() === 'light'}
		<Sun size={18} strokeWidth={1.75} />
	{:else if getMode() === 'dark'}
		<Moon size={18} strokeWidth={1.75} />
	{:else}
		<Monitor size={18} strokeWidth={1.75} />
	{/if}
</button>
