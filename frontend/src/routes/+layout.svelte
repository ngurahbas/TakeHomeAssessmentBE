<script lang="ts">
	import './layout.css';
	import { AppBar } from '@skeletonlabs/skeleton-svelte';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';

	let { children, data } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Real Estate AI Assistant</title>
</svelte:head>

<AppBar>
	<AppBar.Toolbar class="container mx-auto">
		<AppBar.Lead>
			<a href="/" class="font-bold text-lg">Real Estate AI</a>
		</AppBar.Lead>
		<AppBar.Trail class="flex items-center gap-3">
			{#if data.user}
				<span class="text-sm opacity-75 hidden sm:inline">Signed in as {data.user.email}</span>
				<span class="badge preset-soft-primary">{data.user.role}</span>
			{:else if page.url.pathname !== '/login'}
				<a href="/login" class="btn btn-sm preset-filled-primary-500">Sign in</a>
			{/if}
		</AppBar.Trail>
	</AppBar.Toolbar>
</AppBar>

<main class="container mx-auto p-6">
	{@render children()}
</main>
