import pytest
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.valkey import ValkeyContainer

TEST_SEED_ADMIN_EMAIL = "admin@example.com"
TEST_SEED_ADMIN_PASSWORD = "correct-horse-battery-staple"
TEST_SECONDARY_USER_EMAIL = "agent@example.com"
TEST_SECONDARY_USER_PASSWORD = "secondary-test-password"


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


@pytest.fixture
def secondary_user(db_pool_seeded):
    """Insert a non-admin user directly via the seeded pool; return (id, email, password)."""
    from app.auth.security import hash_password

    pool = db_pool_seeded
    password_hash = hash_password(TEST_SECONDARY_USER_PASSWORD)
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO app_user (email, password_hash, role) "
                "VALUES (%s, %s, 'AGENT') "
                "ON CONFLICT (email) DO UPDATE SET role = EXCLUDED.role "
                "RETURNING id",
                (TEST_SECONDARY_USER_EMAIL, password_hash),
            )
            (user_id,) = cur.fetchone()
    return {"id": user_id, "email": TEST_SECONDARY_USER_EMAIL, "password": TEST_SECONDARY_USER_PASSWORD}


@pytest.fixture
def admin_token(client_with_full_stack):
    response = client_with_full_stack.post(
        "/api/auth/login",
        json={"email": TEST_SEED_ADMIN_EMAIL, "password": TEST_SEED_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture
def non_admin_token(client_with_full_stack, secondary_user):
    response = client_with_full_stack.post(
        "/api/auth/login",
        json={
            "email": secondary_user["email"],
            "password": secondary_user["password"],
        },
    )
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture
def property_create_payload():
    return {
        "title": "Modern Test Property",
        "description": "A property used by the test suite.",
        "property_type": "APARTMENT",
        "listing_type": "RENT",
        "price_amount": 1500.0,
        "price_currency": "USD",
        "bedrooms": 2,
        "bathrooms": 1,
        "area_sqm": 65.5,
        "address_line": "1 Test Street",
        "city": "Testville",
        "district": "Test District",
        "postal_code": "00000",
        "country_code": "US",
        "latitude": 40.0,
        "longitude": -74.0,
        "status": "AVAILABLE",
        "amenities": ["parking", "Pool", "parking"],
        "images": [
            {"url": "https://example.com/1.jpg", "sort_order": 0, "alt": "front"},
            {"url": "https://example.com/2.jpg", "sort_order": 1, "alt": "kitchen"},
        ],
    }
