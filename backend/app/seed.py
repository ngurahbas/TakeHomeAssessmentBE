import json
import logging
from pathlib import Path
from typing import Any

from psycopg_pool import ConnectionPool

from app.auth.security import hash_password
from app.settings import Settings

logger = logging.getLogger(__name__)


DEFAULT_SEED_PROPERTIES_PATH = (
    Path(__file__).resolve().parent / "seed_data" / "properties.json"
)


def ensure_seed_admin(settings: Settings, pool: ConnectionPool) -> None:
    email = settings.seed_admin_email
    password = settings.seed_admin_password
    if not email or not password:
        logger.info("seed: skipped (SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD unset)")
        return
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM app_user")
            (count,) = cur.fetchone()
            if count > 0:
                logger.info("seed: skipped (app_user already has %d row(s))", count)
                return
            password_hash = hash_password(password, rounds=settings.auth_bcrypt_rounds)
            cur.execute(
                "INSERT INTO app_user (email, password_hash, role) "
                "VALUES (%s, %s, 'ADMIN') "
                "ON CONFLICT (email) DO NOTHING",
                (email, password_hash),
            )
            if cur.rowcount == 0:
                logger.info("seed: skipped (admin already exists)")
                return
    logger.info("seed: inserted ADMIN user %s", email)


def ensure_seed_properties(
    settings: Settings,
    pool: ConnectionPool,
    *,
    path: str | Path | None = None,
) -> None:
    """Insert the vendored property seed rows when enabled and the table is empty.

    Assumes a single replica first-boots the database; the count-then-insert
    sequence is not safe under concurrent first-boots, but that is not a
    realistic scenario for the single-container compose setup.
    """
    if not settings.seed_properties_enabled:
        logger.info("seed: property seed skipped (SEED_PROPERTIES not enabled)")
        return
    seed_path = Path(path or settings.seed_properties_path or DEFAULT_SEED_PROPERTIES_PATH)
    if not seed_path.is_file():
        logger.warning("seed: property seed file not found at %s; skipping", seed_path)
        return
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM property")
            (count,) = cur.fetchone()
            if count > 0:
                logger.info(
                    "seed: property seed skipped (property already has %d row(s))",
                    count,
                )
                return
            rows = json.loads(seed_path.read_text(encoding="utf-8"))
            if not isinstance(rows, list) or not rows:
                logger.warning("seed: property seed file is empty; skipping")
                return
            inserted = _insert_properties(conn, rows)
    logger.info(
        "seed: inserted %d property row(s) from %s "
        "(source: Sekirkallc/ai-data-factory-real-estate, MIT)",
        inserted,
        seed_path,
    )


def _coerce_seed_row(row: dict) -> dict:
    out: dict[str, Any] = dict(row)
    images = out.get("images") or []
    out["images"] = json.dumps(
        [
            {
                "url": str(img.get("url", "")),
                "sort_order": int(img.get("sort_order", 0)),
                "alt": img.get("alt"),
            }
            for img in images
        ]
    )
    return out


def _insert_properties(conn, rows: list[dict]) -> int:
    sql = """
        INSERT INTO property (
            title, description, property_type, listing_type,
            price_amount, price_currency,
            bedrooms, bathrooms, area_sqm,
            address_line, city, district, postal_code, country_code,
            latitude, longitude, status, amenities, images
        ) VALUES (
            %(title)s, %(description)s, %(property_type)s, %(listing_type)s,
            %(price_amount)s, %(price_currency)s,
            %(bedrooms)s, %(bathrooms)s, %(area_sqm)s,
            %(address_line)s, %(city)s, %(district)s, %(postal_code)s, %(country_code)s,
            %(latitude)s, %(longitude)s, %(status)s, %(amenities)s::text[], %(images)s::jsonb
        )
    """
    coerced = [_coerce_seed_row(r) for r in rows]
    with conn.cursor() as cur:
        cur.executemany(sql, coerced)
    return len(coerced)
