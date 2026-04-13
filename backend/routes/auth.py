# backend/routes/auth.py
"""Authentication routes - OAuth, login, register, logout."""
from __future__ import annotations

import logging
import os
import secrets
import time
from typing import Any, Dict, Mapping

import httpx
from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from backend.auth import (
    _pbkdf2_hash,
    _pbkdf2_verify,
    clear_session,
    create_refresh_session,
    create_user,
    current_user,
    get_ip,
    get_session_user_id,
    get_user_by_email,
    get_user_by_id,
    make_access_token,
    normalize_email,
    revoke_refresh_token,
    set_session,
    validate_email,
    validate_refresh_token,
)
from backend.config import API_PREFIX, APP_BASE_PATH
from backend.database import _now, db
from backend.models import LoginIn, MeOut, RefreshIn, RegisterIn, TokenOut

logger = logging.getLogger("codebot.auth.routes")

# Simple in-memory IP rate limiter for auth endpoints (register/login)
_auth_rate_store: dict[str, list[float]] = {}
_AUTH_RATE_LIMIT_WINDOW = 60 * 60  # 1 hour
_REGISTER_LIMIT = 5  # max registrations per IP per hour
_LOGIN_LIMIT = 20  # max logins per IP per hour


def _check_auth_ip_rate(ip: str, limit: int, window: int = _AUTH_RATE_LIMIT_WINDOW) -> bool:
    now = time.time()
    arr = _auth_rate_store.get(ip) or []
    arr = [t for t in arr if t > now - window]  # purge old
    if len(arr) >= limit:
        _auth_rate_store[ip] = arr
        return False
    arr.append(now)
    _auth_rate_store[ip] = arr
    return True


async def _verify_recaptcha(token: str) -> bool:
    """Verify reCAPTCHA token if secret is configured via env var RECAPTCHA_SECRET."""
    secret = os.getenv("RECAPTCHA_SECRET", "").strip()
    if not secret:
        return True
    verify_url = "https://www.google.com/recaptcha/api/siteverify"
    async with httpx.AsyncClient() as client:
        r = await client.post(verify_url, data={"secret": secret, "response": token}, timeout=10.0)
        if r.status_code != 200:
            return False
        try:
            data = r.json()
            return bool(data.get("success"))
        except Exception:
            return False


def _admin_emails() -> set[str]:
    """
    Comma-separated list of emails that should be admin.
    Example:
      CODEBOT_ADMIN_EMAILS=omatic657@gmail.com,other@nyptidindustries.com
    """
    raw = os.getenv("CODEBOT_ADMIN_EMAILS", "") or ""
    out: set[str] = set()
    for part in raw.split(","):
        e = (part or "").strip().lower()
        if e:
            out.add(e)
    return out


def _maybe_promote_admin(email: str, user_id: str) -> None:
    """If email is in CODEBOT_ADMIN_EMAILS, set is_admin=1."""
    try:
        email_norm = (email or "").strip().lower()
        if not email_norm:
            return
        if email_norm not in _admin_emails():
            return
        with db() as conn:
            conn.execute("UPDATE users SET is_admin=1 WHERE id = ?", (user_id,))
    except Exception as e:
        logger.warning(f"Admin promotion failed for {email}: {e}")


def _bootstrap_admin_if_enabled(email: str, user_id: str) -> None:
    """
    Optional safety valve:
    If CODEBOT_BOOTSTRAP_ADMIN=true and there are NO admins yet,
    promote the logging-in user to admin (useful for fresh installs).
    """
    try:
        if (os.getenv("CODEBOT_BOOTSTRAP_ADMIN", "").strip().lower() not in ("1", "true", "yes")):
            return
        with db() as conn:
            row = conn.execute("SELECT COUNT(1) AS c FROM users WHERE is_admin = 1").fetchone()
            try:
                c = int(row["c"])  # type: ignore[index]
            except Exception:
                c = int(row[0]) if row else 0
            if c > 0:
                return
            conn.execute("UPDATE users SET is_admin=1 WHERE id = ?", (user_id,))
            logger.warning(f"BOOTSTRAP ADMIN: promoted {email} ({user_id}) to admin")
    except Exception as e:
        logger.warning(f"Bootstrap admin failed: {e}")


