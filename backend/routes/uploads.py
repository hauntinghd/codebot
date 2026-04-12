"""File upload routes - ZIP, MP4, MP3, images, code files."""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from backend.auth import _is_test_mode_user, current_user, is_active_subscription, require_subscribed
from backend.config import API_PREFIX, DEV_MODE, MAX_UPLOAD_BYTES, UPLOADS_DIR
from backend.database import _now, db
from backend.services.chat_helpers import check_test_mode_protection, get_image_upload_count

logger = logging.getLogger("codebot")


def _header_test_mode_enabled(request: Request) -> bool:
    """True if request header explicitly enables test-mode behaviors."""
    try:
        return (request.headers.get("X-Test-Mode", "") or "").strip().lower() in ("true", "1", "yes", "on")
    except Exception:
        return False


def _require_paid_or_test_mode(request: Request, u: Dict[str, Any]) -> None:
    """
    Enforce:
      - DEV_MODE bypasses
      - Admin bypasses
      - If X-Test-Mode header is enabled AND user is a test-mode user => bypass
      - Otherwise require active subscription
    """
    if DEV_MODE:
        return
    if int(u.get("is_admin") or 0) == 1:
        return

    # test-mode bypass
    if _header_test_mode_enabled(request) and _is_test_mode_user(u):
        return

    if not is_active_subscription(u):
        raise HTTPException(status_code=402, detail="Subscription required")


