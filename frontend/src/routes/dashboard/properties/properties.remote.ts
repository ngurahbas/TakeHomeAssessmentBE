import * as v from 'valibot';
import { form, getRequestEvent, query } from '$app/server';
import { invalid, redirect } from '@sveltejs/kit';
import { ApiError, apiFetch } from '$lib/server/api';
import {
	PropertyCreateSchema,
	PropertyIdSchema,
	PropertyListFiltersSchema,
	PropertyUpdateSchema,
	type PropertyListFiltersInput
} from './properties.schemas';
import type { PropertyList, PropertyOut } from './properties.types';
export type { PropertyListFiltersInput } from './properties.schemas';

const KNOWN_FIELDS = new Set([
	'title',
	'description',
	'property_type',
	'listing_type',
	'price_amount',
	'price_currency',
	'bedrooms',
	'bathrooms',
	'area_sqm',
	'address_line',
	'city',
	'district',
	'postal_code',
	'country_code',
	'latitude',
	'longitude',
	'status',
	'amenities',
	'images'
]);

type BackendDetailItem = { loc?: unknown; msg?: unknown; type?: unknown };
type ParsedValidation = {
	formMessage: string | null;
	fieldErrors: Record<string, string>;
};

function parseBackendValidation(body: unknown): ParsedValidation {
	const result: ParsedValidation = { formMessage: null, fieldErrors: {} };
	if (!body || typeof body !== 'object') return result;
	const detail = (body as { detail?: unknown }).detail;
	if (!Array.isArray(detail)) return result;
	for (const entry of detail as BackendDetailItem[]) {
		const msg = typeof entry?.msg === 'string' ? entry.msg : null;
		if (!msg) continue;
		const loc = Array.isArray(entry?.loc) ? (entry!.loc as unknown[]) : [];
		const leaf = loc[loc.length - 1];
		if (typeof leaf === 'string' && KNOWN_FIELDS.has(leaf)) {
			result.fieldErrors[leaf] = msg;
		} else {
			result.formMessage = result.formMessage ? `${result.formMessage}; ${msg}` : msg;
		}
	}
	return result;
}

function normalizeAmenities(raw: unknown): string[] {
	if (typeof raw !== 'string') return [];
	const seen = new Set<string>();
	const out: string[] = [];
	for (const part of raw.split(',')) {
		const key = part.trim().toLowerCase();
		if (!key || seen.has(key)) continue;
		seen.add(key);
		out.push(key);
	}
	return out;
}

function normalizeImages(raw: unknown): Array<{ url: string; sort_order: number; alt: string | null }> {
	if (typeof raw !== 'string') return [];
	let parsed: unknown;
	try {
		parsed = JSON.parse(raw);
	} catch {
		return [];
	}
	if (!Array.isArray(parsed)) return [];
	return parsed
		.map((row) => {
			if (!row || typeof row !== 'object') return null;
			const r = row as Record<string, unknown>;
			const url = typeof r.url === 'string' ? r.url.trim() : '';
			if (!url) return null;
			const sortOrderRaw = r.sort_order;
			const sortOrder =
				typeof sortOrderRaw === 'number'
					? sortOrderRaw
					: typeof sortOrderRaw === 'string' && sortOrderRaw.trim() !== ''
						? Number(sortOrderRaw)
						: 0;
			const alt = typeof r.alt === 'string' && r.alt.trim() !== '' ? r.alt.trim() : null;
			return { url, sort_order: Number.isFinite(sortOrder) ? sortOrder : 0, alt };
		})
		.filter((r): r is { url: string; sort_order: number; alt: string | null } => r !== null);
}

function parseOptionalNumber(value: unknown): number | null {
	if (typeof value !== 'string') return null;
	const trimmed = value.trim();
	if (trimmed === '') return null;
	const n = Number(trimmed);
	return Number.isFinite(n) ? n : null;
}

export const listProperties = query('unchecked', async (raw: PropertyListFiltersInput) => {
	const parsed = v.safeParse(PropertyListFiltersSchema, raw);
	if (!parsed.success) {
		throw new Error('Invalid filter input');
	}
	const f = parsed.output;
	const qs = new URLSearchParams();
	if (f.city) qs.set('city', f.city);
	if (f.listing_type) qs.set('listing_type', f.listing_type);
	if (f.property_type) qs.set('property_type', f.property_type);
	if (f.status) qs.set('status', f.status);
	if (typeof f.min_price === 'number' && !Number.isNaN(f.min_price))
		qs.set('min_price', String(f.min_price));
	if (typeof f.max_price === 'number' && !Number.isNaN(f.max_price))
		qs.set('max_price', String(f.max_price));
	if (typeof f.bedrooms === 'number' && !Number.isNaN(f.bedrooms))
		qs.set('bedrooms', String(f.bedrooms));
	if (f.q) qs.set('q', f.q);
	qs.set('limit', String(f.limit));
	qs.set('offset', String(f.offset));
	return apiFetch<PropertyList>(`/api/properties?${qs.toString()}`, { method: 'GET' });
});

export const getProperty = query<number, PropertyOut | null>('unchecked', async (id) => {
	try {
		return await apiFetch<PropertyOut>(`/api/properties/${id}`, { method: 'GET' });
	} catch (err) {
		if (err instanceof ApiError && err.status === 404) return null;
		throw err;
	}
});

