"""Admin routes - credit management and costs."""
from __future__ import annotations

import sqlite3
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException

from backend.auth import current_user, get_user_by_id
from backend.config import API_PREFIX
from backend.credits import add_credits, get_user_credits
from backend.database import db
from backend.models import AddCreditsIn


def require_admin(u: sqlite3.Row = Depends(current_user)) -> sqlite3.Row:
    """Require admin access."""
    if int(u["is_admin"]) != 1:
        raise HTTPException(status_code=403, detail="Admin access required")
    return u


def register_routes(api: FastAPI):
    """Register admin routes."""

    @api.get(f"{API_PREFIX}/admin/credits/{{user_id}}")
    async def get_user_credits_admin(
        user_id: str,
        admin: sqlite3.Row = Depends(require_admin),
    ) -> Dict[str, Any]:
        """View user credits and recent transactions."""
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        credits = get_user_credits(user_id)
        
        # Get recent transactions
        with db() as conn:
            rows = conn.execute(
                """
                SELECT id, amount, description, model_used, tokens_input, tokens_output, created_at
                FROM credit_transactions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (user_id,),
            ).fetchall()
        
        transactions = [
            {
                "id": str(r["id"]),
                "amount": float(r["amount"]),
                "description": str(r["description"]),
                "model_used": str(r["model_used"]) if r["model_used"] else None,
                "tokens_input": int(r["tokens_input"]) if r["tokens_input"] else None,
                "tokens_output": int(r["tokens_output"]) if r["tokens_output"] else None,
                "created_at": int(r["created_at"]),
            }
            for r in rows
        ]
        
        return {
            "user_id": user_id,
            "email": str(user["email"]),
            "credits_remaining": credits,
            "plan": str(user["plan"] or "none"),
            "transactions": transactions,
        }

    @api.post(f"{API_PREFIX}/admin/credits/{{user_id}}/add")
    async def add_credits_admin(
        user_id: str,
        payload: AddCreditsIn,
        admin: sqlite3.Row = Depends(require_admin),
    ) -> Dict[str, Any]:
        """Manually add credits to a user."""
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if payload.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        
        add_credits(user_id, payload.amount, payload.description)
        
        return {
            "ok": True,
            "user_id": user_id,
            "amount_added": payload.amount,
            "credits_remaining": get_user_credits(user_id),
        }

    @api.get(f"{API_PREFIX}/admin/costs")
    async def get_costs_admin(admin: sqlite3.Row = Depends(require_admin)) -> Dict[str, Any]:
        """View total costs, credits issued, and profit margin."""
        with db() as conn:
            # Total credits issued
            credits_row = conn.execute(
                "SELECT SUM(amount) as total FROM credit_transactions WHERE amount > 0"
            ).fetchone()
            total_credits_issued = float(credits_row["total"] or 0)
            
            # Total credits spent
            spent_row = conn.execute(
                "SELECT SUM(ABS(amount)) as total FROM credit_transactions WHERE amount < 0"
            ).fetchone()
            total_credits_spent = float(spent_row["total"] or 0)
            
            # Total transactions
            count_row = conn.execute("SELECT COUNT(*) as count FROM credit_transactions").fetchone()
            total_transactions = int(count_row["count"] or 0)
            
            # Model usage breakdown
            model_rows = conn.execute(
                """
                SELECT model_used, COUNT(*) as count, SUM(ABS(amount)) as total_cost
                FROM credit_transactions
                WHERE model_used IS NOT NULL AND amount < 0
                GROUP BY model_used
                """
            ).fetchall()
            
            model_usage = [
                {
                    "model": str(r["model_used"]),
                    "count": int(r["count"]),
                    "total_cost": float(r["total_cost"]),
                }
                for r in model_rows
            ]
        
        return {
            "total_credits_issued": total_credits_issued,
            "total_credits_spent": total_credits_spent,
            "total_transactions": total_transactions,
            "model_usage": model_usage,
            "profit_margin": total_credits_issued - total_credits_spent,
        }

