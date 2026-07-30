import logging

from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)


def make_pool(conninfo: str) -> ConnectionPool:
    pool = ConnectionPool(
        conninfo=conninfo,
        min_size=1,
        max_size=5,
        timeout=5.0,
        max_idle=300.0,
        reconnect_timeout=5.0,
        open=False,
    )
    pool.open()
    return pool


def probe(pool: ConnectionPool, *, timeout: float = 2.0) -> tuple[bool, str | None]:
    try:
        with pool.connection(timeout=timeout) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True, None
    except Exception as exc:
        logger.warning("db health probe failed: %s", exc)
        return False, f"{type(exc).__name__}: {exc}"
