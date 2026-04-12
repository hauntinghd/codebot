"""Helper functions for chat operations."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

from backend.database import _now, db

logger = logging.getLogger("codebot")


def get_chat_owner(chat_id: str) -> str:
    """Get owner user_id for a chat."""
    with db() as conn:
        row = conn.execute("SELECT user_id FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not row:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Chat not found")
        return str(row["user_id"])


def get_recent_messages(chat_id: str, limit: int) -> List[sqlite3.Row]:
    """Get recent messages for a chat."""
    with db() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?",
            (chat_id, int(limit)),
        ).fetchall()
    return list(reversed(rows))


def set_chat_title_if_empty(chat_id: str, hint: str) -> None:
    """Set chat title if it's empty."""
    hint = (hint or "").strip()
    if not hint:
        return
    hint = hint[:80]
    with db() as conn:
        row = conn.execute("SELECT title FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if row and (row["title"] or "") == "":
            conn.execute("UPDATE chats SET title = ?, updated_at = ? WHERE id = ?", (hint, _now(), chat_id))


def check_test_mode_protection(user: sqlite3.Row, request) -> bool:
    """Check if test mode is active."""
    from backend.auth import _is_test_mode_user

    if not _is_test_mode_user(user):
        return False
    return request.headers.get("X-Test-Mode", "").lower() in ("true", "1", "yes")


def get_image_upload_count(user_id: str) -> int:
    """Get count of PNG/WebP uploads for a user."""
    with db() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) as count FROM file_uploads
            WHERE user_id = ? AND file_type IN ('png', 'webp')
            """,
            (user_id,),
        ).fetchone()
        return int(row["count"] or 0) if row else 0


def build_file_context(
    user_id: str,
    max_tokens: int = 16000,
    allowed_file_ids: Optional[list[str]] = None,
) -> tuple[str, int, int]:
    """
    Build file context from uploaded files.
    Returns: (file_context_text, file_count, code_length)
    """
    import tempfile

    from backend.config import MAX_FILE_READ_BYTES
    from backend.common_helpers import (
        estimate_tokens,
        extract_zip_safely,
        file_importance_score,
        read_text_file_limited,
    )

    file_context_parts: List[str] = []
    file_count = 0
    code_length = 0
    current_tokens = 0

    # Fetch candidate files
    with db() as conn:
        if allowed_file_ids:
            placeholders = ",".join(["?"] * len(allowed_file_ids))
            rows = conn.execute(
                f"SELECT * FROM file_uploads WHERE user_id = ? AND id IN ({placeholders}) ORDER BY created_at DESC",
                (user_id, *allowed_file_ids),
            ).fetchall()
            zip_rows = [r for r in rows if str(r["file_type"]).lower() == "zip"]
            code_rows = [r for r in rows if str(r["file_type"]).lower() == "code"]
        else:
            zip_rows = []
            zip_row = conn.execute(
                "SELECT * FROM file_uploads WHERE user_id = ? AND file_type = 'zip' ORDER BY created_at DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            if zip_row:
                zip_rows.append(zip_row)

            code_rows = conn.execute(
                "SELECT * FROM file_uploads WHERE user_id = ? AND file_type = 'code' ORDER BY created_at DESC LIMIT 10",
                (user_id,),
            ).fetchall()

    # Process ZIP files
    for zip_row in zip_rows:
        zip_path = Path(str(zip_row["file_path"]))
        if not zip_path.exists():
            continue

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                extract_zip_safely(zip_path, Path(tmpdir))
                extracted_root = Path(tmpdir)

                file_candidates: List[Tuple[int, str, Path]] = []
                for fp in extracted_root.rglob("*"):
                    if not fp.is_file():
                        continue

                    rel_path = str(fp.relative_to(extracted_root)).replace("\\", "/")

                    # skip binaries/media/archives
                    if any(
                        rel_path.lower().endswith(ext)
                        for ext in (
                            ".png",
                            ".jpg",
                            ".jpeg",
                            ".gif",
                            ".webp",
                            ".ico",
                            ".pdf",
                            ".zip",
                            ".tar",
                            ".gz",
                            ".exe",
                            ".dll",
                            ".so",
                            ".dylib",
                        )
                    ):
                        continue

                    score = file_importance_score(rel_path)
                    if score > -500:
                        file_candidates.append((score, rel_path, fp))

                file_candidates.sort(key=lambda x: x[0], reverse=True)

                for _score, rel_path, fp in file_candidates:
                    if current_tokens >= max_tokens:
                        break

                    try:
                        txt = read_text_file_limited(fp, MAX_FILE_READ_BYTES)
                        if not txt.strip():
                            continue

                        file_tokens = estimate_tokens(txt)

                        # Hard per-file cap
                        if file_tokens > 2000:
                            max_chars = int(1500 / 0.25)  # heuristic
                            txt = txt[:max_chars] + "\n\n[... file truncated for length ...]"
                            file_tokens = 1500

                        if current_tokens + file_tokens <= max_tokens:
                            code_length += len(txt)
                            file_context_parts.append(f"--- FILE: {rel_path} ---\n{txt}\n")
                            file_count += 1
                            current_tokens += file_tokens
                        else:
                            break
                    except Exception:
                        continue
            except Exception as e:
                logger.warning("ZIP extraction error: %s", e)

    # Add uploaded code files
    for code_row in code_rows:
        file_name = "unknown"
        try:
            if code_row is not None:
                try:
                    file_name = str(code_row["file_name"])
                except Exception:
                    file_name = "unknown"

            code_path = Path(str(code_row["file_path"]))
            if not (code_path.exists() and code_path.is_file()):
                continue

            txt = read_text_file_limited(code_path, MAX_FILE_READ_BYTES)
            if not txt.strip():
                continue

            file_tokens = estimate_tokens(txt)
            if file_tokens > 2000:
                max_chars = int(1500 / 0.25)
                txt = txt[:max_chars] + "\n\n[... file truncated for length - MVP optimization ...]"
                file_tokens = 1500

            if current_tokens + file_tokens <= max_tokens:
                code_length += len(txt)
                file_context_parts.append(f"--- CODE FILE: {file_name} ---\n{txt}\n")
                file_count += 1
                current_tokens += file_tokens
            else:
                break
        except Exception as e:
            logger.warning("Error reading code file %s: %s", file_name, e)
            continue

    return "\n".join(file_context_parts), file_count, code_length
