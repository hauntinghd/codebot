"""Multi-media file upload and analysis routes for CodeBot.

Supports individual analysis of:
- Images (PNG, JPEG, WebP): Vision API
- Video (MP4): Frame extraction
- Audio (MP3, WAV): Transcription
- Code files: Direct analysis
- ZIP archives: Extraction
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
import sqlite3

from backend.auth import current_user, is_active_subscription
from backend.config import API_PREFIX, UPLOADS_DIR
from backend.database import _now, db
from backend.services.media_handler import FileValidator, MultiMediaAnalyzer

logger = logging.getLogger("codebot")


def register_multimedia_routes(api: FastAPI):
    """Register multi-media upload routes."""

    @api.post(f"{API_PREFIX}/uploads/validate")
    async def validate_files(
        files: List[UploadFile] = File(...),
        u: sqlite3.Row = Depends(current_user),
    ) -> Dict[str, Any]:
        """
        Validate multiple files for upload without actually uploading.

        Returns validation results for each file.
        """
        results = []
        current_uploads = {"images": 0, "video": 0, "audio": 0, "code": 0, "archive": 0}

        for file in files:
            validation = FileValidator.validate_file(
                filename=file.filename or "unknown",
                file_size=file.size or 0,
                mimetype=file.content_type,
                current_uploads=current_uploads,
            )

            if validation["valid"]:
                # Increment count for this type
                current_uploads[validation["file_type"]] += 1

            results.append({
                "filename": file.filename,
                **validation,
            })

        return {
            "valid": all(r["valid"] for r in results),
            "validations": results,
            "summary": FileValidator.get_summary({
                ft: [r for r in results if r.get("file_type") == ft and r["valid"]]
                for ft in current_uploads.keys()
            }),
        }

    @api.post(f"{API_PREFIX}/uploads/multimedia")
    async def upload_multimedia(
        files: List[UploadFile] = File(...),
        u: sqlite3.Row = Depends(current_user),
    ) -> Dict[str, Any]:
        """
        Upload multiple media files (images, video, audio, code, archives).

        Each file is stored separately and can be analyzed individually.
        """
        user_id = str(u["id"])

        # Validate first
        current_uploads = {"images": 0, "video": 0, "audio": 0, "code": 0, "archive": 0}
        validations = []

        for file in files:
            validation = FileValidator.validate_file(
                filename=file.filename or "unknown",
                file_size=file.size or 0,
                mimetype=file.content_type,
                current_uploads=current_uploads,
            )
            validations.append(validation)

            if validation["valid"]:
                current_uploads[validation["file_type"]] += 1
            else:
                raise HTTPException(
                    status_code=400,
                    detail=validation["error"],
                )

        # All valid, now store files
        uploaded = []
        with db() as conn:
            for file, validation in zip(files, validations):
                if not validation["valid"]:
                    continue

                file_type = validation["file_type"]
                file_id = str(uuid.uuid4())

                # Create directory for file type
                user_upload_dir = UPLOADS_DIR / user_id / file_type
                user_upload_dir.mkdir(parents=True, exist_ok=True)

                # Read file content
                content = await file.read()
                file_size = len(content)

                # Save file
                file_path = user_upload_dir / f"{file_id}_{file.filename}"
                file_path.write_bytes(content)

                # Record in database
                conn.execute(
                    """
                    INSERT INTO file_uploads (id, user_id, file_name, file_type, file_size, file_path, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_id,
                        user_id,
                        file.filename or "unknown",
                        file_type,
                        file_size,
                        str(file_path),
                        _now(),
                    ),
                )

                # Get analysis cost estimate
                cost_estimate = MultiMediaAnalyzer.get_analysis_cost(file_type, file_size)

                uploaded.append({
                    "id": file_id,
                    "filename": file.filename,
                    "type": file_type,
                    "size": file_size,
                    "size_mb": round(file_size / 1024 / 1024, 2),
                    "cost_estimate": cost_estimate,
                })

        return {
            "uploaded_count": len(uploaded),
            "uploads": uploaded,
            "summary": FileValidator.get_summary({
                ft: [u for u in uploaded if u["type"] == ft]
                for ft in current_uploads.keys()
            }),
        }

    @api.post(f"{API_PREFIX}/uploads/analyze")
    async def analyze_file(
        file_id: str,
        u: sqlite3.Row = Depends(current_user),
    ) -> Dict[str, Any]:
        """
        Analyze a single uploaded file.

        The analysis approach depends on file type:
        - Images: Vision API (describe content)
        - Video: Frame extraction + vision
        - Audio: Transcription
        - Code: Direct analysis in chat
        - Archives: Extraction summary
        """
        user_id = str(u["id"])

        # Get file metadata
        with db() as conn:
            file_meta = conn.execute(
                "SELECT * FROM file_uploads WHERE id = ? AND user_id = ?",
                (file_id, user_id),
            ).fetchone()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        file_type = file_meta["file_type"]
        file_path = file_meta["file_path"]

        # Determine analysis approach
        analysis_result = {
            "file_id": file_id,
            "filename": file_meta["file_name"],
            "type": file_type,
            "status": "ready_for_analysis",
        }

        if not Path(file_path).exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        # Different handlers per type
        if file_type == "images":
            analysis_result["instructions"] = "Use Vision API to analyze image content"
            analysis_result["analysis_method"] = "vision_api"
        elif file_type == "video":
            analysis_result["instructions"] = "Extract key frames and analyze with Vision API"
            analysis_result["analysis_method"] = "video_frames"
        elif file_type == "audio":
            analysis_result["instructions"] = "Transcribe audio, then analyze transcript"
            analysis_result["analysis_method"] = "transcription"
        elif file_type == "code":
            analysis_result["instructions"] = "Analyze code directly in chat context"
            analysis_result["analysis_method"] = "direct_analysis"
        elif file_type == "archive":
            analysis_result["instructions"] = "Extract and analyze file structure"
            analysis_result["analysis_method"] = "extraction"

        return analysis_result

    @api.get(f"{API_PREFIX}/uploads/multimedia")
    async def list_multimedia(
        u: sqlite3.Row = Depends(current_user),
    ) -> Dict[str, Any]:
        """List all uploaded multimedia files by type."""
        user_id = str(u["id"])

        with db() as conn:
            files = conn.execute(
                "SELECT * FROM file_uploads WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()

        # Group by type
        by_type = {}
        for file in files:
            file_type = file["file_type"]
            if file_type not in by_type:
                by_type[file_type] = []

            by_type[file_type].append({
                "id": file["id"],
                "filename": file["file_name"],
                "size": file["file_size"],
                "size_mb": round(file["file_size"] / 1024 / 1024, 2),
                "created_at": file["created_at"],
            })

        return {
            "total": len(files),
            "by_type": by_type,
            "summary": FileValidator.get_summary(by_type),
        }

    @api.delete(f"{API_PREFIX}/uploads/multimedia/{{file_id}}")
    async def delete_multimedia(
        file_id: str,
        u: sqlite3.Row = Depends(current_user),
    ) -> Dict[str, Any]:
        """Delete a multimedia file."""
        user_id = str(u["id"])

        with db() as conn:
            file_meta = conn.execute(
                "SELECT * FROM file_uploads WHERE id = ? AND user_id = ?",
                (file_id, user_id),
            ).fetchone()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        # Delete from disk
        file_path = Path(file_meta["file_path"])
        if file_path.exists():
            file_path.unlink()

        # Delete from database
        with db() as conn:
            conn.execute("DELETE FROM file_uploads WHERE id = ?", (file_id,))

        return {"deleted": file_id, "filename": file_meta["file_name"]}

    @api.get(f"{API_PREFIX}/uploads/limits")
    async def get_upload_limits(
        u: sqlite3.Row = Depends(current_user),
    ) -> Dict[str, Any]:
        """Get upload limits and current usage."""
        user_id = str(u["id"])

        with db() as conn:
            counts = {}
            for file_type in ["images", "video", "audio", "code", "archive"]:
                count = conn.execute(
                    "SELECT COUNT(*) as cnt FROM file_uploads WHERE user_id = ? AND file_type = ?",
                    (user_id, file_type),
                ).fetchone()["cnt"]
                counts[file_type] = count

        from backend.services.media_handler import FILE_CONFIGS

        return {
            "limits": {ft: FILE_CONFIGS[ft]["max_count"] for ft in counts.keys()},
            "current_usage": counts,
            "available": {
                ft: FILE_CONFIGS[ft]["max_count"] - counts.get(ft, 0)
                for ft in FILE_CONFIGS.keys()
            },
        }


__all__ = ["register_multimedia_routes"]
