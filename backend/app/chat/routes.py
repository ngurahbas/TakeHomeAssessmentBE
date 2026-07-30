from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg_pool import ConnectionPool

from app.auth.routes import get_current_user, get_db_pool
from app.auth.schemas import UserOut
from app.chat import service
from app.chat.llm import LLMError
from app.chat.schemas import (
    ChatConversationCreate,
    ChatConversationList,
    ChatConversationOut,
    ChatMessageCreate,
    SendMessageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post(
    "/conversations",
    response_model=ChatConversationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    body: ChatConversationCreate,
    user: Annotated[UserOut, Depends(get_current_user)],
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
) -> ChatConversationOut:
    title = body.title.strip() if body.title else None
    if title == "":
        title = None
    return ChatConversationOut.model_validate(
        service.create_conversation(pool, user=user, title=title)
    )


@router.get(
    "/conversations",
    response_model=ChatConversationList,
)
def list_conversations(
    user: Annotated[UserOut, Depends(get_current_user)],
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ChatConversationList:
    items, total = service.list_conversations(
        pool, user=user, limit=limit, offset=offset
    )
    return ChatConversationList(
        items=items, total=total, limit=limit, offset=offset
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ChatConversationOut,
)
def get_conversation(
    conversation_id: int,
    user: Annotated[UserOut, Depends(get_current_user)],
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
) -> ChatConversationOut:
    try:
        conv = service.get_conversation(
            pool, user=user, conversation_id=conversation_id
        )
    except service.ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversation not found",
        )
    return ChatConversationOut.model_validate(conv)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation(
    conversation_id: int,
    user: Annotated[UserOut, Depends(get_current_user)],
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
) -> None:
    ok = service.delete_conversation(
        pool, user=user, conversation_id=conversation_id
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversation not found",
        )
    return None


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
)
def send_message(
    conversation_id: int,
    body: ChatMessageCreate,
    user: Annotated[UserOut, Depends(get_current_user)],
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
) -> SendMessageResponse:
    try:
        return service.send_message(
            pool, user=user, conversation_id=conversation_id, content=body.content
        )
    except service.ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversation not found",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"llm error: {exc}",
        )
