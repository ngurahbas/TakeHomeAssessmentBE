# Frontend: AGENTS

## Stack
- SvelteKit 2.70 + Svelte 5 (runes + `await` in templates)
- Bun 1 (package manager + runtime; `svelte-adapter-bun` for prod)
- TypeScript 5
- Tailwind v4 (`@tailwindcss/vite`)
- Skeleton v3 (`@skeletonlabs/skeleton` + `@skeletonlabs/skeleton-svelte`, theme `cerberus`)
- `bits-ui` (headless primitives, available for future pages)
- `valibot` for standard-schema validation in remote functions
- SvelteKit experimental features: `compilerOptions.experimental.async`, `kit.experimental.remoteFunctions`, `kit.experimental.explicitEnvironmentVariables`

## Layout
- `vite.config.ts`: `sveltekit({ alias: { $lib: 'src/lib' }, env: { dir: 'src' }, adapter, experimental })` plus the Tailwind plugin.
- `src/env.ts`: single source of env-var declarations via `defineEnvVars(...)`. Imported values come from `$app/env/private` (auto-generated types, server-only).
- `src/app.html`: `<html data-theme="cerberus">`, dark-mode-friendly body classes.
- `src/routes/layout.css` (imported by `+layout.svelte`): Tailwind + Skeleton + theme `@import`s.
- `src/app.d.ts`: `App.Locals.user: User | null`, `App.PageData.user: User | null`.
- `src/hooks.server.ts`: reads `session` cookie, calls `/api/auth/me` through `apiFetch`, populates `event.locals.user`. On 401/403, clears the cookie. Per-request `WeakMap` cache.
- `src/lib/server/api.ts`: typed `apiFetch<T>(path, init, cookieToken?)` — prepends `BACKEND_PREFIX`, attaches `Authorization: Bearer …`, throws `ApiError(status, body)` on non-2xx.
- `src/lib/server/session.ts`: `SESSION_COOKIE = 'session'`, `sessionCookieOptions()` (httpOnly, sameSite=lax, secure when `NODE_ENV=production`, 24h maxAge), `clearSessionCookie()`.
- `src/lib/types.ts`: shared `User`, `LoginResponse`.
- `src/routes/+layout.svelte`: Skeleton `AppBar` (Toolbar/Lead/Trail) + container `<main>`.
- `src/routes/+layout.server.ts`: returns `{ user: locals.user }`.
- `src/routes/+page.svelte`: minimal placeholder ("Signed in as …" / "Sign in" CTA).
- `src/routes/login/+page.server.ts`: redirects to `/` if already signed in.
- `src/routes/login/+page.svelte`: Skeleton card form, spreads `{...login}`, uses `login.fields.email.as('email')` / `login.fields.password.as('password')` and renders issues.
- `src/routes/login/auth.remote.ts`: `login = form(valibotSchema, handler)`. Validates email/password, calls `apiFetch('/api/auth/login', { method: 'POST', body: { email, password } })`. On 401, `invalid(issue.password('Invalid email or password'))`. On success, sets the `session` cookie and `redirect(303, '/')`.
- `src/routes/public/ai-chat/+page.svelte`: standalone AI chat UI (no AppBar — see `STANDALONE_PREFIXES` in `src/routes/+layout.svelte`). State is keyed by a UUID stored in `localStorage` under `public-ai-chat:chat-id`; on first visit the storage key is empty and the backend mints a new chat_id. On every turn the page sends `{chat_id, content}` to `sendPublicMessage` and writes the returned `chat_id` back to `localStorage`. The reset button clears the storage key + UI state. On `PublicChatUnavailableError` it surfaces a Skeleton `alert` and appends a fallback assistant bubble; if the backend's 502 detail includes a `chat_id` (LLM failed mid-turn), the page adopts it so the next retry resumes the same session. `isThinking` always resets in `finally` so the input re-enables.
- `src/routes/public/ai-chat/chat.remote.ts`: `sendPublicMessage = command<PublicChatSendRequest, PublicChatSendResponse>('unchecked', fn)` — server-side handler that calls `apiFetch('/public/ai-chat', { method: 'POST', body: { chat_id, content } }, null)`. Wraps any `ApiError` in a typed `PublicChatUnavailableError(status, message, chatId)` so the page can show a friendly message instead of the raw 502 body and adopt the fallback `chat_id` if the backend provided one. Reaches the same FastAPI `app/chat/llm.complete` that the authed chat uses. **Files in `*.remote.ts` may only export remote functions** — types and the error class live in a sibling `chat.types.ts`.

