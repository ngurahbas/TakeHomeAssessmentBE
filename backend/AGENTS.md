# Backend: AGENTS

## Stack
- Python 3.14 (Docker base image `python:3.14-slim`)
- FastAPI + uvicorn
- pytest using FastAPI's `TestClient`

## Layout
- `app/main.py`: FastAPI app. Today only `GET /api/health`. Lifespan creates the DB pool at startup and closes it on shutdown. Health response shape: `{"status": "ok", "database_url_set": bool, "db": "ok"|"down"?, "db_error": str?}`.
- `app/db.py`: `make_pool(conninfo)` builds a `psycopg_pool.ConnectionPool` (created with `open=False`, then `pool.open()` is called so connections are opened lazily on first borrow); `probe(pool, *, timeout=2.0)` runs `SELECT 1` through the pool and returns `(ok, error_message)`.
- `app/settings.py`: single, deliberate env loader. All `os.environ` reads happen here via `get_settings()`; do not sprinkle reads across handlers.
- `tests/conftest.py`: pytest fixtures — `postgres_container` (session-scoped, spins up a real `postgres:18` via `testcontainers.community.postgres.PostgresContainer`, skips if Docker is unavailable) and `client_with_postgres` (function-scoped, sets `DATABASE_URL` to the container's URL with the `postgresql+psycopg://` driver prefix stripped, and yields a `TestClient(app)` context manager so the lifespan runs).
- `tests/test_health.py`: all tests run the real `probe` and the real pool — no mocks. One test uses the testcontainers Postgres; one uses a deliberately-unreachable URL to assert the down path.
- `requirements.txt`: production deps (installed by the Docker image).
- `requirements-dev.txt`: test-only deps (pytest, httpx2, testcontainers[postgresql]); chains `-r requirements.txt`.
- `run.py`: local dev entrypoint: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.
- `Dockerfile`: runs `uvicorn app.main:app --host 0.0.0.0 --port 8000` on port 8000.
- `.venv/`: already created locally; safe to reuse.

## Common Commands (run from `backend/`)
- Install deps (dev/test): `pip install -r requirements-dev.txt` (or use the existing `.venv`).
- Install deps (production-style, no test deps): `pip install -r requirements.txt`.
- Dev server: `python run.py` (or `uvicorn app.main:app --reload`).
- All tests: `pytest` (requires a reachable Docker daemon for the testcontainers-based tests; those tests skip cleanly otherwise).
- Single test: `pytest tests/test_health.py -k <name>`.

## Docker
From the repo root: `docker compose up --build`. The `db` (postgres:18) and `backend` services are defined. `db` exposes `5432:5432` (dev only — change before deploying), has a `pg_isready` healthcheck, and persists to the `postgres_data` named volume. `backend` binds `8000:8000`, receives `DATABASE_URL` from compose, waits for `db` to be healthy via `depends_on: { db: { condition: service_healthy } }`, and rebuilds on changes under `./backend`. DB credentials in `compose.yaml` are dev-only.

## Workflow Rules
- **Dependencies**: before adding or bumping anything in `requirements.txt` or `requirements-dev.txt`, look up the latest stable version on the web (PyPI / the package's official docs) and ask the user before editing the file. Do not silently pin a version you have not verified.
- **Verify with tests**: after any implementation change, run `pytest` from `backend/` and make sure it passes. Prefer adding or updating a test alongside the code change.
- **Env vars**: `.env` is gitignored at the repo root. Env loading lives in `app/settings.py` via `get_settings()`; add new config there rather than sprinkling `os.environ` reads across handlers.
