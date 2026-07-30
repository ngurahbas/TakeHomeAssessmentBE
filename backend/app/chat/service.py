from __future__ import annotations

import logging
from typing import Any, Callable

from psycopg_pool import ConnectionPool

from app.auth.schemas import UserOut
from app.chat import llm, repository
from app.chat.schemas import (
    ChatMessageOut,
    ChatRole,
    SendMessageResponse,
)
from app.chat.tools import TOOLS, tool_roster_prompt
from app.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class ConversationNotFoundError(LookupError):
    pass


def create_conversation(
    pool: ConnectionPool,
    *,
    user: UserOut,
    title: str | None,
) -> dict[str, Any]:
    with pool.connection() as conn:
        return repository.create_conversation(conn, user_id=user.id, title=title)


def get_conversation(
    pool: ConnectionPool, *, user: UserOut, conversation_id: int
) -> dict[str, Any]:
    with pool.connection() as conn:
        conv = repository.get_conversation_owned(
            conn, user_id=user.id, conversation_id=conversation_id
        )
    if conv is None:
        raise ConversationNotFoundError(conversation_id)
    return conv


def list_conversations(
    pool: ConnectionPool,
    *,
    user: UserOut,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    with pool.connection() as conn:
        return repository.list_conversations(
            conn, user_id=user.id, limit=limit, offset=offset
        )


def delete_conversation(
    pool: ConnectionPool, *, user: UserOut, conversation_id: int
) -> bool:
    with pool.connection() as conn:
        return repository.delete_conversation(
            conn, user_id=user.id, conversation_id=conversation_id
        )


def send_message(
    pool: ConnectionPool,
    *,
    user: UserOut,
    conversation_id: int,
    content: str,
    settings: Settings | None = None,
    llm_complete: Callable[..., str] | None = None,
) -> SendMessageResponse:
    settings = settings or get_settings()
    complete = llm_complete or llm.complete
    max_chars = settings.llm_max_input_chars
    if len(content) > max_chars:
        raise ValueError(f"content exceeds {max_chars} characters")

    with pool.connection() as conn:
        conv = repository.get_conversation_owned(
            conn, user_id=user.id, conversation_id=conversation_id
        )
        if conv is None:
            raise ConversationNotFoundError(conversation_id)

        user_message = repository.append_message(
            conn,
            conversation_id=conversation_id,
            role=ChatRole.USER,
            content=content,
        )

        history = repository.load_history(
            conn, conversation_id=conversation_id, cap=settings.llm_max_history_messages
        )
        repository.touch_conversation(conn, conversation_id=conversation_id)

    system_content = f"{settings.llm_system_prompt} {tool_roster_prompt()}"
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_content}
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": content})

    try:
        assistant_content = complete(messages, settings=settings, tools=TOOLS)
    except llm.LLMError:
        logger.exception("llm: chat completion failed")
        raise

    with pool.connection() as conn:
        assistant_message = repository.append_message(
            conn,
            conversation_id=conversation_id,
            role=ChatRole.ASSISTANT,
            content=assistant_content,
        )
        repository.touch_conversation(conn, conversation_id=conversation_id)

    return SendMessageResponse(
        conversation_id=conversation_id,
        user_message=ChatMessageOut.model_validate(user_message.model_dump()),
        assistant_message=ChatMessageOut.model_validate(
            assistant_message.model_dump()
        ),
    )
