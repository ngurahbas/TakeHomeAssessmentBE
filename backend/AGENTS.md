# Backend: AGENTS

## Stack
- Python 3.14 (Docker base image `python:3.14-slim`)
- FastAPI + uvicorn
- pydantic v2
- psycopg (binary + pool) for Postgres
- valkey (valkey-py) for session storage; valkey 8 server in compose
- bcrypt for password hashing
- pytest using FastAPI's `TestClient`; `testcontainers[postgresql,valkey]` for real infra

## Layout
- `app/main.py`: FastAPI app. Lifespan creates the Postgres pool and the Valkey client, runs `ensure_schema` and `ensure_seed_admin` (only when the DB is reachable — failures are logged and skipped so the app can still report `db=down`), and closes both on shutdown. Routes: `GET /api/health`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`. Health response shape: `{"status": "ok", "database_url_set": bool, "db": "ok"|"down"?, "db_error": str?, "valkey": "ok"|"down"?, "valkey_error": str?}` — the `valkey` fields are present only when `VALKEY_URL` is set.
- `app/db.py`: `make_pool(conninfo)` builds a `psycopg_pool.ConnectionPool` (created with `open=False`, then `pool.open()` is called so connections are opened lazily on first borrow); `probe(pool, *, timeout=2.0)` runs `SELECT 1` through the pool and returns `(ok, error_message)`.
- `app/valkey_client.py`: `make_valkey(url)` builds a `valkey.Valkey.from_url(url, decode_responses=True, socket_timeout=2.0)` so values come back as `str`; `probe(client, *, timeout=2.0)` calls `PING` and returns `(ok, error_message)`.
- `app/settings.py`: single, deliberate env loader. All `os.environ` reads happen here via `get_settings()`; do not sprinkle reads across handlers. Keys: `DATABASE_URL`, `VALKEY_URL`, `AUTH_TOKEN_TTL_SECONDS` (default `86400`), `AUTH_BCRYPT_ROUNDS` (default `12`), `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD`.
- `app/migrations.py`: `SCHEMA_STATEMENTS` (tuple of idempotent DDL) and `ensure_schema(conn)` run inside a single transaction at lifespan startup. Today: the `app_user` table.
- `app/seed.py`: `ensure_seed_admin(settings, pool)` — if `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` are both set and `app_user` is empty, inserts one row with `role='ADMIN'`. Idempotent.
- `app/auth/`: subpackage for auth.
  - `app/auth/roles.py`: `ROLE_ADMIN = "ADMIN"`. Single source of truth for the role literal. When a second role appears, replace with a `Role(StrEnum)` and switch `UserOut.role` to `Literal[...]` — no SQL migration of the `role` column.
  - `app/auth/security.py`: `hash_password`, `verify_password` (bcrypt), `new_token` (`secrets.token_urlsafe(32)`), `session_key(token)` (`sess:{token}`).
  - `app/auth/schemas.py`: pydantic v2 models — `LoginRequest` (email is normalized to lowercase + validated with a regex; password `min_length=1`, `max_length=72` to honor bcrypt 5.0.0's 72-byte limit), `UserOut`, `LoginResponse`.
  - `app/auth/routes.py`: APIRouter mounted at `/api/auth`. Login inserts `sess:{token} -> user_id` in Valkey with TTL = `AUTH_TOKEN_TTL_SECONDS`. `get_current_user` is a reusable dependency that reads the bearer token, looks up the session in Valkey, and loads the user from Postgres. Logout goes through `get_current_user` so an already-revoked token returns 401.
- **RBAC policy**: no SQL-level role enforcement (no `CHECK` constraints, no row-level security, no trigger guards). When a second role is added, authorization is a Python dependency (e.g. `require_admin`) in `app/auth/`.
- `tests/conftest.py`: pytest fixtures — `postgres_container` (session, `postgres:18`), `valkey_container` (session, `valkey/valkey:8`), `client_with_postgres` (function, DB only), `client_with_full_stack` (function, DB + Valkey + seed env), `db_pool_seeded` (function, gives direct pool access after migrations + seed run). Test seed credentials are `admin@example.com` / `correct-horse-battery-staple` (constants in `conftest.py`).
- `tests/test_health.py`: health endpoint tests, all real infra, no mocks.
- `tests/test_auth.py`: login / logout / me tests against real Postgres + Valkey, plus a direct-DB test for the seed role.
- `requirements.txt`: production deps.
- `requirements-dev.txt`: test-only deps; chains `-r requirements.txt`.
- `run.py`: local dev entrypoint: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.
- `Dockerfile`: runs `uvicorn app.main:app --host 0.0.0.0 --port 8000` on port 8000.
- `.venv/`: already created locally; safe to reuse.

## Common Commands (run from `backend/`)
- Install deps (dev/test): `pip install -r requirements-dev.txt` (or use the existing `.venv`).
- Install deps (production-style, no test deps): `pip install -r requirements.txt`.
- Dev server: `python run.py` (or `uvicorn app.main:app --reload`).
- All tests: `pytest` (requires a reachable Docker daemon for the testcontainers-based tests; those tests skip cleanly otherwise).
- Single test: `pytest tests/test_health.py -k <name>` (or `tests/test_auth.py`).

## Docker
From the repo root: `docker compose up --build`. Three services: `db` (postgres:18), `valkey` (valkey/valkey:8), `backend`. `db` exposes `5432:5432` (dev only — change before deploying), has a `pg_isready` healthcheck, and persists to the `postgres_data` volume. `valkey` exposes `6379:6379`, has a `valkey-cli ping` healthcheck, and persists to the `valkey_data` volume. `backend` binds `8000:8000`, receives `DATABASE_URL` and `VALKEY_URL` from compose, references `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` from the host environment (resolved from the gitignored `.env` at the repo root — see Workflow Rules), waits for both `db` and `valkey` to be healthy, and rebuilds on changes under `./backend`. DB and seed credentials in `compose.yaml` are dev-only.

## Workflow Rules
- **Dependencies**: before adding or bumping anything in `requirements.txt` or `requirements-dev.txt`, look up the latest stable version on the web (PyPI / the package's official docs) and ask the user before editing the file. Do not silently pin a version you have not verified.
- **Verify with tests**: after any implementation change, run `pytest` from `backend/` and make sure it passes. Prefer adding or updating a test alongside the code change.
- **Env vars**: `.env` is gitignored at the repo root. Env loading lives in `app/settings.py` via `get_settings()`; add new config there rather than sprinkling `os.environ` reads across handlers.
- **Session store**: Valkey only. Keys are `sess:{token}` → `user_id` (str). No `app_user_session` Postgres table; sessions are not in SQL.
- **Password hashing**: bcrypt 5.x. The 72-byte limit is enforced at the pydantic layer (`LoginRequest.password` `max_length=72`). If longer passwords ever need support, pre-hash with SHA-256 + base64 before bcrypt (per the bcrypt docs).
