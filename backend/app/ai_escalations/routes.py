from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from psycopg_pool import ConnectionPool

from app.ai_escalations import repository
from app.ai_escalations.schemas import (
    AiEscalationDetail,
    AiEscalationList,
)
from app.auth.deps import require_admin
from app.auth.routes import get_db_pool
from app.auth.schemas import UserOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-escalations", tags=["ai-escalations"])


@router.get("", response_model=AiEscalationList)
def list_escalations(
    _user: Annotated[UserOut, Depends(require_admin)],
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AiEscalationList:
    with pool.connection() as conn:
        items, total = repository.list_escalations(
            conn, limit=limit, offset=offset
        )
    return AiEscalationList(
        items=items, total=total, limit=limit, offset=offset
    )


@router.get("/{escalation_id}", response_model=AiEscalationDetail)
def get_escalation(
    escalation_id: Annotated[int, Path(..., ge=1)],
    _user: Annotated[UserOut, Depends(require_admin)],
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
) -> AiEscalationDetail:
    with pool.connection() as conn:
        detail = repository.get_escalation_with_session(
            conn, id=escalation_id
        )
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="escalation not found",
        )
    return AiEscalationDetail.model_validate(detail)
