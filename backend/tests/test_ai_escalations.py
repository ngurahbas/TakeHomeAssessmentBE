from __future__ import annotations

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    TEST_SEED_ADMIN_EMAIL,
    TEST_SEED_ADMIN_PASSWORD,
    TEST_SECONDARY_USER_EMAIL,
    TEST_SECONDARY_USER_PASSWORD,
)


pytestmark = pytest.mark.usefixtures("client_with_full_stack")


@pytest.fixture(autouse=True)
def _truncate_state(db_pool_seeded):
    """Per-test isolation: clear escalations, public chat messages/sessions.

    Mirrors the truncation in tests/test_escalation.py:13.
    """
    with db_pool_seeded.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE ai_escalation RESTART IDENTITY")
            cur.execute("TRUNCATE TABLE public_chat_message CASCADE")
            cur.execute("TRUNCATE TABLE public_chat_session CASCADE")
    yield


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login_admin(client: TestClient) -> str:
    response = client.post(
        "/api/auth/login",
        json={
            "email": TEST_SEED_ADMIN_EMAIL,
            "password": TEST_SEED_ADMIN_PASSWORD,
        },
    )
    assert response.status_code == 200
    return response.json()["token"]


def _seed_escalation(
    pool,
    *,
    intention: str,
    message_count: int = 0,
) -> str:
    """Insert a public_chat_session + N messages + 1 escalation. Return chat_id."""
    from app.public_chat import repository

    with pool.connection() as conn:
        chat_id = repository.create_session(conn)
        for i in range(message_count):
            role = "user" if i % 2 == 0 else "assistant"
            repository.append_message(
                conn,
                session_id=chat_id,
                role=role,
                content=f"msg {i}",
            )
        repository.create_escalation(
            conn, public_chat_id=chat_id, user_intention=intention
        )
    return chat_id


# ---------------------------------------------------------------------------
# Auth gating
# ---------------------------------------------------------------------------


def test_list_without_token_returns_401(client_with_full_stack):
    response = client_with_full_stack.get("/api/ai-escalations")
    assert response.status_code == 401


def test_list_with_non_admin_token_returns_403(
    client_with_full_stack, non_admin_token
):
    response = client_with_full_stack.get(
        "/api/ai-escalations", headers=_auth(non_admin_token)
    )
    assert response.status_code == 403


def test_get_without_token_returns_401(client_with_full_stack):
    response = client_with_full_stack.get("/api/ai-escalations/1")
    assert response.status_code == 401


