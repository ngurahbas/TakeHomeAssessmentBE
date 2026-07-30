from __future__ import annotations

import json
import re
import uuid

import httpx
import pytest

pytestmark = pytest.mark.usefixtures("client_with_full_stack")


@pytest.fixture(autouse=True)
def _truncate_state(db_pool_seeded):
    """Wipe per-test state so cross-test leakage from the session-scoped
    Postgres container cannot poison ai_escalation assertions. We also clear
    public_chat_session because the CASCADE FK from ai_escalation chains
    through it."""
    with db_pool_seeded.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE ai_escalation RESTART IDENTITY")
            cur.execute("TRUNCATE TABLE public_chat_message CASCADE")
            cur.execute("TRUNCATE TABLE public_chat_session CASCADE")
    yield


# ---------------------------------------------------------------------------
# Test doubles (mirrors test_public_chat.py / test_search_property.py shapes)
# ---------------------------------------------------------------------------


def _llama_cpp_payload(content: str, *, reasoning: str | None = None) -> dict:
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
    tool_name: str,
    arguments: str,
    *,
    tool_call_id: str = "call_esc_001",
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

    monkeypatch.setattr("app.public_chat.llm.httpx.Client", patched_client)
    return transport


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------


def test_ai_escalation_table_exists_with_expected_columns(db_pool_seeded):
    with db_pool_seeded.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'ai_escalation'
                ORDER BY ordinal_position
                """
            )
            rows = cur.fetchall()
    cols = {name: (dtype, nullable) for name, dtype, nullable in rows}
    assert set(cols) == {"id", "public_chat_id", "user_intention", "created_at"}
    assert cols["id"][0] == "bigint"
    assert cols["id"][1] == "NO"
    assert cols["public_chat_id"][0] == "uuid"
    assert cols["public_chat_id"][1] == "NO"
    assert cols["user_intention"][0] == "text"
    assert cols["user_intention"][1] == "NO"
    assert cols["created_at"][0] == "timestamp with time zone"
    assert cols["created_at"][1] == "NO"


def test_ai_escalation_has_fk_to_public_chat_session(db_pool_seeded):
    with db_pool_seeded.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    tc.constraint_name,
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    rc.delete_rule
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                    ON ccu.constraint_name = tc.constraint_name
                JOIN information_schema.referential_constraints rc
                    ON rc.constraint_name = tc.constraint_name
                WHERE tc.table_name = 'ai_escalation'
                  AND tc.constraint_type = 'FOREIGN KEY'
                """
            )
            rows = cur.fetchall()
    assert len(rows) == 1
    constraint, table, col, ftable, fcol, delete_rule = rows[0]
    assert table == "ai_escalation"
    assert col == "public_chat_id"
    assert ftable == "public_chat_session"
    assert fcol == "id"
    assert delete_rule == "CASCADE"


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


def test_create_escalation_inserts_and_returns_row(db_pool_seeded):
    from app.public_chat import repository

    with db_pool_seeded.connection() as conn:
        session_id = repository.create_session(conn)
        row = repository.create_escalation(
            conn,
            public_chat_id=session_id,
            user_intention="User wanted help with a mortgage application.",
        )

    assert isinstance(row["id"], int)
    assert row["public_chat_id"] == session_id
    assert row["user_intention"] == "User wanted help with a mortgage application."
    assert re.match(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        row["created_at"],
    )


def test_create_escalation_accepts_empty_intention_at_db_layer(db_pool_seeded):
    """The DB schema (Option A, minimal) only enforces NOT NULL, not
    non-empty. The application layer (execute_escalate_to_human) is what
    rejects empty/whitespace — verified in
    `test_execute_escalate_to_human_requires_user_intention`."""
    from app.public_chat import repository

    with db_pool_seeded.connection() as conn:
        session_id = repository.create_session(conn)
        row = repository.create_escalation(
            conn,
            public_chat_id=session_id,
            user_intention="",
        )
    assert row["user_intention"] == ""


def test_create_escalation_rejects_unknown_chat_id(db_pool_seeded):
    from app.public_chat import repository

    bogus = str(uuid.uuid4())
    with db_pool_seeded.connection() as conn:
        with pytest.raises(Exception):
            repository.create_escalation(
                conn,
                public_chat_id=bogus,
                user_intention="x",
            )


