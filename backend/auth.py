# backend/auth.py
"""Authentication, JWT, OAuth, and user management."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import uuid
from typing import Any, Dict, Optional, Tuple

from fastapi import Depends, Header, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordBearer

from backend.config import (
    ACCESS_TOKEN_TTL_SECONDS,
    APP_BASE_PATH,
    DEV_MODE,
    EMAIL_RE,
    JWT_SECRET,
    REFRESH_TOKEN_TTL_SECONDS,
)
from backend.database import _now, db

logger = logging.getLogger("codebot")

# -------------------------
# Helpers
# -------------------------
def normalize_email(email: str) -> str:
    """Normalize email address."""
    return (email or "").strip().lower()


def validate_email(email: str) -> None:
    """Validate email format."""
    if not EMAIL_RE.match(email or ""):
        raise HTTPException(status_code=400, detail="Invalid email")


def _truthy_header(val: str) -> bool:
    v = (val or "").strip().lower()
    return v in ("1", "true", "yes", "on")


# -------------------------
# Admin allowlist (email)
# -------------------------
def _admin_emails() -> set[str]:
    """
    Admin emails are determined by env var ADMIN_EMAILS (comma-separated).
    Always includes omatic657@gmail.com as a hard fallback.
    """
    raw = (os.getenv("ADMIN_EMAILS") or os.getenv("CODEBOT_ADMIN_EMAILS") or "").strip()
    items = [normalize_email(x) for x in raw.split(",")] if raw else []
    return {e for e in set(items) if e}


def is_admin_email(email: str) -> bool:
    return normalize_email(email) in _admin_emails()


# -------------------------
# Test-mode allowlist (email)
# -------------------------
def _test_mode_emails() -> set[str]:
    """
    Test-mode users are determined by env var TEST_MODE_EMAILS (comma-separated).
    Always includes admin emails by default.
    """
    raw = (os.getenv("TEST_MODE_EMAILS") or "").strip()
    items = [normalize_email(x) for x in raw.split(",")] if raw else []
    return {e for e in (_admin_emails() | set(items)) if e}


def _is_test_mode_user(*args: Any, **kwargs: Any) -> bool:
    """
    Backwards-compatible test-mode gate.

    Supports BOTH call styles:
      1) _is_test_mode_user(u: Dict[str, Any]) -> bool
      2) _is_test_mode_user(request: Request, u: Dict[str, Any]) -> bool
    """
    request: Optional[Request] = None
    u: Optional[Dict[str, Any]] = None

    if len(args) == 1 and isinstance(args[0], dict):
        u = args[0]
    elif len(args) >= 2 and isinstance(args[0], Request) and isinstance(args[1], dict):
        request = args[0]
        u = args[1]

    if u is None:
        maybe_u = kwargs.get("u") or kwargs.get("user")
        if isinstance(maybe_u, dict):
            u = maybe_u
    if request is None:
        maybe_r = kwargs.get("request")
        if isinstance(maybe_r, Request):
            request = maybe_r

    if not u:
        return False

    try:
        if DEV_MODE:
            return True

        if request is not None:
            hdr = request.headers.get("X-Test-Mode")
            if hdr is not None and not _truthy_header(hdr):
                return False

        if int(u.get("is_admin") or 0) == 1:
            return True

        email = normalize_email(str(u.get("email") or ""))
        if email and email in _test_mode_emails():
            return True

        if int(u.get("is_test_mode") or 0) == 1:
            return True
        if str(u.get("plan") or "").lower() in ("test", "tester", "internal"):
            return True
    except Exception:
        pass

    return False


# -------------------------
# Password hashing (PBKDF2)
# -------------------------
def _pbkdf2_hash(password: str) -> str:
    import secrets

    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000, dklen=32)
    salt_b64 = base64.urlsafe_b64encode(salt).decode("utf-8").rstrip("=")
    dk_b64 = base64.urlsafe_b64encode(dk).decode("utf-8").rstrip("=")
    return f"pbkdf2_sha256:100000:{salt_b64}:{dk_b64}"


def _pbkdf2_verify(password: str, encoded: str) -> bool:
    try:
        parts = encoded.split(":")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        _, it_s, salt_b64, dk_b64 = parts
        iterations = int(it_s)

        def restore_padding(s: str) -> str:
            return s + "=" * (-len(s) % 4)

        salt = base64.urlsafe_b64decode(restore_padding(salt_b64).encode())
        expected = base64.urlsafe_b64decode(restore_padding(dk_b64).encode())
        got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)
        return hmac.compare_digest(got, expected)
    except Exception:
        return False


# -------------------------
# JWT (minimal, dependency-free)
# -------------------------
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("utf-8"))


def jwt_encode(payload: Dict[str, Any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url(sig)}"


def jwt_decode(token: str, secret: str) -> Dict[str, Any]:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".", 2)
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        sig = _b64url_decode(sig_b64)
        expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if "exp" in payload and int(payload["exp"]) < _now():
            raise ValueError("token expired")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def make_access_token(user_id: str) -> str:
    now = _now()
    payload = {"sub": user_id, "type": "access", "iat": now, "exp": now + ACCESS_TOKEN_TTL_SECONDS}
    return jwt_encode(payload, JWT_SECRET)


def make_refresh_token(user_id: str, token_id: str) -> str:
    now = _now()
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": token_id,
        "iat": now,
        "exp": now + REFRESH_TOKEN_TTL_SECONDS,
    }
    return jwt_encode(payload, JWT_SECRET)


oauth2 = OAuth2PasswordBearer(tokenUrl=f"{APP_BASE_PATH}/api/auth/login")


# -------------------------
# User management
# -------------------------
def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_user_by_id(user_id: str) -> Optional[sqlite3.Row]:
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def create_user(email: str, password: str) -> str:
    user_id = str(uuid.uuid4())
    pw_hash = _pbkdf2_hash(password)
    now = _now()
    is_admin = 1 if is_admin_email(email) else 0

    with db() as conn:
        conn.execute(
            "INSERT INTO users (id, email, pw_hash, created_at, is_admin) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, pw_hash, now, is_admin),
        )
    return user_id


def create_refresh_session(user_id: str, user_agent: str, ip: str) -> Tuple[str, str]:
    token_id = str(uuid.uuid4())
    now = _now()
    expires_at = now + REFRESH_TOKEN_TTL_SECONDS
    with db() as conn:
        conn.execute(
            "INSERT INTO refresh_tokens (id, user_id, issued_at, expires_at, revoked_at, user_agent, ip) "
            "VALUES (?, ?, ?, ?, 0, ?, ?)",
            (token_id, user_id, now, expires_at, user_agent[:200], ip[:64]),
        )
    return token_id, make_refresh_token(user_id, token_id)


def revoke_refresh_token(token_id: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE refresh_tokens SET revoked_at = ? WHERE id = ? AND revoked_at = 0",
            (_now(), token_id),
        )


def validate_refresh_token(refresh_token: str) -> Tuple[str, str]:
    payload = jwt_decode(refresh_token, JWT_SECRET)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = str(payload.get("sub", ""))
    token_id = str(payload.get("jti", ""))
    if not user_id or not token_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    with db() as conn:
        row = conn.execute(
            "SELECT * FROM refresh_tokens WHERE id = ? AND user_id = ?",
            (token_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Refresh session not found")
        if int(row["revoked_at"] or 0) != 0:
            raise HTTPException(status_code=401, detail="Refresh token revoked")
        if int(row["expires_at"]) < _now():
            raise HTTPException(status_code=401, detail="Refresh token expired")

    return user_id, token_id


# -------------------------
# Session management (SessionMiddleware ONLY)
# -------------------------
def get_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


def get_session_user_id(request: Request) -> Optional[str]:
    """
    Source of truth: request.session (provided by Starlette SessionMiddleware).
    We do NOT decode cookies manually. Starlette handles that.
    """
    try:
        sess = getattr(request, "session", None)
        if isinstance(sess, dict):
            uid = sess.get("user_id")
            return str(uid) if uid else None
    except Exception:
        pass
    return None


def set_session(response: Response, user_id: str, request: Optional[Request] = None) -> None:
    """
    Set login session into request.session.
    SessionMiddleware will emit/update the signed session cookie automatically.
    """
    if request is None:
        return
    try:
        if hasattr(request, "session") and isinstance(request.session, dict):
            request.session["user_id"] = str(user_id)
    except Exception:
        pass


def clear_session(response: Response, request: Optional[Request] = None) -> None:
    """
    Clear request.session. SessionMiddleware will clear the cookie.
    Also explicitly delete the SessionMiddleware cookie name as a safety belt.
    """
    if request is None:
        return

    try:
        if hasattr(request, "session") and isinstance(request.session, dict):
            request.session.clear()
    except Exception:
        pass

    # Safety belt: delete the configured SessionMiddleware cookie name.
    try:
        cookie_name = f"cb_session{(APP_BASE_PATH or '').replace('/', '_')}"
        cookie_path = (APP_BASE_PATH or "/").rstrip("/") or "/"
        response.delete_cookie(key=cookie_name, path=cookie_path)
    except Exception:
        pass


# -------------------------
# Current user dependency
# -------------------------
async def current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    user_id: Optional[str] = None

    # Token first (API calls)
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            payload = jwt_decode(token, JWT_SECRET)
            if payload.get("type") == "access":
                user_id = str(payload.get("sub", "")) or None
        except Exception:
            user_id = None

    # Session fallback (web UI)
    if not user_id:
        user_id = get_session_user_id(request)

    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    row = get_user_by_id(user_id)
    if not row:
        raise HTTPException(status_code=401, detail="User not found")

    # Enforce admin by email every time (auto-promote in DB if needed)
    try:
        email = normalize_email(str(row["email"] or ""))
        desired_admin = 1 if is_admin_email(email) else 0
        current_admin = int(row["is_admin"] or 0)
        if desired_admin == 1 and current_admin != 1:
            with db() as conn:
                conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
            row = get_user_by_id(user_id) or row
    except Exception:
        pass

    try:
        return {k: row[k] for k in row.keys()}
    except Exception:
        try:
            return dict(row)  # type: ignore[arg-type]
        except Exception:
            return {"raw": row}


# -------------------------
# Subscription helpers
# -------------------------
def is_active_subscription(u: Dict[str, Any]) -> bool:
    if int(u.get("is_admin") or 0) == 1:
        return True

    status = str(u.get("subscription_status") or "none")
    cpe = int(u.get("current_period_end") or 0)

    if status in ("active", "trialing"):
        if cpe == 0:
            return True
        return cpe > _now()

    return False


async def require_subscribed(
    request: Request,
    u: Dict[str, Any] = Depends(current_user),
) -> Dict[str, Any]:
    if DEV_MODE:
        return u

    if int(u.get("is_admin") or 0) == 1:
        return u

    if not is_active_subscription(u):
        raise HTTPException(status_code=402, detail="Subscription required")

    return u


# -------------------------
# Admin helpers
# -------------------------
def require_admin(u: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    email = normalize_email(str(u.get("email") or ""))
    if not is_admin_email(email):
        raise HTTPException(status_code=403, detail="Admin access required")
    if int(u.get("is_admin") or 0) != 1:
        raise HTTPException(status_code=403, detail="Admin access denied")
    return u
