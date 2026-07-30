from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from psycopg_pool import ConnectionPool

from app.auth.routes import get_db_pool
from app.chat.llm import LLMError, complete
from app.chat.tools import TOOLS, tool_roster_prompt
from app.public_chat import repository
from app.public_chat.schemas import (
    PublicChatMessageOut,
    PublicChatSendRequest,
    PublicChatSendResponse,
    PublicChatSessionOut,
)
from app.settings import get_settings
from typing import Annotated
from fastapi import Depends

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public/ai-chat", tags=["public-chat"])


@router.post("", response_model=PublicChatSendResponse)
def post_message(
    body: PublicChatSendRequest,
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
) -> PublicChatSendResponse:
    settings = get_settings()

    with pool.connection() as conn:
        if body.chat_id is not None:
            session = repository.get_session(conn, session_id=body.chat_id)
            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="chat not found",
                )
            session_id = session["id"]
        else:
            session_id = repository.create_session(conn)

        user_message = repository.append_message(
            conn, session_id=session_id, role="user", content=body.content
        )
        history = repository.load_history(
            conn,
            session_id=session_id,
            cap=settings.llm_max_history_messages,
        )
        repository.touch_session(conn, session_id=session_id)

    system_content = f"{settings.llm_system_prompt} {tool_roster_prompt()}"
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_content}
    ]
    for m in history:
        messages.append({"role": m["role"], "content": m["content"]})

    try:
        assistant_content = complete(messages, settings=settings, tools=TOOLS)
    except LLMError as exc:
        logger.warning("public_chat: llm error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": f"llm error: {exc}",
                "chat_id": session_id,
            },
        )

    with pool.connection() as conn:
        assistant_message = repository.append_message(
            conn,
            session_id=session_id,
            role="assistant",
            content=assistant_content,
        )
        repository.touch_session(conn, session_id=session_id)

    return PublicChatSendResponse(
        chat_id=session_id,
        user_message=PublicChatMessageOut.model_validate(user_message),
        assistant_message=PublicChatMessageOut.model_validate(assistant_message),
    )


@router.get("/{chat_id}", response_model=PublicChatSessionOut)
def get_session(
    chat_id: str,
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
) -> PublicChatSessionOut:
    with pool.connection() as conn:
        session = repository.get_session(conn, session_id=chat_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="chat not found",
        )
    return PublicChatSessionOut.model_validate(session)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    chat_id: str,
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
) -> None:
    with pool.connection() as conn:
        ok = repository.delete_session(conn, session_id=chat_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="chat not found",
        )
    return None
