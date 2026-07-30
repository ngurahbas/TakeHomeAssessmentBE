from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class PublicChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


def _coerce_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("chat_id must be a valid UUID") from exc


class PublicChatMessageOut(BaseModel):
    id: int
    role: PublicChatRole
    content: str
    created_at: str


class PublicChatSendRequest(BaseModel):
    chat_id: str | None = Field(default=None)
    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator("chat_id")
    @classmethod
    def _validate_chat_id(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        return _coerce_uuid(value)


class PublicChatSendResponse(BaseModel):
    chat_id: str
    user_message: PublicChatMessageOut
    assistant_message: PublicChatMessageOut


class PublicChatSessionOut(BaseModel):
    id: str
    created_at: str
    last_active_at: str
    messages: list[PublicChatMessageOut]
