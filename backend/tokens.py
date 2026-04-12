"""CBT token management: simple DB-backed token balances and transactions."""
from __future__ import annotations

import logging
import sqlite3
import uuid
from backend.database import db, _now

logger = logging.getLogger("codebot.tokens")


def _ensure_tables() -> None:
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_tokens (
                user_id TEXT PRIMARY KEY,
                cbt_balance INTEGER DEFAULT 0,
                updated_at INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS token_transactions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                amount INTEGER,
                description TEXT,
                created_at INTEGER
            )
            """
        )


def get_user_tokens(user_id: str) -> int:
    _ensure_tables()
    with db() as conn:
        row = conn.execute("SELECT cbt_balance FROM user_tokens WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return int(row[0] or 0)
        return 0


def add_user_tokens(user_id: str, amount: int, description: str = "") -> None:
    """Add CBT tokens to a user's balance and log transaction."""
    _ensure_tables()
    now = _now()
    tx_id = str(uuid.uuid4())
    with db() as conn:
        # Insert or update balance
        conn.execute(
            "INSERT INTO user_tokens (user_id, cbt_balance, updated_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET cbt_balance = user_tokens.cbt_balance + excluded.cbt_balance, updated_at = excluded.updated_at",
            (user_id, int(amount), now),
        )
        # Insert transaction
        conn.execute(
            "INSERT INTO token_transactions (id, user_id, amount, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (tx_id, user_id, int(amount), description, now),
        )


def set_user_tokens(user_id: str, amount: int) -> None:
    _ensure_tables()
    now = _now()
    with db() as conn:
        conn.execute(
            "INSERT INTO user_tokens (user_id, cbt_balance, updated_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET cbt_balance = excluded.cbt_balance, updated_at = excluded.updated_at",
            (user_id, int(amount), now),
        )
