# backend/routes/credits.py
"""Credits routes."""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Request

from backend.auth import require_subscribed
from backend.config import API_PREFIX
from backend.credits import check_and_reset_credits, get_user_credits
from backend.database import db


def register_routes(api: FastAPI):
    """Register credits routes."""

    @api.get(f"{API_PREFIX}/credits")
    async def get_credits(
        request: Request,
        u: sqlite3.Row = Depends(require_subscribed),
    ) -> Dict[str, Any]:
        user_id = str(u["id"])

        # Non-admin users: ensure monthly reset happens
        if int(u["is_admin"]) != 1:
            check_and_reset_credits(user_id)
            credits_row = get_user_credits(user_id)
            credits_remaining = float(credits_row.get("credits_remaining", 0.0))
        else:
            # Admin bypass (if that's your intended behavior)
            credits_remaining = 0.0

        # Recent transactions
        with db() as conn:
            rows = conn.execute(
                """
                SELECT id, amount, description, model_used, created_at
                FROM credit_transactions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (user_id,),
            ).fetchall()

        transactions: List[Dict[str, Any]] = [
            {
                "id": str(r["id"]),
                "amount": float(r["amount"]),
                "description": str(r["description"]),
                "model_used": str(r["model_used"]) if r["model_used"] else None,
                "created_at": int(r["created_at"]),
            }
            for r in rows
        ]

        return {
            "credits_remaining": credits_remaining,
            "plan": str(u["plan"] or "none"),
            "transactions": transactions,
        }
