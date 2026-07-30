from __future__ import annotations

from typing import Any

from psycopg import Connection

from app.public_chat import repository as chat_repository


def _row_to_escalation(
    row: tuple, *, message_count: int | None = None
) -> dict[str, Any]:
    eid, chat_id, intention, created_at = row
    out: dict[str, Any] = {
        "id": eid,
        "public_chat_id": str(chat_id),
        "user_intention": intention,
        "created_at": created_at.isoformat(),
    }
    if message_count is not None:
        out["message_count"] = message_count
    return out


def list_escalations(
    conn: Connection,
    *,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                a.id,
                a.public_chat_id,
                a.user_intention,
                a.created_at,
                COALESCE(
                    (
                        SELECT COUNT(*)::int
                        FROM public_chat_message m
                        WHERE m.session_id = a.public_chat_id
                    ),
                    0
                ) AS message_count
            FROM ai_escalation a
            ORDER BY a.created_at DESC, a.id DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        rows = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM ai_escalation")
        (total,) = cur.fetchone()
    items = [
        _row_to_escalation(
            (eid, chat_id, intention, created_at),
            message_count=message_count,
        )
        for (eid, chat_id, intention, created_at, message_count) in rows
    ]
    return items, int(total)


def get_escalation(
    conn: Connection, *, id: int
) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, public_chat_id, user_intention, created_at
            FROM ai_escalation
            WHERE id = %s
            """,
            (id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_escalation(row)


def get_escalation_with_session(
    conn: Connection, *, id: int
) -> dict[str, Any] | None:
    escalation = get_escalation(conn, id=id)
    if escalation is None:
        return None
    session = chat_repository.get_session(
        conn, session_id=escalation["public_chat_id"]
    )
    if session is None:
        # Session was deleted; cascade should have removed the escalation,
        # but guard against drift.
        return None
    return {**escalation, "session": session}
