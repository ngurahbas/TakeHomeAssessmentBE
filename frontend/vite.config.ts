import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { svelteInspector } from '@sveltejs/vite-plugin-svelte-inspector';
import adapter from 'svelte-adapter-bun';
import fs from 'node:fs';
import { defineConfig, type Plugin } from 'vite';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const inspectorDir = fileURLToPath(
	new URL('./node_modules/@sveltejs/vite-plugin-svelte-inspector/src/runtime', import.meta.url)
);

// Workaround for https://github.com/sveltejs/kit bug in
// @sveltejs/vite-plugin-svelte-inspector@3.0.1 where `fs.existsSync(id)` is
// called with the id still containing the `?v=...` query string, so the
// file existence check always fails for the runtime .js entry. We register
// a `resolveId`/`load` pair that returns the runtime .js files directly.
// The .svelte file is left alone so the normal svelte-plugin loader can
// compile it.
function inspectorFix(): Plugin {
	return {
		name: 'svelte-inspector-fix',
		apply: 'serve',
		enforce: 'pre',
		resolveId(id) {
			if (
				id.startsWith('virtual:svelte-inspector-path:') &&
				id.endsWith('.js')
			) {
				return id.replace('virtual:svelte-inspector-path:', inspectorDir + path.sep);
			}
		},
		load(id) {
			if (id.startsWith(inspectorDir) && id.endsWith('.js')) {
				const file = id.split('?')[0];
				return fs.readFileSync(file, 'utf-8');
			}
		}
	};
}

export default defineConfig({
	plugins: [
		tailwindcss(),
		inspectorFix(),
		sveltekit({
			alias: {
				$lib: 'src/lib'
			},
			env: {
				dir: 'src'
			},
			compilerOptions: {
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true,
				experimental: {
					async: true
				}
			},
			adapter: adapter(),
			experimental: {
				remoteFunctions: true,
				explicitEnvironmentVariables: true
			},
			inspector: true
		}),
		svelteInspector()
	]
});
