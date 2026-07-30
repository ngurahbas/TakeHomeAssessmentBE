from __future__ import annotations

from pydantic import BaseModel, Field

from app.public_chat.schemas import PublicChatSessionOut


class AiEscalationOut(BaseModel):
    id: int
    public_chat_id: str
    user_intention: str
    created_at: str


class AiEscalationListItem(AiEscalationOut):
    message_count: int = Field(..., ge=0)


class AiEscalationList(BaseModel):
    items: list[AiEscalationListItem]
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)


class AiEscalationDetail(BaseModel):
    id: int
    public_chat_id: str
    user_intention: str
    created_at: str
    session: PublicChatSessionOut
