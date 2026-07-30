import { BACKEND_PREFIX } from '$app/env/private';
import { SESSION_COOKIE } from './session';

export class ApiError extends Error {
	readonly status: number;
	readonly body: unknown;

	constructor(status: number, body: unknown, message?: string) {
		super(message ?? `Backend returned ${status}`);
		this.name = 'ApiError';
		this.status = status;
		this.body = body;
	}
}

type ApiFetchInit = Omit<RequestInit, 'body'> & {
	body?: BodyInit | Record<string, unknown> | null;
	token?: string | null;
};

function readBackendPrefix(): string {
	if (!BACKEND_PREFIX) {
		throw new Error(
			'BACKEND_PREFIX is not set. Define it in the frontend service environment.'
		);
	}
	return BACKEND_PREFIX;
}

export async function apiFetch<T = unknown>(
	path: string,
	init: ApiFetchInit = {},
	cookieToken?: string | null
): Promise<T> {
	const base = readBackendPrefix();
	const url = path.startsWith('http') ? path : `${base}${path.startsWith('/') ? '' : '/'}${path}`;

	const headers = new Headers(init.headers);
	let body = init.body;
	if (body && typeof body === 'object' && !(body instanceof FormData) && !(body instanceof Blob)) {
		headers.set('content-type', 'application/json');
		body = JSON.stringify(body);
	}
	const token = init.token ?? cookieToken;
	if (token) {
		headers.set('authorization', `Bearer ${token}`);
	}

	let response: Response;
	try {
		response = await fetch(url, { ...init, headers, body: body as BodyInit | undefined });
	} catch (err) {
		throw new ApiError(0, null, `Backend unreachable: ${(err as Error).message}`);
	}

	if (!response.ok) {
		let payload: unknown = null;
		const text = await response.text();
		if (text) {
			try {
				payload = JSON.parse(text);
			} catch {
				payload = text;
			}
		}
		throw new ApiError(response.status, payload);
	}

	if (response.status === 204) return undefined as T;

	const contentType = response.headers.get('content-type') ?? '';
	if (contentType.includes('application/json')) {
		return (await response.json()) as T;
	}
	return (await response.text()) as unknown as T;
}

export function getTokenFromCookies(getCookie: (name: string) => string | undefined): string | null {
	return getCookie(SESSION_COOKIE) ?? null;
}
