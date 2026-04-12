from __future__ import annotations

from typing import Optional

from backend.database import db


def ensure_message_verifications_table() -> None:
    """
    Ensures the table exists for any verification/audit hooks the chat route expects.
    Safe to call on startup.
    """
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS message_verifications (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                reason TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_message_verifications_user ON message_verifications(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_message_verifications_chat ON message_verifications(chat_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_message_verifications_message ON message_verifications(message_id)"
        )
