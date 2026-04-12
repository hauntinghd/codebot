"""Projects routes - ZIP upload, file management, builder save/load."""
from __future__ import annotations

import shutil
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile

from backend.auth import current_user, get_user_by_id, is_active_subscription, require_subscribed
from backend.config import API_PREFIX, MAX_FILE_READ_BYTES, MAX_UPLOAD_BYTES, PROJECTS_DIR
from backend.database import _now, db
from backend.common_helpers import extract_zip_safely, read_text_file_limited, safe_join, walk_files
from backend.models import ProjectOut
from backend.services.chat_helpers import check_test_mode_protection

MAX_EXPORT_FILES = 200
MAX_EXPORT_BYTES = 5 * 1024 * 1024  # 5MB total

def register_routes(api: FastAPI):
    """Register projects routes."""

    @api.get(f"{API_PREFIX}/projects", response_model=List[ProjectOut])
    async def list_projects(
        request: Request,
        u: sqlite3.Row = Depends(require_subscribed),
    ) -> List[ProjectOut]:
        with db() as conn:
            rows = conn.execute(
                "SELECT id, name, created_at, updated_at FROM projects WHERE user_id = ? ORDER BY created_at DESC LIMIT 200",
                (str(u["id"]),),
            ).fetchall()
        return [
            ProjectOut(
                id=str(r["id"]),
                name=str(r["name"]),
                created_at=int(r["created_at"]),
                updated_at=int(r["updated_at"]),
            )
            for r in rows
        ]

    @api.post(f"{API_PREFIX}/projects/upload", response_model=ProjectOut)
    async def upload_project(
        request: Request,
        name: str = Form(...),
        file: UploadFile = File(...),
        u: sqlite3.Row = Depends(current_user),
    ) -> ProjectOut:
        # Check subscription or test mode
        # DEV_MODE removed: always disabled in production
        if True:
            from backend.auth import _is_test_mode_user
            if not _is_test_mode_user(u) or not (request.headers.get("X-Test-Mode", "").lower() in ("true", "1", "yes")):
                if int(u["is_admin"]) != 1 and not is_active_subscription(u):
                    raise HTTPException(status_code=402, detail="Subscription required")
        
        # Test mode: Allow uploads but store in test directory
        test_mode_active = check_test_mode_protection(u, request)
        
        nm = (name or "").strip()
        if not nm:
            raise HTTPException(status_code=400, detail="Project name required")
        if not file.filename or not file.filename.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="Upload must be a .zip")

        # Stream to disk with size limit
        project_id = str(uuid.uuid4())
        
        # In test mode, store in test directory
        if test_mode_active:
            user_root = (PROJECTS_DIR / "test_mode" / str(u["id"]) / project_id).resolve()
        else:
            user_root = (PROJECTS_DIR / str(u["id"]) / project_id).resolve()
        
        user_root.mkdir(parents=True, exist_ok=True)

        tmp_zip = (user_root / "upload.zip").resolve()
        total = 0
        with tmp_zip.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="ZIP too large")
                f.write(chunk)

        # Extract
        extracted = (user_root / "src").resolve()
        extracted.mkdir(parents=True, exist_ok=True)
        try:
            extract_zip_safely(tmp_zip, extracted)
        finally:
            # Delete zip to save space
            try:
                tmp_zip.unlink(missing_ok=True)
            except TypeError:
                if tmp_zip.exists():
                    tmp_zip.unlink()

        now = _now()
        with db() as conn:
            conn.execute(
                "INSERT INTO projects (id, user_id, name, root_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (project_id, str(u["id"]), nm[:120], str(extracted), now, now),
            )

        return ProjectOut(id=project_id, name=nm[:120], created_at=now, updated_at=now)

    @api.get(f"{API_PREFIX}/projects/{{project_id}}/files")
    async def project_files(
        project_id: str,
        request: Request,
        u: sqlite3.Row = Depends(require_subscribed),
    ) -> Dict[str, Any]:
        with db() as conn:
            prow = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not prow:
            raise HTTPException(status_code=404, detail="Project not found")
        if str(prow["user_id"]) != str(u["id"]) and int(u["is_admin"]) != 1:
            raise HTTPException(status_code=403, detail="Forbidden")

        root = Path(str(prow["root_path"])).resolve()
        return {"project_id": project_id, "files": walk_files(root)}

    @api.get(f"{API_PREFIX}/projects/{{project_id}}/file")
    async def project_file(
        project_id: str,
        path: str,
        request: Request,
        u: sqlite3.Row = Depends(require_subscribed),
    ) -> Dict[str, Any]:
        with db() as conn:
            prow = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not prow:
            raise HTTPException(status_code=404, detail="Project not found")
        if str(prow["user_id"]) != str(u["id"]) and int(u["is_admin"]) != 1:
            raise HTTPException(status_code=403, detail="Forbidden")

        root = Path(str(prow["root_path"])).resolve()
        fp = safe_join(root, path)
        if not fp.exists() or not fp.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        txt = read_text_file_limited(fp, MAX_FILE_READ_BYTES)
        return {"path": path, "content": txt}

    @api.post(f"{API_PREFIX}/projects/from-files", response_model=ProjectOut)
    async def create_project_from_files(
        request: Request,
        u: sqlite3.Row = Depends(require_subscribed),
    ) -> ProjectOut:
        if not is_active_subscription(u) and int(u.get("is_admin", 0)) != 1:
            from backend.auth import _is_test_mode_user
            if not _is_test_mode_user(u) or request.headers.get("X-Test-Mode", "").lower() not in ("true", "1", "yes"):
                raise HTTPException(status_code=402, detail="Subscription required")
        body = await request.json()
        name = (body.get("name") or "").strip() or "Untitled Project"
        files = body.get("files")
        if not isinstance(files, list) or len(files) > MAX_EXPORT_FILES:
            raise HTTPException(status_code=400, detail="files must be a list (max %d)" % MAX_EXPORT_FILES)
        project_id = str(uuid.uuid4())
        user_root = (PROJECTS_DIR / str(u["id"]) / project_id / "src").resolve()
        user_root.mkdir(parents=True, exist_ok=True)
        total_bytes = 0
        for i, item in enumerate(files):
            if total_bytes > MAX_EXPORT_BYTES:
                break
            if not isinstance(item, dict):
                continue
            path = (item.get("path") or "").strip().lstrip("/").replace("\\", "/")
            content = item.get("content")
            if not path or path.startswith("..") or "/.." in path:
                continue
            if content is None:
                content = ""
            content = str(content)
            total_bytes += len(content)
            fp = (user_root / path).resolve()
            if not str(fp).startswith(str(user_root)):
                continue
            fp.parent.mkdir(parents=True, exist_ok=True)
            try:
                fp.write_text(content, encoding="utf-8", errors="replace")
            except Exception:
                pass
        root_path = str(user_root)
        now = _now()
        with db() as conn:
            conn.execute(
                "INSERT INTO projects (id, user_id, name, root_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (project_id, str(u["id"]), name[:120], root_path, now, now),
            )
        return ProjectOut(id=project_id, name=name[:120], created_at=now, updated_at=now)

    @api.get(f"{API_PREFIX}/projects/{{project_id}}/export")
    async def project_export(
        project_id: str,
        request: Request,
        u: sqlite3.Row = Depends(require_subscribed),
    ) -> Dict[str, Any]:
        with db() as conn:
            prow = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not prow:
            raise HTTPException(status_code=404, detail="Project not found")
        if str(prow["user_id"]) != str(u["id"]) and int(u["is_admin"]) != 1:
            raise HTTPException(status_code=403, detail="Forbidden")
        root = Path(str(prow["root_path"])).resolve()
        paths = walk_files(root)
        if len(paths) > MAX_EXPORT_FILES:
            paths = paths[:MAX_EXPORT_FILES]
        files_out: List[Dict[str, str]] = []
        total = 0
        for rel in paths:
            if total > MAX_EXPORT_BYTES:
                break
            fp = safe_join(root, rel)
            if not fp.is_file():
                continue
            try:
                txt = read_text_file_limited(fp, MAX_FILE_READ_BYTES)
                files_out.append({"path": rel, "content": txt})
                total += len(txt)
            except Exception:
                pass
        return {"name": str(prow["name"]), "project_id": project_id, "files": files_out}

    @api.delete(f"{API_PREFIX}/projects/{{project_id}}")
    async def delete_project(
        project_id: str,
        request: Request,
        u: sqlite3.Row = Depends(require_subscribed),
    ) -> Dict[str, Any]:
        # Test mode: Allow deletion of test projects only
        test_mode_active = check_test_mode_protection(u, request)
        
        with db() as conn:
            prow = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not prow:
            raise HTTPException(status_code=404, detail="Project not found")
        if str(prow["user_id"]) != str(u["id"]) and int(u["is_admin"]) != 1:
            raise HTTPException(status_code=403, detail="Forbidden")

        root = Path(str(prow["root_path"])).resolve()
        
        # In test mode, only allow deletion if it's a test project
        if test_mode_active and "test_mode" not in str(root):
            raise HTTPException(
                status_code=403,
                detail="TEST MODE: Can only delete test projects. Turn off test mode to delete real projects."
            )
        
        # Remove DB row first
        with db() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

        # Delete project directory (two levels up: .../<user>/<project>/src)
        proj_dir = root.parent  # src -> project_id dir
        try:
            shutil.rmtree(proj_dir, ignore_errors=True)
        except Exception:
            pass

        return {"ok": True}