def register_routes(api: FastAPI):
    """Register upload routes."""

    @api.post(f"{API_PREFIX}/uploads/zip")
    async def upload_zip(
        request: Request,
        file: UploadFile = File(...),
        u: Dict[str, Any] = Depends(current_user),
    ) -> Dict[str, Any]:
        _require_paid_or_test_mode(request, u)

        if not file.filename or not file.filename.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="File must be a .zip")

        user_id = str(u.get("id") or "")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        test_mode_active = check_test_mode_protection(u, request)
        user_upload_dir = (UPLOADS_DIR / "test_mode" / user_id / "zip") if test_mode_active else (UPLOADS_DIR / user_id / "zip")
        user_upload_dir.mkdir(parents=True, exist_ok=True)

        file_id = str(uuid.uuid4())
        file_path = user_upload_dir / f"{file_id}.zip"

        total = 0
        with file_path.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="File too large")
                f.write(chunk)

        now = _now()
        with db() as conn:
            conn.execute(
                """
                INSERT INTO file_uploads (id, user_id, file_type, file_name, file_path, file_size, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (file_id, user_id, "zip", file.filename or "upload.zip", str(file_path), total, now),
            )

        return {"id": file_id, "file_name": file.filename or "upload.zip", "file_type": "zip", "file_size": total, "created_at": now}

    @api.post(f"{API_PREFIX}/uploads/mp4")
    async def upload_mp4(
        request: Request,
        file: UploadFile = File(...),
        u: Dict[str, Any] = Depends(current_user),
    ) -> Dict[str, Any]:
        _require_paid_or_test_mode(request, u)

        if not file.filename or not file.filename.lower().endswith(".mp4"):
            raise HTTPException(status_code=400, detail="File must be a .mp4")

        user_id = str(u.get("id") or "")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Enforce 1 MP4 per round (between successful assistant messages)
        with db() as conn:
            recent_msg = conn.execute(
                """
                SELECT m.created_at FROM messages m
                JOIN chats c ON m.chat_id = c.id
                WHERE c.user_id = ? AND m.role = 'assistant'
                ORDER BY m.created_at DESC LIMIT 1
                """,
                (user_id,),
            ).fetchone()

            last_message_time = int(recent_msg["created_at"]) if recent_msg else 0

            recent_mp4 = conn.execute(
                """
                SELECT id, created_at FROM file_uploads
                WHERE user_id = ? AND file_type = 'mp4' AND created_at > ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (user_id, last_message_time),
            ).fetchone()

            if recent_mp4:
                raise HTTPException(
                    status_code=400,
                    detail="Only 1 MP4 allowed per round. Send a message first, then upload another MP4.",
                )

        test_mode_active = check_test_mode_protection(u, request)
        user_upload_dir = (UPLOADS_DIR / "test_mode" / user_id / "mp4") if test_mode_active else (UPLOADS_DIR / user_id / "mp4")
        user_upload_dir.mkdir(parents=True, exist_ok=True)

        file_id = str(uuid.uuid4())
        file_path = user_upload_dir / f"{file_id}.mp4"

        total = 0
        max_size = 100 * 1024 * 1024  # 100MB
        with file_path.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size:
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="File too large (max 100MB)")
                f.write(chunk)

        now = _now()
        with db() as conn:
            conn.execute(
                """
                INSERT INTO file_uploads (id, user_id, file_type, file_name, file_path, file_size, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (file_id, user_id, "mp4", file.filename or "upload.mp4", str(file_path), total, now),
            )

        return {"id": file_id, "file_name": file.filename or "upload.mp4", "file_type": "mp4", "file_size": total, "created_at": now}

    @api.post(f"{API_PREFIX}/uploads/mp3")
    async def upload_mp3(
        request: Request,
        file: UploadFile = File(...),
        u: Dict[str, Any] = Depends(current_user),
    ) -> Dict[str, Any]:
        _require_paid_or_test_mode(request, u)

        if not file.filename or not file.filename.lower().endswith(".mp3"):
            raise HTTPException(status_code=400, detail="File must be a .mp3")

        user_id = str(u.get("id") or "")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        test_mode_active = check_test_mode_protection(u, request)
        user_upload_dir = (UPLOADS_DIR / "test_mode" / user_id / "mp3") if test_mode_active else (UPLOADS_DIR / user_id / "mp3")
        user_upload_dir.mkdir(parents=True, exist_ok=True)

        file_id = str(uuid.uuid4())
        file_path = user_upload_dir / f"{file_id}.mp3"

        total = 0
        max_size = 50 * 1024 * 1024
        with file_path.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size:
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="File too large (max 50MB)")
                f.write(chunk)

        now = _now()
        with db() as conn:
            conn.execute(
                """
                INSERT INTO file_uploads (id, user_id, file_type, file_name, file_path, file_size, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (file_id, user_id, "mp3", file.filename or "upload.mp3", str(file_path), total, now),
            )

            # keep most recent 5 MP3 uploads
            rows = conn.execute(
                "SELECT id, file_path FROM file_uploads WHERE user_id = ? AND file_type = 'mp3' ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
            if rows and len(rows) > 5:
                for r in rows[5:]:
                    try:
                        Path(str(r["file_path"])).unlink()
                    except Exception:
                        pass
                    conn.execute("DELETE FROM file_uploads WHERE id = ?", (str(r["id"]),))

        return {"id": file_id, "file_name": file.filename or "upload.mp3", "file_type": "mp3", "file_size": total, "created_at": now}

    @api.post(f"{API_PREFIX}/uploads/image")
    async def upload_image(
        request: Request,
        file: UploadFile = File(...),
        u: Dict[str, Any] = Depends(current_user),
    ) -> Dict[str, Any]:
        user_id = str(u.get("id") or "")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        _require_paid_or_test_mode(request, u)

        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        filename_lower = file.filename.lower()
        if not filename_lower.endswith((".png", ".webp", ".jpg", ".jpeg")):
            raise HTTPException(status_code=400, detail="File must be .png, .jpg, .jpeg, or .webp")

        if filename_lower.endswith(".png"):
            file_type = "png"
        elif filename_lower.endswith((".jpg", ".jpeg")):
            file_type = "jpg"
        else:
            file_type = "webp"

        test_mode_active = check_test_mode_protection(u, request)
        current_count = get_image_upload_count(user_id)

        if not test_mode_active and current_count >= 20:
            raise HTTPException(
                status_code=400,
                detail=f"Upload limit reached. Maximum 20 images allowed per account. You have {current_count}.",
            )

        user_upload_dir = (UPLOADS_DIR / "test_mode" / user_id / "images") if test_mode_active else (UPLOADS_DIR / user_id / "images")
        user_upload_dir.mkdir(parents=True, exist_ok=True)

        file_id = str(uuid.uuid4())
        file_path = user_upload_dir / f"{file_id}.{file_type}"

        total = 0
        max_size = 20 * 1024 * 1024
        with file_path.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size:
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="File too large (max 20MB)")
                f.write(chunk)

        now = _now()
        with db() as conn:
            conn.execute(
                """
                INSERT INTO file_uploads (id, user_id, file_type, file_name, file_path, file_size, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (file_id, user_id, file_type, file.filename or f"upload.{file_type}", str(file_path), total, now),
            )

        return {"id": file_id, "file_name": file.filename or f"upload.{file_type}", "file_type": file_type, "file_size": total, "created_at": now}

    @api.post(f"{API_PREFIX}/uploads/code")
    async def upload_code_file(
        request: Request,
        file: UploadFile = File(...),
        u: Dict[str, Any] = Depends(current_user),
    ) -> Dict[str, Any]:
        user_id = str(u.get("id") or "")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Code uploads are gated like the rest
        _require_paid_or_test_mode(request, u)

        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        filename_lower = file.filename.lower()
        code_extensions = [
            ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c", ".h", ".hpp", ".cs", ".php", ".rb",
            ".swift", ".kt", ".scala", ".clj", ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd", ".sql", ".html",
            ".css", ".scss", ".less", ".sass", ".vue", ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
            ".md", ".txt", ".log",
        ]
        if not any(filename_lower.endswith(ext) for ext in code_extensions):
            raise HTTPException(status_code=400, detail="Unsupported code file type.")

        ext = Path(filename_lower).suffix.lower()
        test_mode_active = check_test_mode_protection(u, request)

        user_upload_dir = (UPLOADS_DIR / "test_mode" / user_id / "code") if test_mode_active else (UPLOADS_DIR / user_id / "code")
        user_upload_dir.mkdir(parents=True, exist_ok=True)

        file_id = str(uuid.uuid4())
        file_path = user_upload_dir / f"{file_id}{ext}"

        total = 0
        max_size = 5 * 1024 * 1024
        with file_path.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size:
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="File too large (max 5MB)")
                f.write(chunk)

        now = _now()
        with db() as conn:
            conn.execute(
                """
                INSERT INTO file_uploads (id, user_id, file_type, file_name, file_path, file_size, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (file_id, user_id, "code", file.filename, str(file_path), total, now),
            )

        return {"id": file_id, "file_name": file.filename, "file_type": "code", "file_size": total, "created_at": now}

    @api.get(f"{API_PREFIX}/uploads")
    async def list_uploads(
        request: Request,
        file_type: Optional[str] = None,
        u: Dict[str, Any] = Depends(require_subscribed),
    ) -> Dict[str, Any]:
        user_id = str(u.get("id") or "")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        query = "SELECT * FROM file_uploads WHERE user_id = ?"
        params = [user_id]

        if file_type:
            query += " AND file_type = ?"
            params.append(file_type)

        query += " ORDER BY created_at DESC"

        with db() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        uploads = [
            {
                "id": str(r["id"]),
                "file_name": str(r["file_name"]),
                "file_type": str(r["file_type"]),
                "file_size": int(r["file_size"]),
                "created_at": int(r["created_at"]),
            }
            for r in rows
        ]

        image_count = get_image_upload_count(user_id)
        return {"uploads": uploads, "image_upload_count": image_count, "image_upload_limit": 20}

    @api.get(f"{API_PREFIX}/uploads/{{file_id}}")
    async def get_upload(
        file_id: str,
        request: Request,
        u: Dict[str, Any] = Depends(require_subscribed),
    ) -> FileResponse:
        user_id = str(u.get("id") or "")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        with db() as conn:
            row = conn.execute(
                "SELECT * FROM file_uploads WHERE id = ? AND user_id = ?",
                (file_id, user_id),
            ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = Path(str(row["file_path"]))
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        return FileResponse(str(file_path), filename=str(row["file_name"]), media_type="application/octet-stream")

    @api.delete(f"{API_PREFIX}/uploads/{{file_id}}")
    async def delete_upload(
        file_id: str,
        request: Request,
        u: Dict[str, Any] = Depends(current_user),
    ) -> Dict[str, Any]:
        _require_paid_or_test_mode(request, u)

        user_id = str(u.get("id") or "")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        with db() as conn:
            row = conn.execute(
                "SELECT * FROM file_uploads WHERE id = ? AND user_id = ?",
                (file_id, user_id),
            ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = Path(str(row["file_path"]))

        with db() as conn:
            conn.execute("DELETE FROM file_uploads WHERE id = ?", (file_id,))

        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass

        return {"ok": True, "id": file_id}
