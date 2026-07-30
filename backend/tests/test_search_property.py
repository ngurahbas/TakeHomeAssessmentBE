from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.usefixtures("client_with_full_stack")


@pytest.fixture(autouse=True)
def _truncate_property(db_pool_seeded):
    """Wipe the `property` table before each test so cross-test leakage
    from the session-scoped Postgres container cannot poison counts or
    city-filter assertions."""
    with db_pool_seeded.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE property RESTART IDENTITY")
    yield


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_conversation(client, token):
    response = client.post(
        "/api/chat/conversations", json={}, headers=_auth(token)
    )
    assert response.status_code == 201, response.text
    return response.json()


def _llama_cpp_payload(content: str, *, reasoning: str | None = None) -> dict:
    """Snapshot of the real llama.cpp /v1/chat/completions response,
    captured 2026-07-30 from http://localhost:1234/v1
    (unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL)."""
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


def _tool_call_payload(
    tool_name: str, arguments: str, *, tool_call_id: str = "call_search_001"
) -> dict:
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
                            "id": tool_call_id,
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


class _ScriptedTransport:
    """Plays a fixed list of payloads back in order, one per outbound call.
    Mirrors the httpx.MockTransport pattern in test_public_chat.py but with a
    cleaner queue interface so multi-turn tool-call flows are easy to write."""

    def __init__(self, payloads: list[dict]) -> None:
        self._payloads = list(payloads)
        self.calls: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.calls.append(body)
        if not self._payloads:
            return httpx.Response(
                500, json={"error": "test ran out of scripted payloads"}
            )
        return httpx.Response(200, json=self._payloads.pop(0))

    def close(self) -> None:
        pass

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self(request)


def _patch_llm_with_queue(monkeypatch, payloads: list[dict]) -> _ScriptedTransport:
    transport = _ScriptedTransport(payloads)
    real_client = httpx.Client

    def patched_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr("app.chat.llm.httpx.Client", patched_client)
    return transport


