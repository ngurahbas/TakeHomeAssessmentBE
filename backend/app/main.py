import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.db import make_pool, probe
from app.settings import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    pool = make_pool(settings.database_url) if settings.database_url else None
    app.state.db_pool = pool
    logger.info("startup: db_pool=%s", "set" if pool else "none")
    try:
        yield
    finally:
        if pool is not None:
            await asyncio.get_event_loop().run_in_executor(None, pool.close)


app = FastAPI(title="Real Estate AI Assistant", lifespan=lifespan)


@app.get("/api/health")
def health(request: Request):
    settings = get_settings()
    body: dict = {
        "status": "ok",
        "database_url_set": settings.database_url is not None,
    }
    pool = request.app.state.db_pool
    if settings.database_url and pool is not None:
        ok, err = probe(pool)
        body["db"] = "ok" if ok else "down"
        if err:
            body["db_error"] = err
    return body