def test_get_with_non_admin_token_returns_403(
    client_with_full_stack, non_admin_token
):
    response = client_with_full_stack.get(
        "/api/ai-escalations/1", headers=_auth(non_admin_token)
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Empty list
# ---------------------------------------------------------------------------


def test_list_empty_returns_total_zero(client_with_full_stack, admin_token):
    response = client_with_full_stack.get(
        "/api/ai-escalations", headers=_auth(admin_token)
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {"items": [], "total": 0, "limit": 20, "offset": 0}


# ---------------------------------------------------------------------------
# List happy path
# ---------------------------------------------------------------------------


def test_list_returns_rows_newest_first_with_message_count(
    client_with_full_stack, db_pool_seeded, admin_token
):
    pool = db_pool_seeded
    chat_old = _seed_escalation(pool, intention="oldest", message_count=1)
    chat_mid = _seed_escalation(pool, intention="middle", message_count=3)
    chat_new = _seed_escalation(pool, intention="newest", message_count=0)

    response = client_with_full_stack.get(
        "/api/ai-escalations", headers=_auth(admin_token)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert [item["user_intention"] for item in body["items"]] == [
        "newest",
        "middle",
        "oldest",
    ]
    assert [item["message_count"] for item in body["items"]] == [0, 3, 1]
    assert [item["public_chat_id"] for item in body["items"]] == [
        chat_new,
        chat_mid,
        chat_old,
    ]
    # ids are sequential BIGSERIAL 1, 2, 3
    assert [item["id"] for item in body["items"]] == [3, 2, 1]
    for item in body["items"]:
        assert re.match(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
            item["created_at"],
        )


def test_list_pagination_respects_limit_and_offset(
    client_with_full_stack, db_pool_seeded, admin_token
):
    pool = db_pool_seeded
    for i in range(3):
        _seed_escalation(pool, intention=f"e{i}")

    page1 = client_with_full_stack.get(
        "/api/ai-escalations?limit=2&offset=0",
        headers=_auth(admin_token),
    )
    assert page1.status_code == 200
    body1 = page1.json()
    assert body1["total"] == 3
    assert body1["limit"] == 2
    assert body1["offset"] == 0
    assert len(body1["items"]) == 2
    # Newest-first: e2, e1
    assert [item["user_intention"] for item in body1["items"]] == ["e2", "e1"]

    page2 = client_with_full_stack.get(
        "/api/ai-escalations?limit=2&offset=2",
        headers=_auth(admin_token),
    )
    assert page2.status_code == 200
    body2 = page2.json()
    assert body2["total"] == 3
    assert body2["offset"] == 2
    assert [item["user_intention"] for item in body2["items"]] == ["e0"]


# ---------------------------------------------------------------------------
# Param validation
# ---------------------------------------------------------------------------


def test_list_with_limit_zero_returns_422(client_with_full_stack, admin_token):
    response = client_with_full_stack.get(
        "/api/ai-escalations?limit=0", headers=_auth(admin_token)
    )
    assert response.status_code == 422


def test_list_with_limit_too_high_returns_422(
    client_with_full_stack, admin_token
):
    response = client_with_full_stack.get(
        "/api/ai-escalations?limit=999", headers=_auth(admin_token)
    )
    assert response.status_code == 422


def test_list_with_negative_offset_returns_422(
    client_with_full_stack, admin_token
):
    response = client_with_full_stack.get(
        "/api/ai-escalations?offset=-1", headers=_auth(admin_token)
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


def test_get_detail_returns_escalation_with_session_messages(
    client_with_full_stack, db_pool_seeded, admin_token
):
    from app.public_chat import repository

    pool = db_pool_seeded
    with pool.connection() as conn:
        chat_id = repository.create_session(conn)
        repository.append_message(
            conn, session_id=chat_id, role="user", content="hi"
        )
        repository.append_message(
            conn,
            session_id=chat_id,
            role="assistant",
            content="hello, how can I help?",
        )
        escalation = repository.create_escalation(
            conn,
            public_chat_id=chat_id,
            user_intention="wants to book a viewing",
        )
        escalation_id = escalation["id"]

    response = client_with_full_stack.get(
        f"/api/ai-escalations/{escalation_id}",
        headers=_auth(admin_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == escalation_id
    assert body["public_chat_id"] == chat_id
    assert body["user_intention"] == "wants to book a viewing"
    assert "created_at" in body
    assert body["session"]["id"] == chat_id
    assert len(body["session"]["messages"]) == 2
    assert body["session"]["messages"][0]["role"] == "user"
    assert body["session"]["messages"][0]["content"] == "hi"
    assert body["session"]["messages"][1]["role"] == "assistant"


def test_get_detail_unknown_id_returns_404(
    client_with_full_stack, admin_token
):
    response = client_with_full_stack.get(
        "/api/ai-escalations/99999", headers=_auth(admin_token)
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "escalation not found"


def test_get_detail_with_zero_id_returns_422(
    client_with_full_stack, admin_token
):
    response = client_with_full_stack.get(
        "/api/ai-escalations/0", headers=_auth(admin_token)
    )
    assert response.status_code == 422


def test_get_detail_with_non_int_id_returns_422(
    client_with_full_stack, admin_token
):
    response = client_with_full_stack.get(
        "/api/ai-escalations/abc", headers=_auth(admin_token)
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Cascade
# ---------------------------------------------------------------------------


def test_deleting_session_cascades_to_escalation(
    client_with_full_stack, db_pool_seeded, admin_token
):
    """Deleting a public_chat_session removes its escalation via FK CASCADE."""
    from app.public_chat import repository

    pool = db_pool_seeded
    with pool.connection() as conn:
        chat_id = repository.create_session(conn)
        repository.create_escalation(
            conn, public_chat_id=chat_id, user_intention="will cascade"
        )

    list_before = client_with_full_stack.get(
        "/api/ai-escalations", headers=_auth(admin_token)
    )
    assert list_before.json()["total"] == 1

    with pool.connection() as conn:
        repository.delete_session(conn, session_id=chat_id)

    list_after = client_with_full_stack.get(
        "/api/ai-escalations", headers=_auth(admin_token)
    )
    assert list_after.json()["total"] == 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
