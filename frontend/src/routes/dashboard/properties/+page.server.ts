import { error } from '@sveltejs/kit';
import { apiFetch, getTokenFromCookies } from '$lib/server/api';
import {
	LISTING_TYPES,
	PROPERTY_STATUSES,
	PROPERTY_TYPES,
	type ListingType,
	type PropertyList,
	type PropertyListFilters,
	type PropertyStatus,
	type PropertyType
} from './properties.types';
import type { PageServerLoad } from './$types';

function asString(value: string | null): string {
	return value ?? '';
}

function asNumber(value: string | null): number | null {
	if (value === null) return null;
	const trimmed = value.trim();
	if (trimmed === '') return null;
	const n = Number(trimmed);
	return Number.isFinite(n) ? n : null;
}

function asEnum<T extends string>(value: string | null, allowed: readonly T[]): T | null {
	if (!value) return null;
	return (allowed as readonly string[]).includes(value) ? (value as T) : null;
}

function clampInt(value: number | null, min: number, max: number, fallback: number): number {
	if (value === null || !Number.isFinite(value)) return fallback;
	return Math.max(min, Math.min(max, Math.trunc(value)));
}

export const load: PageServerLoad = async ({ url, cookies }) => {
	const token = getTokenFromCookies(cookies.get);
	const params = url.searchParams;

	const filters: PropertyListFilters = {
		city: asString(params.get('city')) || null,
		listing_type: asEnum<ListingType>(params.get('listing_type'), LISTING_TYPES),
		property_type: asEnum<PropertyType>(params.get('property_type'), PROPERTY_TYPES),
		status: asEnum<PropertyStatus>(params.get('status'), PROPERTY_STATUSES),
		min_price: asNumber(params.get('min_price')),
		max_price: asNumber(params.get('max_price')),
		bedrooms: asNumber(params.get('bedrooms')),
		q: asString(params.get('q')) || null,
		limit: clampInt(asNumber(params.get('limit')), 1, 100, 20),
		offset: clampInt(asNumber(params.get('offset')), 0, Number.MAX_SAFE_INTEGER, 0)
	};

	const qs = new URLSearchParams();
	if (filters.city) qs.set('city', filters.city);
	if (filters.listing_type) qs.set('listing_type', filters.listing_type);
	if (filters.property_type) qs.set('property_type', filters.property_type);
	if (filters.status) qs.set('status', filters.status);
	if (filters.min_price !== null) qs.set('min_price', String(filters.min_price));
	if (filters.max_price !== null) qs.set('max_price', String(filters.max_price));
	if (filters.bedrooms !== null) qs.set('bedrooms', String(filters.bedrooms));
	if (filters.q) qs.set('q', filters.q);
	qs.set('limit', String(filters.limit));
	qs.set('offset', String(filters.offset));

	let list: PropertyList;
	try {
		list = await apiFetch<PropertyList>(`/api/properties?${qs.toString()}`, { method: 'GET' }, token);
	} catch (err) {
		if (err && typeof err === 'object' && 'status' in err) {
			const status = (err as { status: number }).status;
			if (status === 401 || status === 403) {
				throw error(403, 'You do not have access to this resource.');
			}
		}
		throw err;
	}

	return {
		filters,
		list
	};
};
