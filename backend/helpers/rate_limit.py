"""Rate limiting utilities for API requests."""
from __future__ import annotations

import time
from typing import Optional

from backend.database import _now, db


def check_rate_limit(user_id: str, has_byok: bool = False, is_admin: bool = False) -> tuple[bool, int]:
    """
    Check if user is within rate limits.
    
    Args:
        user_id: User ID
        has_byok: Whether user has Bring Your Own Key configured
        is_admin: Whether user is admin
    
    Returns:
        (allowed: bool, remaining: int)
    """
    if is_admin:
        return True, 9999  # Unlimited for admins
    
    # Rate limits per hour
    limit = 5000 if has_byok else 5000
    window_seconds = 3600  # 1 hour
    
    now = _now()
    reset_time = now + window_seconds
    
    with db() as conn:
        # Get or create rate limit record
        row = conn.execute(
            "SELECT request_count, reset_at FROM rate_limits WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        
        if row:
            request_count = int(row["request_count"])
            reset_at = int(row["reset_at"])
            
            # Check if window expired
            if now >= reset_at:
                # Reset window
                conn.execute(
                    "UPDATE rate_limits SET window_start = ?, request_count = 1, reset_at = ? WHERE user_id = ?",
                    (now, reset_time, user_id)
                )
                return True, limit - 1
            
            # Check if over limit
            if request_count >= limit:
                return False, 0
            
            # Increment counter
            conn.execute(
                "UPDATE rate_limits SET request_count = request_count + 1 WHERE user_id = ?",
                (user_id,)
            )
            return True, limit - request_count - 1
        else:
            # Create new record
            conn.execute(
                "INSERT INTO rate_limits (user_id, window_start, request_count, reset_at, created_at) VALUES (?, ?, 1, ?, ?)",
                (user_id, now, reset_time, now)
            )
            return True, limit - 1


def get_rate_limit_info(user_id: str, has_byok: bool = False, is_admin: bool = False) -> dict:
    """
    Get rate limit information for a user.
    
    Returns:
        {
            "limit": int,
            "remaining": int,
            "reset_at": int (unix timestamp)
        }
    """
    if is_admin:
        return {"limit": 9999, "remaining": 9999, "reset_at": _now() + 3600}
    
    limit = 5000 if has_byok else 5000
    
    with db() as conn:
        row = conn.execute(
            "SELECT request_count, reset_at FROM rate_limits WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        
        if row:
            request_count = int(row["request_count"])
            reset_at = int(row["reset_at"])
            
            # Check if window expired
            if _now() >= reset_at:
                return {"limit": limit, "remaining": limit, "reset_at": _now() + 3600}
            
            return {
                "limit": limit,
                "remaining": max(0, limit - request_count),
                "reset_at": reset_at
            }
        else:
            return {"limit": limit, "remaining": limit, "reset_at": _now() + 3600}
