# Backend: AGENTS

## Stack
- Python 3.14 (Docker base image `python:3.14-slim`)
- FastAPI + uvicorn
- pytest using FastAPI's `TestClient`

## Layout
- `app/main.py`: FastAPI app. Today only `GET /api/health` → `{"status": "ok"}`.
- `tests/test_health.py`: only existing test. Imports via `from app.main import app`, so tests must run with `backend/` as the working directory / pytest rootdir.
- `requirements.txt`: pinned deps.
- `run.py`: local dev entrypoint: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.
- `Dockerfile`: runs `uvicorn app.main:app --host 0.0.0.0 --port 8000` on port 8000.
- `.venv/`: already created locally; safe to reuse.

## Common Commands (run from `backend/`)
- Install deps: `pip install -r requirements.txt` (or use the existing `.venv`).
- Dev server: `python run.py` (or `uvicorn app.main:app --reload`).
- All tests: `pytest`.
- Single test: `pytest tests/test_health.py -k <name>`.

## Docker
From the repo root: `docker compose up --build`. Only the `backend` service is defined; it binds `8000:8000` and rebuilds on changes under `./backend`.

## Workflow Rules
- **Dependencies**: before adding or bumping anything in `requirements.txt`, look up the latest stable version on the web (PyPI / the package's official docs) and ask the user before editing the file. Do not silently pin a version you have not verified.
- **Verify with tests**: after any implementation change, run `pytest` from `backend/` and make sure it passes. Prefer adding or updating a test alongside the code change.
- **Env vars**: `.env` is gitignored at the repo root. There is no env-loading wiring in `app/main.py` yet. Introduce it deliberately when needed (don't sprinkle `os.environ` reads across handlers).
