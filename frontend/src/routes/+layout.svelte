<script lang="ts">
	import './layout.css';
	import { AppBar } from '@skeletonlabs/skeleton-svelte';
	import favicon from '$lib/assets/favicon.svg';

	let { children, data } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Real Estate AI Assistant</title>
</svelte:head>

<AppBar />

<main class="container mx-auto p-6">
	{@render children()}
</main>
