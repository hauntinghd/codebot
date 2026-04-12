"""BYOK (Bring Your Own Key) routes."""
from __future__ import annotations

import logging
import sqlite3
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request

from backend.auth import current_user
from backend.byok import encrypt_api_key
from backend.config import API_PREFIX
from backend.database import db
from backend.models import ApiKeyOut, ApiKeySetIn

logger = logging.getLogger("codebot")


def register_routes(api: FastAPI):
    """Register BYOK routes."""

    @api.post(f"{API_PREFIX}/api-key", response_model=Dict[str, str])
    async def set_api_key(
        payload: ApiKeySetIn,
        request: Request,
        u: sqlite3.Row = Depends(current_user),
    ) -> Dict[str, str]:
        """Set user's API key (BYOK). Available for all users (required for CodeBot to function)."""
        user_id = str(u["id"])
        is_admin = int(u["is_admin"]) if "is_admin" in u.keys() else 0
        plan = str(u["plan"]) if "plan" in u.keys() else "none"
        
        # Allow BYOK for admins always, or paid tiers
        if is_admin != 1 and plan not in ("basic", "pro", "elite"):
            raise HTTPException(
                status_code=403,
                detail="BYOK is only available for Basic ($50/m) and Pro ($250/m) subscriptions, or admin users"
            )
        
        # Validate provider
        valid_providers = ["openai", "anthropic", "gemini", "replicate", "grok"]
        if payload.provider.lower() not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Supported: {', '.join(valid_providers)}"
            )
        
        # Validate API key format (basic checks)
        api_key = payload.api_key.strip()
        if not api_key or len(api_key) < 10:
            raise HTTPException(status_code=400, detail="Invalid API key format")
        
        # Encrypt and store
        encrypted_key = encrypt_api_key(api_key)
        provider = payload.provider.lower()
        
        with db() as conn:
            conn.execute(
                "UPDATE users SET api_key_encrypted = ?, api_key_provider = ? WHERE id = ?",
                (encrypted_key, provider, user_id),
            )
        
        logger.info(f"User {user_id} set BYOK API key (provider: {provider})")
        return {"ok": "true", "message": "API key saved successfully"}

    @api.get(f"{API_PREFIX}/api-key", response_model=ApiKeyOut)
    async def get_api_key_status(
        u: sqlite3.Row = Depends(current_user),
    ) -> ApiKeyOut:
        """Get user's API key status (doesn't return the actual key)."""
        encrypted_key = u["api_key_encrypted"] if "api_key_encrypted" in u.keys() else None
        provider = u["api_key_provider"] if "api_key_provider" in u.keys() else None
        
        return ApiKeyOut(
            has_key=bool(encrypted_key),
            provider=str(provider) if provider else None,
        )

    @api.delete(f"{API_PREFIX}/api-key")
    async def delete_api_key(
        u: sqlite3.Row = Depends(current_user),
    ) -> Dict[str, str]:
        """Delete user's API key."""
        user_id = str(u["id"])
        
        with db() as conn:
            conn.execute(
                "UPDATE users SET api_key_encrypted = NULL, api_key_provider = 'openai' WHERE id = ?",
                (user_id,),
            )
        
        logger.info(f"User {user_id} deleted BYOK API key")
        return {"ok": "true", "message": "API key deleted successfully"}