export const createProperty = form(PropertyCreateSchema, async (data, issue) => {
	const payload = {
		title: data.title,
		description: typeof data.description === 'string' ? data.description : '',
		property_type: data.property_type,
		listing_type: data.listing_type,
		price_amount: data.price_amount,
		price_currency: data.price_currency,
		bedrooms: parseOptionalNumber(data.bedrooms),
		bathrooms: parseOptionalNumber(data.bathrooms),
		area_sqm: parseOptionalNumber(data.area_sqm),
		address_line: data.address_line,
		city: data.city,
		district: typeof data.district === 'string' && data.district.trim() !== '' ? data.district.trim() : null,
		postal_code:
			typeof data.postal_code === 'string' && data.postal_code.trim() !== '' ? data.postal_code.trim() : null,
		country_code: data.country_code,
		latitude: parseOptionalNumber(data.latitude),
		longitude: parseOptionalNumber(data.longitude),
		status: data.status,
		amenities: normalizeAmenities(data.amenities),
		images: normalizeImages(data.images)
	};

	let created: PropertyOut;
	try {
		created = await apiFetch<PropertyOut>('/api/properties', {
			method: 'POST',
			body: payload
		});
	} catch (err) {
		if (err instanceof ApiError) {
			if (err.status === 401 || err.status === 403) {
				return invalid(
					issue(
						err.status === 401
							? 'You must be signed in to create properties.'
							: 'Only administrators can create properties.'
					)
				);
			}
			if (err.status === 422) {
				const { fieldErrors, formMessage } = parseBackendValidation(err.body);
				for (const [field, message] of Object.entries(fieldErrors)) {
					// @ts-expect-error -- dynamic field access on issue proxy
					invalid(issue[field](message));
				}
				if (formMessage) {
					invalid(issue(formMessage));
				}
				if (Object.keys(fieldErrors).length === 0 && !formMessage) {
					invalid(issue('Validation failed. Please review the form.'));
				}
				return;
			}
		}
		throw err;
	}
	redirect(303, `/dashboard/properties/${created.id}`);
});

export const updateProperty = form(PropertyUpdateSchema, async (data, issue) => {
	const id = data.id;
	const payload: Record<string, unknown> = {};
	if (data.title !== undefined) payload.title = data.title;
	if (data.description !== undefined) payload.description = data.description;
	if (data.property_type !== undefined) payload.property_type = data.property_type;
	if (data.listing_type !== undefined) payload.listing_type = data.listing_type;
	if (data.price_amount !== undefined) payload.price_amount = parseOptionalNumber(data.price_amount);
	if (data.price_currency !== undefined) payload.price_currency = data.price_currency;
	if (data.bedrooms !== undefined) payload.bedrooms = parseOptionalNumber(data.bedrooms);
	if (data.bathrooms !== undefined) payload.bathrooms = parseOptionalNumber(data.bathrooms);
	if (data.area_sqm !== undefined) payload.area_sqm = parseOptionalNumber(data.area_sqm);
	if (data.address_line !== undefined) payload.address_line = data.address_line;
	if (data.city !== undefined) payload.city = data.city;
	if (data.district !== undefined)
		payload.district =
			typeof data.district === 'string' && data.district.trim() !== '' ? data.district.trim() : null;
	if (data.postal_code !== undefined)
		payload.postal_code =
			typeof data.postal_code === 'string' && data.postal_code.trim() !== ''
				? data.postal_code.trim()
				: null;
	if (data.country_code !== undefined) payload.country_code = data.country_code;
	if (data.latitude !== undefined) payload.latitude = parseOptionalNumber(data.latitude);
	if (data.longitude !== undefined) payload.longitude = parseOptionalNumber(data.longitude);
	if (data.status !== undefined) payload.status = data.status;
	if (data.amenities !== undefined) payload.amenities = normalizeAmenities(data.amenities);
	if (data.images !== undefined) payload.images = normalizeImages(data.images);

	let updated: PropertyOut;
	try {
		updated = await apiFetch<PropertyOut>(`/api/properties/${id}`, {
			method: 'PATCH',
			body: payload
		});
	} catch (err) {
		if (err instanceof ApiError) {
			if (err.status === 401 || err.status === 403) {
				return invalid(
					issue(
						err.status === 401
							? 'You must be signed in to update properties.'
							: 'Only administrators can update properties.'
					)
				);
			}
			if (err.status === 404) {
				return invalid(issue('Property not found.'));
			}
			if (err.status === 422) {
				const { fieldErrors, formMessage } = parseBackendValidation(err.body);
				for (const [field, message] of Object.entries(fieldErrors)) {
					// @ts-expect-error -- dynamic field access on issue proxy
					invalid(issue[field](message));
				}
				if (formMessage) {
					invalid(issue(formMessage));
				}
				if (Object.keys(fieldErrors).length === 0 && !formMessage) {
					invalid(issue('Validation failed. Please review the form.'));
				}
				return;
			}
		}
		throw err;
	}
	redirect(303, `/dashboard/properties/${updated.id}`);
});

export const deleteProperty = form(PropertyIdSchema, async (data, issue) => {
	try {
		await apiFetch<void>(`/api/properties/${data.id}`, { method: 'DELETE' });
	} catch (err) {
		if (err instanceof ApiError) {
			if (err.status === 401 || err.status === 403) {
				return invalid(
					issue(
						err.status === 401
							? 'You must be signed in to delete properties.'
							: 'Only administrators can delete properties.'
					)
				);
			}
			if (err.status === 404) {
				return invalid(issue('Property not found.'));
			}
		}
		throw err;
	}
	const event = getRequestEvent();
	const back = event.url.searchParams.get('back');
	redirect(303, back && back.startsWith('/') ? back : '/dashboard/properties');
});
