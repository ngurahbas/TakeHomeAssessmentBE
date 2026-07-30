import json

import httpx
import pytest

pytestmark = pytest.mark.usefixtures("client_with_full_stack")


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_conversation(client, token, *, title: str | None = None):
    body: dict = {}
    if title is not None:
        body["title"] = title
    response = client.post(
        "/api/chat/conversations", json=body, headers=_auth(token)
    )
    assert response.status_code == 201, response.text
    return response.json()


def _llama_cpp_payload(content: str, *, reasoning: str | None = None) -> dict:
    """Snapshot of the real llama.cpp /v1/chat/completions response,
    captured 2026-07-30 from http://localhost:1234/v1
    (unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL). Update if the upstream
    contract changes."""
    message: dict = {"role": "assistant", "content": content}
    if reasoning is not None:
        message["reasoning_content"] = reasoning
    return {
        "id": "chatcmpl-TEST",
        "object": "chat.completion",
        "created": 1785399003,
        "model": "unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL",
        "system_fingerprint": "b9598-fdc3db9b6",
        "choices": [
            {"index": 0, "finish_reason": "stop", "message": message}
        ],
        "usage": {
            "prompt_tokens": 25,
            "completion_tokens": 10,
            "total_tokens": 35,
            "prompt_tokens_details": {"cached_tokens": 0},
        },
    }


def _patch_llm(monkeypatch, *, contents: list[str], reasoning: str | None = None):
    """Patch the httpx transport used by app.chat.llm so the real complete()
    + _extract_content() run against real-shape llama.cpp responses. Returns
    a list (one entry per outbound call) of the message arrays the service
    sent to the LLM."""
    sent: list[list[dict]] = []
    payloads_iter = iter(
        _llama_cpp_payload(c, reasoning=reasoning) for c in contents
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body["messages"])
        return httpx.Response(200, json=next(payloads_iter))

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def patched_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr("app.chat.llm.httpx.Client", patched_client)
    return sent


def test_unauthenticated_requests_are_rejected(client):
    response = client.get("/api/chat/conversations")
    assert response.status_code == 401


def test_create_and_list_conversation(client, non_admin_token):
    created = _create_conversation(
        client, non_admin_token, title="Looking in Berlin"
    )
    assert created["title"] == "Looking in Berlin"
    assert created["messages"] == []

    response = client.get(
        "/api/chat/conversations", headers=_auth(non_admin_token)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == created["id"]
    assert body["items"][0]["title"] == "Looking in Berlin"
    assert body["items"][0]["message_count"] == 0


def test_create_conversation_strips_blank_title(client, non_admin_token):
    created = _create_conversation(client, non_admin_token, title="   ")
    assert created["title"] is None


def test_get_conversation_includes_messages(client, non_admin_token, monkeypatch):
    sent = _patch_llm(monkeypatch, contents=["hello there"])

    conv = _create_conversation(client, non_admin_token, title="Chat 1")
    response = client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        json={"content": "hi"},
        headers=_auth(non_admin_token),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["conversation_id"] == conv["id"]
    assert payload["user_message"]["role"] == "user"
    assert payload["user_message"]["content"] == "hi"
    assert payload["assistant_message"]["role"] == "assistant"
    assert payload["assistant_message"]["content"] == "hello there"

    fetched = client.get(
        f"/api/chat/conversations/{conv['id']}", headers=_auth(non_admin_token)
    )
    assert fetched.status_code == 200
    body = fetched.json()
    assert len(body["messages"]) == 2
    assert [m["role"] for m in body["messages"]] == ["user", "assistant"]
    assert body["messages"][0]["content"] == "hi"
    assert body["messages"][1]["content"] == "hello there"

    assert len(sent) == 1
    outbound = sent[0]
    assert outbound[0]["role"] == "system"
    assert outbound[-1] == {"role": "user", "content": "hi"}
    history_roles = [m["role"] for m in outbound[1:-1]]
    assert history_roles == ["user"]


def test_conversation_history_accumulates(client, non_admin_token, monkeypatch):
    sent = _patch_llm(
        monkeypatch, contents=["first reply", "second reply", "third reply"]
    )

    conv = _create_conversation(client, non_admin_token)
    for content in ("one", "two", "three"):
        response = client.post(
            f"/api/chat/conversations/{conv['id']}/messages",
            json={"content": content},
            headers=_auth(non_admin_token),
        )
        assert response.status_code == 200

    fetched = client.get(
        f"/api/chat/conversations/{conv['id']}", headers=_auth(non_admin_token)
    )
    body = fetched.json()
    assert [m["content"] for m in body["messages"]] == [
        "one",
        "first reply",
        "two",
        "second reply",
        "three",
        "third reply",
    ]

    listed = client.get(
        "/api/chat/conversations", headers=_auth(non_admin_token)
    ).json()
    assert listed["items"][0]["message_count"] == 6

    assert len(sent) == 3
    assert sent[0][-1] == {"role": "user", "content": "one"}
    assert sent[1][-1] == {"role": "user", "content": "two"}
    assert sent[2][-1] == {"role": "user", "content": "three"}


def test_reasoning_content_is_not_persisted(
    client, non_admin_token, monkeypatch
):
    sent = _patch_llm(
        monkeypatch,
        contents=["PONG"],
        reasoning="Step 1. Reason about PONG. Step 2. Output PONG.",
    )

    conv = _create_conversation(client, non_admin_token, title="reasoning")
    response = client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        json={"content": "Reply with exactly: PONG"},
        headers=_auth(non_admin_token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["assistant_message"]["content"] == "PONG"
    assert "Reason" not in body["assistant_message"]["content"]

    fetched = client.get(
        f"/api/chat/conversations/{conv['id']}", headers=_auth(non_admin_token)
    ).json()
    persisted = fetched["messages"]
    assert len(persisted) == 2
    assert persisted[1]["role"] == "assistant"
    assert persisted[1]["content"] == "PONG"
    assert "Step 1" not in persisted[1]["content"]

    assert len(sent) == 1


def test_message_validation_rejects_empty_content(client, non_admin_token, monkeypatch):
    _patch_llm(monkeypatch, contents=["ok"])
    conv = _create_conversation(client, non_admin_token)
    response = client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        json={"content": ""},
        headers=_auth(non_admin_token),
    )
    assert response.status_code == 422


def test_message_validation_rejects_oversize_content(
    client, non_admin_token, monkeypatch
):
    from app.settings import get_settings

    _patch_llm(monkeypatch, contents=["ok"])
    settings = get_settings()
    conv = _create_conversation(client, non_admin_token)
    response = client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        json={"content": "x" * (settings.llm_max_input_chars + 1)},
        headers=_auth(non_admin_token),
    )
    assert response.status_code == 400