def is_oauth_configured(oauth) -> bool:
    """
    OAuth enablement:
    - Prefer explicit config flag if present
    - But ALSO allow OAuth when oauth.google exists (runtime-registered) so we don't soft-disable in prod.
    """
    try:
        from backend.config import OAUTH_ENABLED

        if bool(OAUTH_ENABLED):
            return True
    except Exception:
        pass

    # Fallback: if the OAuth client is actually registered, treat as enabled.
    try:
        return bool(oauth is not None and getattr(oauth, "google", None))
    except Exception:
        return False


def _base_url(request: Request) -> str:
    """
    Best-effort external base URL derived from the inbound request.
    This is critical for OAuth state integrity: start host must match callback host.
    """
    # Starlette builds base_url from the ASGI scope. With ProxyHeadersMiddleware (uvicorn proxy_headers),
    # this respects X-Forwarded-Proto/Host.
    return str(request.base_url).rstrip("/")


def _oauth_callback_url(request: Request) -> str:
    """
    Compute callback URL.
    Priority:
      1) GOOGLE_OAUTH_REDIRECT (explicit override)
      2) Derived from inbound request host (prevents mismatching_state when frontend hits localhost vs prod)
    """
    try:
        from backend.config import GOOGLE_OAUTH_REDIRECT

        override = (GOOGLE_OAUTH_REDIRECT or "").strip()
        if override:
            return override
    except Exception:
        pass

    # Derived from actual request host (fixes mismatching_state across envs)
    base = _base_url(request)
    base_path = (APP_BASE_PATH or "").rstrip("/")
    # API_PREFIX already includes "/api"
    return f"{base}{base_path}{API_PREFIX}/auth/oauth/google/callback"


def _record_to_dict(rec: Any) -> dict[str, Any]:
    """
    Normalize DB records to a plain dict so we can safely use .get().

    - sqlite3.Row supports dict(row) -> {col: val}
    - Some code paths may already return dict-like objects
    """
    if rec is None:
        return {}
    if isinstance(rec, dict):
        return rec
    try:
        return dict(rec)  # sqlite3.Row and many mapping-like objects
    except Exception:
        # Last resort: attempt Mapping interface
        if isinstance(rec, Mapping):
            return {k: rec[k] for k in rec.keys()}  # type: ignore[attr-defined]
        return {}


