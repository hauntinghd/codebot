from __future__ import annotations

from typing import Any, Dict, List

from backend.database import db


def get_recent_messages(chat_id: str, limit: int = 18) -> List[Dict[str, Any]]:
    """
    Return recent chat messages in ascending order (oldest -> newest) as a list of dicts.

    Expected schema: messages(chat_id, role, content, created_at, ai_layer?)
    """
    if not chat_id:
        return []

    try:
        lim = int(limit)
    except Exception:
        lim = 18
    lim = max(1, min(lim, 200))

    with db() as conn:
        rows = conn.execute(
            """
            SELECT role, content, created_at, ai_layer
            FROM messages
            WHERE chat_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (chat_id, lim),
        ).fetchall()

    # We queried DESC; return ASC for LLM context
    out: List[Dict[str, Any]] = []
    for r in reversed(rows or []):
        # sqlite3.Row supports keys(); ai_layer may not exist in older schemas
        ai_layer = ""
        try:
            ai_layer = r["ai_layer"] if "ai_layer" in r.keys() else ""
        except Exception:
            ai_layer = ""

        out.append(
            {
                "role": str(r["role"]),
                "content": str(r["content"] or ""),
                "created_at": int(r["created_at"]) if r["created_at"] is not None else 0,
                "ai_layer": str(ai_layer or ""),
            }
        )

    return out
