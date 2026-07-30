from __future__ import annotations

import json
from typing import Any

from psycopg import Connection

from app.properties.schemas import (
    PropertyCreate,
    PropertyImageOut,
    PropertyListItem,
    PropertyOut,
    PropertyUpdate,
)

_BASE_COLUMNS = (
    "id, title, description, property_type, listing_type, "
    "price_amount, price_currency, "
    "bedrooms, bathrooms, area_sqm, "
    "address_line, city, district, postal_code, country_code, "
    "latitude, longitude, status, amenities, images, "
    "created_at, updated_at, created_by, updated_by"
)

_LIST_COLUMNS = (
    "id, title, property_type, listing_type, "
    "price_amount, price_currency, city, country_code, status, "
    "bedrooms, bathrooms, area_sqm, images, created_at"
)


def _row_to_out(row: tuple) -> PropertyOut:
    (
        pid,
        title,
        description,
        property_type,
        listing_type,
        price_amount,
        price_currency,
        bedrooms,
        bathrooms,
        area_sqm,
        address_line,
        city,
        district,
        postal_code,
        country_code,
        latitude,
        longitude,
        status,
        amenities,
        images,
        created_at,
        updated_at,
        created_by,
        updated_by,
    ) = row
    return PropertyOut(
        id=pid,
        title=title,
        description=description,
        property_type=property_type,
        listing_type=listing_type,
        price_amount=float(price_amount),
        price_currency=price_currency,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        area_sqm=None if area_sqm is None else float(area_sqm),
        address_line=address_line,
        city=city,
        district=district,
        postal_code=postal_code,
        country_code=country_code,
        latitude=None if latitude is None else float(latitude),
        longitude=None if longitude is None else float(longitude),
        status=status,
        amenities=list(amenities or []),
        images=[PropertyImageOut(**img) for img in (images or [])],
        created_at=created_at.isoformat(),
        updated_at=updated_at.isoformat(),
        created_by=created_by,
        updated_by=updated_by,
    )


def _row_to_list_item(row: tuple) -> PropertyListItem:
    (
        pid,
        title,
        property_type,
        listing_type,
        price_amount,
        price_currency,
        city,
        country_code,
        status,
        bedrooms,
        bathrooms,
        area_sqm,
        images,
        created_at,
    ) = row
    return PropertyListItem(
        id=pid,
        title=title,
        property_type=property_type,
        listing_type=listing_type,
        price_amount=float(price_amount),
        price_currency=price_currency,
        city=city,
        country_code=country_code,
        status=status,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        area_sqm=None if area_sqm is None else float(area_sqm),
        images=[PropertyImageOut(**img) for img in (images or [])],
        created_at=created_at.isoformat(),
    )


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return value
    if hasattr(value, "value"):
        return value.value
    return value


def _normalize_image(img: dict) -> dict:
    return {
        "url": str(img["url"]),
        "sort_order": int(img.get("sort_order", 0)),
        "alt": img.get("alt"),
    }


def _normalize_payload(data: dict) -> dict:
    out: dict[str, Any] = {}
    for key, value in data.items():
        if key == "images" and value is not None:
            out[key] = json.dumps([_normalize_image(img) for img in value])
        elif key == "amenities" and value is not None:
            out[key] = list(value)
        else:
            out[key] = _normalize_scalar(value)
    return out


def create_property(
    conn: Connection, payload: PropertyCreate, *, created_by: int
) -> PropertyOut:
    data = _normalize_payload(payload.model_dump())
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO property (
                title, description, property_type, listing_type,
                price_amount, price_currency,
                bedrooms, bathrooms, area_sqm,
                address_line, city, district, postal_code, country_code,
                latitude, longitude, status, amenities, images,
                created_by, updated_by
            ) VALUES (
                %(title)s, %(description)s, %(property_type)s, %(listing_type)s,
                %(price_amount)s, %(price_currency)s,
                %(bedrooms)s, %(bathrooms)s, %(area_sqm)s,
                %(address_line)s, %(city)s, %(district)s, %(postal_code)s, %(country_code)s,
                %(latitude)s, %(longitude)s, %(status)s, %(amenities)s::text[], %(images)s::jsonb,
                %(created_by)s, %(created_by)s
            )
            RETURNING {_BASE_COLUMNS}
            """,
            {**data, "created_by": created_by},
        )
        row = cur.fetchone()
    assert row is not None
    return _row_to_out(row)


def get_property(conn: Connection, property_id: int) -> PropertyOut | None:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {_BASE_COLUMNS} FROM property WHERE id = %s",
            (property_id,),
        )
        row = cur.fetchone()
    return _row_to_out(row) if row else None


def list_properties(
    conn: Connection,
    *,
    city: str | None,
    listing_type: str | None,
    property_type: str | None,
    status: str | None,
    min_price: float | None,
    max_price: float | None,
    bedrooms: int | None,
    q: str | None,
    limit: int,
    offset: int,
) -> tuple[list[PropertyListItem], int]:
    where: list[str] = []
    params: list[Any] = []
    if city:
        where.append("city = %s")
        params.append(city)
    if listing_type:
        where.append("listing_type = %s")
        params.append(listing_type)
    if property_type:
        where.append("property_type = %s")
        params.append(property_type)
    if status:
        where.append("status = %s")
        params.append(status)
    if min_price is not None:
        where.append("price_amount >= %s")
        params.append(min_price)
    if max_price is not None:
        where.append("price_amount <= %s")
        params.append(max_price)
    if bedrooms is not None:
        where.append("bedrooms = %s")
        params.append(bedrooms)
    if q:
        where.append("(title ILIKE %s OR description ILIKE %s)")
        like = f"%{q}%"
        params.append(like)
        params.append(like)
    where_sql = " WHERE " + " AND ".join(where) if where else ""

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM property{where_sql}", params)
        (total,) = cur.fetchone()
        cur.execute(
            f"SELECT {_LIST_COLUMNS} FROM property{where_sql} "
            f"ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s",
            [*params, limit, offset],
        )
        rows = cur.fetchall()
    return [_row_to_list_item(r) for r in rows], int(total)


def update_property(
    conn: Connection,
    property_id: int,
    payload: PropertyUpdate,
    *,
    updated_by: int,
) -> PropertyOut | None:
    data = _normalize_payload(payload.model_dump(exclude_unset=True))
    if not data:
        return get_property(conn, property_id)

    set_parts: list[str] = []
    params: list[Any] = []
    for key, value in data.items():
        if value is None and key in ("amenities", "images"):
            continue
        if key == "amenities":
            set_parts.append(f"{key} = %s::text[]")
            params.append(value)
        elif key == "images":
            set_parts.append(f"{key} = %s::jsonb")
            params.append(value)
        else:
            set_parts.append(f"{key} = %s")
            params.append(value)
    set_parts.append("updated_at = NOW()")
    set_parts.append("updated_by = %s")
    params.append(updated_by)
    params.append(property_id)

    sql = f"UPDATE property SET {', '.join(set_parts)} WHERE id = %s RETURNING {_BASE_COLUMNS}"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    return _row_to_out(row) if row else None


def delete_property(conn: Connection, property_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM property WHERE id = %s", (property_id,))
        return cur.rowcount > 0
