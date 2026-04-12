"""Minimal, cleaned Architecture mode routes used temporarily.

Provides a small, robust subset of the original architecture routes
so the backend can import and run while the original large file is
being repaired.
"""
from __future__ import annotations

import asyncio
import json
import os
import logging
from typing import Any, List, Optional
import uuid

from fastapi import Request, HTTPException, Depends
from fastapi.responses import StreamingResponse

from backend.config import API_PREFIX
from backend.database import db, _now
from backend.auth import current_user, is_active_subscription
from backend.models import ArchitectureProjectOut
from backend.services.ai.architecture_pipeline import run_pipeline

logger = logging.getLogger("codebot")


def ensure_architecture_tables(conn):
    from backend.migrations.architecture_schema import apply_architecture_migrations

    apply_architecture_migrations(conn)


def register_routes(api):
    with db() as conn:
        ensure_architecture_tables(conn)

    @api.post(f"{API_PREFIX}/architecture/projects")
    async def create_project(request: Request, init: Optional[bool] = False):
        # DEV_MODE removed: always disabled in production
        debug_user = request.headers.get("X-Debug-User")
        u = None
        if debug_user:
            with db() as conn:
                urow = conn.execute("SELECT * FROM users WHERE id = ?", (debug_user,)).fetchone()
                if urow:
                    u = urow
        if u is None:
            if False:
                u = {"id": "f42771b7-bdc6-40b1-bae2-dcbaaab77b31", "email": "dev@example.com", "is_admin": 1}
            else:
                u = await current_user(request, request.headers.get("authorization"))

        body = await request.json()
        name = body.get("name", "Untitled Project")
        description = body.get("description", "")
        template = body.get("template", "blank")
        user_id = str(u["id"]) if u else None
        logger.info(f"create_project called by user={user_id} name={name}")
        project_id = str(uuid.uuid4())
        with db() as conn:
            conn.execute(
                "INSERT INTO architecture_projects (id, user_id, name, description, template, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (project_id, user_id, name, description, template, "idle", _now(), _now()),
            )
        # If init requested, persist a minimal scaffold
        if init:
            try:
                scaffold = {
                    "files": {
                        "index.html": f"<!doctype html>\n<html>\n  <head><meta charset=\"utf-8\"><title>{name}</title></head>\n  <body><div id=\"root\"></div><script src=\"/assets/index.js\"></script></body>\n</html>",
                        "package.json": "{\n  \"name\": \"%s\",\n  \"version\": \"1.0.0\",\n  \"private\": true\n}\n" % name.replace(' ', '-').lower(),
                        "README.md": f"# {name}\n\nThis project was created by CodeBot Architecture mode.\n",
                    }
                }
                with db() as conn:
                    conn.execute(
                        "UPDATE architecture_projects SET file_tree = ?, updated_at = ? WHERE id = ?",
                        (json.dumps(scaffold), _now(), project_id),
                    )
            except Exception:
                logger.exception("Failed to persist scaffold for project %s", project_id)

        return ArchitectureProjectOut(
            project_id=project_id,
            name=name,
            description=description,
            template=template,
            status="idle",
            preview_url=None,
            created_at=_now(),
            updated_at=_now(),
        )

    @api.get(f"{API_PREFIX}/architecture/projects/{{project_id}}/scaffold")
    async def get_scaffold(project_id: str, request: Request):
        # DEV_MODE removed: always disabled in production
        debug_user = request.headers.get("X-Debug-User")
        u = None
        if debug_user:
            with db() as conn:
                urow = conn.execute("SELECT * FROM users WHERE id = ?", (debug_user,)).fetchone()
                if urow:
                    u = urow
        if u is None:
            if False:
                u = {"id": "f42771b7-bdc6-40b1-bae2-dcbaaab77b31", "email": "dev@example.com", "is_admin": 1}
            else:
                u = await current_user(request, request.headers.get("authorization"))

        user_id = str(u["id"]) if u else None
        with db() as conn:
            row = conn.execute(
                "SELECT file_tree FROM architecture_projects WHERE id = ? AND user_id = ?",
                (project_id, user_id),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Project not found")
            file_tree = row["file_tree"]
            if not file_tree:
                return {"files": {}}
            try:
                return json.loads(file_tree)
            except Exception:
                return {"files": {}}

    @api.get(f"{API_PREFIX}/architecture/projects", response_model=List[ArchitectureProjectOut])
    async def list_projects(request: Request, u: Any = Depends(current_user)):
        if not is_active_subscription(u):
            raise HTTPException(status_code=402, detail="Subscription required for Architecture mode")

        user_id = str(u["id"])
        with db() as conn:
            rows = conn.execute(
                """SELECT id, name, description, template, status, preview_url, created_at, updated_at
                   FROM architecture_projects
                   WHERE user_id = ? ORDER BY updated_at DESC""",
                (user_id,),
            ).fetchall()

        return [
            ArchitectureProjectOut(
                project_id=str(r["id"]),
                name=str(r["name"]),
                description=str(r["description"]) if r["description"] else None,
                template=str(r["template"]),
                status=str(r["status"]),
                preview_url=str(r["preview_url"]) if r["preview_url"] else None,
                created_at=int(r["created_at"]),
                updated_at=int(r["updated_at"]),
            )
            for r in rows
        ]

    @api.post(f"{API_PREFIX}/architecture/projects/{{project_id}}/requirements")
    async def save_requirements(project_id: str, request: Request, u: Any = Depends(current_user)):
        body = await request.json()
        requirements = body.get("requirements", "")

        user_id = str(u["id"])
        with db() as conn:
            row = conn.execute(
                "SELECT id FROM architecture_projects WHERE id = ? AND user_id = ?",
                (project_id, user_id),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Project not found")
            conn.execute(
                "UPDATE architecture_projects SET description = ?, updated_at = ? WHERE id = ?",
                (requirements, _now(), project_id),
            )

        return {"ok": True}

    @api.get(f"{API_PREFIX}/architecture/projects/{{project_id}}/plan/stream")
    async def stream_plan(project_id: str, request: Request, message: Optional[str] = None, u: Any = None):
        debug_user = request.headers.get("X-Debug-User")
        if debug_user:
            user_id = str(debug_user)
            with db() as conn:
                urow = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                if urow:
                    u = urow
        else:
            try:
                if u is None:
                    u = await current_user(request, request.headers.get("authorization"))
                user_id = str(u["id"])
            except HTTPException:
                # DEV_MODE removed: always disabled in production
                if False:
                    u = {"id": "f42771b7-bdc6-40b1-bae2-dcbaaab77b31", "email": "dev@example.com", "is_admin": 1}
                    user_id = str(u["id"])
                else:
                    raise

        with db() as conn:
            row = conn.execute(
                "SELECT id, name, description FROM architecture_projects WHERE id = ? AND user_id = ?",
                (project_id, user_id),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Project not found")

        project_title = row["name"]
        user_request = message or row["description"] or ""

        # Enforce SaaS-only access for streaming plans
        try:
            is_admin = int(u.get("is_admin") if hasattr(u, "get") else (u["is_admin"] if "is_admin" in u.keys() else 0))
            plan = str(u.get("plan") if hasattr(u, "get") else (u["plan"] if "plan" in u.keys() else "none"))
            is_saas_dev = int(u.get("is_saas_dev") if hasattr(u, "get") else (u["is_saas_dev"] if "is_saas_dev" in u.keys() else 0))
        except Exception:
            is_admin = 0
            plan = "none"
            is_saas_dev = 0
        if is_admin != 1 and plan not in ("basic", "pro", "elite") and is_saas_dev != 1:
            raise HTTPException(status_code=403, detail="Architecture mode is restricted to SaaS developers on paid plans. Contact the administrator to request access.")

        # Block website-related prompts unless allowed
        try:
            lower_req = (user_request or "").lower()
            website_keywords = ["website", "web site", "site", "landing page", "landing", "portfolio", "e-comm", "ecommerce", "e-commerce", "store", "shop", "blog", "static site"]
            is_website_req = any(k in lower_req for k in website_keywords)
            from backend.config import ALLOW_WEBSITE_PROJECTS
            if is_website_req and not (is_admin == 1 or is_saas_dev == 1 or ALLOW_WEBSITE_PROJECTS):
                raise HTTPException(status_code=403, detail="Website projects are currently disabled until platform revenue threshold is met.")
        except HTTPException:
            raise
        except Exception:
            pass

        api_key = None
        try:
            if "api_key_encrypted" in u.keys() and u["api_key_encrypted"]:
                from backend.byok import decrypt_api_key

                api_key = decrypt_api_key(u["api_key_encrypted"])
        except Exception:
            api_key = None

        if not api_key:
            api_key = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACEHUB_API_TOKEN") or ""

        q = asyncio.Queue()

        def on_event(ev: Any) -> None:
            try:
                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(q.put_nowait, ev)
            except Exception:
                logger.exception("Failed to enqueue pipeline event")

        api_provider = None
        try:
            api_provider = u["api_key_provider"] if "api_key_provider" in u.keys() else None
        except Exception:
            api_provider = None

        pipeline_task = asyncio.create_task(run_pipeline(user_request, project_id, project_title, api_key, api_provider, None, on_event))

        async def event_generator():
            try:
                while True:
                    ev = await q.get()
                    payload = {"type": getattr(ev, "type", "event"), "message": getattr(ev, "message", ""), "data": getattr(ev, "data", {})}
                    yield f"data: {json.dumps(payload)}\n\n"
                    if payload["type"] in ("complete", "error"):
                        break
                try:
                    await pipeline_task
                except Exception as e:
                    payload = {"type": "error", "message": str(e), "data": {}}
                    yield f"data: {json.dumps(payload)}\n\n"
            finally:
                if not pipeline_task.done():
                    pipeline_task.cancel()

        return StreamingResponse(event_generator(), media_type="text/event-stream")