def test_ownership_isolation_on_get(client, non_admin_token, chat_other_token):
    conv = _create_conversation(client, non_admin_token, title="mine")
    response = client.get(
        f"/api/chat/conversations/{conv['id']}",
        headers=_auth(chat_other_token),
    )
    assert response.status_code == 404

    response = client.get(
        f"/api/chat/conversations/{conv['id']}",
        headers=_auth(non_admin_token),
    )
    assert response.status_code == 200


def test_ownership_isolation_on_list(client, non_admin_token, chat_other_token):
    _create_conversation(client, non_admin_token, title="alpha-iso")
    _create_conversation(client, chat_other_token, title="beta-iso")
    mine = client.get(
        "/api/chat/conversations", headers=_auth(non_admin_token)
    ).json()
    other = client.get(
        "/api/chat/conversations", headers=_auth(chat_other_token)
    ).json()
    mine_titles = {c["title"] for c in mine["items"]}
    other_titles = {c["title"] for c in other["items"]}
    assert "alpha-iso" in mine_titles
    assert "alpha-iso" not in other_titles
    assert "beta-iso" in other_titles
    assert "beta-iso" not in mine_titles
    assert all(c["id"] for c in mine["items"] + other["items"])
    mine_ids = {c["id"] for c in mine["items"]}
    other_ids = {c["id"] for c in other["items"]}
    assert mine_ids.isdisjoint(other_ids)


def test_ownership_isolation_on_delete(client, non_admin_token, chat_other_token):
    conv = _create_conversation(client, non_admin_token)
    response = client.delete(
        f"/api/chat/conversations/{conv['id']}",
        headers=_auth(chat_other_token),
    )
    assert response.status_code == 404
    response = client.delete(
        f"/api/chat/conversations/{conv['id']}",
        headers=_auth(non_admin_token),
    )
    assert response.status_code == 204
    response = client.get(
        f"/api/chat/conversations/{conv['id']}",
        headers=_auth(non_admin_token),
    )
    assert response.status_code == 404


def test_message_to_other_users_conversation_is_404(
    client, non_admin_token, chat_other_token, monkeypatch
):
    _patch_llm(monkeypatch, contents=["ok"])
    conv = _create_conversation(client, non_admin_token)
    response = client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        json={"content": "sneak in"},
        headers=_auth(chat_other_token),
    )
    assert response.status_code == 404


def test_llm_failure_returns_502(client, non_admin_token, monkeypatch):
    from app.chat import llm as chat_llm
    from app.chat import service

    def boom(messages, *, settings=None, tools=None, pool=None, public_chat_id=None):
        raise chat_llm.LLMError("upstream is sad")

    monkeypatch.setattr(service.llm, "complete", boom)
    conv = _create_conversation(client, non_admin_token)
    response = client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        json={"content": "hi"},
        headers=_auth(non_admin_token),
    )
    assert response.status_code == 502

    fetched = client.get(
        f"/api/chat/conversations/{conv['id']}", headers=_auth(non_admin_token)
    ).json()
    assert [m["role"] for m in fetched["messages"]] == ["user"]
    assert fetched["messages"][0]["content"] == "hi"
