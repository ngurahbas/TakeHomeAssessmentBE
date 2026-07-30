import logging

import valkey

logger = logging.getLogger(__name__)


def make_valkey(url: str) -> valkey.Valkey:
    return valkey.Valkey.from_url(url, decode_responses=True, socket_timeout=2.0)


def probe(client: valkey.Valkey, *, timeout: float = 2.0) -> tuple[bool, str | None]:
    try:
        if client.ping():
            return True, None
        return False, "PING returned falsy"
    except Exception as exc:
        logger.warning("valkey health probe failed: %s", exc)
        return False, f"{type(exc).__name__}: {exc}"