## Backend access
- The browser **never** talks to the FastAPI backend directly. All API calls go through a SvelteKit remote function (`form` / `query` / `command`) that runs on the SvelteKit server.
- `BACKEND_PREFIX` is resolved from the frontend service environment in `compose.yaml`. It is declared in `src/env.ts` and imported as `BACKEND_PREFIX` from `$app/env/private`.
- The bearer token stays server-side: the browser only ever holds the `session` httpOnly cookie; SvelteKit's `apiFetch` attaches the `Authorization` header when calling the backend.

## Common Commands (run from `frontend/`)
- Install deps: `bun install`.
- Dev server: `bun --bun run dev` (or `bun run dev`). Reads `.env` if present; copy `.env.example` to `.env` and set `BACKEND_PREFIX` for local development against a running compose stack.
- Type check: `bun run check`.
- Build for prod: `BACKEND_PREFIX=http://backend:8000 bun run build` (compose does this with a build arg).
- Run prod locally: `BACKEND_PREFIX=http://localhost:8000 bun run start` (after a `bun run build`).

## Svelte inspector (dev only)
- The Svelte inspector is enabled via `inspector: true` in the `sveltekit()` plugin call in `vite.config.ts`, plus the `svelteInspector()` plugin and a small `inspectorFix()` workaround plugin for a `fs.existsSync(id)` bug in `@sveltejs/vite-plugin-svelte-inspector@3.0.1` (the only version compatible with our Vite 5 / `@sveltejs/vite-plugin-svelte@4` pair).
- Default key combo: **Alt+X** to toggle the inspector overlay; **click** a component in the overlay to open it in your editor; **arrow keys** to navigate the component tree. Configure via the `inspector` option in `vite.config.ts` (or remove `inspector: true` to disable).

## Docker
- `Dockerfile`: `oven/bun:1` base for deps + build, `oven/bun:1-slim` for the runtime image. `BACKEND_PREFIX` is a build arg and is also re-set as a runtime env. `CMD ["bun", "./build/index.js"]`, `EXPOSE 3000`.
- The compose `frontend` service is the only port published (`3000:3000`). The `backend` service is intentionally not published; the browser can only reach the SvelteKit process, which proxies API calls to `backend:8000` in-network.
- `ORIGIN` is set on the frontend service in `compose.yaml` so SvelteKit can verify the `Origin` header on POSTs (cross-site POSTs are otherwise rejected with 403).

## Workflow Rules
- **Server-only modules**: anything that touches `BACKEND_PREFIX`, secrets, or `apiFetch` lives under `src/lib/server/` and is only imported from `+page.server.ts`, `+page.remote.ts`, `+server.ts`, `hooks.server.ts`, or other server-only files.
- **Cookies for auth**: the bearer token from the backend never reaches the browser. Always set it via `cookies.set(SESSION_COOKIE, token, sessionCookieOptions())` from inside a remote function or `+page.server.ts`.
- **Validation**: new remote `form` functions use `valibot` schemas as the first argument. Surface field-level errors with `invalid(issue.field('…'))` and whole-form errors with `invalid('…')`.
- **Skeleton classes first**: prefer Skeleton's utility classes (`btn`, `card`, `input`, `label`, `preset-*`, etc.) for styling. Reach for `bits-ui` only when you need headless behavior Skeleton doesn't provide.
- **Dependencies**: before adding or bumping a frontend dependency, look up the latest stable version on the web (npm) and ask the user before editing the file. Do not silently pin a version you have not verified.
