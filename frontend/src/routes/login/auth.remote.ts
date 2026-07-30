import * as v from 'valibot';
import { getRequestEvent } from '$app/server';
import { form } from '$app/server';
import { invalid, redirect } from '@sveltejs/kit';
import { ApiError, apiFetch } from '$lib/server/api';
import { SESSION_COOKIE, sessionCookieOptions } from '$lib/server/session';
import type { LoginResponse } from '$lib/types';

const LoginSchema = v.object({
	email: v.pipe(v.string('Email is required'), v.trim(), v.email('Enter a valid email address'), v.maxLength(255)),
	password: v.pipe(
		v.string('Password is required'),
		v.minLength(1, 'Password is required'),
		v.maxLength(72, 'Password is too long')
	)
});

export const login = form(LoginSchema, async ({ email, password }, issue) => {
	let data: LoginResponse;
	try {
		data = await apiFetch<LoginResponse>(
			'/api/auth/login',
			{
				method: 'POST',
				body: { email, password }
			},
			null
		);
	} catch (err) {
		if (err instanceof ApiError && err.status === 401) {
			invalid(issue.password('Invalid email or password'));
		}
		if (err instanceof ApiError && err.status === 422) {
			invalid(issue.email('Please check the email format'));
		}
		throw err;
	}

	const event = getRequestEvent();
	event.cookies.set(SESSION_COOKIE, data.token, sessionCookieOptions());
	const next = event.url.searchParams.get('next');
	redirect(303, next && next.startsWith('/') ? next : '/dashboard');
});
