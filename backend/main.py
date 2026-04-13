# backend/main.py
"""
FastAPI main entry point - CodeBot backend (host + mounted API).

Primary objective:
- Make Google OAuth state survive redirects reliably (fix mismatching_state / CSRF).
Key decisions:
- Use Starlette SessionMiddleware as the ONLY session mechanism.
- DO NOT set or parse any legacy "session" cookie in auth flow.
- Cookie Path MUST be APP_BASE_PATH (e.g. /codebot) so the browser sends it on /codebot/* routes.
- SameSite=Lax is sufficient for OAuth because the callback is a top-level navigation.
  (None is not required for this flow, and causes avoidable browser edge cases.)
"""
from __future__ import annotations

import json
import logging
import os
from typing import List

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from backend.routes.auth import register_routes as register_auth_routes  # IMPORTANT: used, do not re-alias
from backend.routes.uploads import register_routes as register_uploads_routes
from backend.routes.projects import register_routes as register_projects_routes
from backend.routes.chat import register_routes as register_chat_routes
from backend.routes.chats import register_routes as register_chats_routes
from backend.routes.billing import register_routes as register_billing_routes
from backend.routes.credits import register_routes as register_credits_routes
from backend.routes.admin import register_routes as register_admin_routes
from backend.routes.settings import router as settings_router
from backend.routes.preview import router as preview_router
from backend.routes.preview_proxy import router as preview_proxy_router
from backend.routes.webcontainer import router as webcontainer_router
from backend.routes.builder import router as builder_router
from .auth import get_session_user_id
from .config import (
    ALLOWED_ORIGINS,
    APP_BASE_PATH,
    APP_BASE_URL,
    REFRESH_TOKEN_TTL_SECONDS,
    SESSION_SECRET,
)
from .database import init_db

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("codebot")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)

logger.info("--- Backend startup ---")

# ---------------------------------------------------------------------------
# DB init
# ---------------------------------------------------------------------------
init_db()

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------
# This "api" app is what we mount under APP_BASE_PATH (usually "/codebot")
api = FastAPI(title="CodeBot API", version="1.0.0")

# Host wrapper (nginx typically targets this app)
app = FastAPI(title="CodeBot Host", version="1.0.0")

