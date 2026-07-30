import { error } from '@sveltejs/kit';
import { apiFetch, getTokenFromCookies } from '$lib/server/api';
import type { PropertyOut } from '../properties.types';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, cookies }) => {
	const id = Number(params.id);
	if (!Number.isInteger(id) || id <= 0) {
		throw error(400, 'Invalid property id');
	}
	const token = getTokenFromCookies(cookies.get);
	let property: PropertyOut | null;
	try {
		property = await apiFetch<PropertyOut>(`/api/properties/${id}`, { method: 'GET' }, token);
	} catch (err) {
		if (err && typeof err === 'object' && 'status' in err) {
			const status = (err as { status: number }).status;
			if (status === 404) {
				throw error(404, 'Property not found');
			}
			if (status === 401 || status === 403) {
				throw error(403, 'You do not have access to this property.');
			}
		}
		throw err;
	}
	if (!property) {
		throw error(404, 'Property not found');
	}
	return { property };
};
