<script lang="ts">
	import { Search, X } from 'lucide-svelte';
	import {
		LISTING_TYPES,
		PROPERTY_STATUSES,
		PROPERTY_TYPES,
		type ListingType,
		type PropertyListFilters,
		type PropertyStatus,
		type PropertyType
	} from '../properties.types';

	let {
		filters
	}: {
		filters: PropertyListFilters;
	} = $props();

	const city = $derived(filters.city ?? '');
	const q = $derived(filters.q ?? '');
	const listingType = $derived(filters.listing_type ?? '');
	const propertyType = $derived(filters.property_type ?? '');
	const status = $derived(filters.status ?? '');
	const minPrice = $derived(filters.min_price === null ? '' : String(filters.min_price));
	const maxPrice = $derived(filters.max_price === null ? '' : String(filters.max_price));
	const bedrooms = $derived(filters.bedrooms === null ? '' : String(filters.bedrooms));

	const TYPE_LABEL: Record<PropertyType, string> = {
		APARTMENT: 'Apartment',
		HOUSE: 'House',
		VILLA: 'Villa',
		STUDIO: 'Studio',
		OFFICE: 'Office',
		LAND: 'Land'
	};
	const LISTING_LABEL: Record<ListingType, string> = {
		SALE: 'For sale',
		RENT: 'For rent'
	};
	const STATUS_LABEL: Record<PropertyStatus, string> = {
		AVAILABLE: 'Available',
		RESERVED: 'Reserved',
		SOLD: 'Sold',
		RENTED: 'Rented'
	};
</script>

<form
	method="GET"
	action="/dashboard/properties"
	class="card preset-filled-surface-100-900 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4"
>
	<label class="label">
		<span class="label-text text-xs">Search</span>
		<div class="input-group grid-cols-[auto_1fr]">
			<span class="bg-surface-200-800 grid place-items-center px-2">
				<Search size={14} strokeWidth={1.75} />
			</span>
			<input
				type="search"
				name="q"
				value={q}
				placeholder="Title or description"
				class="input"
				autocomplete="off"
			/>
		</div>
	</label>

	<label class="label">
		<span class="label-text text-xs">City</span>
		<input
			type="text"
			name="city"
			value={city}
			placeholder="e.g. Istanbul"
			class="input"
			autocomplete="off"
		/>
	</label>

	<label class="label">
		<span class="label-text text-xs">Listing</span>
		<select name="listing_type" class="select">
			<option value="">Any</option>
			{#each LISTING_TYPES as lt (lt)}
				<option value={lt} selected={listingType === lt}>{LISTING_LABEL[lt]}</option>
			{/each}
		</select>
	</label>

	<label class="label">
		<span class="label-text text-xs">Type</span>
		<select name="property_type" class="select">
			<option value="">Any</option>
			{#each PROPERTY_TYPES as pt (pt)}
				<option value={pt} selected={propertyType === pt}>{TYPE_LABEL[pt]}</option>
			{/each}
		</select>
	</label>

	<label class="label">
		<span class="label-text text-xs">Status</span>
		<select name="status" class="select">
			<option value="">Any</option>
			{#each PROPERTY_STATUSES as s (s)}
				<option value={s} selected={status === s}>{STATUS_LABEL[s]}</option>
			{/each}
		</select>
	</label>

	<label class="label">
		<span class="label-text text-xs">Min price</span>
		<input
			type="number"
			name="min_price"
			value={minPrice}
			placeholder="0"
			min="0"
			class="input"
			step="any"
		/>
	</label>

	<label class="label">
		<span class="label-text text-xs">Max price</span>
		<input
			type="number"
			name="max_price"
			value={maxPrice}
			placeholder="∞"
			min="0"
			class="input"
			step="any"
		/>
	</label>

	<label class="label">
		<span class="label-text text-xs">Bedrooms</span>
		<input
			type="number"
			name="bedrooms"
			value={bedrooms}
			placeholder="Any"
			min="0"
			max="50"
			class="input"
		/>
	</label>

	<div class="flex items-end gap-2 sm:col-span-2 lg:col-span-4">
		<button type="submit" class="btn preset-filled-primary-500">
			<Search size={14} strokeWidth={1.75} />
			<span>Apply filters</span>
		</button>
		<a href="/dashboard/properties" class="btn preset-tonal-surface">
			<X size={14} strokeWidth={1.75} />
			<span>Reset</span>
		</a>
	</div>
</form>
