from __future__ import annotations

from typing import Any

from psycopg import Connection

from app.chat.schemas import (
    ChatMessageOut,
    ChatRole,
)


def _row_to_message(row: tuple) -> ChatMessageOut:
    mid, conversation_id, role, content, created_at = row
    return ChatMessageOut(
        id=mid,
        conversation_id=conversation_id,
        role=ChatRole(role),
        content=content,
        created_at=created_at.isoformat(),
    )


def _row_to_summary(row: tuple) -> dict[str, Any]:
    cid, title, created_at, updated_at, message_count = row
    return {
        "id": cid,
        "title": title,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "message_count": int(message_count),
    }


def create_conversation(
    conn: Connection, *, user_id: int, title: str | None
) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chat_conversation (user_id, title)
            VALUES (%s, %s)
            RETURNING id, title, created_at, updated_at
            """,
            (user_id, title),
        )
        row = cur.fetchone()
    assert row is not None
    cid, title_v, created_at, updated_at = row
    return {
        "id": cid,
        "title": title_v,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "messages": [],
    }


def get_conversation_owned(
    conn: Connection, *, user_id: int, conversation_id: int
) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM chat_conversation
            WHERE id = %s AND user_id = %s
            """,
            (conversation_id, user_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        cid, title, created_at, updated_at = row
        cur.execute(
            """
            SELECT id, conversation_id, role, content, created_at
            FROM chat_message
            WHERE conversation_id = %s
            ORDER BY created_at ASC, id ASC
            """,
            (cid,),
        )
        messages = [_row_to_message(r) for r in cur.fetchall()]
    return {
        "id": cid,
        "title": title,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "messages": messages,
    }


def list_conversations(
    conn: Connection, *, user_id: int, limit: int, offset: int
) -> tuple[list[dict[str, Any]], int]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM chat_conversation WHERE user_id = %s",
            (user_id,),
        )
        (total,) = cur.fetchone()
        cur.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   COALESCE(m.cnt, 0) AS message_count
            FROM chat_conversation c
            LEFT JOIN (
                SELECT conversation_id, COUNT(*) AS cnt
                FROM chat_message
                GROUP BY conversation_id
            ) m ON m.conversation_id = c.id
            WHERE c.user_id = %s
            ORDER BY c.updated_at DESC, c.id DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset),
        )
        rows = cur.fetchall()
    return [_row_to_summary(r) for r in rows], int(total)


def append_message(
    conn: Connection,
    *,
    conversation_id: int,
    role: ChatRole,
    content: str,
) -> ChatMessageOut:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chat_message (conversation_id, role, content)
            VALUES (%s, %s, %s)
            RETURNING id, conversation_id, role, content, created_at
            """,
            (conversation_id, role.value, content),
        )
        row = cur.fetchone()
    assert row is not None
    return _row_to_message(row)


def touch_conversation(conn: Connection, *, conversation_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE chat_conversation SET updated_at = NOW() WHERE id = %s",
            (conversation_id,),
        )


def load_history(
    conn: Connection, *, conversation_id: int, cap: int
) -> list[dict[str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT role, content
            FROM (
                SELECT id, role, content, created_at
                FROM chat_message
                WHERE conversation_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
            ) recent
            ORDER BY created_at ASC, id ASC
            """,
            (conversation_id, cap),
        )
        rows = cur.fetchall()
    return [{"role": role, "content": content} for role, content in rows]


def delete_conversation(
    conn: Connection, *, user_id: int, conversation_id: int
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM chat_conversation WHERE id = %s AND user_id = %s",
            (conversation_id, user_id),
        )
        return cur.rowcount > 0
