"""Chats routes (list/create/messages/stream)."""

from __future__ import annotations

import inspect
import json
import os
import time
import uuid
from typing import Any, AsyncGenerator, Dict, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.auth import require_subscribed
from backend.config import API_PREFIX
from backend.database import db


class ChatCreate(BaseModel):
    title: Optional[str] = None


MAX_CHAT_MESSAGES_CONTEXT = 18


def _now() -> int:
    return int(time.time())


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return any(r["name"] == column for r in rows)


def _table_exists(conn, table: str) -> bool:
    r = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return r is not None


def _ensure_tables() -> None:
    """
    Ensure required tables/columns exist.
    - chats must have updated_at
    - Prefer existing `messages` table if present; else create `chat_messages`
    """
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )

        # If older chats existed without updated_at, migrate.
        if not _column_exists(conn, "chats", "updated_at"):
            conn.execute("ALTER TABLE chats ADD COLUMN updated_at INTEGER;")
            conn.execute("UPDATE chats SET updated_at = created_at WHERE updated_at IS NULL;")

        # Only create fallback table if canonical messages doesn't exist.
        if not _table_exists(conn, "messages") and not _table_exists(conn, "chat_messages"):
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )


def _assert_chat_owner(conn, chat_id: str, user_id: str) -> None:
    row = conn.execute("SELECT user_id FROM chats WHERE id = ?", (chat_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Chat not found")
    if str(row["user_id"]) != str(user_id):
        raise HTTPException(status_code=403, detail="Forbidden")


def _write_message(
    conn,
    *,
    chat_id: str,
    user_id: str,
    role: str,
    content: str,
    created_at: int,
    ai_layer: Optional[str] = None,
) -> str:
    """
    Write into canonical `messages` if present; else into `chat_messages`.
    Returns message_id.
    """
    msg_id = str(uuid.uuid4())

    if _table_exists(conn, "messages"):
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(messages);").fetchall()]
        if "ai_layer" in cols and ai_layer is not None:
            conn.execute(
                "INSERT INTO messages (id, chat_id, role, content, created_at, ai_layer) VALUES (?, ?, ?, ?, ?, ?)",
                (msg_id, chat_id, role, content, created_at, ai_layer),
            )
        else:
            conn.execute(
                "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (msg_id, chat_id, role, content, created_at),
            )
    else:
        conn.execute(
            "INSERT INTO chat_messages (id, chat_id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, chat_id, user_id, role, content, created_at),
        )

    return msg_id


def _get_recent_messages_safe(chat_id: str, limit: int) -> list[dict[str, Any]]:
    """
    Uses your existing helper if available, else falls back to DB read.
    """
    try:
        from backend.helpers.messages import get_recent_messages  # type: ignore

        return get_recent_messages(chat_id, limit)
    except Exception:
        with db() as conn:
            if _table_exists(conn, "messages"):
                rows = conn.execute(
                    "SELECT role, content, created_at FROM messages WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?",
                    (chat_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT role, content, created_at FROM chat_messages WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?",
                    (chat_id, limit),
                ).fetchall()

        out = [{"role": str(r["role"]), "content": str(r["content"]), "created_at": int(r["created_at"])} for r in rows]
        out.reverse()
        return out


def _wants_zip(user_text: str, blueprint: Optional[Dict[str, Any]] = None) -> bool:
    ut = (user_text or "").lower()
    if any(k in ut for k in ["zip", ".zip", "send as a zip", "as a zip", "zip file"]):
        return True
    bp = blueprint or {}
    fte = bp.get("files_to_edit") or []
    return isinstance(fte, list) and len(fte) >= 6


def _try_build_zip_from_engineer_output(engineer_out: Any, project_name: str) -> Optional[Dict[str, Any]]:
    """
    Tries to call your project packager without hard-depending on a specific API.
    """
    if not (isinstance(engineer_out, dict) and isinstance(engineer_out.get("files"), list)):
        return None

    files = engineer_out.get("files") or []
    if not files:
        return None

    try:
        from backend.services import project_packager  # type: ignore
    except Exception:
        try:
            import backend.services.project_packager as project_packager  # type: ignore
        except Exception:
            return None

    for fn_name in ("create_project_zip", "package_project", "package_files", "build_zip", "make_zip"):
        if hasattr(project_packager, fn_name):
            fn = getattr(project_packager, fn_name)
            result = fn(files=files, project_name=project_name)  # type: ignore

            zip_path = None
            if isinstance(result, dict):
                zip_path = result.get("zip_path") or result.get("path") or result.get("file")
            else:
                zip_path = result

            if not zip_path:
                return None

            return {"zip_path": str(zip_path), "project_name": project_name, "file_count": len(files)}

    return None


def _get_field(row: Any, *names: str) -> Optional[Any]:
    if hasattr(row, "get"):
        for n in names:
            v = row.get(n)
            if v is not None:
                return v
    try:
        keys = set(row.keys())
        for n in names:
            if n in keys:
                return row[n]
    except Exception:
        pass
    return None


def _decrypt_user_key_best_effort(u: Any) -> Optional[str]:
    """
    Best-effort decrypt for BYOK if your repo has a decrypt helper.
    If it doesn't, returns None and resolver will fall back to server-side keys.
    """
    raw_key = _get_field(u, "api_key", "openai_api_key", "llm_api_key")
    if raw_key:
        k = str(raw_key).strip()
        return k or None

    enc_key = _get_field(u, "api_key_encrypted", "encrypted_api_key")
    if not enc_key:
        return None

    enc_key_str = str(enc_key).strip()
    if not enc_key_str:
        return None

    candidates = [
        ("backend.auth", "decrypt_api_key"),
        ("backend.security", "decrypt_api_key"),
        ("backend.crypto", "decrypt_api_key"),
        ("backend.helpers.crypto", "decrypt_api_key"),
        ("backend.helpers.security", "decrypt_api_key"),
    ]
    for mod_name, fn_name in candidates:
        try:
            mod = __import__(mod_name, fromlist=[fn_name])
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                out = fn(enc_key_str)
                if out:
                    return str(out).strip() or None
        except Exception:
            continue

    return None


def _pick_model_from_env_or_config() -> str:
    """
    Avoid hardcoding a model you may not have access to.
    Order:
      CODEBOT_MODEL -> XAI_MODEL -> GROK_MODEL -> DEFAULT_MODEL -> backend.config.DEFAULT_MODEL -> fallback
    """
    for k in ("CODEBOT_MODEL", "XAI_MODEL", "GROK_MODEL", "DEFAULT_MODEL"):
        v = os.getenv(k)
        if v and v.strip():
            return v.strip()

    try:
        from backend.config import DEFAULT_MODEL  # type: ignore
        if DEFAULT_MODEL:
            return str(DEFAULT_MODEL).strip()
    except Exception:
        pass

    # Conservative fallback (you SHOULD set env to a model you have access to)
    return "grok-4"


def _safe_call(fn: Any, **kwargs: Any) -> Any:
    """
    Calls fn with ONLY the kwargs it actually supports.
    - If fn accepts **kwargs, pass through all kwargs.
    - Otherwise, filter to matching parameter names.
    """
    sig = inspect.signature(fn)
    params = sig.parameters

    # Supports **kwargs?
    for p in params.values():
        if p.kind == inspect.Parameter.VAR_KEYWORD:
            return fn(**kwargs)

    filtered = {k: v for k, v in kwargs.items() if k in params}
    return fn(**filtered)


def _call_internet_policy(user_text: str, file_count: int, code_length: int) -> Dict[str, Any]:
    """
    Your helper signature has changed multiple times in your repo history.
    This wrapper will NOT break if the helper adds/removes kwargs.
    """
    # Try common import locations/names, but do not crash if missing.
    fn = None
    try:
        from backend.helpers.internet_policy import check_internet_policy  # type: ignore
        fn = check_internet_policy
    except Exception:
        try:
            from backend.helpers.internet_policy import check_internet_policy as check_internet_policy2  # type: ignore
            fn = check_internet_policy2
        except Exception:
            fn = None

    if not fn:
        # If helper isn't present, default to "not allowed" to be safe.
        return {"allowed": False, "reason": "internet_policy helper not available"}

    try:
        out = _safe_call(
            fn,
            user_text=user_text,
            prompt=user_text,
            text=user_text,
            file_count=file_count,
            files_count=file_count,
            code_length=code_length,
            code_chars=code_length,
        )
        if isinstance(out, dict):
            return out
        # normalize non-dict returns
        return {"allowed": bool(out), "reason": None}
    except Exception as e:
        return {"allowed": False, "reason": f"internet_policy error: {e}"}


def _resolve_llm_client_and_model(u: Any) -> Tuple[Any, str, bool]:
    """
    Uses the resolver functions that exist in your repo:
      - backend.services.ai.provider_resolver.resolve_provider_and_key
      - backend.services.ai.provider_resolver.make_llm_client

    Returns: (client, model, is_byok)
    """
    from backend.services.ai import provider_resolver as pr  # type: ignore

    user_provider = _get_field(u, "provider", "llm_provider", "ai_provider", "current_provider")
    user_key = _decrypt_user_key_best_effort(u)

    provider, api_key = pr.resolve_provider_and_key(
        user_provider=str(user_provider).strip() if user_provider else None,
        user_key=user_key,
    )
    client = pr.make_llm_client(provider=provider, api_key=api_key)

    model = _pick_model_from_env_or_config()
    is_byok = bool(user_key)
    return client, model, is_byok


def _build_file_context_compat(user_id: str) -> Tuple[str, int, int]:
    """
    Your build_file_context signature is:
      (files: Optional[Sequence[str]] = None, *, project_root: Optional[str] = None) -> str

    So we:
      - call it without max_tokens
      - derive file_count/code_length from returned context
    """
    try:
        from backend.helpers.files_context import build_file_context  # type: ignore
    except Exception:
        return "", 0, 0

    project_root = os.getenv("PROJECT_ROOT") or os.getenv("CODEBOT_PROJECT_ROOT")

    try:
        ctx = _safe_call(build_file_context, files=None, project_root=project_root)
        ctx_str = str(ctx or "")
    except Exception:
        ctx_str = ""

    # Best-effort metrics (used only for policy heuristics)
    code_length = len(ctx_str)
    # file_count is hard to know from a single string; approximate by counting common separators
    file_count = 0
    if ctx_str:
        # crude heuristic: count occurrences of typical filename headers
        file_count = ctx_str.count("File: ") + ctx_str.count("file: ") + ctx_str.count("PATH: ") + ctx_str.count("\n--- ")

    return ctx_str, int(file_count), int(code_length)


def register_routes(api: FastAPI) -> None:
    _ensure_tables()

    @api.get(f"{API_PREFIX}/chats")
    async def list_chats(
        request: Request,
        u=Depends(require_subscribed),
    ) -> Dict[str, Any]:
        user_id = str(u["id"])
        with db() as conn:
            rows = conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM chats
                WHERE user_id = ?
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 200
                """,
                (user_id,),
            ).fetchall()

        return {
            "chats": [
                {
                    "id": str(r["id"]),
                    "title": (str(r["title"]) if r["title"] is not None else "New Chat"),
                    "created_at": int(r["created_at"]),
                    "updated_at": int(r["updated_at"]) if r["updated_at"] is not None else int(r["created_at"]),
                }
                for r in rows
            ]
        }

    @api.post(f"{API_PREFIX}/chats")
    async def create_chat(
        payload: ChatCreate,
        request: Request,
        u=Depends(require_subscribed),
    ) -> Dict[str, Any]:
        user_id = str(u["id"])
        chat_id = str(uuid.uuid4())
        now = _now()
        title = ((payload.title or "New Chat").strip()[:200]) or "New Chat"

        with db() as conn:
            conn.execute(
                """
                INSERT INTO chats (id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (chat_id, user_id, title, now, now),
            )

        return {"id": chat_id, "title": title, "created_at": now, "updated_at": now}

    @api.get(f"{API_PREFIX}/chats/{{chat_id}}/messages")
    async def get_messages(
        chat_id: str,
        request: Request,
        u=Depends(require_subscribed),
    ) -> Dict[str, Any]:
        user_id = str(u["id"])
        with db() as conn:
            _assert_chat_owner(conn, chat_id, user_id)

            if _table_exists(conn, "messages"):
                rows = conn.execute(
                    """
                    SELECT id, role, content, created_at
                    FROM messages
                    WHERE chat_id = ?
                    ORDER BY created_at ASC
                    LIMIT 500
                    """,
                    (chat_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, role, content, created_at
                    FROM chat_messages
                    WHERE chat_id = ?
                    ORDER BY created_at ASC
                    LIMIT 500
                    """,
                    (chat_id,),
                ).fetchall()

        return {
            "messages": [
                {
                    "id": str(r["id"]),
                    "role": str(r["role"]),
                    "content": str(r["content"]),
                    "created_at": int(r["created_at"]),
                }
                for r in rows
            ]
        }

    @api.get(f"{API_PREFIX}/chats/{{chat_id}}/stream")
    async def stream_chat_message(
        chat_id: str,
        content: str,
        request: Request,
        u=Depends(require_subscribed),
    ):
        """
        SSE stream connected to CodeBot pipeline:
          router -> engineer -> auditor -> corrector
        plus optional zip artifact packaging when engineer returns structured project files.

        Critical: This generator NEVER raises after the response starts.
        It emits SSE 'error' events instead, so the UI doesn't show "stream connection lost".
        """
        user_id = str(u["id"])
        user_text = (content or "").strip()
        if not user_text:
            raise HTTPException(status_code=400, detail="Message content required")

        async def event_generator() -> AsyncGenerator[str, None]:
            # Helper to emit events
            def _emit(obj: Dict[str, Any]) -> str:
                return f"data: {json.dumps(obj)}\n\n"

            # Heavy imports inside generator only.
            try:
                from backend.services.corrector import correct_and_verify  # type: ignore
                from backend.services.ai.router import create_blueprint  # type: ignore
                from backend.services.ai.engineer import generate_code  # type: ignore
                from backend.services.ai.auditor import audit_code  # type: ignore
            except Exception as import_err:
                yield _emit({"type": "error", "message": f"Pipeline import error: {import_err}"})
                return

            # Resolve LLM client/model using your real provider_resolver functions.
            try:
                client, model, is_byok = _resolve_llm_client_and_model(u)
            except Exception as e:
                yield _emit({"type": "error", "message": f"Pipeline resolver error: {e}"})
                return

            # 1) Ownership + persist user message
            now = _now()
            try:
                with db() as conn:
                    _assert_chat_owner(conn, chat_id, user_id)
                    user_msg_id = _write_message(
                        conn,
                        chat_id=chat_id,
                        user_id=user_id,
                        role="user",
                        content=user_text,
                        created_at=now,
                    )
                    conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now, chat_id))
            except Exception as e:
                yield _emit({"type": "error", "message": f"DB error writing user message: {e}"})
                return

            yield _emit({"type": "user_message", "id": user_msg_id})

            # 2) Context + internet policy (compat)
            file_context, file_count, code_length = _build_file_context_compat(user_id)
            recent = _get_recent_messages_safe(chat_id, MAX_CHAT_MESSAGES_CONTEXT)

            internet_access_check = _call_internet_policy(
                user_text=user_text,
                file_count=file_count,
                code_length=code_length,
            )
            yield _emit(
                {
                    "type": "internet_policy",
                    "allowed": internet_access_check.get("allowed"),
                    "reason": internet_access_check.get("reason"),
                }
            )

            # 3) Router -> blueprint
            try:
                yield _emit({"type": "layer_start", "layer": "router", "description": "Planning approach..."})
                blueprint = await create_blueprint(
                    user_request=user_text,
                    file_context=(file_context[:5000] if file_context else None),
                    chat_history=recent,
                )
                yield _emit({"type": "layer_complete", "layer": "router", "data": blueprint})
            except Exception as e:
                yield _emit({"type": "error", "message": f"Router failed: {e}"})
                return

            # 4) Engineer -> code / project
            try:
                yield _emit({"type": "layer_start", "layer": "engineer", "description": f"Generating code... (model={model})"})
                user_plan = str(_get_field(u, "plan") or "none")

                engineer_out = await generate_code(
                    user_request=user_text,
                    blueprint=blueprint,
                    file_context=file_context,
                    chat_history=recent,
                    api_client=client,
                    model=model,
                    user_plan=user_plan,
                    user_id=user_id,
                )
            except HTTPException as he:
                # IMPORTANT: Do not raise (SSE already started). Emit error event.
                yield _emit(
                    {
                        "type": "error",
                        "message": f"Engineer failed ({he.status_code}): {he.detail}",
                        "hint": "If this is a 404 model error, set CODEBOT_MODEL/XAI_MODEL/GROK_MODEL/DEFAULT_MODEL to a model your xAI key can access.",
                    }
                )
                # Persist as assistant message so it shows in history
                try:
                    with db() as conn:
                        asst_id = _write_message(
                            conn,
                            chat_id=chat_id,
                            user_id=user_id,
                            role="assistant",
                            content=f"[Engineer Error] {he.detail}",
                            created_at=_now(),
                            ai_layer="engineer_error",
                        )
                        conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (_now(), chat_id))
                    yield _emit({"type": "complete", "message_id": asst_id, "content": f"[Engineer Error] {he.detail}"})
                except Exception:
                    pass
                return
            except Exception as e:
                yield _emit({"type": "error", "message": f"Engineer failed: {e}"})
                return

            wants_zip = _wants_zip(user_text, blueprint)
            artifact = None
            project_name = None
            preview_text = None

            if isinstance(engineer_out, dict) and isinstance(engineer_out.get("files"), list):
                project_name = str(engineer_out.get("project_name") or "generated-project")
                preview_text = str(engineer_out.get("_preview") or "Project generated.")
                if wants_zip:
                    artifact = _try_build_zip_from_engineer_output(engineer_out, project_name)

            # Stream output without flooding UI
            try:
                if isinstance(engineer_out, dict) and isinstance(engineer_out.get("files"), list):
                    yield _emit({"type": "code_chunk", "data": preview_text or "Project generated."})
                else:
                    generated_text = str(engineer_out or "")
                    chunk = 512
                    for i in range(0, len(generated_text), chunk):
                        yield _emit({"type": "code_chunk", "data": generated_text[i : i + chunk]})
                yield _emit({"type": "layer_complete", "layer": "engineer"})
            except Exception as e:
                yield _emit({"type": "error", "message": f"Streaming engineer output failed: {e}"})
                return

            # 5) Auditor
            try:
                yield _emit({"type": "layer_start", "layer": "auditor", "description": "Reviewing code..."})
                audit_result = await audit_code(
                    generated_code=engineer_out,
                    blueprint=blueprint,
                    user_request=user_text,
                    api_client=client,
                    model=model,
                )
                yield _emit({"type": "layer_complete", "layer": "auditor", "data": audit_result})
            except Exception as e:
                yield _emit({"type": "error", "message": f"Auditor failed: {e}"})
                audit_result = None  # continue to corrector best-effort

            # 6) Corrector
            try:
                yield _emit({"type": "layer_start", "layer": "corrector", "description": "Verifying accuracy..."})

                if isinstance(engineer_out, dict) and isinstance(engineer_out.get("files"), list):
                    final_text_for_corrector = preview_text or "Project generated."
                else:
                    if isinstance(audit_result, dict) and audit_result.get("verified_code"):
                        final_text_for_corrector = str(audit_result.get("verified_code"))
                    else:
                        final_text_for_corrector = str(engineer_out or "")

                corrected_response, verification_analysis = await correct_and_verify(
                    response=final_text_for_corrector,
                    context={"user_request": user_text, "blueprint": blueprint},
                    files_accessed=[],
                    inject_citations=bool(internet_access_check.get("allowed")),
                )

                yield _emit(
                    {
                        "type": "layer_complete",
                        "layer": "corrector",
                        "verified": (verification_analysis or {}).get("verified"),
                        "confidence": (verification_analysis or {}).get("confidence"),
                    }
                )
            except Exception as e:
                yield _emit({"type": "error", "message": f"Corrector failed: {e}"})
                corrected_response = None
                final_text_for_corrector = str(engineer_out or "")

            # 7) Emit zip artifact event if available
            if artifact:
                yield _emit({"type": "artifact", "kind": "zip", **artifact})

            # 8) Persist assistant message
            stored_content = (corrected_response or final_text_for_corrector or "").strip()
            if artifact:
                stored_content = (stored_content + "\n\n[Artifact] Project packaged as .zip and is ready to download.").strip()

            asst_now = _now()
            try:
                with db() as conn:
                    asst_id = _write_message(
                        conn,
                        chat_id=chat_id,
                        user_id=user_id,
                        role="assistant",
                        content=stored_content,
                        created_at=asst_now,
                        ai_layer="multi_layer",
                    )
                    conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (asst_now, chat_id))
            except Exception as e:
                yield _emit({"type": "error", "message": f"DB error writing assistant message: {e}"})
                return

            yield _emit({"type": "complete", "message_id": asst_id, "content": stored_content})

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
