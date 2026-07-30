from __future__ import annotations

import logging
from typing import Any

import httpx

from app.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


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
) -> str:
    settings = settings or get_settings()
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    body: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        "stream": False,
    }
    headers = {"User-Agent": "real-estate-ai-backend/0.1"}
    if settings.llm_api_key and settings.llm_api_key != "not-needed":
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=settings.llm_timeout_seconds)
    try:
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
            payload = response.json()
        except ValueError as exc:
            raise LLMError(f"LLM response was not JSON: {exc}") from exc
    finally:
        if owns_client:
            client.close()

    return _extract_content(payload)
