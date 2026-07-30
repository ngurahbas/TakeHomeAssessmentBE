<script lang="ts">
	import { ArrowLeft } from 'lucide-svelte';
	import { updateProperty } from '../../properties.remote';
	import type { PropertyOut } from '../../properties.types';
	import PropertyForm from '../../_components/PropertyForm.svelte';

	let {
		data
	}: {
		data: { property: PropertyOut };
	} = $props();

	const property = $derived(data.property);
</script>

<svelte:head>
	<title>Edit {property.title} · Real Estate AI</title>
</svelte:head>

<section class="space-y-4">
	<header class="flex items-center gap-3">
		<a
			href={`/dashboard/properties/${property.id}`}
			class="btn-icon btn-icon-sm preset-tonal-surface"
			aria-label="Back"
		>
			<ArrowLeft size={16} strokeWidth={1.75} />
		</a>
		<div>
			<h1 class="h2">Edit property</h1>
			<p class="opacity-70 text-sm">{property.title}</p>
		</div>
	</header>

	<PropertyForm
		mode="edit"
		form={updateProperty}
		initial={property}
		submitLabel="Save changes"
	/>
</section>
