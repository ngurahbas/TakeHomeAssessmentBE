import json
import re
import uuid

import httpx
import pytest

pytestmark = pytest.mark.usefixtures("client_with_full_stack")


def _llama_cpp_payload(content: str, *, reasoning: str | None = None) -> dict:
    """Real llama.cpp /v1/chat/completions response shape captured 2026-07-30
    from http://localhost:1234/v1 (unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL)."""
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
    the list of outbound messages arrays (one per call)."""
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


def test_first_message_creates_session(client, monkeypatch):
    sent = _patch_llm(monkeypatch, contents=["Hello from the LLM"])

    response = client.post(
        "/public/ai-chat",
        json={"content": "hi"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    chat_id = body["chat_id"]
    uuid.UUID(chat_id)
    assert body["user_message"]["role"] == "user"
    assert body["user_message"]["content"] == "hi"
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["content"] == "Hello from the LLM"

    assert len(sent) == 1
    outbound = sent[0]
    assert outbound[0]["role"] == "system"
    assert outbound[-1] == {"role": "user", "content": "hi"}


def test_subsequent_messages_use_existing_chat_id(client, monkeypatch):
    sent = _patch_llm(monkeypatch, contents=["first answer", "second answer"])

    first = client.post("/public/ai-chat", json={"content": "first?"}).json()
    chat_id = first["chat_id"]
    second = client.post(
        "/public/ai-chat", json={"chat_id": chat_id, "content": "second?"}
    ).json()
    assert second["chat_id"] == chat_id
    assert second["user_message"]["content"] == "second?"
    assert second["assistant_message"]["content"] == "second answer"

    assert len(sent) == 2
    assert sent[0][-1] == {"role": "user", "content": "first?"}
    assert sent[1] == [
        {"role": "system", "content": sent[1][0]["content"]},
        {"role": "user", "content": "first?"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": "second?"},
    ]


def test_get_session_returns_full_history(client, monkeypatch):
    _patch_llm(monkeypatch, contents=["first answer", "second answer"])

    first = client.post("/public/ai-chat", json={"content": "first?"}).json()
    client.post(
        "/public/ai-chat",
        json={"chat_id": first["chat_id"], "content": "second?"},
    )

    response = client.get(f"/public/ai-chat/{first['chat_id']}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == first["chat_id"]
    assert [m["role"] for m in body["messages"]] == [
        "user", "assistant", "user", "assistant"
    ]
    assert [m["content"] for m in body["messages"]] == [
        "first?", "first answer", "second?", "second answer"
    ]


def test_delete_session_clears_messages(client, monkeypatch):
    _patch_llm(monkeypatch, contents=["ok"])
    created = client.post("/public/ai-chat", json={"content": "hi"}).json()

    response = client.delete(f"/public/ai-chat/{created['chat_id']}")
    assert response.status_code == 204

    response = client.get(f"/public/ai-chat/{created['chat_id']}")
    assert response.status_code == 404


def test_unknown_chat_id_returns_404(client, monkeypatch):
    _patch_llm(monkeypatch, contents=["ok"])
    missing = str(uuid.uuid4())
    response = client.post(
        "/public/ai-chat", json={"chat_id": missing, "content": "hi"}
    )
    assert response.status_code == 404


def test_get_unknown_chat_id_returns_404(client):
    response = client.get(f"/public/ai-chat/{uuid.uuid4()}")
    assert response.status_code == 404


def test_chat_id_must_be_uuid(client, monkeypatch):
    _patch_llm(monkeypatch, contents=["ok"])
    response = client.post(
        "/public/ai-chat", json={"chat_id": "not-a-uuid", "content": "hi"}
    )
    assert response.status_code == 422


def test_post_message_ignores_reasoning_content(client, monkeypatch):
    _patch_llm(
        monkeypatch,
        contents=["PONG"],
        reasoning="Step 1. Think about PONG. Step 2. Output PONG.",
    )

    response = client.post(
        "/public/ai-chat",
        json={"content": "Reply with: PONG"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["assistant_message"]["content"] == "PONG"
    assert "Step" not in body["assistant_message"]["content"]


def test_endpoint_is_unauthenticated(client, monkeypatch):
    _patch_llm(monkeypatch, contents=["ok"])
    response = client.post("/public/ai-chat", json={"content": "hi"})
    assert response.status_code == 200
    response = client.get(f"/public/ai-chat/{uuid.uuid4()}")
    assert response.status_code == 404


def test_post_message_rejects_empty_content(client):
    response = client.post("/public/ai-chat", json={"content": ""})
    assert response.status_code == 422


def test_post_message_rejects_oversize_content(client):
    response = client.post(
        "/public/ai-chat", json={"content": "x" * 4001}
    )
    assert response.status_code == 422


def test_llm_failure_returns_502_with_chat_id(client, monkeypatch):
    from app.chat import llm as chat_llm
    from app.public_chat import routes

    def boom(messages, *, settings=None, tools=None, pool=None):
        raise chat_llm.LLMError("upstream is sad")

    monkeypatch.setattr(routes, "complete", boom)
    response = client.post("/public/ai-chat", json={"content": "hi"})
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "llm error" in detail["message"]
    chat_id = detail["chat_id"]
    assert _UUID_RE.match(chat_id)

    # Session exists with the user message but no assistant reply —
    # the next turn can retry against the same chat_id.
    fetch = client.get(f"/public/ai-chat/{chat_id}")
    assert fetch.status_code == 200
    body = fetch.json()
    assert body["id"] == chat_id
    assert [m["role"] for m in body["messages"]] == ["user"]
    assert body["messages"][0]["content"] == "hi"


_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def test_chat_id_is_uuid_format(client, monkeypatch):
    _patch_llm(monkeypatch, contents=["ok"])
    response = client.post("/public/ai-chat", json={"content": "hi"})
    assert _UUID_RE.match(response.json()["chat_id"])


def _tool_call_payload(tool_name: str, arguments: str) -> dict:
    return {
        "id": "chatcmpl-TOOL",
        "object": "chat.completion",
        "created": 1785399003,
        "model": "unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL",
        "choices": [
            {
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_test_001",
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": arguments,
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {
            "prompt_tokens": 25,
            "completion_tokens": 10,
            "total_tokens": 35,
            "prompt_tokens_details": {"cached_tokens": 0},
        },
    }


def test_say_nice_thing_tool_is_called_when_user_is_sad(client, monkeypatch):
    payloads = [
        _tool_call_payload("SayNiceThing", "{}"),
        _llama_cpp_payload("You are wonderful!"),
    ]
    sent: list[list[dict]] = []
    payloads_iter = iter(payloads)

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

    response = client.post(
        "/public/ai-chat",
        json={"content": "I am sad"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["assistant_message"]["content"] == "You are wonderful!"

    assert len(sent) == 2
    first_call_messages = sent[0]
    second_call_messages = sent[1]

    assert "I am sad" in first_call_messages[-1]["content"]

    assert "tool" in [m["role"] for m in second_call_messages]
    tool_msgs = [m for m in second_call_messages if m["role"] == "tool"]
    assert len(tool_msgs) == 1
    tool_content = tool_msgs[0]["content"]
    assert isinstance(tool_content, str)
    assert len(tool_content) > 0


def test_say_nice_thing_tool_is_passed_in_request(client, monkeypatch):
    sent: list[list[dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        return httpx.Response(200, json=_llama_cpp_payload("Hello!"))

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def patched_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr("app.chat.llm.httpx.Client", patched_client)

    response = client.post("/public/ai-chat", json={"content": "hi"})
    assert response.status_code == 200, response.text

    assert len(sent) == 1
    tools = sent[0].get("tools")
    assert tools is not None
    names = [t["function"]["name"] for t in tools]
    assert "SayNiceThing" in names


def test_system_prompt_mentions_say_nice_thing(client, monkeypatch):
    sent: list[list[dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        return httpx.Response(200, json=_llama_cpp_payload("Hello!"))

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def patched_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr("app.chat.llm.httpx.Client", patched_client)

    response = client.post("/public/ai-chat", json={"content": "hi"})
    assert response.status_code == 200, response.text

    assert len(sent) == 1
    system_msg = sent[0]["messages"][0]
    assert system_msg["role"] == "system"
    assert "SayNiceThing" in system_msg["content"]
    assert "only tools" in system_msg["content"].lower()
    assert "Do not invent" in system_msg["content"]
