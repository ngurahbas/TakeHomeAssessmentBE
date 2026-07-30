from __future__ import annotations

import json
import logging
import random
from typing import Any

from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

# Keys that are injected by the server into executor kwargs. `execute_tool_call`
# strips these from the LLM-supplied `args` dict before forwarding, so the LLM
# cannot forge server context (e.g. by passing a fake public_chat_id).
_SERVER_INJECTED_KEYS: frozenset[str] = frozenset({"public_chat_id"})

SAY_NICE_THING_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "SayNiceThing",
        "description": "Returns a nice, uplifting word or phrase to cheer someone up.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

SEARCH_PROPERTY_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "SearchProperty",
        "description": (
            "Search the property catalog for listings that match the user's "
            "request. Always filters to AVAILABLE listings only — do not "
            "mention or filter by status. Returns up to max_results rows "
            "(default 5, max 10) as a compact JSON array. Call once per turn "
            "with the most specific filters the user mentioned; if the user "
            "named a city, pass it via the `city` parameter; otherwise use "
            "the `q` parameter for free-text matching against title and "
            "description."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "description": (
                        "Free-text search matched (case-insensitive) against "
                        "the listing's title and description. Use this when "
                        "the user describes a property in words rather than "
                        "by structured filters (e.g. 'cozy studio near the "
                        "park')."
                    ),
                },
                "city": {
                    "type": "string",
                    "description": (
                        "City name to filter by, e.g. 'Boston'. Use the "
                        "spelling the user supplied; do not invent a city."
                    ),
                },
                "listing_type": {
                    "type": "string",
                    "enum": ["SALE", "RENT"],
                    "description": "Whether the listing is for sale or for rent.",
                },
                "property_type": {
                    "type": "string",
                    "enum": [
                        "APARTMENT",
                        "HOUSE",
                        "VILLA",
                        "STUDIO",
                        "OFFICE",
                        "LAND",
                    ],
                    "description": "Kind of property.",
                },
                "min_price": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Inclusive lower bound on price_amount.",
                },
                "max_price": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Inclusive upper bound on price_amount.",
                },
                "bedrooms": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Exact number of bedrooms required.",
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": (
                        "Maximum number of listings to return. Defaults to 5 "
                        "when omitted. Use a small number to keep the reply "
                        "focused."
                    ),
                },
            },
            "required": [],
        },
    },
}

ESCALATE_TO_HUMAN_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "EscalateToHuman",
        "description": (
            "Escalate the conversation to a human agent. Call this whenever "
            "you cannot fulfill the user's request with your other tools or "
            "your own knowledge. Triggers include: out-of-scope questions "
            "(legal, mortgage, negotiation, complaints, scheduling a "
            "viewing), the user explicitly asks to speak to a real person, "
            "or the user is clearly frustrated after an attempted search. "
            "Do NOT call this just because a property search returned an "
            "empty list — the user can usually refine the query themselves. "
            "Pass a concise `user_intention` describing what the user "
            "wanted; the server records the escalation against the current "
            "public chat session and a human will follow up."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_intention": {
                    "type": "string",
                    "minLength": 1,
                    "description": (
                        "One or two sentences describing what the user "
                        "wanted to accomplish or why they need a human."
                    ),
                },
            },
            "required": ["user_intention"],
        },
    },
}

_NICE_WORDS: list[str] = [
    "You are a wonderful person!",
    "You are absolutely amazing!",
    "You are truly incredible!",
    "You are doing fantastic!",
    "You are awesome!",
    "You have a brilliant mind!",
    "You are a magnificent human being!",
    "You are doing a splendid job!",
    "You are simply marvelous!",
    "You are an outstanding individual!",
    "You are truly remarkable!",
    "You are absolutely exceptional!",
    "You are doing a terrific job!",
    "You are superb at what you do!",
    "You are truly glorious!",
]


def execute_say_nice_thing(
    *,
    pool: ConnectionPool | None = None,
    public_chat_id: str | None = None,
) -> str:
    del public_chat_id  # not relevant to this tool; accepted for signature uniformity
    word = random.choice(_NICE_WORDS)
    logger.info("tool SayNiceThing executed, returning %r", word)
    return word


_SEARCH_PROPERTY_RESULT_FIELDS: tuple[str, ...] = (
    "id",
    "title",
    "property_type",
    "listing_type",
    "price_amount",
    "price_currency",
    "city",
    "country_code",
    "bedrooms",
    "bathrooms",
    "area_sqm",
)

