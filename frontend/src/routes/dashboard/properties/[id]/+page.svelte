<script lang="ts">
	import { ArrowLeft, Bed, Building2, Image as ImageIcon, MapPin, Pencil, Wallet } from 'lucide-svelte';
	import { deleteProperty } from '../properties.remote';
	import {
		STATUS_PRESET,
		type PropertyOut,
		type PropertyStatus
	} from '../properties.types';
	import DeletePropertyDialog from '../_components/DeletePropertyDialog.svelte';

	let {
		data
	}: {
		data: { property: PropertyOut };
	} = $props();

	const property = $derived(data.property);

	function statusPresetClass(s: PropertyStatus): string {
		return STATUS_PRESET[s];
	}

	function formatPrice(amount: number, currency: string): string {
		const formatter = new Intl.NumberFormat('en-US', {
			maximumFractionDigits: 2,
			minimumFractionDigits: 0
		});
		return `${currency} ${formatter.format(amount)}`;
	}

	function formatDateTime(iso: string): string {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toISOString().replace('T', ' ').slice(0, 16);
	}
</script>

<svelte:head>
	<title>{property.title} · Real Estate AI</title>
</svelte:head>

<section class="space-y-6">
	<header class="flex flex-wrap items-end justify-between gap-3">
		<div class="flex items-start gap-3">
			<a
				href="/dashboard/properties"
				class="btn-icon btn-icon-sm preset-tonal-surface"
				aria-label="Back to list"
			>
				<ArrowLeft size={16} strokeWidth={1.75} />
			</a>
			<div>
				<h1 class="h2 leading-tight">{property.title}</h1>
				<p class="opacity-70 mt-1 text-sm">
					{property.address_line}, {property.city}{property.district ? ` (${property.district})` : ''},
					{property.country_code}
				</p>
			</div>
		</div>
		<div class="flex items-center gap-2">
			<a
				href={`/dashboard/properties/${property.id}/edit`}
				class="btn preset-filled-primary-500"
			>
				<Pencil size={14} strokeWidth={1.75} />
				<span>Edit</span>
			</a>
			<DeletePropertyDialog
				id={property.id}
				title={property.title}
				form={deleteProperty.for(String(property.id))}
			/>
		</div>
	</header>

	<div class="grid gap-4 lg:grid-cols-3">
		<div class="card preset-filled-surface-100-900 space-y-4 p-5 lg:col-span-2">
			<div class="flex flex-wrap items-center gap-2 text-sm">
				<span class="badge {statusPresetClass(property.status)}">{property.status}</span>
				<span class="badge preset-tonal-surface text-xs">{property.listing_type}</span>
				<span class="badge preset-tonal-surface text-xs">{property.property_type}</span>
			</div>

			{#if property.description}
				<p class="text-sm leading-relaxed whitespace-pre-line">{property.description}</p>
			{:else}
				<p class="text-sm italic opacity-60">No description provided.</p>
			{/if}

			{#if property.amenities.length > 0}
				<div>
					<p class="text-xs font-semibold tracking-wider uppercase opacity-60">Amenities</p>
					<div class="mt-2 flex flex-wrap gap-2">
						{#each property.amenities as a (a)}
							<span class="chip preset-tonal-primary text-xs">{a}</span>
						{/each}
					</div>
				</div>
			{/if}

			{#if property.images.length > 0}
				<div>
					<p class="text-xs font-semibold tracking-wider uppercase opacity-60">Images</p>
					<ul class="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
						{#each property.images as img, i (img.url + i)}
							<li
								class="border-surface-200-800 bg-surface-50-950 space-y-1 overflow-hidden rounded-md border"
							>
								<a href={img.url} target="_blank" rel="noopener noreferrer" class="block">
									<img
										src={img.url}
										alt={img.alt ?? property.title}
										class="aspect-video w-full object-cover"
										loading="lazy"
									/>
								</a>
								<div class="p-2 text-xs">
									{#if img.alt}
										<p class="font-medium">{img.alt}</p>
									{/if}
									<p class="opacity-60">sort_order: {img.sort_order}</p>
								</div>
							</li>
						{/each}
					</ul>
				</div>
			{:else}
				<p class="text-xs italic opacity-60">No images attached.</p>
			{/if}
		</div>

		<aside class="space-y-4">
			<div class="card preset-filled-surface-100-900 space-y-3 p-5">
				<div class="flex items-center gap-3">
					<span
						class="bg-primary-500/15 text-primary-500 grid h-9 w-9 place-items-center rounded-full"
					>
						<Wallet size={16} strokeWidth={1.75} />
					</span>
					<div>
						<p class="text-xs font-semibold tracking-wider uppercase opacity-60">Price</p>
						<p class="h3 leading-none">{formatPrice(property.price_amount, property.price_currency)}</p>
					</div>
				</div>
			</div>

			<div class="card preset-filled-surface-100-900 space-y-3 p-5 text-sm">
				<div class="flex items-center gap-3">
					<span
						class="bg-primary-500/15 text-primary-500 grid h-9 w-9 place-items-center rounded-full"
					>
						<Building2 size={16} strokeWidth={1.75} />
					</span>
					<div>
						<p class="text-xs font-semibold tracking-wider uppercase opacity-60">Specs</p>
						<p>{property.bedrooms ?? '—'} bed · {property.bathrooms ?? '—'} bath</p>
						<p class="opacity-70 text-xs">
							{property.area_sqm === null ? 'Area n/a' : `${property.area_sqm} m²`}
						</p>
					</div>
				</div>
			</div>

			<div class="card preset-filled-surface-100-900 space-y-2 p-5 text-sm">
				<div class="flex items-center gap-3">
					<span
						class="bg-primary-500/15 text-primary-500 grid h-9 w-9 place-items-center rounded-full"
					>
						<MapPin size={16} strokeWidth={1.75} />
					</span>
					<p class="text-xs font-semibold tracking-wider uppercase opacity-60">Location</p>
				</div>
				<div class="text-sm">
					<p>{property.address_line}</p>
					<p>
						{property.city}{property.district ? `, ${property.district}` : ''}
						{property.postal_code ? ` ${property.postal_code}` : ''}
					</p>
					<p class="opacity-70">{property.country_code}</p>
					{#if property.latitude !== null && property.longitude !== null}
						<p class="opacity-70 text-xs">
							{property.latitude}, {property.longitude}
						</p>
					{/if}
				</div>
			</div>

			<div class="card preset-filled-surface-100-900 space-y-1 p-5 text-xs">
				<p class="font-semibold tracking-wider uppercase opacity-60">Audit</p>
				<p>Created: {formatDateTime(property.created_at)}</p>
				<p>Updated: {formatDateTime(property.updated_at)}</p>
				<p>By user: {property.created_by ?? '—'}</p>
			</div>

			<div class="card preset-filled-surface-100-900 space-y-1 p-5 text-xs">
				<div class="flex items-center gap-2">
					<Bed size={14} strokeWidth={1.75} />
					<p class="font-semibold tracking-wider uppercase opacity-60">System</p>
				</div>
				<p>ID: {property.id}</p>
			</div>
		</aside>
	</div>
</section>
