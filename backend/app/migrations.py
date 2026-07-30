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
    """
    CREATE TABLE IF NOT EXISTS property (
        id              BIGSERIAL       PRIMARY KEY,
        title           VARCHAR(200)    NOT NULL,
        description     TEXT            NOT NULL DEFAULT '',
        property_type   VARCHAR(32)     NOT NULL,
        listing_type    VARCHAR(16)     NOT NULL,
        price_amount    NUMERIC(14,2)   NOT NULL,
        price_currency  CHAR(3)         NOT NULL,
        bedrooms        INT,
        bathrooms       INT,
        area_sqm        NUMERIC(10,2),
        address_line    VARCHAR(255)    NOT NULL,
        city            VARCHAR(128)    NOT NULL,
        district        VARCHAR(128),
        postal_code     VARCHAR(32),
        country_code    CHAR(2)         NOT NULL,
        latitude        NUMERIC(9,6),
        longitude       NUMERIC(9,6),
        status          VARCHAR(16)     NOT NULL DEFAULT 'AVAILABLE',
        amenities       TEXT[]          NOT NULL DEFAULT '{}',
        images          JSONB           NOT NULL DEFAULT '[]'::jsonb,
        created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
        created_by      BIGINT          REFERENCES app_user(id) ON DELETE SET NULL,
        updated_by      BIGINT          REFERENCES app_user(id) ON DELETE SET NULL,
        CONSTRAINT property_price_nonneg_chk CHECK (price_amount >= 0),
        CONSTRAINT property_area_nonneg_chk  CHECK (area_sqm IS NULL OR area_sqm >= 0),
        CONSTRAINT property_images_array_chk CHECK (jsonb_typeof(images) = 'array')
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS property_status_city_idx   ON property (status, city)
    """,
    """
    CREATE INDEX IF NOT EXISTS property_listing_price_idx ON property (listing_type, price_amount)
    """,
    """
    CREATE INDEX IF NOT EXISTS property_created_at_idx    ON property (created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS property_amenities_gin_idx ON property USING GIN (amenities)
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_conversation (
        id         BIGSERIAL    PRIMARY KEY,
        user_id    BIGINT       NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
        title      VARCHAR(200),
        created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS chat_conversation_user_updated_idx
        ON chat_conversation (user_id, updated_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_message (
        id              BIGSERIAL    PRIMARY KEY,
        conversation_id BIGINT       NOT NULL REFERENCES chat_conversation(id) ON DELETE CASCADE,
        role            VARCHAR(16)  NOT NULL,
        content         TEXT         NOT NULL,
        created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
        CONSTRAINT chat_message_role_chk
            CHECK (role IN ('system', 'user', 'assistant'))
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS chat_message_conv_created_idx
        ON chat_message (conversation_id, created_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS public_chat_session (
        id            UUID         PRIMARY KEY,
        created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
        last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS public_chat_message (
        id          BIGSERIAL    PRIMARY KEY,
        session_id  UUID         NOT NULL REFERENCES public_chat_session(id) ON DELETE CASCADE,
        role        VARCHAR(16)  NOT NULL,
        content     TEXT         NOT NULL,
        created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
        CONSTRAINT public_chat_message_role_chk
            CHECK (role IN ('system', 'user', 'assistant'))
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS public_chat_message_session_idx
        ON public_chat_message (session_id, created_at)
    """,
)


def ensure_schema(conn: Connection) -> None:
    with conn.transaction():
        for stmt in SCHEMA_STATEMENTS:
            conn.execute(stmt)
    logger.info("migrations: ensure_schema complete")
