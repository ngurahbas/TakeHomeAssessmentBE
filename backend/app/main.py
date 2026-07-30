import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.auth.routes import router as auth_router
from app.chat.routes import router as chat_router
from app.db import make_pool, probe as db_probe
from app.migrations import ensure_schema
from app.properties.routes import router as properties_router
from app.seed import ensure_seed_admin, ensure_seed_properties
from app.settings import get_settings
from app.valkey_client import make_valkey, probe as valkey_probe

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    pool = make_pool(settings.database_url) if settings.database_url else None
    valkey_client = make_valkey(settings.valkey_url) if settings.valkey_url else None
    app.state.db_pool = pool
    app.state.valkey = valkey_client
    logger.info(
        "startup: db_pool=%s valkey=%s",
        "set" if pool else "none",
        "set" if valkey_client else "none",
    )
    if pool is not None:
        db_ok, db_err = db_probe(pool, timeout=2.0)
        if not db_ok:
            logger.warning(
                "startup: db unreachable, skipping migrations/seed: %s", db_err
            )
        else:
            try:
                with pool.connection() as conn:
                    ensure_schema(conn)
                ensure_seed_admin(settings, pool)
                ensure_seed_properties(settings, pool)
            except Exception:
                logger.exception("startup: migrations/seed failed")
    try:
        yield
    finally:
        loop = asyncio.get_running_loop()
        if pool is not None:
            await loop.run_in_executor(None, pool.close)
        if valkey_client is not None:
            await loop.run_in_executor(None, valkey_client.close)


app = FastAPI(title="Real Estate AI Assistant", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(properties_router)
app.include_router(chat_router)


@app.get("/api/health")
def health(request: Request):
    settings = get_settings()
    body: dict = {
        "status": "ok",
        "database_url_set": settings.database_url is not None,
    }
    pool = request.app.state.db_pool
    if settings.database_url and pool is not None:
        ok, err = db_probe(pool)
        body["db"] = "ok" if ok else "down"
        if err:
            body["db_error"] = err
    valkey_client = request.app.state.valkey
    if settings.valkey_url and valkey_client is not None:
        ok, err = valkey_probe(valkey_client)
        body["valkey"] = "ok" if ok else "down"
        if err:
            body["valkey_error"] = err
    return body
