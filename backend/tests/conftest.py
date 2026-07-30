import pytest
from testcontainers.community.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_container():
    try:
        with PostgresContainer("postgres:18") as pg:
            yield pg
    except Exception as exc:
        pytest.skip(f"Docker unavailable for testcontainers: {exc}")


@pytest.fixture
def client_with_postgres(postgres_container, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app
    from app.settings import get_settings

    url = postgres_container.get_connection_url(driver="psycopg")
    url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()