def test_create_escalation_cascades_on_session_delete(db_pool_seeded):
    from app.public_chat import repository

    with db_pool_seeded.connection() as conn:
        session_id = repository.create_session(conn)
        repository.create_escalation(
            conn,
            public_chat_id=session_id,
            user_intention="first",
        )
        repository.create_escalation(
            conn,
            public_chat_id=session_id,
            user_intention="second",
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM ai_escalation WHERE public_chat_id = %s",
                (session_id,),
            )
            assert cur.fetchone()[0] == 2
        repository.delete_session(conn, session_id=session_id)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM ai_escalation WHERE public_chat_id = %s",
                (session_id,),
            )
            assert cur.fetchone()[0] == 0


# ---------------------------------------------------------------------------
# Tool schema & executor
# ---------------------------------------------------------------------------


def test_escalate_to_human_schema_only_exposes_user_intention():
    from app.public_chat.tools import ESCALATE_TO_HUMAN_SCHEMA

    assert ESCALATE_TO_HUMAN_SCHEMA["function"]["name"] == "EscalateToHuman"
    params = ESCALATE_TO_HUMAN_SCHEMA["function"]["parameters"]
    assert set(params["properties"]) == {"user_intention"}
    assert params["required"] == ["user_intention"]
    assert params["properties"]["user_intention"]["type"] == "string"
    # The schema must NOT leak the server-injected public_chat_id.
    assert "public_chat_id" not in params["properties"]


def test_execute_escalate_to_human_requires_user_intention(db_pool_seeded):
    from app.public_chat import tools

    with pytest.raises(ValueError, match="user_intention is required"):
        tools.execute_escalate_to_human(
            pool=db_pool_seeded,
            public_chat_id=str(uuid.uuid4()),
            user_intention=None,
        )
    with pytest.raises(ValueError, match="user_intention is required"):
        tools.execute_escalate_to_human(
            pool=db_pool_seeded,
            public_chat_id=str(uuid.uuid4()),
            user_intention="   ",
        )


def test_execute_escalate_to_human_requires_public_chat_id(db_pool_seeded):
    from app.public_chat import tools

    with pytest.raises(
        ValueError, match="EscalateToHuman requires a public chat session id"
    ):
        tools.execute_escalate_to_human(
            pool=db_pool_seeded,
            public_chat_id=None,
            user_intention="x",
        )


def test_execute_escalate_to_human_requires_pool(db_pool_seeded):
    from app.public_chat import tools

    with pytest.raises(RuntimeError, match="requires a database pool"):
        tools.execute_escalate_to_human(
            pool=None,
            public_chat_id=str(uuid.uuid4()),
            user_intention="x",
        )


def test_execute_escalate_to_human_happy_path(db_pool_seeded):
    from app.public_chat import repository
    from app.public_chat import tools

    with db_pool_seeded.connection() as conn:
        session_id = repository.create_session(conn)

    result = tools.execute_escalate_to_human(
        pool=db_pool_seeded,
        public_chat_id=session_id,
        user_intention="  user wants to negotiate price  ",
    )

    assert isinstance(result["id"], int)
    assert result["public_chat_id"] == session_id
    assert result["user_intention"] == "user wants to negotiate price"
    assert "A human agent will follow up shortly." in result["message"]
    assert re.match(r"^\d{4}-\d{2}-\d{2}", result["created_at"])


def test_execute_escalate_to_human_unknown_session_raises(db_pool_seeded):
    from app.public_chat import tools

    bogus = str(uuid.uuid4())
    with pytest.raises(Exception):
        tools.execute_escalate_to_human(
            pool=db_pool_seeded,
            public_chat_id=bogus,
            user_intention="x",
        )


# ---------------------------------------------------------------------------
# Tool dispatch via /public/ai-chat
# ---------------------------------------------------------------------------


def test_public_chat_tools_include_escalate_to_human(client, monkeypatch):
    transport = _patch_llm_with_queue(monkeypatch, [_llama_cpp_payload("hi")])

    response = client.post("/public/ai-chat", json={"content": "hi"})
    assert response.status_code == 200, response.text

    assert len(transport.calls) == 1
    tools = transport.calls[0].get("tools")
    assert tools is not None
    names = [t["function"]["name"] for t in tools]
    assert "EscalateToHuman" in names
    assert "SayNiceThing" in names
    assert "SearchProperty" in names


