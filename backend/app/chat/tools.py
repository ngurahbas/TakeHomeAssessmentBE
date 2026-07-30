from __future__ import annotations

import json
import logging
import random
from typing import Any

from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

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


def execute_say_nice_thing(*, pool: ConnectionPool | None = None) -> str:
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
    q: str | None = None,
    city: str | None = None,
    listing_type: str | None = None,
    property_type: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    bedrooms: int | None = None,
    max_results: int | None = None,
) -> list[dict[str, Any]]:
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


TOOLS: list[dict[str, Any]] = [SAY_NICE_THING_SCHEMA, SEARCH_PROPERTY_SCHEMA]

TOOL_MAP: dict[str, Any] = {
    "SayNiceThing": execute_say_nice_thing,
    "SearchProperty": execute_search_property,
}


def tool_roster_prompt() -> str:
    names = ", ".join(sorted(TOOL_MAP.keys()))
    return (
        f"The only tools available to you are: {names}. "
        "Do not invent or mention any other tools."
    )


def execute_tool_call(
    tool_name: str,
    arguments: str,
    *,
    pool: ConnectionPool | None = None,
) -> str:
    fn = TOOL_MAP.get(tool_name)
    if fn is None:
        logger.warning("tool call ignored: unknown tool %r", tool_name)
        return json.dumps({"error": f"unknown tool: {tool_name}"})
    logger.info("tool call dispatched: %s(%s)", tool_name, arguments)
    args: dict[str, Any] = json.loads(arguments) if arguments else {}
    result = fn(**args, pool=pool)
    if isinstance(result, str):
        return result
    return json.dumps({"result": result})
