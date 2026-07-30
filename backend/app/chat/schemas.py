from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class ChatMessageOut(BaseModel):
    id: int
    conversation_id: int
    role: ChatRole
    content: str
    created_at: str


class ChatConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ChatConversationSummary(BaseModel):
    id: int
    title: str | None
    created_at: str
    updated_at: str
    message_count: int


class ChatConversationList(BaseModel):
    items: list[ChatConversationSummary]
    total: int
    limit: int
    offset: int


class ChatConversationOut(BaseModel):
    id: int
    title: str | None
    created_at: str
    updated_at: str
    messages: list[ChatMessageOut]


class SendMessageResponse(BaseModel):
    conversation_id: int
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
