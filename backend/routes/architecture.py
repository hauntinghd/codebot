"""Minimal, stable Architecture mode routes (safe, importable).

This module exposes a small subset of the original functionality:
- list projects
- save requirements
- stream planning events (SSE) via `run_pipeline`

It intentionally avoids embedding large multi-line literals and keeps
behavior simple so the backend can import this module reliably.
"""

from __future__ import annotations

import asyncio
import json
import os
import logging
from typing import Any, List, Optional

from fastapi import Request, HTTPException, Depends
from fastapi.responses import StreamingResponse

from backend.config import API_PREFIX, ALLOW_WEBSITE_PROJECTS
from backend.database import db, _now
from backend.auth import current_user, is_active_subscription
from backend.models import ArchitectureProjectOut
from backend.services.ai.architecture_pipeline import run_pipeline
import uuid

logger = logging.getLogger("codebot")


def ensure_architecture_tables(conn):
    from backend.migrations.architecture_schema import apply_architecture_migrations

    apply_architecture_migrations(conn)


def register_routes(api):
    @api.post(f"{API_PREFIX}/architecture/projects")
    async def create_project(request: Request, init: Optional[bool] = False, u: Any = Depends(current_user)):
        body = await request.json()
        name = body.get("name", "Untitled Project")
        description = body.get("description", "")
        template = body.get("template", "blank")
        user_id = str(u["id"])
        logger.info(f"create_project called by user={user_id} name={name}")
        # Restrict Architecture mode to paid SaaS developers or admins
        is_admin = int(u.get("is_admin") if hasattr(u, "get") else (u["is_admin"] if "is_admin" in u.keys() else 0))
        plan = str(u.get("plan") if hasattr(u, "get") else (u["plan"] if "plan" in u.keys() else "none"))
        is_saas_dev = int(u.get("is_saas_dev") if hasattr(u, "get") else (u["is_saas_dev"] if "is_saas_dev" in u.keys() else 0))
        if is_admin != 1 and plan not in ("basic", "pro", "elite") and is_saas_dev != 1:
            raise HTTPException(status_code=403, detail="Architecture mode is restricted to SaaS developers on paid plans. Contact the administrator to request access.")
        # If creating a website template is disallowed at platform level, block it before inserting the project
        if template == "website" and not ALLOW_WEBSITE_PROJECTS:
            raise HTTPException(status_code=403, detail="Website projects are currently disabled until platform revenue threshold is met.")
        # Generate a stable UUID for the project id so it is never NULL
        project_id = str(uuid.uuid4())
        with db() as conn:
            # Insert new project with explicit id; include built flag (0 = not built)
            conn.execute(
                "INSERT INTO architecture_projects (id, user_id, name, description, template, built, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (project_id, user_id, name, description, template, 0, "idle", _now(), _now()),
            )
            row = conn.execute(
                "SELECT id, name, description, template, status, preview_url, created_at, updated_at FROM architecture_projects WHERE id = ?",
                (project_id,),
            ).fetchone()
        logger.info(f"Created architecture project id={project_id} user={user_id} name={name}")
        # Create a minimal scaffold and store it in the file_tree column as JSON
        try:
            scaffold = {
                "files": {
                    "index.html": "<!doctype html>\n<html>\n  <head><meta charset=\"utf-8\"><title>{}</title></head>\n  <body><div id=\"root\"></div><script src=\"/assets/index-ZezxKoxz.js\"></script></body>\n</html>".format(name),
                    "package.json": json.dumps({
                        "name": name.replace(' ', '-').lower(),
                        "version": "1.0.0",
                        "private": True
                    }, indent=2) + "\n",
                    "README.md": f"# {name}\n\nThis project was created by CodeBot Architecture mode.\n",
                }
            }

            # If creating a website template is disallowed at platform level, block it.
            if template == "website" and not ALLOW_WEBSITE_PROJECTS:
                raise HTTPException(status_code=403, detail="Website projects are currently disabled until platform revenue threshold is met.")

            with db() as conn:
                conn.execute(
                    "UPDATE architecture_projects SET file_tree = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(scaffold), _now(), project_id),
                )
        except Exception:
            logger.exception("Failed to persist scaffold for project %s", project_id)
        return ArchitectureProjectOut(
            project_id=str(row["id"]),
            name=str(row["name"]),
            description=str(row["description"]),
            template=str(row["template"]),
            status=str(row["status"]),
            preview_url=str(row["preview_url"]) if row["preview_url"] else None,
            created_at=int(row["created_at"]),
            updated_at=int(row["updated_at"]),
        )

    @api.get(f"{API_PREFIX}/architecture/projects/{{project_id}}/scaffold")
    async def get_scaffold(project_id: str, request: Request, u: Any = Depends(current_user)):
        """Return the scaffold/file map for a project so the frontend can mount it into WebContainer."""
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
    """Register a minimal, robust set of architecture routes."""

    with db() as conn:
        ensure_architecture_tables(conn)

    @api.get(f"{API_PREFIX}/architecture/projects", response_model=List[ArchitectureProjectOut])
    async def list_projects(request: Request, u: Any = Depends(current_user)):
        if not is_active_subscription(u):
            raise HTTPException(status_code=402, detail="Subscription required for Architecture mode")

        user_id = str(u["id"])
        logger.info(f"list_projects called by user={user_id}")
        with db() as conn:
            rows = conn.execute(
                "SELECT id, name, description, template, status, preview_url, created_at, updated_at "
                "FROM architecture_projects WHERE user_id = ? ORDER BY updated_at DESC",
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
        """Stream plan/build events as SSE using the patched `run_pipeline` helper."""

        # allow quick local debug by passing X-Debug-User header with a user id
        debug_user = request.headers.get("X-Debug-User")
        if debug_user:
            with db() as conn:
                urow = conn.execute("SELECT * FROM users WHERE id = ?", (debug_user,)).fetchone()
                if urow:
                    u = urow
        else:
            if False:
                u = {"id": "f42771b7-bdc6-40b1-bae2-dcbaaab77b31", "email": "dev@example.com", "is_admin": 1}
            else:
                u = await current_user(request, request.headers.get("authorization"))

        user_id = str(u["id"])
        # Enforce SaaS-only access (same rules as create_project)
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
        # Allow a quick debug/scratch project id of '0' which doesn't require DB rows
        if project_id == "0":
            project_title = "Quick Plan"
            user_request = message or ""
        else:
            with db() as conn:
                row = conn.execute(
                    "SELECT id, name, description FROM architecture_projects WHERE id = ? AND user_id = ?",
                    (project_id, user_id),
                ).fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Project not found")

            project_title = row["name"]
            user_request = message or row["description"] or ""

            # Block website-related prompts until platform enables website projects
            try:
                lower_req = (user_request or "").lower()
                website_keywords = ["website", "web site", "site", "landing page", "landing", "portfolio", "e-comm", "ecommerce", "e-commerce", "store", "shop", "blog", "static site"]
                is_website_req = any(k in lower_req for k in website_keywords)
                if is_website_req and not (is_admin == 1 or is_saas_dev == 1 or ALLOW_WEBSITE_PROJECTS):
                    raise HTTPException(status_code=403, detail="Website projects are currently disabled until platform revenue threshold is met.")
            except HTTPException:
                raise
            except Exception:
                pass

        # Prefer BYOK; fallback to HF env tokens. Ensure `api_key` is always
        # defined to avoid runtime NameError in streaming tasks.
        api_key = ""
        try:
            if u and isinstance(u, dict) and "api_key_encrypted" in u.keys() and u["api_key_encrypted"]:
                from backend.byok import decrypt_api_key

                decrypted = decrypt_api_key(u["api_key_encrypted"])
                if decrypted:
                    api_key = decrypted
        except Exception:
            logger.exception("Failed to decrypt user's BYOK api_key")

        if not api_key:
            api_key = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACEHUB_API_TOKEN") or ""

        q: "asyncio.Queue[Any]" = asyncio.Queue()

        def on_event(ev: Any) -> None:
            try:
                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(q.put_nowait, ev)
            except Exception:
                logger.exception("Failed to enqueue pipeline event")

        # Determine API key provider from user record when available
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
                    payload = {
                        "type": getattr(ev, "type", "event"),
                        "message": getattr(ev, "message", ""),
                        "data": getattr(ev, "data", {}),
                    }
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
