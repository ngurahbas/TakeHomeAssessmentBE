from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from psycopg import Connection


def _row_to_message(row: tuple) -> dict[str, Any]:
    mid, role, content, created_at = row
    return {
        "id": mid,
        "role": role,
        "content": content,
        "created_at": created_at.isoformat(),
    }


def create_session(conn: Connection) -> str:
    new_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public_chat_session (id)
            VALUES (%s)
            RETURNING id, created_at, last_active_at
            """,
            (new_id,),
        )
        row = cur.fetchone()
    assert row is not None
    return new_id


def get_session(
    conn: Connection, *, session_id: str
) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, created_at, last_active_at
            FROM public_chat_session
            WHERE id = %s
            """,
            (session_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        sid, created_at, last_active_at = row
        cur.execute(
            """
            SELECT id, role, content, created_at
            FROM public_chat_message
            WHERE session_id = %s
            ORDER BY created_at ASC, id ASC
            """,
            (sid,),
        )
        messages = [_row_to_message(r) for r in cur.fetchall()]
    return {
        "id": str(sid),
        "created_at": created_at.isoformat(),
        "last_active_at": last_active_at.isoformat(),
        "messages": messages,
    }


def touch_session(conn: Connection, *, session_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE public_chat_session SET last_active_at = NOW() WHERE id = %s",
            (session_id,),
        )


def append_message(
    conn: Connection,
    *,
    session_id: str,
    role: str,
    content: str,
) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public_chat_message (session_id, role, content)
            VALUES (%s, %s, %s)
            RETURNING id, role, content, created_at
            """,
            (session_id, role, content),
        )
        row = cur.fetchone()
    assert row is not None
    return _row_to_message(row)


def load_history(
    conn: Connection, *, session_id: str, cap: int
) -> list[dict[str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT role, content
            FROM (
                SELECT id, role, content, created_at
                FROM public_chat_message
                WHERE session_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
            ) recent
            ORDER BY created_at ASC, id ASC
            """,
            (session_id, cap),
        )
        rows = cur.fetchall()
    return [{"role": role, "content": content} for role, content in rows]


def delete_session(
    conn: Connection, *, session_id: str
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM public_chat_session WHERE id = %s",
            (session_id,),
        )
        return cur.rowcount > 0
