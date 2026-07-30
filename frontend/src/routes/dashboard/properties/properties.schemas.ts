import * as v from 'valibot';
import {
	LISTING_TYPES,
	PROPERTY_STATUSES,
	PROPERTY_TYPES
} from './properties.types';

const requiredString = (min: number, max: number, label: string) =>
	v.pipe(
		v.string(`${label} is required`),
		v.trim(),
		v.minLength(min, `${label} must be at least ${min} character${min === 1 ? '' : 's'}`),
		v.maxLength(max, `${label} must be at most ${max} characters`)
	);

const optionalString = (max: number, label: string) =>
	v.optional(
		v.pipe(v.string(), v.maxLength(max, `${label} must be at most ${max} characters`)),
		''
	);

const trimmedUpper = (length: number, label: string) =>
	v.pipe(
		v.string(`${label} is required`),
		v.trim(),
		v.toUpperCase(),
		v.length(length, `${label} must be ${length} characters`)
	);

export const PropertyImageSchema = v.object({
	url: v.pipe(
		v.string('Image URL is required'),
		v.trim(),
		v.minLength(1, 'Image URL is required'),
		v.url('Image URL must be a valid URL')
	),
	sort_order: v.pipe(
		v.string(),
		v.transform((s) => (s.trim() === '' ? 0 : Number(s))),
		v.minValue(0, 'sort_order must be 0 or greater')
	),
	alt: v.optional(
		v.pipe(v.string(), v.maxLength(200, 'Alt must be at most 200 characters')),
		''
	)
});

export const PropertyCreateSchema = v.object({
	title: requiredString(1, 200, 'Title'),
	description: optionalString(10_000, 'Description'),
	property_type: v.picklist(PROPERTY_TYPES, 'Choose a property type'),
	listing_type: v.picklist(LISTING_TYPES, 'Choose a listing type'),
	price_amount: v.pipe(
		v.string('Price is required'),
		v.minLength(1, 'Price is required'),
		v.transform((s) => Number(s)),
		v.minValue(0, 'Price must be at least 0')
	),
	price_currency: trimmedUpper(3, 'Currency code'),
	bedrooms: v.optional(v.string(), ''),
	bathrooms: v.optional(v.string(), ''),
	area_sqm: v.optional(v.string(), ''),
	address_line: requiredString(1, 255, 'Address'),
	city: requiredString(1, 128, 'City'),
	district: v.optional(
		v.pipe(v.string(), v.trim(), v.maxLength(128, 'District must be at most 128 characters')),
		''
	),
	postal_code: v.optional(
		v.pipe(v.string(), v.trim(), v.maxLength(32, 'Postal code must be at most 32 characters')),
		''
	),
	country_code: trimmedUpper(2, 'Country code'),
	latitude: v.optional(v.string(), ''),
	longitude: v.optional(v.string(), ''),
	status: v.picklist(PROPERTY_STATUSES, 'Choose a status'),
	amenities: v.optional(v.string(), ''),
	images: v.optional(
		v.pipe(
			v.string(),
			v.transform((raw) => {
				try {
					const parsed = JSON.parse(raw);
					return Array.isArray(parsed) ? parsed : [];
				} catch {
					return [];
				}
			})
		),
		'[]'
	)
});

export const PropertyUpdateSchema = v.object({
	id: v.pipe(v.string(), v.transform((s) => Number(s)), v.minValue(1)),
	title: v.optional(v.pipe(v.string(), v.trim(), v.minLength(1), v.maxLength(200))),
	description: v.optional(v.pipe(v.string(), v.maxLength(10_000))),
	property_type: v.optional(v.picklist(PROPERTY_TYPES)),
	listing_type: v.optional(v.picklist(LISTING_TYPES)),
	price_amount: v.optional(v.string(), ''),
	price_currency: v.optional(v.pipe(v.string(), v.trim(), v.toUpperCase(), v.length(3))),
	bedrooms: v.optional(v.string(), ''),
	bathrooms: v.optional(v.string(), ''),
	area_sqm: v.optional(v.string(), ''),
	address_line: v.optional(v.pipe(v.string(), v.trim(), v.minLength(1), v.maxLength(255))),
	city: v.optional(v.pipe(v.string(), v.trim(), v.minLength(1), v.maxLength(128))),
	district: v.optional(v.pipe(v.string(), v.trim(), v.maxLength(128))),
	postal_code: v.optional(v.pipe(v.string(), v.trim(), v.maxLength(32))),
	country_code: v.optional(v.pipe(v.string(), v.trim(), v.toUpperCase(), v.length(2))),
	latitude: v.optional(v.string(), ''),
	longitude: v.optional(v.string(), ''),
	status: v.optional(v.picklist(PROPERTY_STATUSES)),
	amenities: v.optional(v.string()),
	images: v.optional(
		v.pipe(
			v.string(),
			v.transform((raw) => {
				try {
					const parsed = JSON.parse(raw);
					return Array.isArray(parsed) ? parsed : [];
				} catch {
					return [];
				}
			})
		)
	)
});

export const PropertyIdSchema = v.object({
	id: v.pipe(v.string(), v.transform((s) => Number(s)), v.minValue(1))
});

export const PropertyListFiltersSchema = v.object({
	city: v.optional(v.pipe(v.string(), v.maxLength(128))),
	listing_type: v.optional(v.picklist(LISTING_TYPES)),
	property_type: v.optional(v.picklist(PROPERTY_TYPES)),
	status: v.optional(v.picklist(PROPERTY_STATUSES)),
	min_price: v.optional(
		v.pipe(v.string(), v.transform((s) => (s.trim() === '' ? null : Number(s))))
	),
	max_price: v.optional(
		v.pipe(v.string(), v.transform((s) => (s.trim() === '' ? null : Number(s))))
	),
	bedrooms: v.optional(
		v.pipe(v.string(), v.transform((s) => (s.trim() === '' ? null : Number(s))))
	),
	q: v.optional(v.pipe(v.string(), v.maxLength(200))),
	limit: v.optional(
		v.pipe(v.string(), v.transform((s) => Number(s)), v.minValue(1), v.maxValue(100)),
		'20'
	),
	offset: v.optional(
		v.pipe(v.string(), v.transform((s) => Number(s)), v.minValue(0)),
		'0'
	)
});

export type PropertyCreateInput = v.InferInput<typeof PropertyCreateSchema>;
export type PropertyUpdateInput = v.InferInput<typeof PropertyUpdateSchema>;
export type PropertyListFiltersInput = v.InferInput<typeof PropertyListFiltersSchema>;