def test_public_chat_dispatch_creates_escalation_row(
    client, db_pool_seeded, monkeypatch
):
    payloads = [
        _tool_call_payload(
            "EscalateToHuman",
            json.dumps({"user_intention": "User asked to speak to a human."}),
        ),
        _llama_cpp_payload(
            "I'm connecting you with a human agent now."
        ),
    ]
    _patch_llm_with_queue(monkeypatch, payloads)

    response = client.post(
        "/public/ai-chat",
        json={"content": "I want to talk to a real person"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    chat_id = body["chat_id"]
    assert _UUID_RE.match(chat_id)
    assert body["assistant_message"]["content"] == (
        "I'm connecting you with a human agent now."
    )

    with db_pool_seeded.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT public_chat_id, user_intention
                FROM ai_escalation
                WHERE public_chat_id = %s
                """,
                (chat_id,),
            )
            rows = cur.fetchall()

    assert len(rows) == 1
    assert str(rows[0][0]) == chat_id
    assert rows[0][1] == "User asked to speak to a human."


def test_server_injected_public_chat_id_overrides_llm_value(
    client, db_pool_seeded, monkeypatch
):
    """The LLM might pass any value (or omit) public_chat_id; the server
    must always overwrite it with the real session id from the request."""
    bogus_id = str(uuid.uuid4())
    payloads = [
        _tool_call_payload(
            "EscalateToHuman",
            json.dumps(
                {
                    "public_chat_id": bogus_id,
                    "user_intention": "User asked to speak to a human.",
                }
            ),
        ),
        _llama_cpp_payload("ok"),
    ]
    _patch_llm_with_queue(monkeypatch, payloads)

    response = client.post(
        "/public/ai-chat",
        json={"content": "I want to talk to a real person"},
    )
    assert response.status_code == 200, response.text
    real_chat_id = response.json()["chat_id"]
    assert real_chat_id != bogus_id

    with db_pool_seeded.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT public_chat_id FROM ai_escalation")
            rows = cur.fetchall()

    assert len(rows) == 1
    assert str(rows[0][0]) == real_chat_id
    assert str(rows[0][0]) != bogus_id


def test_unknown_tool_does_not_create_escalation(
    client, db_pool_seeded, monkeypatch
):
    payloads = [
        _tool_call_payload("NotARealTool", "{}"),
        _llama_cpp_payload("ok"),
    ]
    _patch_llm_with_queue(monkeypatch, payloads)

    response = client.post("/public/ai-chat", json={"content": "hi"})
    assert response.status_code == 200, response.text

    with db_pool_seeded.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM ai_escalation")
            (count,) = cur.fetchone()
    assert count == 0


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


def test_system_prompt_mentions_escalate_to_human(client, monkeypatch):
    transport = _patch_llm_with_queue(monkeypatch, [_llama_cpp_payload("hi")])

    response = client.post("/public/ai-chat", json={"content": "hi"})
    assert response.status_code == 200, response.text

    system_msg = transport.calls[0]["messages"][0]
    assert system_msg["role"] == "system"
    content = system_msg["content"]
    assert "EscalateToHuman" in content
    assert "user_intention" in content
    # Both escalation examples are present.
    assert "I want to speak to a real person" in content
    assert "I need help applying for a mortgage" in content
    assert "three tools" in content
    # Roster should enumerate the public toolset.
    assert "EscalateToHuman" in content.split("only tools available to you are:")[1]


def test_system_prompt_makes_escalation_mandatory_when_cannot_fulfill(
    client, monkeypatch
):
    """Guard against future rewrites silently dropping the broadened trigger.
    The system prompt must explicitly tell the LLM to call EscalateToHuman
    when it cannot fulfill the request, and must NOT escalate on a single
    empty SearchProperty result."""
    transport = _patch_llm_with_queue(monkeypatch, [_llama_cpp_payload("hi")])

    response = client.post("/public/ai-chat", json={"content": "hi"})
    assert response.status_code == 200, response.text

    content = transport.calls[0]["messages"][0]["content"]
    # MANDATORY (EscalateToHuman) clause exists and ties the trigger to
    # "cannot fulfill", not just an explicit ask.
    assert "MANDATORY (EscalateToHuman)" in content
    assert "cannot fulfill" in content
    # Empty-result carve-out is present so the model does not escalate on
    # every typo'd city.
    assert "do not escalate just because the result is empty" in content
