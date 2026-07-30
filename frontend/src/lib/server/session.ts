import type { Cookies } from '@sveltejs/kit';

export const SESSION_COOKIE = 'session';

const isProduction = process.env.NODE_ENV === 'production';

function baseCookieOptions(maxAge: number) {
	return {
		path: '/',
		httpOnly: true,
		sameSite: 'lax' as const,
		secure: isProduction,
		maxAge
	};
}

export function sessionCookieOptions() {
	return baseCookieOptions(60 * 60 * 24);
}

export function clearSessionCookie(cookies: Cookies) {
	cookies.set(SESSION_COOKIE, '', baseCookieOptions(0));
}
