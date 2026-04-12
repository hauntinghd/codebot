# backend/routes/settings.py
from __future__ import annotations

import sqlite3
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import current_user, _pbkdf2_hash, _pbkdf2_verify
from backend.config import API_PREFIX
from backend.database import db

router = APIRouter()


class ProfileUpdateIn(BaseModel):
    display_name: str


@router.post(f"{API_PREFIX}/profile")
async def update_profile(payload: ProfileUpdateIn, u: sqlite3.Row = Depends(current_user)) -> Dict[str, Any]:
    display_name = (payload.display_name or "").strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="Display name cannot be empty")

    # Update only if column exists; otherwise fail loudly so you fix schema explicitly.
    with db() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "display_name" not in cols:
            raise HTTPException(
                status_code=500,
                detail="users.display_name column missing. Add it or change SettingsPage to use an existing field.",
            )

        conn.execute(
            "UPDATE users SET display_name = ? WHERE id = ?",
            (display_name, u["id"]),
        )

    return {"ok": True}


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


@router.post(f"{API_PREFIX}/auth/change-password")
async def change_password(payload: ChangePasswordIn, u: sqlite3.Row = Depends(current_user)) -> Dict[str, Any]:
    cur = (payload.current_password or "").strip()
    new = (payload.new_password or "").strip()

    if not cur or not new:
        raise HTTPException(status_code=400, detail="Missing password fields")
    if len(new) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    pw_hash = str(u["pw_hash"] or "")
    if not pw_hash:
        # This happens for OAuth-only accounts. You can choose to allow setting a password instead,
        # but your UI currently asks for "current password", so we block.
        raise HTTPException(status_code=400, detail="This account does not have a password set (OAuth-only).")

    if not _pbkdf2_verify(cur, pw_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    new_hash = _pbkdf2_hash(new)

    with db() as conn:
        conn.execute(
            "UPDATE users SET pw_hash = ? WHERE id = ?",
            (new_hash, u["id"]),
        )

    return {"ok": True}
