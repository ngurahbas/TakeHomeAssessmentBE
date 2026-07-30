import logging

from psycopg_pool import ConnectionPool

from app.auth.security import hash_password
from app.settings import Settings

logger = logging.getLogger(__name__)


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
