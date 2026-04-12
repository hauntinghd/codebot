from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.auth import current_user
from backend.database import db
from backend.credits import get_user_credits, usage_bump
from backend.helpers.files_context import build_file_context
from backend.helpers.internet_policy import check_internet_policy, validate_response
from backend.helpers.subscriptions import is_active_subscription
from backend.helpers.tables import ensure_message_verifications_table
from backend.helpers.chat_owner import get_chat_owner
from backend.helpers.messages import get_recent_messages
from backend.services.corrector import correct_and_verify
from backend.services.corrector_badge import corrector

logger = logging.getLogger("codebot")

API_PREFIX = "/codebot/api"
MAX_CONTEXT_TOKENS = 8000
MAX_CHAT_MESSAGES_CONTEXT = 18


def _now() -> int:
    return int(time.time())


def _infer_feature(code_mode: bool, layers: List[str]) -> str:
    if code_mode:
        return "code"
    if "router" in layers and "engineer" in layers:
        return "multi_layer"
    return "chat"


def _resolve_llm_client_and_model(u: Any):
    """
    Your existing resolver should live elsewhere; keeping signature unchanged.
    Import locally to avoid circulars.
    """
    from backend.services.ai.provider_resolver import resolve_client_and_model

    return resolve_client_and_model(u)


async def _cbt_charge(
    user_id: str,
    feature: str,
    request_id: str,
    tokens_in: int,
    tokens_out: int,
    provider_cost_usd_estimate: float,
):
    from backend.services.credits_client import cbt_charge

    return await cbt_charge(
        user_id=user_id,
        feature=feature,
        request_id=request_id,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        provider_cost_usd_estimate=provider_cost_usd_estimate,
    )


def _wants_zip(user_text: str, blueprint: Optional[Dict[str, Any]] = None) -> bool:
    ut = (user_text or "").lower()
    if any(k in ut for k in ["zip", ".zip", "send as a zip", "as a zip", "zip file"]):
        return True
    bp = blueprint or {}
    # If the router indicates many files, treat as zip-worthy.
    fte = bp.get("files_to_edit") or []
    return isinstance(fte, list) and len(fte) >= 6


def _try_build_zip_from_engineer_output(
    engineer_output: Any,
    project_name: str,
) -> Optional[Dict[str, Any]]:
    """
    Adapter to your project_packager.py.
    We don't assume function names; we try common ones.
    Expected packager behaviors we support:
      - returns a path-like (str/Path) to the zip
      - or returns dict with zip_path / path
    """
    try:
        from backend.services import project_packager  # type: ignore
    except Exception:
        try:
            import backend.services.project_packager as project_packager  # type: ignore
        except Exception:
            return None

    files = None
    if isinstance(engineer_output, dict) and isinstance(engineer_output.get("files"), list):
        files = engineer_output.get("files")

    if not files:
        return None

    candidates = [
        "create_project_zip",
        "package_project",
        "package_files",
        "build_zip",
        "make_zip",
    ]

    fn = None
    for name in candidates:
        if hasattr(project_packager, name):
            fn = getattr(project_packager, name)
            break
    if fn is None:
        return None

    result = fn(files=files, project_name=project_name)  # type: ignore

    zip_path = None
    if isinstance(result, dict):
        zip_path = result.get("zip_path") or result.get("path") or result.get("file")
    else:
        zip_path = result

    if not zip_path:
        return None

    return {
        "zip_path": str(zip_path),
        "project_name": project_name,
        "file_count": len(files),
    }


