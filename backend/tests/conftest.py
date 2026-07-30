import pytest
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.valkey import ValkeyContainer

TEST_SEED_ADMIN_EMAIL = "admin@example.com"
TEST_SEED_ADMIN_PASSWORD = "correct-horse-battery-staple"


def _postgres_url(container) -> str:
    url = container.get_connection_url(driver="psycopg")
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


@pytest.fixture(scope="session")
def postgres_container():
    try:
        with PostgresContainer("postgres:18") as pg:
            yield pg
    except Exception as exc:
        pytest.skip(f"Docker unavailable for testcontainers: {exc}")


@pytest.fixture(scope="session")
def valkey_container():
    try:
        with ValkeyContainer("valkey/valkey:8") as vk:
            yield vk
    except Exception as exc:
        pytest.skip(f"Docker unavailable for testcontainers: {exc}")


@pytest.fixture
def client_with_postgres(postgres_container, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app
    from app.settings import get_settings

    monkeypatch.setenv("DATABASE_URL", _postgres_url(postgres_container))
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


@pytest.fixture
def client_with_full_stack(
    postgres_container, valkey_container, monkeypatch
):
    from fastapi.testclient import TestClient

    from app.main import app
    from app.settings import get_settings

    monkeypatch.setenv("DATABASE_URL", _postgres_url(postgres_container))
    monkeypatch.setenv("VALKEY_URL", valkey_container.get_connection_url())
    monkeypatch.setenv("SEED_ADMIN_EMAIL", TEST_SEED_ADMIN_EMAIL)
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", TEST_SEED_ADMIN_PASSWORD)
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


@pytest.fixture
def db_pool_seeded(postgres_container, monkeypatch):
    from app.db import make_pool
    from app.migrations import ensure_schema
    from app.seed import ensure_seed_admin
    from app.settings import get_settings

    monkeypatch.setenv("DATABASE_URL", _postgres_url(postgres_container))
    monkeypatch.setenv("SEED_ADMIN_EMAIL", TEST_SEED_ADMIN_EMAIL)
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", TEST_SEED_ADMIN_PASSWORD)
    get_settings.cache_clear()
    pool = make_pool(get_settings().database_url)
    try:
        with pool.connection() as conn:
            ensure_schema(conn)
        ensure_seed_admin(get_settings(), pool)
        yield pool
    finally:
        pool.close()
    get_settings.cache_clear()
