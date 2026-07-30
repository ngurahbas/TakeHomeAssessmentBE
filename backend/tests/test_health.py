from fastapi.testclient import TestClient

from app.main import app
from app.settings import get_settings


def test_health_returns_ok_when_database_url_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database_url_set": False}


def test_health_reports_db_ok_against_real_postgres(client_with_postgres):
    response = client_with_postgres.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database_url_set": True,
        "db": "ok",
    }


def test_health_reports_db_down_when_postgres_unreachable(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@127.0.0.1:1/x")
    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["db"] == "down"
    assert body["db_error"]