# ---------------------------------------------------------------------------
# OAuth init (Authlib) + Google client registration
# ---------------------------------------------------------------------------
oauth = None
try:
    from authlib.integrations.starlette_client import OAuth  # type: ignore

    oauth = OAuth()
    logger.info("[OAuth] Authlib OAuth initialized")

    google_client_id = (os.getenv("GOOGLE_OAUTH_CLIENT_ID") or "").strip()
    google_client_secret = (os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or "").strip()

    if google_client_id and google_client_secret:
        oauth.register(
            name="google",
            client_id=google_client_id,
            client_secret=google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
        logger.info("[OAuth] Google client registered (oauth.google is available)")
    else:
        logger.warning("[OAuth] Google client NOT registered: missing client id/secret")
except Exception as e:
    oauth = None
    logger.warning(f"[OAuth] Authlib OAuth not available ({e})")

# Register auth routes
# Register routes
register_auth_routes(api, oauth)

# Orchestrator API routes (needed by frontend/index.html)
register_uploads_routes(api)
register_projects_routes(api)

# Chat routes
register_chat_routes(api)
register_chats_routes(api)

# Billing, credits, and admin routes
register_billing_routes(api)
register_credits_routes(api)
register_admin_routes(api)

# Router-based endpoints
# NOTE: these routers already include their own prefixes where applicable
api.include_router(settings_router)
api.include_router(preview_router)
api.include_router(preview_proxy_router)
api.include_router(webcontainer_router, prefix="/api/webcontainer")
api.include_router(builder_router)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
def _parse_origins(value) -> List[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        items = list(value)
    elif isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            items = parsed if isinstance(parsed, list) else [s]
        except Exception:
            items = [x.strip() for x in s.split(",") if x.strip()]
    else:
        items = [str(value)]
    out: List[str] = []
    seen = set()
    for raw in items:
        o = str(raw).strip()
        if o and o not in seen:
            seen.add(o)
            out.append(o)
    return out


DEV_ORIGINS = ["http://127.0.0.1:45001", "http://localhost:45001"]
ENV_ORIGINS = _parse_origins(os.getenv("CODEBOT_ALLOWED_ORIGINS"))
CFG_ORIGINS = _parse_origins(ALLOWED_ORIGINS)

ALLOW_ORIGINS: List[str] = []
_seen = set()
for origin in (CFG_ORIGINS + ENV_ORIGINS + DEV_ORIGINS):
    o = str(origin).strip()
    if o and o not in _seen:
        _seen.add(o)
        ALLOW_ORIGINS.append(o)

OFFLINE_MODE = os.getenv("OFFLINE_MODE", "").lower() == "true"
logger.info(f"[CORS] allow_origins={ALLOW_ORIGINS}")
logger.info(f"[CORS] offline_mode={OFFLINE_MODE}")

api.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_origin_regex=r"^https?://(.+\.trycloudflare\.com|.+\.onrender\.com|.+\.nyptidindustries\.com|localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Session middleware (OAuth state + login session must survive redirects)
# ---------------------------------------------------------------------------
_is_https = str(APP_BASE_URL).lower().startswith("https")

# IMPORTANT:
# OAuth callback from Google is a top-level navigation => SameSite=Lax works reliably.
# SameSite=None is not required for this flow and can create browser-specific edge cases.
_same_site = "lax"

_cookie_path = (APP_BASE_PATH or "/").rstrip("/") or "/"
_session_cookie_name = f"cb_session{(APP_BASE_PATH or '').replace('/', '_')}"

logger.info(
    f"[SESSION] https={_is_https} same_site={_same_site} cookie={_session_cookie_name} path={_cookie_path}"
)

api.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie=_session_cookie_name,
    https_only=_is_https,
    max_age=REFRESH_TOKEN_TTL_SECONDS,
    same_site=_same_site,
    path=_cookie_path,
)

# ---------------------------------------------------------------------------
# Proxy helper (Node service behind /api/billing and /api/credits)
# ---------------------------------------------------------------------------
NODE_SERVICE_BASE = (os.getenv("NODE_SERVICE_BASE", "http://127.0.0.1:4001") or "").strip()


def _strip_base_path(path: str) -> str:
    if APP_BASE_PATH and path.startswith(APP_BASE_PATH):
        return path[len(APP_BASE_PATH) :]
    return path


def _filter_hop_by_hop_headers(headers: dict) -> dict:
    out = dict(headers)
    out.pop("host", None)
    out.pop("content-length", None)
    out.pop("connection", None)
    out.pop("transfer-encoding", None)
    return out


async def proxy_to_node(request: Request) -> Response:
    path = _strip_base_path(request.url.path)
    query = request.url.query
    target = f"{NODE_SERVICE_BASE}{path}"
    if query:
        target += f"?{query}"

    headers = _filter_hop_by_hop_headers(dict(request.headers))

    # Forward authenticated user_id if present (derived from SessionMiddleware session)
    try:
        uid = get_session_user_id(request)
        if uid:
            headers["x-user-id"] = str(uid)
    except Exception:
        pass

    body = await request.body()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(request.method, target, content=body, headers=headers)

    out_headers = dict(resp.headers)
    out_headers.pop("transfer-encoding", None)
    out_headers.pop("connection", None)
    out_headers.pop("content-encoding", None)

    return Response(content=resp.content, status_code=resp.status_code, headers=out_headers)


@api.api_route("/api/credits/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_credits(path: str, request: Request):
    return await proxy_to_node(request)


@api.api_route("/api/billing/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_billing(path: str, request: Request):
    return await proxy_to_node(request)


# ---------------------------------------------------------------------------
# Admin pipeline config (admin-only)
# ---------------------------------------------------------------------------
from backend.auth import get_user_by_id

def _require_admin(request: Request):
    uid = get_session_user_id(request)
    if not uid:
        return None
    user = get_user_by_id(uid)
    if not user:
        return None
    try:
        is_admin_val = user["is_admin"]
    except (KeyError, TypeError):
        is_admin_val = getattr(user, "is_admin", False)
    if not is_admin_val:
        return None
    return uid


def _mask_key(key: str) -> str:
    if not key or len(key) < 12:
        return "***"
    return key[:6] + "..." + key[-4:]


def _read_env_var(name: str) -> str:
    from pathlib import Path as _P
    env_path = _P(__file__).parent.parent / ".env"
    if not env_path.exists():
        return os.getenv(name, "")
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    return os.getenv(name, "")


def _update_env_vars(updates: dict):
    from pathlib import Path as _P
    env_path = _P(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    lines = env_path.read_text().splitlines()
    keys_found = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        matched = False
        for key, val in updates.items():
            if stripped.startswith(f"{key}="):
                new_lines.append(f"{key}={val}")
                keys_found.add(key)
                matched = True
                break
        if not matched:
            new_lines.append(line)
    for key, val in updates.items():
        if key not in keys_found:
            new_lines.append(f"{key}={val}")
    env_path.write_text("\n".join(new_lines) + "\n")
    for key, val in updates.items():
        os.environ[key] = val


@api.get("/api/admin/pipeline-config")
async def admin_get_pipeline_config(request: Request):
    if not _require_admin(request):
        return Response(content='{"error":"forbidden"}', status_code=403, media_type="application/json")
    xai_key = _read_env_var("OPENAI_API_KEY")
    xai_model = _read_env_var("XAI_MODEL") or _read_env_var("OPENAI_MODEL") or ""
    return {"xai_key_masked": _mask_key(xai_key), "xai_model": xai_model}


@api.post("/api/admin/pipeline-config")
async def admin_set_pipeline_config(request: Request):
    if not _require_admin(request):
        return Response(content='{"error":"forbidden"}', status_code=403, media_type="application/json")
    try:
        body = await request.json()
    except Exception:
        return Response(content='{"error":"invalid json"}', status_code=400, media_type="application/json")
    updates = {}
    if body.get("xai_key"):
        updates["OPENAI_API_KEY"] = body["xai_key"]
    if body.get("model"):
        updates["XAI_MODEL"] = body["model"]
    if updates:
        _update_env_vars(updates)
        # Also update the backend-ts .env
        from pathlib import Path as _P
        ts_env = _P(__file__).parent.parent / "backend-ts" / ".env"
        if ts_env.exists():
            ts_lines = ts_env.read_text().splitlines()
            ts_new = []
            ts_found = set()
            for line in ts_lines:
                matched = False
                for key, val in updates.items():
                    if line.strip().startswith(f"{key}="):
                        ts_new.append(f"{key}={val}")
                        ts_found.add(key)
                        matched = True
                        break
                if not matched:
                    ts_new.append(line)
            for key, val in updates.items():
                if key not in ts_found:
                    ts_new.append(f"{key}={val}")
            ts_env.write_text("\n".join(ts_new) + "\n")
    return {"ok": True}


@api.post("/api/admin/pipeline-test")
async def admin_test_pipeline(request: Request):
    if not _require_admin(request):
        return Response(content='{"error":"forbidden"}', status_code=403, media_type="application/json")
    try:
        body = await request.json()
    except Exception:
        body = {}
    prompt = body.get("prompt", "Say hello in one sentence.")
    xai_key = os.environ.get("OPENAI_API_KEY", "") or _read_env_var("OPENAI_API_KEY")
    xai_model = os.environ.get("XAI_MODEL", "") or _read_env_var("XAI_MODEL") or "grok-4-1-fast"
    xai_base = os.environ.get("XAI_API_BASE_URL", "https://api.x.ai/v1")
    if not xai_key:
        return {"ok": False, "error": "No API key configured."}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{xai_base}/chat/completions",
                headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
                json={"model": xai_model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 256},
            )
            if resp.status_code != 200:
                return {"ok": False, "error": f"API returned HTTP {resp.status_code}: {resp.text[:500]}"}
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"ok": True, "model": xai_model, "response": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@api.api_route("/health", methods=["GET", "HEAD"], include_in_schema=False)
def health():
    return {"ok": True}


# ---------------------------------------------------------------------------
# Mount API under APP_BASE_PATH (typically "/codebot")
# ---------------------------------------------------------------------------
app.mount(APP_BASE_PATH, api)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url=f"{APP_BASE_PATH}/")


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
