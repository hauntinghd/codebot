from __future__ import annotations

from typing import Optional

from backend.database import db


def get_chat_owner(chat_id: str) -> Optional[str]:
    """
    Return the user_id (owner) for a chat_id, or None if chat does not exist.

    Expected schema: chats(id TEXT PRIMARY KEY, user_id TEXT, ...)
    If your schema uses a different column name (owner_id/created_by), update below.
    """
    if not chat_id:
        return None

    with db() as conn:
        row = conn.execute(
            "SELECT user_id FROM chats WHERE id = ? LIMIT 1",
            (chat_id,),
        ).fetchone()

    if not row:
        return None

    # sqlite3.Row supports dict-like access
    owner = row["user_id"] if "user_id" in row.keys() else None
    return str(owner) if owner is not None else None