def _make_property(
    client,
    admin_token: str,
    *,
    city: str,
    title: str,
    status: str = "AVAILABLE",
    listing_type: str = "RENT",
    property_type: str = "APARTMENT",
    price_amount: float = 1500.0,
    bedrooms: int = 1,
    description: str = "A property used by the test suite.",
) -> dict:
    payload = {
        "title": title,
        "description": description,
        "property_type": property_type,
        "listing_type": listing_type,
        "price_amount": price_amount,
        "price_currency": "USD",
        "bedrooms": bedrooms,
        "bathrooms": 1,
        "area_sqm": 60.0,
        "address_line": f"1 {title} Way",
        "city": city,
        "district": "Test District",
        "postal_code": "00000",
        "country_code": "US",
        "status": status,
        "amenities": ["parking"],
        "images": [],
    }
    response = client.post(
        "/api/properties", json=payload, headers=_auth(admin_token)
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_search_property_tool_is_passed_in_request(client, monkeypatch):
    transport = _patch_llm_with_queue(monkeypatch, [_llama_cpp_payload("ok")])

    response = client.post("/public/ai-chat", json={"content": "hi"})
    assert response.status_code == 200, response.text

    assert len(transport.calls) == 1
    tools = transport.calls[0].get("tools")
    assert tools is not None
    names = sorted(t["function"]["name"] for t in tools)
    assert names == ["SayNiceThing", "SearchProperty"]
    search = next(t for t in tools if t["function"]["name"] == "SearchProperty")
    params = search["function"]["parameters"]
    assert params["type"] == "object"
    props = params["properties"]
    assert {"q", "city", "listing_type", "property_type",
            "min_price", "max_price", "bedrooms", "max_results"} <= set(props)
    assert props["listing_type"]["enum"] == ["SALE", "RENT"]
    assert "AVAILABLE" not in params["properties"]
    assert "status" not in params["properties"]


def test_search_property_called_with_city_returns_matching_rows(
    client, admin_token, monkeypatch
):
    _make_property(client, admin_token, city="Boston", title="Boston Loft")
    _make_property(
        client, admin_token, city="Boston", title="Boston Townhouse",
        price_amount=2800.0, bedrooms=2,
    )
    _make_property(client, admin_token, city="Seattle", title="Seattle Studio")

    transport = _patch_llm_with_queue(
        monkeypatch,
        [
            _tool_call_payload("SearchProperty", json.dumps({"city": "Boston"})),
            _llama_cpp_payload("I found 2 Boston listings."),
        ],
    )

    response = client.post(
        "/public/ai-chat", json={"content": "Show me rentals in Boston"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["assistant_message"]["content"] == "I found 2 Boston listings."

    assert len(transport.calls) == 2
    tool_message = next(
        m for m in transport.calls[1]["messages"] if m["role"] == "tool"
    )
    payload = json.loads(tool_message["content"])
    assert isinstance(payload, dict) and "result" in payload
    results = payload["result"]
    assert isinstance(results, list)
    assert len(results) == 2
    titles = {r["title"] for r in results}
    assert titles == {"Boston Loft", "Boston Townhouse"}
    assert all(r["city"] == "Boston" for r in results)


def test_search_property_filters_by_price_and_bedrooms(
    client, admin_token, monkeypatch
):
    _make_property(
        client, admin_token, city="Boston", title="Cheap Studio",
        price_amount=900.0, bedrooms=0, property_type="STUDIO",
    )
    _make_property(
        client, admin_token, city="Boston", title="Mid Loft",
        price_amount=1800.0, bedrooms=1,
    )
    _make_property(
        client, admin_token, city="Boston", title="Big House",
        price_amount=4500.0, bedrooms=4, property_type="HOUSE",
    )

    transport = _patch_llm_with_queue(
        monkeypatch,
        [
            _tool_call_payload(
                "SearchProperty",
                json.dumps(
                    {
                        "city": "Boston",
                        "min_price": 1000,
                        "max_price": 3000,
                        "bedrooms": 1,
                    }
                ),
            ),
            _llama_cpp_payload("One match."),
        ],
    )

    response = client.post(
        "/public/ai-chat", json={"content": "1BR in Boston under 3000"}
    )
    assert response.status_code == 200, response.text

    tool_message = next(
        m for m in transport.calls[1]["messages"] if m["role"] == "tool"
    )
    results = json.loads(tool_message["content"])["result"]
    assert [r["title"] for r in results] == ["Mid Loft"]


def test_search_property_filters_by_text_q(
    client, admin_token, monkeypatch
):
    _make_property(
        client, admin_token, city="Boston",
        title="Sunny Garden Apartment", description="A lovely garden retreat.",
    )
    _make_property(
        client, admin_token, city="Boston",
        title="Downtown Loft", description="Near the harbor, very urban.",
    )

    transport = _patch_llm_with_queue(
        monkeypatch,
        [
            _tool_call_payload(
                "SearchProperty", json.dumps({"q": "garden"})
            ),
            _llama_cpp_payload("Found the garden apartment."),
        ],
    )

    response = client.post(
        "/public/ai-chat", json={"content": "I want something with a garden"}
    )
    assert response.status_code == 200, response.text

    tool_message = next(
        m for m in transport.calls[1]["messages"] if m["role"] == "tool"
    )
    results = json.loads(tool_message["content"])["result"]
    assert [r["title"] for r in results] == ["Sunny Garden Apartment"]


def test_search_property_only_returns_available(
    client, admin_token, monkeypatch
):
    _make_property(
        client, admin_token, city="Boston", title="Available Loft",
        status="AVAILABLE",
    )
    _make_property(
        client, admin_token, city="Boston", title="Sold Townhouse",
        status="SOLD",
    )
    _make_property(
        client, admin_token, city="Boston", title="Rented Flat",
        status="RENTED",
    )

    transport = _patch_llm_with_queue(
        monkeypatch,
        [
            _tool_call_payload("SearchProperty", json.dumps({"city": "Boston"})),
            _llama_cpp_payload("Only 1 is available."),
        ],
    )

    response = client.post(
        "/public/ai-chat", json={"content": "Show me anything in Boston"}
    )
    assert response.status_code == 200, response.text

    tool_message = next(
        m for m in transport.calls[1]["messages"] if m["role"] == "tool"
    )
    results = json.loads(tool_message["content"])["result"]
    assert [r["title"] for r in results] == ["Available Loft"]


def test_search_property_empty_result_is_handled(
    client, admin_token, monkeypatch
):
    transport = _patch_llm_with_queue(
        monkeypatch,
        [
            _tool_call_payload("SearchProperty", json.dumps({"city": "Nowhere"})),
            _llama_cpp_payload("I could not find any listings there."),
        ],
    )

    response = client.post(
        "/public/ai-chat", json={"content": "Anything in Nowhere?"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["assistant_message"]["content"] == (
        "I could not find any listings there."
    )

    tool_message = next(
        m for m in transport.calls[1]["messages"] if m["role"] == "tool"
    )
    results = json.loads(tool_message["content"])["result"]
    assert results == []


def test_search_property_caps_max_results(
    client, admin_token, monkeypatch
):
    for i in range(12):
        _make_property(
            client, admin_token, city="Boston",
            title=f"Boston Unit {i:02d}",
        )

    transport = _patch_llm_with_queue(
        monkeypatch,
        [
            _tool_call_payload(
                "SearchProperty", json.dumps({"city": "Boston"})
            ),
            _llama_cpp_payload("Here are 5 of the 12."),
        ],
    )

    response = client.post(
        "/public/ai-chat", json={"content": "Show me all Boston rentals"}
    )
    assert response.status_code == 200, response.text

    tool_message = next(
        m for m in transport.calls[1]["messages"] if m["role"] == "tool"
    )
    results = json.loads(tool_message["content"])["result"]
    assert len(results) == 5
    for row in results:
        assert "images" not in row
        assert "description" not in row
        assert "address_line" not in row
        assert set(row.keys()) == {
            "id", "title", "property_type", "listing_type",
            "price_amount", "price_currency", "city", "country_code",
            "bedrooms", "bathrooms", "area_sqm",
        }


def test_search_property_respects_explicit_max_results(
    client, admin_token, monkeypatch
):
    for i in range(8):
        _make_property(
            client, admin_token, city="Boston",
            title=f"Boston Place {i:02d}",
        )

    transport = _patch_llm_with_queue(
        monkeypatch,
        [
            _tool_call_payload(
                "SearchProperty",
                json.dumps({"city": "Boston", "max_results": 2}),
            ),
            _llama_cpp_payload("Top 2."),
        ],
    )

    response = client.post(
        "/public/ai-chat", json={"content": "Just the top 2 in Boston"}
    )
    assert response.status_code == 200, response.text

    tool_message = next(
        m for m in transport.calls[1]["messages"] if m["role"] == "tool"
    )
    results = json.loads(tool_message["content"])["result"]
    assert len(results) == 2


def test_search_property_max_results_is_clamped(
    client, admin_token, monkeypatch
):
    for i in range(20):
        _make_property(
            client, admin_token, city="Boston",
            title=f"Boston Spot {i:02d}",
        )

    transport = _patch_llm_with_queue(
        monkeypatch,
        [
            _tool_call_payload(
                "SearchProperty",
                json.dumps({"city": "Boston", "max_results": 999}),
            ),
            _llama_cpp_payload("Capped."),
        ],
    )

    response = client.post(
        "/public/ai-chat", json={"content": "Give me everything in Boston"}
    )
    assert response.status_code == 200, response.text

    tool_message = next(
        m for m in transport.calls[1]["messages"] if m["role"] == "tool"
    )
    results = json.loads(tool_message["content"])["result"]
    assert len(results) == 10


def test_search_property_in_authenticated_chat(
    client, admin_token, non_admin_token, monkeypatch
):
    _make_property(client, admin_token, city="Boston", title="Authed Boston Loft")

    transport = _patch_llm_with_queue(
        monkeypatch,
        [
            _tool_call_payload("SearchProperty", json.dumps({"city": "Boston"})),
            _llama_cpp_payload("Found 1."),
        ],
    )

    conv = _create_conversation(client, non_admin_token)
    response = client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        json={"content": "Rentals in Boston?"},
        headers=_auth(non_admin_token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["assistant_message"]["content"] == "Found 1."

    tool_message = next(
        m for m in transport.calls[1]["messages"] if m["role"] == "tool"
    )
    results = json.loads(tool_message["content"])["result"]
    assert [r["title"] for r in results] == ["Authed Boston Loft"]


def test_system_prompt_mentions_search_property(client, monkeypatch):
    transport = _patch_llm_with_queue(monkeypatch, [_llama_cpp_payload("hi")])

    response = client.post("/public/ai-chat", json={"content": "hi"})
    assert response.status_code == 200, response.text

    system_msg = transport.calls[0]["messages"][0]
    assert system_msg["role"] == "system"
    content = system_msg["content"]
    assert "SearchProperty" in content
    assert "AVAILABLE" in content
    assert "city" in content
    assert "listing_type" in content
    assert "property_type" in content
    assert "MANDATORY" in content
    assert "find a villa in Dallas" in content
    assert "SayNiceThing" in content
    assert "I am sad" in content


def test_search_property_with_unknown_tool_is_ignored(client, monkeypatch):
    transport = _patch_llm_with_queue(
        monkeypatch,
        [
            _tool_call_payload("NotARealTool", "{}"),
            _llama_cpp_payload("I do not have that tool."),
        ],
    )

    response = client.post(
        "/public/ai-chat", json={"content": "do something weird"}
    )
    assert response.status_code == 200, response.text

    tool_message = next(
        m for m in transport.calls[1]["messages"] if m["role"] == "tool"
    )
    payload = json.loads(tool_message["content"])
    assert "error" in payload
    assert "NotARealTool" in payload["error"]


def test_search_property_no_filter_returns_available_listings(
    client, admin_token, monkeypatch
):
    _make_property(client, admin_token, city="Boston", title="Boston A")
    _make_property(client, admin_token, city="Boston", title="Boston B")

    transport = _patch_llm_with_queue(
        monkeypatch,
        [
            _tool_call_payload("SearchProperty", "{}"),
            _llama_cpp_payload("Two listings."),
        ],
    )

    response = client.post(
        "/public/ai-chat", json={"content": "Show me some rentals"}
    )
    assert response.status_code == 200, response.text

    tool_message = next(
        m for m in transport.calls[1]["messages"] if m["role"] == "tool"
    )
    results = json.loads(tool_message["content"])["result"]
    assert {r["title"] for r in results} == {"Boston A", "Boston B"}
