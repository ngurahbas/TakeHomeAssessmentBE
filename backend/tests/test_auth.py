from fastapi.testclient import TestClient

from app.auth.roles import ROLE_ADMIN
from tests.conftest import TEST_SEED_ADMIN_EMAIL, TEST_SEED_ADMIN_PASSWORD


def _login(client: TestClient, email: str, password: str):
    return client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )


def test_login_with_valid_credentials_returns_token_and_user(
    client_with_full_stack,
):
    client = client_with_full_stack
    response = _login(client, TEST_SEED_ADMIN_EMAIL, TEST_SEED_ADMIN_PASSWORD)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["token"], str) and body["token"]
    assert body["user"]["email"] == TEST_SEED_ADMIN_EMAIL
    assert body["user"]["role"] == ROLE_ADMIN
    assert isinstance(body["user"]["id"], int) and body["user"]["id"] > 0


def test_login_with_wrong_password_returns_401(client_with_full_stack):
    client = client_with_full_stack
    response = _login(client, TEST_SEED_ADMIN_EMAIL, "definitely-wrong")
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid credentials"


def test_login_with_unknown_user_returns_401(client_with_full_stack):
    client = client_with_full_stack
    response = _login(client, "nobody@example.com", "irrelevant")
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid credentials"


def test_login_payload_validation_rejects_short_password(client_with_full_stack):
    client = client_with_full_stack
    response = client.post(
        "/api/auth/login",
        json={"email": TEST_SEED_ADMIN_EMAIL, "password": ""},
    )
    assert response.status_code == 422


def test_login_payload_validation_rejects_long_password(client_with_full_stack):
    client = client_with_full_stack
    response = client.post(
        "/api/auth/login",
        json={"email": TEST_SEED_ADMIN_EMAIL, "password": "x" * 73},
    )
    assert response.status_code == 422


def test_login_payload_validation_rejects_malformed_email(client_with_full_stack):
    client = client_with_full_stack
    response = _login(client, "not-an-email", TEST_SEED_ADMIN_PASSWORD)
    assert response.status_code == 422


def test_login_response_role_equals_ROLE_ADMIN(client_with_full_stack):
    client = client_with_full_stack
    response = _login(client, TEST_SEED_ADMIN_EMAIL, TEST_SEED_ADMIN_PASSWORD)
    assert response.status_code == 200
    assert response.json()["user"]["role"] == ROLE_ADMIN


def test_me_with_valid_token_returns_user(client_with_full_stack):
    client = client_with_full_stack
    token = _login(client, TEST_SEED_ADMIN_EMAIL, TEST_SEED_ADMIN_PASSWORD).json()[
        "token"
    ]
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == TEST_SEED_ADMIN_EMAIL
    assert response.json()["role"] == ROLE_ADMIN


def test_me_without_token_returns_401(client_with_full_stack):
    client = client_with_full_stack
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_unknown_token_returns_401(client_with_full_stack):
    client = client_with_full_stack
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


def test_logout_revokes_token(client_with_full_stack):
    client = client_with_full_stack
    token = _login(client, TEST_SEED_ADMIN_EMAIL, TEST_SEED_ADMIN_PASSWORD).json()[
        "token"
    ]
    me_ok = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_ok.status_code == 200

    logout = client.post(
        "/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    assert logout.status_code == 204

    me_after = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_after.status_code == 401

    replay = client.post(
        "/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    assert replay.status_code == 401


def test_logout_without_token_returns_401(client_with_full_stack):
    client = client_with_full_stack
    response = client.post("/api/auth/logout")
    assert response.status_code == 401


def test_seed_user_has_admin_role(db_pool_seeded):
    pool = db_pool_seeded
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email, role FROM app_user WHERE email = %s",
                (TEST_SEED_ADMIN_EMAIL,),
            )
            row = cur.fetchone()
    assert row is not None
    email, role = row
    assert email == TEST_SEED_ADMIN_EMAIL
    assert role == ROLE_ADMIN
