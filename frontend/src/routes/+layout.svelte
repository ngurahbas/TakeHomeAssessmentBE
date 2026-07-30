<script lang="ts">
	import './layout.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { AppBar } from '@skeletonlabs/skeleton-svelte';
	import favicon from '$lib/assets/favicon.svg';
	import ThemeSelector from '$lib/components/ThemeSelector.svelte';
	import ThemeSwitcher from '$lib/components/ThemeSwitcher.svelte';
	import { init as initTheme } from '$lib/theme.svelte';

	let { children, data } = $props();

	const STANDALONE_PREFIXES = ['/public'];
	const isStandalone = $derived(
		STANDALONE_PREFIXES.some((p) => $page.url.pathname.startsWith(p))
	);

	onMount(() => {
		initTheme();
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Real Estate AI Assistant</title>
</svelte:head>

{#if isStandalone}
	{@render children()}
{:else}
	<AppBar>
		<AppBar.Toolbar>
			<AppBar.Lead />
			<AppBar.Trail>
				<ThemeSelector />
				<ThemeSwitcher />
			</AppBar.Trail>
		</AppBar.Toolbar>
	</AppBar>

	<main class="container mx-auto p-6">
		{@render children()}
	</main>
{/if}
