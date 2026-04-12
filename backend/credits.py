"""
backend/credits.py

Credits compatibility + service layer.

Other modules import these symbols from backend.credits:
- get_user_credits, add_credits (routes/admin.py)
- initialize_user_credits (routes/billing.py)
- check_and_reset_credits, usage_bump (routes/chat.py and others)

This module MUST NOT crash at import time.
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Dict, Any

from backend.database import db

log = logging.getLogger("codebot")


# -----------------------------
# DB bootstrap (safe / idempotent)
# -----------------------------
def _ensure_tables() -> None:
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_credits (
                user_id TEXT PRIMARY KEY,
                credits_remaining REAL NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL DEFAULT 0,
                last_reset_at INTEGER NOT NULL DEFAULT 0,
                plan TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS credit_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                model_used TEXT,
                created_at INTEGER NOT NULL
            )
            """
        )


def initialize_user_credits(user_id: str, *, plan: str = "starter", starting_credits: float = 0.0) -> None:
    """
    Ensures a user has a row in user_credits.
    billing.py expects this symbol to exist.
    """
    _ensure_tables()
    now = int(time.time())
    with db() as conn:
        row = conn.execute(
            "SELECT user_id FROM user_credits WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row:
            # Keep plan up to date; do not overwrite credits.
            conn.execute(
                "UPDATE user_credits SET plan = COALESCE(?, plan), updated_at = ? WHERE user_id = ?",
                (plan, now, user_id),
            )
            return

        conn.execute(
            """
            INSERT INTO user_credits (user_id, credits_remaining, updated_at, last_reset_at, plan)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, float(starting_credits), now, 0, plan),
        )


def get_user_credits(user_id: str) -> float:
    _ensure_tables()
    with db() as conn:
        row = conn.execute(
            "SELECT credits_remaining FROM user_credits WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            initialize_user_credits(user_id, plan="starter", starting_credits=0.0)
            return 0.0
        return float(row["credits_remaining"])


def add_credits(
    user_id: str,
    amount: float,
    *,
    description: str = "Credit adjustment",
    model_used: Optional[str] = None,
) -> float:
    """
    Adds (or subtracts if amount < 0) credits and writes a transaction row.
    admin.py expects this symbol to exist.
    Returns the new balance.
    """
    _ensure_tables()
    now = int(time.time())

    with db() as conn:
        row = conn.execute(
            "SELECT credits_remaining FROM user_credits WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            initialize_user_credits(user_id, plan="starter", starting_credits=0.0)
            current = 0.0
        else:
            current = float(row["credits_remaining"])

        new_balance = current + float(amount)

        conn.execute(
            "UPDATE user_credits SET credits_remaining = ?, updated_at = ? WHERE user_id = ?",
            (new_balance, now, user_id),
        )

        conn.execute(
            """
            INSERT INTO credit_transactions (user_id, amount, description, model_used, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, float(amount), description, model_used, now),
        )

    return float(new_balance)


def check_and_reset_credits(user_id: str) -> None:
    """
    Placeholder reset hook.

    If you later implement plan-based monthly resets, do it here.
    For now: do nothing and never crash.
    """
    _ensure_tables()
    return


def usage_bump(
    user_id: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_usd: float = 0.0,
    provider: str = "",
    model: str = "",
) -> None:
    """
    Backwards-compat shim. MUST NOT crash.

    Preferred path:
      backend.services.usage.usage_bump(...)
    Fallback:
      subtract cost_usd from credit ledger if cost_usd > 0
    """
    # Try real usage service if present
    try:
        from backend.services.usage import usage_bump as real_usage_bump  # type: ignore

        try:
            real_usage_bump(
                user_id=user_id,
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                cost_usd=float(cost_usd),
                provider=str(provider),
                model=str(model),
            )
            return
        except TypeError:
            # older signature fallback
            real_usage_bump(user_id, int(prompt_tokens), int(completion_tokens))
            return
    except Exception as e:
        log.warning("usage_bump shim could not call backend.services.usage.usage_bump: %s", e)

    # Fallback ledger update
    try:
        if float(cost_usd) > 0:
            add_credits(
                user_id,
                -float(cost_usd),
                description="Model usage",
                model_used=str(model) if model else None,
            )
    except Exception as e:
        log.warning("usage_bump fallback ledger update failed: %s", e)


def get_recent_transactions(user_id: str, limit: int = 20) -> list[Dict[str, Any]]:
    """
    Utility for routes that want to show recent credit activity.
    """
    _ensure_tables()
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, amount, description, model_used, created_at
            FROM credit_transactions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, int(limit)),
        ).fetchall()

    return [
        {
            "id": str(r["id"]),
            "amount": float(r["amount"]),
            "description": str(r["description"]) if r["description"] else "",
            "model_used": str(r["model_used"]) if r["model_used"] else None,
            "created_at": int(r["created_at"]),
        }
        for r in rows
    ]