def register_routes(api, oauth):
    # ---------------------------------------------------------------------
    # Owner password reset (bootstrap only — uses ADMIN_EMAILS env)
    # ---------------------------------------------------------------------
    @api.post(f"{API_PREFIX}/auth/reset-owner")
    async def reset_owner_password(request: Request):
        """Reset password for admin email accounts. No auth required — validates email against ADMIN_EMAILS."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")
        email = normalize_email(body.get("email", ""))
        new_pw = body.get("password", "")
        if not email or not new_pw or len(new_pw) < 6:
            raise HTTPException(status_code=400, detail="Email and password (6+ chars) required")
        if email not in _admin_emails():
            raise HTTPException(status_code=403, detail="Not an admin email")
        row = get_user_by_email(email)
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        new_hash = _pbkdf2_hash(new_pw)
        with db() as conn:
            conn.execute("UPDATE users SET pw_hash=?, is_admin=1 WHERE id=?", (new_hash, str(row["id"])))
        return {"ok": True, "message": "Password reset and admin promoted"}

    # ---------------------------------------------------------------------
    # Email/Password Auth (JWT)
    # ---------------------------------------------------------------------
    @api.post(f"{API_PREFIX}/auth/register", response_model=TokenOut)
    async def register(payload: RegisterIn, request: Request) -> TokenOut:
        email = normalize_email(payload.email)
        validate_email(email)

        password = payload.password or ""
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

        if get_user_by_email(email):
            raise HTTPException(status_code=409, detail="Email already registered")

        ip = get_ip(request)
        if not _check_auth_ip_rate(ip, _REGISTER_LIMIT):
            raise HTTPException(
                status_code=429,
                detail="Too many registration attempts from this IP. Try again later.",
            )

        # Honeypot detection (if client sent unexpected hp field)
        raw: Any = None
        try:
            raw = await request.json()
            if isinstance(raw, dict) and raw.get("hp"):
                raise HTTPException(status_code=400, detail="Bot detection triggered")
        except Exception:
            pass

        # Optional reCAPTCHA
        captcha_token = raw.get("captcha_token") if isinstance(raw, dict) else None
        if captcha_token:
            ok = await _verify_recaptcha(captcha_token)
            if not ok:
                raise HTTPException(status_code=400, detail="reCAPTCHA verification failed")

        user_id = str(create_user(email, password))

        # Admin promotion hooks
        _maybe_promote_admin(email, user_id)
        _bootstrap_admin_if_enabled(email, user_id)

        ua = request.headers.get("user-agent", "")
        ip = get_ip(request)
        _, refresh = create_refresh_session(user_id, ua, ip)
        access = make_access_token(user_id)

        return TokenOut(access_token=access, refresh_token=refresh)

    @api.post(f"{API_PREFIX}/auth/login", response_model=TokenOut)
    async def login(payload: LoginIn, request: Request) -> TokenOut:
        email = normalize_email(payload.email)
        validate_email(email)

        ip = get_ip(request)
        if not _check_auth_ip_rate(ip, _LOGIN_LIMIT):
            raise HTTPException(status_code=429, detail="Too many login attempts from this IP. Try again later.")

        row = get_user_by_email(email)
        if not row:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not _pbkdf2_verify(payload.password or "", str(row["pw_hash"])):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        with db() as conn:
            conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (_now(), row["id"]))

        # Admin promotion hooks
        _maybe_promote_admin(email, str(row["id"]))
        _bootstrap_admin_if_enabled(email, str(row["id"]))

        ua = request.headers.get("user-agent", "")
        ip = get_ip(request)
        _, refresh = create_refresh_session(str(row["id"]), ua, ip)
        access = make_access_token(str(row["id"]))

        return TokenOut(access_token=access, refresh_token=refresh)

    @api.post(f"{API_PREFIX}/auth/refresh", response_model=TokenOut)
    async def refresh(payload: RefreshIn, request: Request) -> TokenOut:
        user_id, token_id = validate_refresh_token(payload.refresh_token)
        revoke_refresh_token(token_id)

        ua = request.headers.get("user-agent", "")
        ip = get_ip(request)
        _, new_refresh = create_refresh_session(user_id, ua, ip)
        new_access = make_access_token(user_id)

        return TokenOut(access_token=new_access, refresh_token=new_refresh)

    # ---------------------------------------------------------------------
    # Cookie-session -> JWT bridge (critical for Builder UI)
    # ---------------------------------------------------------------------
    @api.get(f"{API_PREFIX}/auth/session/token")
    async def session_token(request: Request) -> Dict[str, Any]:
        """
        Exchange an existing cookie-session (cb_session_*) for a JWT access token.
        Frontend stores this in localStorage for API calls.
        """
        uid = get_session_user_id(request)
        if not uid:
            raise HTTPException(status_code=401, detail="Not authenticated")
        access = make_access_token(str(uid))
        return {"access_token": access}

    @api.get(f"{API_PREFIX}/auth/session/bootstrap")
    async def session_bootstrap(request: Request) -> Dict[str, Any]:
        """
        One-call endpoint for the frontend login page after OAuth:
          - validates cookie-session
          - (re)applies admin promotion rules (in case env changed)
          - returns JWT
          - returns basic user info (me-lite)
        """
        uid = get_session_user_id(request)
        if not uid:
            raise HTTPException(status_code=401, detail="Not authenticated")

        u_raw = get_user_by_id(str(uid))
        if not u_raw:
            raise HTTPException(status_code=401, detail="Not authenticated")

        u = _record_to_dict(u_raw)

        email = str(u.get("email") or "")
        _maybe_promote_admin(email, str(uid))
        _bootstrap_admin_if_enabled(email, str(uid))

        u2_raw = get_user_by_id(str(uid)) or u_raw
        u2 = _record_to_dict(u2_raw)

        access = make_access_token(str(uid))
        return {
            "access_token": access,
            "me": {
                "id": str(u2.get("id") or uid),
                "email": str(u2.get("email") or email),
                "is_admin": bool(int(u2.get("is_admin") or 0)),
            },
        }

    # Debug helper: confirm cookie-session identity without JWT
    @api.get(f"{API_PREFIX}/auth/whoami")
    async def whoami(request: Request) -> Dict[str, Any]:
        uid = get_session_user_id(request)
        if not uid:
            return {"authenticated": False}
        u_raw = get_user_by_id(str(uid))
        if not u_raw:
            return {"authenticated": False}
        u = _record_to_dict(u_raw)
        return {
            "authenticated": True,
            "id": str(u.get("id") or uid),
            "email": str(u.get("email") or ""),
            "is_admin": bool(int(u.get("is_admin") or 0)),
        }

    # ---------------------------------------------------------------------
    # OAuth (Google) - cookie-session based
    # ---------------------------------------------------------------------
    @api.get(f"{API_PREFIX}/auth/oauth/google")
    async def oauth_google_start(request: Request):
        if not is_oauth_configured(oauth):
            raise HTTPException(status_code=404, detail="OAuth not available")
        if oauth is None or not getattr(oauth, "google", None):
            raise HTTPException(status_code=500, detail="OAuth not initialized on server")

        # CRITICAL: derive redirect_uri from inbound request host unless explicitly overridden.
        # This prevents mismatching_state when the flow is started on localhost vs prod.
        redirect_uri = _oauth_callback_url(request)

        logger.info(f"[OAuth] google_start base={_base_url(request)} redirect_uri={redirect_uri}")

        # Let Authlib manage state entirely (no manual state handling).
        return await oauth.google.authorize_redirect(request, redirect_uri)

    @api.get(f"{API_PREFIX}/auth/oauth/google/callback")
    async def oauth_google_callback(request: Request) -> Any:
        if not is_oauth_configured(oauth):
            raise HTTPException(status_code=404, detail="OAuth not available")
        if oauth is None or not getattr(oauth, "google", None):
            raise HTTPException(status_code=500, detail="OAuth not initialized on server")

        try:
            # This validates the stored state inside the session cookie.
            token = await oauth.google.authorize_access_token(request)

            resp = await oauth.google.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                token=token,
            )
            user_info = resp.json()

            email = normalize_email(user_info.get("email", ""))
            if not email:
                raise HTTPException(status_code=400, detail="No email returned from provider")

            user = get_user_by_email(email)
            if not user:
                user_id = str(create_user(email, secrets.token_urlsafe(32)))
                user = get_user_by_id(user_id)

            if not user:
                raise HTTPException(status_code=500, detail="Failed to create user")

            _maybe_promote_admin(email, str(user["id"]))
            _bootstrap_admin_if_enabled(email, str(user["id"]))

            try:
                with db() as conn:
                    conn.execute(
                        "UPDATE users SET last_login_at = ? WHERE id = ?",
                        (_now(), user["id"]),
                    )
            except Exception:
                pass

            # Redirect to login bootstrap page so frontend can store JWT.
            redirect_to = f"{(APP_BASE_PATH or '').rstrip('/')}/login/?oauth=1"
            if not redirect_to.startswith("/"):
                redirect_to = "/" + redirect_to

            response = RedirectResponse(url=redirect_to)

            # Store app session user_id in the SAME cookie-session that SessionMiddleware manages.
            set_session(response, str(user["id"]), request)

            logger.info(f"[OAuth] callback success email={email} -> {redirect_to}")
            return response

        except HTTPException:
            raise
        except Exception as e:
            msg = str(e) or "OAuth error"

            # Add a targeted hint for the exact failure you're hitting.
            if "mismatching_state" in msg or "CSRF" in msg or "state" in msg.lower():
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "OAuth error: mismatching_state (CSRF). "
                        "This almost always means the OAuth flow was started on a different host/origin "
                        "than the callback. Ensure you start OAuth on the same domain you expect to land on. "
                        f"(request_base={_base_url(request)})"
                    ),
                )

            raise HTTPException(status_code=400, detail=f"OAuth error: {msg}")

    @api.post(f"{API_PREFIX}/auth/logout")
    async def logout_session(request: Request, response: Response) -> Dict[str, Any]:
        clear_session(response, request)
        return {"ok": True}

    # ---------------------------------------------------------------------
    # Me (JWT-based)
    # ---------------------------------------------------------------------
    @api.get(f"{API_PREFIX}/me", response_model=MeOut)
    async def me(u: Dict[str, Any] = Depends(current_user)) -> MeOut:
        from backend.credits import get_user_credits

        credits_remaining = None
        if int(u.get("is_admin") or 0) != 1:
            credits_remaining = get_user_credits(str(u["id"]))

        return MeOut(
            id=str(u["id"]),
            email=str(u["email"]),
            is_admin=bool(int(u.get("is_admin") or 0)),
            subscription_status=str(u.get("subscription_status") or "none"),
            plan=str(u.get("plan") or "none"),
            current_period_end=int(u.get("current_period_end") or 0),
            credits_remaining=credits_remaining,
        )

    @api.post(f"{API_PREFIX}/auth/ping")
    async def ping_post(request: Request) -> Dict[str, Any]:
        return {"ok": True}

    # ---------------------------------------------------------------------
    # Legacy endpoints (email/*) kept for compatibility
    # ---------------------------------------------------------------------
    @api.post(f"{API_PREFIX}/auth/email/register", response_model=TokenOut)
    async def register_email(payload: RegisterIn, request: Request) -> TokenOut:
        email = normalize_email(payload.email)
        validate_email(email)

        password = payload.password or ""
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

        ip = get_ip(request)
        if not _check_auth_ip_rate(ip, _REGISTER_LIMIT):
            raise HTTPException(status_code=429, detail="Too many registration attempts from this IP. Try again later.")

        try:
            raw = await request.json()
            if isinstance(raw, dict) and raw.get("hp"):
                raise HTTPException(status_code=400, detail="Bot detection triggered")
        except Exception:
            pass

        if get_user_by_email(email):
            raise HTTPException(status_code=409, detail="Email already registered")

        user_id = str(create_user(email, password))
        _maybe_promote_admin(email, user_id)
        _bootstrap_admin_if_enabled(email, user_id)

        from backend.credits import initialize_user_credits

        initialize_user_credits(user_id)

        ua = request.headers.get("user-agent", "")
        ip = get_ip(request)

        access_token = make_access_token(user_id)
        _, refresh_token = create_refresh_session(user_id, ua, ip)

        return TokenOut(access_token=access_token, refresh_token=refresh_token)

    @api.post(f"{API_PREFIX}/auth/email/login", response_model=TokenOut)
    async def login_email(payload: LoginIn, request: Request) -> TokenOut:
        email = normalize_email(payload.email)
        validate_email(email)

        ip = get_ip(request)
        if not _check_auth_ip_rate(ip, _LOGIN_LIMIT):
            raise HTTPException(status_code=429, detail="Too many login attempts from this IP. Try again later.")

        user = get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        pw_hash = str(user["pw_hash"])
        if not pw_hash or not _pbkdf2_verify(payload.password or "", pw_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user_id = str(user["id"])
        _maybe_promote_admin(email, user_id)
        _bootstrap_admin_if_enabled(email, user_id)

        ua = request.headers.get("user-agent", "")
        ip = get_ip(request)

        access_token = make_access_token(user_id)
        _, refresh_token = create_refresh_session(user_id, ua, ip)

        from backend.credits import get_user_credits

        _ = get_user_credits(user_id)  # ensure credits row exists

        return TokenOut(access_token=access_token, refresh_token=refresh_token)
