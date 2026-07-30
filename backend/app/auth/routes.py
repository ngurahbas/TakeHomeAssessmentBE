import logging
from typing import Annotated

import valkey
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg_pool import ConnectionPool

from app.auth.schemas import LoginRequest, LoginResponse, UserOut
from app.auth.security import new_token, session_key, verify_password
from app.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)


def extract_bearer_token(creds: HTTPAuthorizationCredentials | None) -> str:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid bearer token",
        )
    return creds.credentials


def get_db_pool(request: Request):
    pool: ConnectionPool | None = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database not configured",
        )
    return pool


def get_valkey(request: Request) -> valkey.Valkey:
    client: valkey.Valkey | None = getattr(request.app.state, "valkey", None)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="session store not configured",
        )
    return client


def _load_user_by_id(pool: ConnectionPool, user_id: int) -> UserOut | None:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, role FROM app_user WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return UserOut(id=row[0], email=row[1], role=row[2])


def get_current_session(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
    valkey_client: Annotated[valkey.Valkey, Depends(get_valkey)],
) -> tuple[str, UserOut]:
    token = extract_bearer_token(creds)
    raw = valkey_client.get(session_key(token))
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired session",
        )
    try:
        user_id = int(raw)
    except (TypeError, ValueError):
        logger.warning("session value not an int: %r", raw)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired session",
        ) from None
    user = _load_user_by_id(pool, user_id)
    if user is None:
        valkey_client.delete(session_key(token))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired session",
        )
    return token, user


def get_current_user(
    session: Annotated[tuple[str, UserOut], Depends(get_current_session)],
) -> UserOut:
    return session[1]


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
    valkey_client: Annotated[valkey.Valkey, Depends(get_valkey)],
) -> LoginResponse:
    settings = get_settings()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, role, password_hash FROM app_user WHERE email = %s",
                (body.email,),
            )
            row = cur.fetchone()
    if row is None or not verify_password(body.password, row[3]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    user = UserOut(id=row[0], email=row[1], role=row[2])
    token = new_token()
    valkey_client.set(session_key(token), str(user.id), ex=settings.auth_token_ttl_seconds)
    return LoginResponse(token=token, user=user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    session: Annotated[tuple[str, UserOut], Depends(get_current_session)],
    valkey_client: Annotated[valkey.Valkey, Depends(get_valkey)],
) -> None:
    token, _ = session
    valkey_client.delete(session_key(token))
    return None


@router.get("/me", response_model=UserOut)
def me(user: Annotated[UserOut, Depends(get_current_user)]) -> UserOut:
    return user
