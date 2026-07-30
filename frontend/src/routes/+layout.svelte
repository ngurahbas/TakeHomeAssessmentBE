<script lang="ts">
	import './layout.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { AppBar } from '@skeletonlabs/skeleton-svelte';
	import { Building2 } from 'lucide-svelte';
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
			<AppBar.Lead>
				<a
					href={data.user ? '/dashboard' : '/'}
					class="flex items-center gap-2 px-2 font-semibold tracking-tight"
				>
					<Building2 size={20} strokeWidth={1.75} class="text-primary-500" />
					<span>Real Estate AI</span>
				</a>
			</AppBar.Lead>
			<AppBar.Trail>
				{#if data.user}
					<a href="/dashboard" class="btn btn-sm preset-tonal-surface">Dashboard</a>
				{:else}
					<a href="/login" class="btn btn-sm preset-filled-primary-500">Sign in</a>
				{/if}
				<ThemeSelector />
				<ThemeSwitcher />
			</AppBar.Trail>
		</AppBar.Toolbar>
	</AppBar>

	<main class="container mx-auto p-6">
		{@render children()}
	</main>
{/if}