_SEARCH_PROPERTY_MAX_RESULTS_DEFAULT = 5
_SEARCH_PROPERTY_MAX_RESULTS_CAP = 10


def _compact_search_result(item: dict[str, Any]) -> dict[str, Any]:
    return {k: item.get(k) for k in _SEARCH_PROPERTY_RESULT_FIELDS}


def execute_search_property(
    *,
    pool: ConnectionPool | None = None,
    public_chat_id: str | None = None,
    q: str | None = None,
    city: str | None = None,
    listing_type: str | None = None,
    property_type: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    bedrooms: int | None = None,
    max_results: int | None = None,
) -> list[dict[str, Any]]:
    del public_chat_id  # not relevant to this tool; accepted for signature uniformity
    if pool is None:
        logger.warning("tool SearchProperty called without a pool")
        return []

    cap = _SEARCH_PROPERTY_MAX_RESULTS_DEFAULT
    if max_results is not None:
        try:
            cap = int(max_results)
        except (TypeError, ValueError):
            cap = _SEARCH_PROPERTY_MAX_RESULTS_DEFAULT
    cap = max(1, min(cap, _SEARCH_PROPERTY_MAX_RESULTS_CAP))

    from app.properties import repository

    with pool.connection() as conn:
        items, _total = repository.list_properties(
            conn,
            city=city,
            listing_type=listing_type,
            property_type=property_type,
            status="AVAILABLE",
            min_price=min_price,
            max_price=max_price,
            bedrooms=bedrooms,
            q=q,
            limit=cap,
            offset=0,
        )
    compact = [_compact_search_result(item.model_dump()) for item in items]
    logger.info(
        "tool SearchProperty executed city=%r q=%r returned %d rows",
        city,
        q,
        len(compact),
    )
    return compact


def execute_escalate_to_human(
    *,
    pool: ConnectionPool | None = None,
    public_chat_id: str | None = None,
    user_intention: str | None = None,
) -> dict[str, Any]:
    if user_intention is None or not str(user_intention).strip():
        raise ValueError("user_intention is required")
    if not public_chat_id:
        raise ValueError("EscalateToHuman requires a public chat session id")
    if pool is None:
        raise RuntimeError("EscalateToHuman requires a database pool")

    from app.public_chat import repository

    intention = str(user_intention).strip()
    with pool.connection() as conn:
        row = repository.create_escalation(
            conn,
            public_chat_id=public_chat_id,
            user_intention=intention,
        )
    logger.info(
        "tool EscalateToHuman executed public_chat_id=%s id=%s",
        public_chat_id,
        row["id"],
    )
    return {
        "id": row["id"],
        "public_chat_id": row["public_chat_id"],
        "user_intention": row["user_intention"],
        "created_at": row["created_at"],
        "message": "A human agent will follow up shortly.",
    }


TOOL_MAP: dict[str, Any] = {
    "SayNiceThing": execute_say_nice_thing,
    "SearchProperty": execute_search_property,
    "EscalateToHuman": execute_escalate_to_human,
}

# Tools exposed to the public (unauthenticated) chat. EscalateToHuman is
# included because the public chat is the only path that carries a
# `public_chat_id` to attribute an escalation to.
TOOLS: list[dict[str, Any]] = [
    SAY_NICE_THING_SCHEMA,
    SEARCH_PROPERTY_SCHEMA,
    ESCALATE_TO_HUMAN_SCHEMA,
]


def tool_roster_prompt(tools: list[dict[str, Any]] | None = None) -> str:
    if tools is None:
        tools = TOOLS
    names = ", ".join(
        sorted(t["function"]["name"] for t in tools if "function" in t)
    )
    return (
        f"The only tools available to you are: {names}. "
        "Do not invent or mention any other tools."
    )


def execute_tool_call(
    tool_name: str,
    arguments: str,
    *,
    pool: ConnectionPool | None = None,
    public_chat_id: str | None = None,
) -> str:
    fn = TOOL_MAP.get(tool_name)
    if fn is None:
        logger.warning("tool call ignored: unknown tool %r", tool_name)
        return json.dumps({"error": f"unknown tool: {tool_name}"})
    logger.info("tool call dispatched: %s(%s)", tool_name, arguments)
    args: dict[str, Any] = json.loads(arguments) if arguments else {}
    # Strip server-injected keys so the LLM can't fake the conversation
    # context. The server's value always wins.
    for injected in _SERVER_INJECTED_KEYS:
        args.pop(injected, None)
    result = fn(**args, pool=pool, public_chat_id=public_chat_id)
    if isinstance(result, str):
        return result
    return json.dumps({"result": result})
