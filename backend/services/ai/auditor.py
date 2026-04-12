from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from fastapi import HTTPException

from backend.config import MODEL_PRICING

logger = logging.getLogger("codebot")


def _safe_json_extract(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}
    blob = m.group(0).strip()
    try:
        return json.loads(blob)
    except Exception:
        blob2 = re.sub(r",\s*([}\]])", r"\1", blob)
        try:
            return json.loads(blob2)
        except Exception:
            return {}


def _summarize_files_for_audit(files: list[dict[str, Any]], max_chars: int = 12000) -> str:
    """
    Auditor should NOT re-ingest huge project code. Give it paths + short snippets only.
    """
    out = []
    used = 0
    for f in files[:60]:
        path = str(f.get("path") or "")
        content = str(f.get("content") or "")
        snippet = content[:800]
        chunk = f"\n- {path}\n  snippet:\n{snippet}\n"
        if used + len(chunk) > max_chars:
            break
        out.append(chunk)
        used += len(chunk)
    return "".join(out).strip()


async def audit_code(
    generated_code: Any,
    blueprint: Dict[str, Any],
    user_request: str,
    api_client: Any,
    model: str,
) -> Dict[str, Any]:
    """
    Size-aware auditor:
    - For small single-string outputs, can return verified_code.
    - For large/multi-file outputs, returns issues/fixes WITHOUT embedding full code in JSON.
      This prevents truncation and JSON parse failure.

    Output schema (always JSON):
    {
      "status": "OK" | "FIX",
      "issues": [{"severity":"error|warning","description":"...","file":"...","line":123}],
      "fixes": {"path":"patch notes or instructions"},
      "verified_code": "..." | null,
      "notes": "..."
    }
    """

    # Detect project mode
    is_project = isinstance(generated_code, dict) and isinstance(generated_code.get("files"), list)
    gen_text = ""
    files_summary = ""

    if is_project:
        files = generated_code.get("files") or []
        files_summary = _summarize_files_for_audit(files, max_chars=14000)
        # Do NOT pass full project contents
        gen_text = f"PROJECT FILES SUMMARY:\n{files_summary}"
    else:
        gen_text = str(generated_code or "")
        # IMPORTANT: do not hard-truncate to 8000; that breaks audits on medium outputs too.
        # Instead, cap at a higher ceiling, but still safe.
        if len(gen_text) > 30000:
            gen_text = gen_text[:30000] + "\n...[truncated for audit]..."

    sys_prompt = (
        "You are CodeBot Auditor.\n"
        "You must return a single JSON object only (no markdown).\n"
        "Your job: identify correctness issues, missing parts, security problems, and runtime blockers.\n"
        "If the output is a multi-file project, DO NOT return the full code in verified_code.\n"
        "Instead, return issues and concrete fixes by file path.\n"
    )

    user_payload = {
        "user_request": user_request,
        "blueprint": blueprint or {},
        "generated": gen_text,
        "rules": [
            "Return JSON only",
            "If project/multi-file: verified_code MUST be null",
            "Prefer actionable fixes, include file paths",
        ],
    }

    try:
        resp = api_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=0.1,
            max_tokens=1600,  # keep auditor bounded; do not let it attempt huge JSON
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "").strip()
        obj = _safe_json_extract(raw) or {}

        status = str(obj.get("status") or "OK").upper()
        if status not in ("OK", "FIX"):
            status = "OK"

        # Normalize for safety
        issues = obj.get("issues")
        if not isinstance(issues, list):
            issues = []
        fixes = obj.get("fixes")
        if not isinstance(fixes, dict):
            fixes = {}

        # Enforce the key rule: never embed huge code in JSON for projects
        if is_project:
            obj["verified_code"] = None

        obj["status"] = status
        obj["issues"] = issues
        obj["fixes"] = fixes
        if "notes" not in obj:
            obj["notes"] = "Audit complete."

        return obj

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Audit failed: {e}")
        raise HTTPException(status_code=502, detail=f"Audit failed: {e}")
