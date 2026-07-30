from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.chat.tools import execute_tool_call
from app.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_MAX_TOOL_CALL_ROUNDS = 10


class LLMError(RuntimeError):
    pass


def _build_request_body(
    messages: list[dict[str, str]],
    model: str,
    tools: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        body["tools"] = tools
    return body


def _post(
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
    client: httpx.Client,
) -> dict[str, Any]:
    try:
        response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("llm: request failed: %s", exc)
        raise LLMError(f"LLM request failed: {exc}") from exc
    if response.status_code >= 400:
        logger.warning(
            "llm: non-2xx status=%s body=%s",
            response.status_code,
            response.text[:500],
        )
        raise LLMError(
            f"LLM returned status {response.status_code}: {response.text[:200]}"
        )
    try:
        return response.json()
    except ValueError as exc:
        raise LLMError(f"LLM response was not JSON: {exc}") from exc


def _extract_content(payload: dict[str, Any]) -> str:
    try:
        choices = payload["choices"]
        message = choices[0]["message"]
        content = message.get("content")
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"unexpected LLM response shape: {payload!r}") from exc
    if not isinstance(content, str) or not content:
        raise LLMError(f"LLM returned empty content: {payload!r}")
    return content


def complete(
    messages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
    client: httpx.Client | None = None,
    tools: list[dict[str, Any]] | None = None,
    pool: Any | None = None,
) -> str:
    settings = settings or get_settings()
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"User-Agent": "real-estate-ai-backend/0.1"}
    if settings.llm_api_key and settings.llm_api_key != "not-needed":
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    working_messages: list[dict[str, Any]] = list(messages)
    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=settings.llm_timeout_seconds)
    try:
        for round_idx in range(_MAX_TOOL_CALL_ROUNDS):
            body = _build_request_body(working_messages, settings.llm_model, tools)
            if tools:
                logger.info(
                    "llm: outbound request model=%s tools=%s messages=%d round=%d",
                    settings.llm_model,
                    [t.get("function", {}).get("name", "?") for t in tools],
                    len(working_messages),
                    round_idx,
                )
            payload = _post(url, body, headers, client)
            message = payload["choices"][0]["message"]

            tool_calls = message.get("tool_calls")
            if not tool_calls:
                content = message.get("content")
                if not isinstance(content, str) or not content:
                    raise LLMError(f"LLM returned empty content: {payload!r}")
                return content

            working_messages.append({"role": "assistant", "tool_calls": tool_calls})
            for tc in tool_calls:
                fn_info = tc.get("function", {})
                tool_name = fn_info.get("name", "")
                arguments = fn_info.get("arguments", "{}")
                logger.info(
                    "llm: executing tool %s with args %s", tool_name, arguments
                )
                result = execute_tool_call(tool_name, arguments, pool=pool)
                working_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    }
                )
        raise LLMError("LLM exceeded max tool call rounds")
    finally:
        if owns_client:
            client.close()
