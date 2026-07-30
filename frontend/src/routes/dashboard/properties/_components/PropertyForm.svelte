<script lang="ts">
	import { Image as ImageIcon, Plus, Save, X } from 'lucide-svelte';
	import type { RemoteForm } from '@sveltejs/kit';
	import {
		LISTING_TYPES,
		PROPERTY_STATUSES,
		PROPERTY_TYPES,
		type ListingType,
		type PropertyImage,
		type PropertyOut,
		type PropertyStatus,
		type PropertyType
	} from '../properties.types';
	import {
		PropertyCreateSchema,
		PropertyIdSchema,
		PropertyUpdateSchema
	} from '../properties.schemas';
	import type * as v from 'valibot';

	type CreateForm = RemoteForm<v.InferInput<typeof PropertyCreateSchema>, unknown>;
	type UpdateForm = RemoteForm<v.InferInput<typeof PropertyUpdateSchema>, unknown>;
	type DeleteForm = RemoteForm<v.InferInput<typeof PropertyIdSchema>, unknown>;

	let {
		mode,
		form,
		initial,
		submitLabel
	}: {
		mode: 'create' | 'edit';
		form: CreateForm | UpdateForm;
		initial?: PropertyOut | null;
		submitLabel: string;
	} = $props();

	const topLevelIssues = $derived(
		(() => {
			const issues = form.fields.issues();
			return (issues ?? []).filter((iss) => !iss.path || iss.path.length === 0);
		})()
	);

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

	type ImageRow = { id: string; url: string; sort_order: string; alt: string };

	let nextRowId = 1;
	function newId(): string {
		return `row-${nextRowId++}`;
	}

	function toRows(images: PropertyImage[] | undefined | null): ImageRow[] {
		if (!images || images.length === 0) {
			return [makeEmptyRow()];
		}
		return images.map((img) => ({
			id: newId(),
			url: img.url,
			sort_order: String(img.sort_order ?? 0),
			alt: img.alt ?? ''
		}));
	}

	function makeEmptyRow(): ImageRow {
		return { id: newId(), url: '', sort_order: '0', alt: '' };
	}

	const initialImages = $derived<ImageRow[]>(toRows(initial?.images));
	let imageRows = $state<ImageRow[]>([]);
	$effect.pre(() => {
		imageRows = toRows(initial?.images);
	});

	const initialAmenitiesText = $derived((initial?.amenities ?? []).join(', '));
	let amenitiesField = $state('');
	$effect.pre(() => {
		amenitiesField = initialAmenitiesText;
	});

	const imageJson = $derived(JSON.stringify(imageRows.map((r) => ({
		url: r.url.trim(),
		sort_order: r.sort_order === '' ? 0 : Number(r.sort_order),
		alt: r.alt.trim() === '' ? null : r.alt.trim()
	}))));

	function addImageRow() {
		imageRows = [...imageRows, makeEmptyRow()];
	}

	function removeImageRow(id: string) {
		imageRows = imageRows.length > 1 ? imageRows.filter((r) => r.id !== id) : [makeEmptyRow()];
	}

	function updateRow(id: string, patch: Partial<ImageRow>) {
		imageRows = imageRows.map((r) => (r.id === id ? { ...r, ...patch } : r));
	}

	const amenitiesChips = $derived(
		amenitiesField
			.split(',')
			.map((s) => s.trim().toLowerCase())
			.filter(Boolean)
	);
</script>

<form
	{...form}
	method="POST"
	class="space-y-6"
