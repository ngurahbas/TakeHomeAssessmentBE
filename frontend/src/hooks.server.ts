import type { Handle } from '@sveltejs/kit';
import { ApiError, apiFetch } from '$lib/server/api';
import { SESSION_COOKIE, clearSessionCookie } from '$lib/server/session';
import type { User } from '$lib/types';

const userByRequest = new WeakMap<object, Promise<User | null>>();

export const handle: Handle = async ({ event, resolve }) => {
	event.locals.user = null;
	const token = event.cookies.get(SESSION_COOKIE);

	if (!token) {
		return resolve(event);
	}

	const cached = userByRequest.get(event);
	const userPromise =
		cached ??
		(async () => {
			try {
				const user = await apiFetch<User>('/api/auth/me', { method: 'GET' }, token);
				return user;
			} catch (err) {
				if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
					clearSessionCookie(event.cookies);
				}
				return null;
			}
		})();

	if (!cached) userByRequest.set(event, userPromise);
	event.locals.user = await userPromise;

	return resolve(event);
};
