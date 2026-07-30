<script lang="ts">
	import { ArrowLeft } from 'lucide-svelte';
	import { createProperty } from '../properties.remote';
	import PropertyForm from '../_components/PropertyForm.svelte';
</script>

<svelte:head>
	<title>New property · Real Estate AI</title>
</svelte:head>

<section class="space-y-4">
	<header class="flex items-center gap-3">
		<a href="/dashboard/properties" class="btn-icon btn-icon-sm preset-tonal-surface" aria-label="Back">
			<ArrowLeft size={16} strokeWidth={1.75} />
		</a>
		<div>
			<h1 class="h2">New property</h1>
			<p class="opacity-70 text-sm">Create a new listing.</p>
		</div>
	</header>

	<PropertyForm mode="create" form={createProperty} submitLabel="Create property" />
</section>