>
	{#if mode === 'edit' && initial}
		<input type="hidden" name="id" value={initial.id} />
	{/if}

	<input type="hidden" name="images" value={imageJson} />

	{#if topLevelIssues.length > 0}
		<div role="alert" class="alert preset-tonal-error flex items-start gap-2 p-3 text-sm">
			{#each topLevelIssues as issue (issue)}
				<span>{issue.message}</span>
			{/each}
		</div>
	{/if}

	<section class="card preset-filled-surface-100-900 space-y-4 p-5">
		<header>
			<h2 class="h4">Basics</h2>
		</header>

		<label class="label">
			<span class="label-text">Title</span>
			<input
				{...form.fields.title.as('text')}
				class="input"
				value={initial?.title ?? ''}
				required
				maxlength="200"
			/>
		</label>

		<label class="label">
			<span class="label-text">Description</span>
			<textarea
				{...form.fields.description.as('text')}
				class="textarea"
				rows="4"
				maxlength="10000"
				placeholder="Describe the property"
			>{initial?.description ?? ''}</textarea>
		</label>

		<div class="grid gap-4 sm:grid-cols-3">
			<label class="label">
				<span class="label-text">Property type</span>
				<select {...form.fields.property_type.as('select')} class="select" required>
					<option value="" disabled selected={!initial?.property_type}>Choose…</option>
					{#each PROPERTY_TYPES as pt (pt)}
						<option value={pt} selected={initial?.property_type === pt}>
							{TYPE_LABEL[pt]}
						</option>
					{/each}
				</select>
			</label>

			<label class="label">
				<span class="label-text">Listing</span>
				<select {...form.fields.listing_type.as('select')} class="select" required>
					<option value="" disabled selected={!initial?.listing_type}>Choose…</option>
					{#each LISTING_TYPES as lt (lt)}
						<option value={lt} selected={initial?.listing_type === lt}>
							{LISTING_LABEL[lt]}
						</option>
					{/each}
				</select>
			</label>

			<label class="label">
				<span class="label-text">Status</span>
				<select {...form.fields.status.as('select')} class="select" required>
					{#each PROPERTY_STATUSES as s (s)}
						<option value={s} selected={(initial?.status ?? 'AVAILABLE') === s}>
							{STATUS_LABEL[s]}
						</option>
					{/each}
				</select>
			</label>
		</div>
	</section>

	<section class="card preset-filled-surface-100-900 space-y-4 p-5">
		<header>
			<h2 class="h4">Pricing</h2>
		</header>
		<div class="grid gap-4 sm:grid-cols-2">
			<label class="label">
				<span class="label-text">Amount</span>
				<input
					{...form.fields.price_amount.as('text')}
					type="number"
					step="any"
					min="0"
					class="input"
					value={initial?.price_amount ?? ''}
					required
				/>
			</label>
			<label class="label">
				<span class="label-text">Currency (3 letters)</span>
				<input
					{...form.fields.price_currency.as('text')}
					type="text"
					class="input uppercase"
					value={initial?.price_currency ?? ''}
					required
					minlength="3"
					maxlength="3"
					placeholder="USD"
				/>
			</label>
		</div>
	</section>

	<section class="card preset-filled-surface-100-900 space-y-4 p-5">
		<header>
			<h2 class="h4">Location</h2>
		</header>

		<label class="label">
			<span class="label-text">Address</span>
			<input
				{...form.fields.address_line.as('text')}
				class="input"
				value={initial?.address_line ?? ''}
				required
				maxlength="255"
			/>
		</label>

		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
			<label class="label">
				<span class="label-text">City</span>
				<input
					{...form.fields.city.as('text')}
					class="input"
					value={initial?.city ?? ''}
					required
					maxlength="128"
				/>
			</label>
			<label class="label">
				<span class="label-text">District</span>
				<input
					{...form.fields.district.as('text')}
					class="input"
					value={initial?.district ?? ''}
					maxlength="128"
				/>
			</label>
			<label class="label">
				<span class="label-text">Postal code</span>
				<input
					{...form.fields.postal_code.as('text')}
					class="input"
					value={initial?.postal_code ?? ''}
					maxlength="32"
				/>
			</label>
			<label class="label">
				<span class="label-text">Country (2 letters)</span>
				<input
					{...form.fields.country_code.as('text')}
					type="text"
					class="input uppercase"
					value={initial?.country_code ?? ''}
					required
					minlength="2"
					maxlength="2"
					placeholder="TR"
				/>
			</label>
		</div>

		<div class="grid gap-4 sm:grid-cols-2">
			<label class="label">
				<span class="label-text">Latitude</span>
				<input
					{...form.fields.latitude.as('text')}
					type="number"
					step="any"
					min="-90"
					max="90"
					class="input"
					value={initial?.latitude ?? ''}
				/>
			</label>
			<label class="label">
				<span class="label-text">Longitude</span>
				<input
					{...form.fields.longitude.as('text')}
					type="number"
					step="any"
					min="-180"
					max="180"
					class="input"
					value={initial?.longitude ?? ''}
				/>
			</label>
		</div>
	</section>

	<section class="card preset-filled-surface-100-900 space-y-4 p-5">
		<header>
			<h2 class="h4">Specs</h2>
		</header>
		<div class="grid gap-4 sm:grid-cols-3">
			<label class="label">
				<span class="label-text">Bedrooms</span>
				<input
					{...form.fields.bedrooms.as('text')}
					type="number"
					min="0"
					max="50"
					class="input"
					value={initial?.bedrooms ?? ''}
				/>
			</label>
			<label class="label">
				<span class="label-text">Bathrooms</span>
				<input
					{...form.fields.bathrooms.as('text')}
					type="number"
					min="0"
					max="50"
					class="input"
					value={initial?.bathrooms ?? ''}
				/>
			</label>
			<label class="label">
				<span class="label-text">Area (m²)</span>
				<input
					{...form.fields.area_sqm.as('text')}
					type="number"
					min="0"
					max="100000"
					step="any"
					class="input"
					value={initial?.area_sqm ?? ''}
				/>
			</label>
		</div>
	</section>

	<section class="card preset-filled-surface-100-900 space-y-3 p-5">
		<header>
			<h2 class="h4">Amenities</h2>
			<p class="text-xs opacity-60">Comma-separated. Duplicates are removed; case is normalised.</p>
		</header>
		<label class="label">
			<span class="sr-only">Amenities</span>
			<input
				{...form.fields.amenities.as('text')}
				type="text"
				class="input"
				placeholder="parking, pool, sea view"
				bind:value={amenitiesField}
			/>
		</label>
		{#if amenitiesChips.length > 0}
			<div class="flex flex-wrap gap-2">
				{#each amenitiesChips as a (a)}
					<span class="chip preset-tonal-primary text-xs">{a}</span>
				{/each}
			</div>
		{/if}
	</section>

	<section class="card preset-filled-surface-100-900 space-y-4 p-5">
		<header class="flex items-center justify-between">
			<div>
				<h2 class="h4">Images</h2>
				<p class="text-xs opacity-60">Add one or more image URLs. Order matters.</p>
			</div>
			<button type="button" class="btn btn-sm preset-tonal-surface" onclick={addImageRow}>
				<Plus size={14} strokeWidth={1.75} />
				<span>Add image</span>
			</button>
		</header>

		<ul class="space-y-3">
			{#each imageRows as row, i (row.id)}
				<li
					class="border-surface-200-800 bg-surface-50-950 space-y-2 rounded-md border p-3"
				>
					<div class="flex items-center justify-between gap-2">
						<span
							class="bg-primary-500/15 text-primary-500 grid h-7 w-7 place-items-center rounded-full"
						>
							<ImageIcon size={14} strokeWidth={1.75} />
						</span>
						<button
							type="button"
							class="btn-icon btn-icon-sm preset-tonal-error"
							aria-label={`Remove image ${i + 1}`}
							onclick={() => removeImageRow(row.id)}
						>
							<X size={14} strokeWidth={1.75} />
						</button>
					</div>
					<label class="label">
						<span class="label-text text-xs">URL</span>
						<input
							type="url"
							class="input"
							placeholder="https://…"
							value={row.url}
							oninput={(e) => updateRow(row.id, { url: e.currentTarget.value })}
						/>
					</label>
					<div class="grid gap-2 sm:grid-cols-2">
						<label class="label">
							<span class="label-text text-xs">Sort order</span>
							<input
								type="number"
								min="0"
								class="input"
								value={row.sort_order}
								oninput={(e) => updateRow(row.id, { sort_order: e.currentTarget.value })}
							/>
						</label>
						<label class="label">
							<span class="label-text text-xs">Alt text (optional)</span>
							<input
								type="text"
								class="input"
								maxlength="200"
								value={row.alt}
								oninput={(e) => updateRow(row.id, { alt: e.currentTarget.value })}
							/>
						</label>
					</div>
				</li>
			{/each}
		</ul>
	</section>

	<div class="flex items-center justify-end gap-2">
		<a href="/dashboard/properties" class="btn preset-tonal-surface">Cancel</a>
		<button type="submit" class="btn preset-filled-primary-500" disabled={!!form.pending}>
			<Save size={14} strokeWidth={1.75} />
			<span>{submitLabel}</span>
		</button>
	</div>
</form>
