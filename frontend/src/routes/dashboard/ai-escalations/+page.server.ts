import { error } from '@sveltejs/kit';
import { apiFetch, getTokenFromCookies } from '$lib/server/api';
import type { AiEscalationList } from './ai-escalations.types';
import type { PageServerLoad } from './$types';

function asNumber(value: string | null): number | null {
	if (value === null) return null;
	const trimmed = value.trim();
	if (trimmed === '') return null;
	const n = Number(trimmed);
	return Number.isFinite(n) ? n : null;
}

function clampInt(value: number | null, min: number, max: number, fallback: number): number {
	if (value === null || !Number.isFinite(value)) return fallback;
	return Math.max(min, Math.min(max, Math.trunc(value)));
}

export const load: PageServerLoad = async ({ url, cookies }) => {
	const token = getTokenFromCookies(cookies.get);
	const params = url.searchParams;

	const limit = clampInt(asNumber(params.get('limit')), 1, 100, 20);
	const offset = clampInt(asNumber(params.get('offset')), 0, Number.MAX_SAFE_INTEGER, 0);

	const qs = new URLSearchParams();
	qs.set('limit', String(limit));
	qs.set('offset', String(offset));

	let list: AiEscalationList;
	try {
		list = await apiFetch<AiEscalationList>(
			`/api/ai-escalations?${qs.toString()}`,
			{ method: 'GET' },
			token
		);
	} catch (err) {
		if (err && typeof err === 'object' && 'status' in err) {
			const status = (err as { status: number }).status;
			if (status === 401 || status === 403) {
				throw error(403, 'You do not have access to this resource.');
			}
		}
		throw err;
	}

	return { list, limit, offset };
};
