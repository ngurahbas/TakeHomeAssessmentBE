import logging

from psycopg import Connection

logger = logging.getLogger(__name__)


SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS app_user (
        id            BIGSERIAL    PRIMARY KEY,
        email         VARCHAR(255) NOT NULL UNIQUE,
        password_hash TEXT         NOT NULL,
        role          VARCHAR(32)  NOT NULL,
        created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
        updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS app_user_email_idx ON app_user (email)
    """,
)


def ensure_schema(conn: Connection) -> None:
    with conn.transaction():
        for stmt in SCHEMA_STATEMENTS:
            conn.execute(stmt)
    logger.info("migrations: ensure_schema complete")