def register_routes(api: APIRouter) -> None:
    @api.get(f"{API_PREFIX}/chats/{{chat_id}}/messages")
    def get_messages(chat_id: str, u: sqlite3.Row = Depends(current_user)):
        """
        NOTE: If you were seeing 404 here earlier, it means routes were not registered
        in backend/main.py. This file alone can't fix that — but this endpoint is correct.
        """
        user_id = str(u["id"])
        owner = get_chat_owner(chat_id)
        is_admin = int(u["is_admin"]) == 1
        if owner != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="Forbidden")

        with db() as conn:
            rows = conn.execute(
                "SELECT id, role, content, created_at, ai_layer FROM messages WHERE chat_id = ? ORDER BY created_at ASC",
                (chat_id,),
            ).fetchall()
        out = []
        for r in rows:
            out.append(
                {
                    "id": r["id"],
                    "role": r["role"],
                    "content": r["content"],
                    "created_at": r["created_at"],
                    "ai_layer": r["ai_layer"] if "ai_layer" in r.keys() else "",
                }
            )
        return out

    @api.get(f"{API_PREFIX}/chats/{{chat_id}}/stream")
    async def stream_chat_message(
        chat_id: str,
        content: str,
        request: Request,
        u: sqlite3.Row = Depends(current_user),
    ):
        user_id = str(u["id"])

        if int(u["is_admin"]) != 1 and not is_active_subscription(u):
            raise HTTPException(status_code=402, detail="Subscription required")

        from backend.helpers.rate_limit import check_rate_limit

        has_byok = bool(u.get("api_key_encrypted") if hasattr(u, "get") else u["api_key_encrypted"])
        is_admin = bool(int(u["is_admin"]))

        allowed, remaining = check_rate_limit(user_id, has_byok=has_byok, is_admin=is_admin)
        if not allowed:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        owner = get_chat_owner(chat_id)
        if owner != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="Forbidden")

        user_text = (content or "").strip()
        if not user_text:
            raise HTTPException(status_code=400, detail="Message content required")

        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                now = _now()
                user_msg_id = str(uuid.uuid4())
                with db() as conn:
                    conn.execute(
                        "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?, ?, 'user', ?, ?)",
                        (user_msg_id, chat_id, user_text, now),
                    )
                    conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now, chat_id))

                yield f"data: {json.dumps({'type': 'user_message', 'id': user_msg_id})}\n\n"

                file_context, file_count, code_length = build_file_context(user_id, max_tokens=MAX_CONTEXT_TOKENS)
                recent = get_recent_messages(chat_id, MAX_CHAT_MESSAGES_CONTEXT)

                # Internet policy check
                internet_access_check = check_internet_policy(user_text, file_count=file_count, code_length=code_length)
                yield f"data: {json.dumps({'type': 'internet_policy', 'allowed': internet_access_check['allowed'], 'reason': internet_access_check['reason']})}\n\n"

                # Router
                yield f"data: {json.dumps({'type': 'layer_start', 'layer': 'router', 'description': 'Planning approach...'})}\n\n"
                from backend.services.ai.router import create_blueprint

                blueprint = await create_blueprint(
                    user_request=user_text,
                    file_context=(file_context[:5000] if file_context else None),
                    chat_history=recent,
                )
                yield f"data: {json.dumps({'type': 'layer_complete', 'layer': 'router', 'data': blueprint})}\n\n"

                # Engineer
                yield f"data: {json.dumps({'type': 'layer_start', 'layer': 'engineer', 'description': 'Generating code...'})}\n\n"
                from backend.services.ai.engineer import generate_code

                client, model, is_byok = _resolve_llm_client_and_model(u)
                cost_multiplier = 0 if is_byok else 1

                user_plan = u.get("plan") if hasattr(u, "get") else (u["plan"] if "plan" in u.keys() else "none")

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

                wants_zip = _wants_zip(user_text, blueprint)

                # If engineer returned project files and user wants zip, package it
                artifact = None
                project_name = None
                preview_text = None

                if isinstance(engineer_out, dict) and isinstance(engineer_out.get("files"), list):
                    project_name = str(engineer_out.get("project_name") or "generated-project")
                    preview_text = str(engineer_out.get("_preview") or "Project generated.")
                    if wants_zip:
                        artifact = _try_build_zip_from_engineer_output(engineer_out, project_name)

                # Stream output:
                if isinstance(engineer_out, dict) and isinstance(engineer_out.get("files"), list):
                    # Do NOT chunk stream every file character; it kills SSE + UI.
                    yield f"data: {json.dumps({'type': 'code_chunk', 'data': preview_text or 'Project generated.'})}\n\n"
                else:
                    generated_code = str(engineer_out or "")
                    chunk_size = 512
                    for i in range(0, len(generated_code), chunk_size):
                        chunk = generated_code[i : i + chunk_size]
                        yield f"data: {json.dumps({'type': 'code_chunk', 'data': chunk})}\n\n"

                yield f"data: {json.dumps({'type': 'layer_complete', 'layer': 'engineer'})}\n\n"

                # Auditor
                yield f"data: {json.dumps({'type': 'layer_start', 'layer': 'auditor', 'description': 'Reviewing code...'})}\n\n"
                from backend.services.ai.auditor import audit_code

                audit_result = await audit_code(
                    generated_code=engineer_out,
                    blueprint=blueprint,
                    user_request=user_text,
                    api_client=client,
                    model=model,
                )
                yield f"data: {json.dumps({'type': 'layer_complete', 'layer': 'auditor', 'data': audit_result})}\n\n"

                # Corrector layer works on preview text (not full project dump)
                yield f"data: {json.dumps({'type': 'layer_start', 'layer': 'corrector', 'description': 'Verifying accuracy...'})}\n\n"

                final_text_for_corrector = ""
                if isinstance(engineer_out, dict) and isinstance(engineer_out.get("files"), list):
                    final_text_for_corrector = preview_text or "Project generated."
                else:
                    final_text_for_corrector = audit_result.get("verified_code") or str(engineer_out or "")

                corrected_response, verification_analysis = await correct_and_verify(
                    response=final_text_for_corrector,
                    context={"user_request": user_text, "blueprint": blueprint},
                    files_accessed=[],
                    inject_citations=internet_access_check["allowed"],
                )

                yield f"data: {json.dumps({'type': 'layer_complete', 'layer': 'corrector', 'verified': verification_analysis.get('verified'), 'confidence': verification_analysis.get('confidence')})}\n\n"

                # If we produced an artifact zip, emit it as an SSE event
                if artifact:
                    yield f"data: {json.dumps({'type': 'artifact', 'kind': 'zip', **artifact})}\n\n"

                # Store assistant message (small + stable, not a giant dump)
                asst_id = str(uuid.uuid4())
                stored_content = corrected_response or final_text_for_corrector

                # If zip was produced, add a clear pointer in the stored chat
                if artifact:
                    stored_content = (
                        (stored_content or "").strip()
                        + "\n\n[Artifact] Project packaged as .zip and is ready to download."
                    ).strip()

                with db() as conn:
                    conn.execute(
                        "INSERT INTO messages (id, chat_id, role, content, created_at, ai_layer) VALUES (?, ?, 'assistant', ?, ?, 'multi_layer')",
                        (asst_id, chat_id, stored_content, _now()),
                    )
                    conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (_now(), chat_id))

                    # Save verification metadata
                    try:
                        ensure_message_verifications_table()
                        conn.execute(
                            """INSERT INTO message_verifications
                               (message_id, confidence_score, has_hallucination, issues_detected, sources_used, verified_at,
                                internet_allowed, internet_reason, internet_violation)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                asst_id,
                                verification_analysis.get("confidence", 0.0),
                                verification_analysis.get("has_hallucination", False),
                                json.dumps(verification_analysis.get("issues", [])),
                                json.dumps(verification_analysis.get("sources", [])),
                                _now(),
                                internet_access_check["allowed"],
                                internet_access_check["reason"],
                                None,
                            ),
                        )
                    except Exception as insert_err:
                        logger.warning(f"message_verifications insert skipped: {insert_err}")

                yield f"data: {json.dumps({'type': 'complete', 'message_id': asst_id, 'content': stored_content})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
