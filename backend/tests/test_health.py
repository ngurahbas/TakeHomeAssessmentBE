from fastapi.testclient import TestClient

from app.main import app
from app.settings import get_settings


def test_health_returns_ok_when_database_url_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("VALKEY_URL", raising=False)
    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database_url_set": False}


def test_health_reports_db_ok_against_real_postgres(client_with_postgres):
    response = client_with_postgres.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database_url_set"] is True
    assert body["db"] == "ok"
    assert "valkey" not in body


def test_health_reports_db_down_when_postgres_unreachable(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@127.0.0.1:1/x")
    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["db"] == "down"
    assert body["db_error"]


def test_health_reports_valkey_ok_against_real_valkey(client_with_full_stack):
    response = client_with_full_stack.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database_url_set"] is True
    assert body["db"] == "ok"
    assert body["valkey"] == "ok"
    assert "valkey_error" not in body


def test_health_omits_valkey_when_valkey_url_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("VALKEY_URL", raising=False)
    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert "valkey" not in body
    assert "valkey_error" not in body
