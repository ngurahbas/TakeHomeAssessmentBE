import * as v from 'valibot';
import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	BACKEND_PREFIX: {
		description: 'Origin where the FastAPI backend is reachable from the SvelteKit server.',
		schema: v.pipe(v.string(), v.minLength(1, 'BACKEND_PREFIX must be set (e.g. http://backend:8000)'))
	}
});
