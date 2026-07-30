from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.auth.roles import ROLE_ADMIN
from app.auth.routes import get_current_user
from app.auth.schemas import UserOut


def require_admin(
    user: Annotated[UserOut, Depends(get_current_user)],
) -> UserOut:
    if user.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin role required",
        )
    return user


__all__ = ["require_admin"]
