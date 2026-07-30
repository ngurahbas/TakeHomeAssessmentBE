import { error } from '@sveltejs/kit';
import { apiFetch, getTokenFromCookies } from '$lib/server/api';
import type { AiEscalationDetail } from '../ai-escalations.types';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ params, cookies }) => {
	const id = Number(params.id);
	if (!Number.isInteger(id) || id <= 0) {
		throw error(400, 'Invalid escalation id');
	}
	const token = getTokenFromCookies(cookies.get);
	let detail: AiEscalationDetail | null;
	try {
		detail = await apiFetch<AiEscalationDetail>(
			`/api/ai-escalations/${id}`,
			{ method: 'GET' },
			token
		);
	} catch (err) {
		if (err && typeof err === 'object' && 'status' in err) {
			const status = (err as { status: number }).status;
			if (status === 404) {
				throw error(404, 'Escalation not found');
			}
			if (status === 401 || status === 403) {
				throw error(403, 'You do not have access to this escalation.');
			}
		}
		throw err;
	}
	if (!detail) {
		throw error(404, 'Escalation not found');
	}
	return { detail };
};
