from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg_pool import ConnectionPool

from app.auth.deps import require_admin
from app.auth.routes import get_db_pool
from app.auth.schemas import UserOut
from app.properties import repository
from app.properties.schemas import (
    PropertyCreate,
    PropertyList,
    PropertyOut,
    PropertyUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/properties", tags=["properties"])


@router.post(
    "",
    response_model=PropertyOut,
    status_code=status.HTTP_201_CREATED,
)
def create_property(
    body: PropertyCreate,
    user: Annotated[UserOut, Depends(require_admin)],
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
) -> PropertyOut:
    with pool.connection() as conn:
        return repository.create_property(conn, body, created_by=user.id)


@router.get("", response_model=PropertyList)
def list_properties(
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
    _: Annotated[UserOut, Depends(require_admin)],
    city: str | None = Query(default=None, max_length=128),
    listing_type: str | None = Query(default=None, max_length=16),
    property_type: str | None = Query(default=None, max_length=32),
    status_: str | None = Query(default=None, alias="status", max_length=16),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    bedrooms: int | None = Query(default=None, ge=0, le=50),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PropertyList:
    with pool.connection() as conn:
        items, total = repository.list_properties(
            conn,
            city=city,
            listing_type=listing_type,
            property_type=property_type,
            status=status_,
            min_price=min_price,
            max_price=max_price,
            bedrooms=bedrooms,
            q=q,
            limit=limit,
            offset=offset,
        )
    return PropertyList(items=items, total=total, limit=limit, offset=offset)


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(
    property_id: int,
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
    _: Annotated[UserOut, Depends(require_admin)],
) -> PropertyOut:
    with pool.connection() as conn:
        prop = repository.get_property(conn, property_id)
    if prop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="property not found",
        )
    return prop


@router.patch("/{property_id}", response_model=PropertyOut)
def update_property(
    property_id: int,
    body: PropertyUpdate,
    user: Annotated[UserOut, Depends(require_admin)],
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
) -> PropertyOut:
    with pool.connection() as conn:
        prop = repository.update_property(conn, property_id, body, updated_by=user.id)
    if prop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="property not found",
        )
    return prop


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: int,
    _: Annotated[UserOut, Depends(require_admin)],
    pool: Annotated[ConnectionPool, Depends(get_db_pool)],
) -> None:
    with pool.connection() as conn:
        ok = repository.delete_property(conn, property_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="property not found",
        )
    return None
