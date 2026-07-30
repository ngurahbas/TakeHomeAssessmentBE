# AGENTS

Two active projects live side-by-side:

- `backend/` — Python 3.14 + FastAPI. See [`backend/AGENTS.md`](backend/AGENTS.md) for the guide.
- `frontend/` — SvelteKit 2 + Bun + Skeleton v3 + bits-ui. See [`frontend/AGENTS.md`](frontend/AGENTS.md) for the guide.

The frontend is the only service published by compose. The browser talks to SvelteKit; SvelteKit talks to the FastAPI backend in-network via `BACKEND_PREFIX`.
