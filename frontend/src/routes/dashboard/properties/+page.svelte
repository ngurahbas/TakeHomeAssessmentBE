<script lang="ts">
	import { Plus } from 'lucide-svelte';
	import { deleteProperty } from './properties.remote';
	import {
		STATUS_PRESET,
		type PropertyList,
		type PropertyListFilters,
		type PropertyStatus
	} from './properties.types';
	import DeletePropertyDialog from './_components/DeletePropertyDialog.svelte';
	import PropertyFilters from './_components/PropertyFilters.svelte';

	let {
		data
	}: {
		data: { filters: PropertyListFilters; list: PropertyList };
	} = $props();

	const filters = $derived(data.filters);
	const list = $derived(data.list);
	const start = $derived(list.offset + 1);
	const end = $derived(list.offset + list.items.length);
	const totalPages = $derived(Math.max(1, Math.ceil(list.total / list.limit)));
	const currentPage = $derived(Math.floor(list.offset / list.limit) + 1);

	function buildHref(filters: PropertyListFilters, override: Partial<PropertyListFilters>): string {
		const merged: PropertyListFilters = {
			city: override.city !== undefined ? override.city : filters.city,
			listing_type:
				override.listing_type !== undefined ? override.listing_type : filters.listing_type,
			property_type:
				override.property_type !== undefined
					? override.property_type
					: filters.property_type,
			status: override.status !== undefined ? override.status : filters.status,
			min_price: override.min_price !== undefined ? override.min_price : filters.min_price,
			max_price: override.max_price !== undefined ? override.max_price : filters.max_price,
			bedrooms: override.bedrooms !== undefined ? override.bedrooms : filters.bedrooms,
			q: override.q !== undefined ? override.q : filters.q,
			limit: override.limit !== undefined ? override.limit : filters.limit,
			offset: override.offset !== undefined ? override.offset : filters.offset
		};
		const qs = new URLSearchParams();
		if (merged.city) qs.set('city', merged.city);
		if (merged.listing_type) qs.set('listing_type', merged.listing_type);
		if (merged.property_type) qs.set('property_type', merged.property_type);
		if (merged.status) qs.set('status', merged.status);
		if (merged.min_price !== null) qs.set('min_price', String(merged.min_price));
		if (merged.max_price !== null) qs.set('max_price', String(merged.max_price));
		if (merged.bedrooms !== null) qs.set('bedrooms', String(merged.bedrooms));
		if (merged.q) qs.set('q', merged.q);
		qs.set('limit', String(merged.limit));
		qs.set('offset', String(Math.max(0, merged.offset)));
		return `/dashboard/properties${qs.toString() ? '?' + qs.toString() : ''}`;
	}

	function formatPrice(amount: number, currency: string): string {
		const formatter = new Intl.NumberFormat('en-US', {
			maximumFractionDigits: 2,
			minimumFractionDigits: 0
		});
		return `${currency} ${formatter.format(amount)}`;
	}

	function formatDate(iso: string): string {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toISOString().slice(0, 10);
	}

	function statusPresetClass(s: PropertyStatus): string {
		return STATUS_PRESET[s];
	}
</script>

<svelte:head>
	<title>Properties · Real Estate AI</title>
</svelte:head>

<section class="space-y-6">
	<header class="flex flex-wrap items-end justify-between gap-3">
		<div>
			<h1 class="h2">Properties</h1>
			<p class="opacity-70 text-sm">
				{list.total.toLocaleString()} total · showing {list.items.length === 0 ? 0 : start}–{end}
			</p>
		</div>
		<a href="/dashboard/properties/new" class="btn preset-filled-primary-500">
			<Plus size={14} strokeWidth={1.75} />
			<span>New property</span>
		</a>
	</header>

	<PropertyFilters {filters} />

	<div class="card preset-filled-surface-100-900 overflow-x-auto">
		{#if list.items.length === 0}
			<div class="p-10 text-center text-sm opacity-70">
				No properties match the current filters.
				<a href="/dashboard/properties" class="anchor">Reset filters</a>
			</div>
		{:else}
			<table class="table">
				<thead>
					<tr>
						<th>Title</th>
						<th>City</th>
						<th>Type</th>
						<th>Listing</th>
						<th class="text-right">Price</th>
						<th>Status</th>
						<th>Bed</th>
						<th>Created</th>
						<th class="text-right">Actions</th>
					</tr>
				</thead>
				<tbody>
					{#each list.items as p (p.id)}
						<tr>
							<td>
								<a
									href={`/dashboard/properties/${p.id}`}
									class="anchor line-clamp-1 font-medium"
									title={p.title}
								>
									{p.title}
								</a>
							</td>
							<td class="whitespace-nowrap">{p.city}, {p.country_code}</td>
							<td class="whitespace-nowrap text-xs uppercase opacity-80">{p.property_type}</td>
							<td class="whitespace-nowrap text-xs uppercase opacity-80">{p.listing_type}</td>
							<td class="text-right whitespace-nowrap font-medium tabular-nums">
								{formatPrice(p.price_amount, p.price_currency)}
							</td>
							<td>
								<span class="badge {statusPresetClass(p.status)} text-[10px]">{p.status}</span>
							</td>
							<td class="text-center tabular-nums">{p.bedrooms ?? '—'}</td>
							<td class="whitespace-nowrap text-xs opacity-70">{formatDate(p.created_at)}</td>
							<td>
								<div class="flex items-center justify-end gap-1">
									<a
										href={`/dashboard/properties/${p.id}`}
										class="btn btn-sm preset-tonal-surface"
									>
										View
									</a>
									<DeletePropertyDialog
										id={p.id}
										title={p.title}
										form={deleteProperty.for(String(p.id))}
									/>
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>

	{#if list.total > list.limit}
		<nav class="flex items-center justify-between text-sm" aria-label="Pagination">
			<p class="opacity-70">
				Page {currentPage} of {totalPages}
			</p>
			<div class="flex items-center gap-2">
				<a
					class="btn btn-sm preset-tonal-surface"
					class:opacity-50={currentPage <= 1}
					aria-disabled={currentPage <= 1}
					href={buildHref(filters, { offset: Math.max(0, list.offset - list.limit) })}
				>
					Previous
				</a>
				<a
					class="btn btn-sm preset-tonal-surface"
					class:opacity-50={currentPage >= totalPages}
					aria-disabled={currentPage >= totalPages}
					href={buildHref(filters, { offset: list.offset + list.limit })}
				>
					Next
				</a>
			</div>
		</nav>
	{/if}
</section>
