from __future__ import annotations

import json
import logging
import random
from typing import Any

logger = logging.getLogger(__name__)

SAY_NICE_THING_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "SayNiceThing",
        "description": "Returns a nice, uplifting word or phrase to cheer someone up.",
        "parameters": {"type": "object", "properties": {}, "required": []},
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


def execute_say_nice_thing() -> str:
    word = random.choice(_NICE_WORDS)
    logger.info("tool SayNiceThing executed, returning %r", word)
    return word


TOOLS: list[dict[str, Any]] = [SAY_NICE_THING_SCHEMA]

TOOL_MAP: dict[str, Any] = {
    "SayNiceThing": execute_say_nice_thing,
}


def tool_roster_prompt() -> str:
    names = ", ".join(sorted(TOOL_MAP.keys()))
    return (
        f"The only tools available to you are: {names}. "
        "Do not invent or mention any other tools."
    )


def execute_tool_call(
    tool_name: str, arguments: str
) -> str:
    fn = TOOL_MAP.get(tool_name)
    if fn is None:
        logger.warning("tool call ignored: unknown tool %r", tool_name)
        return json.dumps({"error": f"unknown tool: {tool_name}"})
    logger.info("tool call dispatched: %s(%s)", tool_name, arguments)
    args: dict[str, Any] = json.loads(arguments) if arguments else {}
    result = fn(**args)
    if isinstance(result, str):
        return result
    return json.dumps({"result": result})
