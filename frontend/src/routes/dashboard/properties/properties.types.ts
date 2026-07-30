export const PROPERTY_TYPES = [
	'APARTMENT',
	'HOUSE',
	'VILLA',
	'STUDIO',
	'OFFICE',
	'LAND'
] as const;
export type PropertyType = (typeof PROPERTY_TYPES)[number];

export const LISTING_TYPES = ['SALE', 'RENT'] as const;
export type ListingType = (typeof LISTING_TYPES)[number];

export const PROPERTY_STATUSES = ['AVAILABLE', 'RESERVED', 'SOLD', 'RENTED'] as const;
export type PropertyStatus = (typeof PROPERTY_STATUSES)[number];

export type PropertyImage = {
	url: string;
	sort_order: number;
	alt: string | null;
};

export type PropertyListItem = {
	id: number;
	title: string;
	property_type: PropertyType;
	listing_type: ListingType;
	price_amount: number;
	price_currency: string;
	city: string;
	country_code: string;
	status: PropertyStatus;
	bedrooms: number | null;
	bathrooms: number | null;
	area_sqm: number | null;
	images: PropertyImage[];
	created_at: string;
};

export type PropertyList = {
	items: PropertyListItem[];
	total: number;
	limit: number;
	offset: number;
};

export type PropertyOut = PropertyListItem & {
	description: string;
	address_line: string;
	district: string | null;
	postal_code: string | null;
	latitude: number | null;
	longitude: number | null;
	amenities: string[];
	updated_at: string;
	created_by: number | null;
	updated_by: number | null;
};

export type PropertyCreatePayload = {
	title: string;
	description: string;
	property_type: PropertyType;
	listing_type: ListingType;
	price_amount: number;
	price_currency: string;
	bedrooms: number | null;
	bathrooms: number | null;
	area_sqm: number | null;
	address_line: string;
	city: string;
	district: string | null;
	postal_code: string | null;
	country_code: string;
	latitude: number | null;
	longitude: number | null;
	status: PropertyStatus;
	amenities: string[];
	images: PropertyImage[];
};

export type PropertyUpdatePayload = Partial<PropertyCreatePayload>;

export type PropertyListFilters = {
	city: string | null;
	listing_type: ListingType | null;
	property_type: PropertyType | null;
	status: PropertyStatus | null;
	min_price: number | null;
	max_price: number | null;
	bedrooms: number | null;
	q: string | null;
	limit: number;
	offset: number;
};

export const STATUS_PRESET: Record<PropertyStatus, string> = {
	AVAILABLE: 'preset-tonal-success',
	RESERVED: 'preset-tonal-warning',
	SOLD: 'preset-tonal-error',
	RENTED: 'preset-tonal-surface'
};
