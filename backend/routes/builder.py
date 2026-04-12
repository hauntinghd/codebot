"""
Builder endpoint: POST /api/builder/run

Handles Build, Ask, and Plan modes from the Builder sidebar.
Streams SSE events through the 5-layer pipeline (router → engineer → auditor → corrector → assembler).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import pathlib
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from backend.auth import get_session_user_id, get_user_by_id
from backend.services.ai.provider_resolver import (
    make_llm_client,
    resolve_provider_and_key,
    get_user_byok_from_row,
    FAL_MODELS,
    LAYER_MODEL_DEFAULTS,
    get_fal_model_id,
    get_layer_model,
    is_fal_available,
)
from backend.services.ai.engineer import _sanitize_ascii_lookalikes, _safe_json_extract

logger = logging.getLogger("codebot")
router = APIRouter()

API_PREFIX = "/api"

FREE_MODELS = {"gemini-2.5-flash-lite", "llama-4-scout", "mistral-small-3.2", "grok-3-mini", "grok-3"}


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _resolve_model(requested: str, layer: str = "engineer") -> str:
    """Map frontend model ids to actual API model ids.
    If fal.ai is available, resolves to fal model IDs.
    Falls back to layer defaults if no specific model requested.
    """
    requested = (requested or "").strip()
    if not requested:
        requested = get_layer_model(layer)

    if is_fal_available():
        return get_fal_model_id(requested)

    # Fallback to xAI if no fal
    return _env("XAI_MODEL", "grok-4-1-fast-reasoning")


def _make_client(model: str = "", layer: str = "engineer", user_row=None):
    """Create an OpenAI-compatible client. Prefers fal.ai for all frontier models."""
    provider, api_key = resolve_provider_and_key(None, None)
    return make_llm_client(provider, api_key)


def _sse(event_type: str, data: Any) -> str:
    payload = {"type": event_type}
    if isinstance(data, dict):
        payload.update(data)
    elif isinstance(data, str):
        payload["message"] = data
    else:
        payload["data"] = data
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _extract_files_array_from_json_string(raw: str) -> Optional[List[Dict[str, Any]]]:
    """
    When full json.loads() fails (e.g. huge or truncated payload), try to extract
    just the "files" array so we can still send a files event and avoid streaming
    raw JSON into the chat.
    """
    raw = (raw or "").strip()
    if not raw or "files" not in raw:
        return None
    # Find "files" key and the following '[' (allow for "files": [ or "files" : [)
    import re as _re
    match = _re.search(r'"files"\s*:\s*\[', raw, _re.IGNORECASE)
    if not match:
        match = _re.search(r"'files'\s*:\s*\[", raw)
    if not match:
        return None
    start = match.end() - 1  # index of '['
    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "[":
            depth += 1
        elif raw[i] == "]":
            depth -= 1
            if depth == 0:
                try:
                    arr = json.loads(raw[start : i + 1])
                    if isinstance(arr, list):
                        out = []
                        for f in arr[:200]:
                            if isinstance(f, dict):
                                path = str(f.get("path") or "").strip().lstrip("/").replace("\\", "/")
                                if path:
                                    out.append({"path": path, "content": _sanitize_ascii_lookalikes(str(f.get("content") or ""))})
                        return out if out else None
                except Exception:
                    pass
                return None
    return None


def _has_prior_clarification(messages: List[Dict[str, str]]) -> bool:
    """Check if the conversation already has assistant clarification responses."""
    return any(m.get("role") == "assistant" for m in messages)


async def _pipeline_build(
    prompt: str,
    messages: List[Dict[str, str]],
    model: str,
    project_id: str,
    project_name: str,
) -> AsyncGenerator[str, None]:
    """Full 5-layer build pipeline with SSE streaming.

    First message: ask clarifying questions if needed.
    After clarification: proceed with full code generation.
    """
    try:
        client = _make_client(layer="engineer")
        actual_model = _resolve_model(model, "engineer")
        chat_history = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages[-12:]]

        # Resolve per-layer models (fal.ai routes each layer to optimal model)
        router_model_id = _resolve_model(model, "router")
        engineer_model_id = _resolve_model(model, "engineer")
        auditor_model_id = _resolve_model(model, "auditor")

        yield _sse("status", {"message": "Building your project…", "models": {
            "router": router_model_id,
            "engineer": engineer_model_id,
            "auditor": auditor_model_id,
        }})

        # Gather conversation context for the engineer
        full_context = prompt
        for m in chat_history:
            if m.get("role") == "assistant" and m.get("content"):
                full_context += f"\n\nPrevious assistant context:\n{m['content'][:2000]}"
            elif m.get("role") == "user" and m.get("content") and m["content"] != prompt:
                full_context += f"\n\nUser also said:\n{m['content'][:1000]}"

        # Layer 1: Router (uses fast reasoning model)
        yield _sse("layer_start", {"layer": "router", "description": f"Planning approach… ({router_model_id})"})
        try:
            from backend.services.ai.router import create_blueprint
            blueprint = await create_blueprint(
                user_request=full_context,
                chat_history=chat_history,
            )
        except Exception as e:
            logger.warning(f"Router layer failed, using fallback: {e}")
            blueprint = {
                "files_to_edit": ["index.html", "styles.css", "app.js"],
                "approach": "Generate a complete static website",
                "complexity": "high",
            }
        # Ensure complexity is high enough so engineer generates all files (HTML + CSS + JS + any pages)
        if isinstance(blueprint, dict):
            complexity = str(blueprint.get("complexity", "")).lower()
            if complexity not in ("high", "very_high", "complex"):
                blueprint["complexity"] = "high"
            # Ensure files_to_edit includes full set for websites so engineer generates every needed file
            files_to_edit = list(blueprint.get("files_to_edit") or [])
            if not isinstance(blueprint.get("files_to_edit"), list):
                files_to_edit = []
            required = ["index.html", "styles.css", "app.js"]
            for r in required:
                if not any(r in str(f).lower() for f in files_to_edit):
                    files_to_edit.append(r)
            # For multi-page/website builds, always include standard pages so nav/buttons can work
            complexity = str(blueprint.get("complexity") or "").lower()
            has_html = any(".html" in str(f).lower() for f in files_to_edit)
            if complexity in ("complex", "high", "very_high") or has_html or "website" in (full_context or "").lower() or "store" in (full_context or "").lower():
                for page in ["products.html", "contact.html", "featured.html", "content.html", "terms.html"]:
                    if not any(page in str(f).lower() for f in files_to_edit):
                        files_to_edit.append(page)
            # Full-stack: Stripe, backend, database, auth → ensure backend files so engineer produces sellworthy output
            prompt_lower = (full_context or "").lower()
            fullstack_keywords = ("stripe", "backend", "database", "checkout", "user account", "auth", "password", "webhook", "payment")
            if any(k in prompt_lower for k in fullstack_keywords):
                for bf in ["server.js", "package.json", ".env.example", "README.md"]:
                    if not any(bf in str(f).lower() for f in files_to_edit):
                        files_to_edit.append(bf)
            blueprint["files_to_edit"] = files_to_edit
        yield _sse("layer_complete", {"layer": "router"})

        # Layer 2: Engineer (uses best coding model — Claude Opus via fal.ai)
        yield _sse("layer_start", {"layer": "engineer", "description": f"Generating code… ({engineer_model_id})"})
        yield _sse("code_chunk", {"data": "Generating your project files...\n\n"})

        try:
            from backend.services.ai.engineer import generate_code
            engineer_out = await generate_code(
                user_request=full_context,
                blueprint=blueprint,
                file_context=None,
                chat_history=chat_history,
                api_client=client,
                model=actual_model,
                user_plan="pro",
                user_id=None,
            )
        except Exception as e:
            logger.warning(f"Engineer with generate_code failed: {e}, using direct LLM")
            from datetime import datetime
            _year = datetime.now().year
            engineer_sys = (
                "You are CodeBot Engineer. Output a single JSON object (NO markdown) with this shape:\n"
                '{"project_name":"string","files":[{"path":"relative/path","content":"full file contents"}],"commands":[],"notes":"optional"}\n'
                "CRITICAL: You MUST output ALL files needed: index.html, styles.css, app.js, and any other pages (e.g. about.html, contact.html). NEVER output only 1 or 2 files — a working site needs HTML + CSS + JS at minimum.\n"
                "Build a COMPLETE static website using ONLY HTML, CSS, and vanilla JavaScript.\n"
                "Do NOT use React, Vue, Next.js, Vite, TypeScript, or any framework.\n"
                "Do NOT include package.json or any config files.\n"
                "The index.html must be a full HTML document with <!DOCTYPE html>, <head>, <body>.\n"
                "Every site is a COMMERCIAL product meant to convert paying customers. Use professional design.\n"
                "EVERY image (hero, products, gallery, about) MUST use Unsplash: https://source.unsplash.com/featured/?KEYWORD/WIDTHxHEIGHT with keywords matching the actual product.\n"
                "Product arrays in JS must also use Unsplash URLs for each product's image field.\n"
                "NEVER use picsum.photos or placehold.co. Use a cohesive color palette matching the brand.\n"
                "Use Google Fonts. Make it look agency-quality.\n"
                f"The current year is {_year}. Use {_year} for copyright.\n"
                "Output ONLY valid JSON, no markdown."
            )
            resp = client.chat.completions.create(
                model=actual_model,
                messages=[
                    {"role": "system", "content": engineer_sys},
                    {"role": "user", "content": f"Build this:\n{full_context}\n\nBlueprint:\n{json.dumps(blueprint, ensure_ascii=False)[:6000]}"},
                ],
                temperature=0.2,
                max_tokens=131072,
                response_format={"type": "json_object"},
            )
            raw = (resp.choices[0].message.content or "").strip()
            # Use robust parser so malformed JSON (e.g. unescaped quotes in content) never raises
            engineer_out = _safe_json_extract(raw) if raw else {}
            if not isinstance(engineer_out, dict) or not engineer_out:
                engineer_out = raw

        is_project = isinstance(engineer_out, dict) and isinstance(engineer_out.get("files"), list)

        # If the engineer returned raw JSON text, try to parse it into a project
        if not is_project and isinstance(engineer_out, str):
            raw_text = engineer_out.strip()
            parsed = _safe_json_extract(raw_text)
            if isinstance(parsed, dict) and isinstance(parsed.get("files"), list):
                engineer_out = parsed
                is_project = True

        if is_project:
            file_list = engineer_out.get("files", [])

            # Generate real images via Grok Image API to replace placeholders
            try:
                from backend.services.ai.grok_images import enhance_files_with_images
                yield _sse("code_chunk", {"data": "Generating product images…\n\n"})
                file_list = await enhance_files_with_images(file_list, max_images=6, user_prompt=prompt)
                engineer_out["files"] = file_list
            except Exception as img_err:
                logger.warning(f"Image generation step failed (non-critical): {img_err}")

            file_names = [f.get("path", "?") for f in file_list if isinstance(f, dict)]
            preview_msg = f"Generated {len(file_names)} files:\n" + "\n".join(f"  - {n}" for n in file_names[:20])
            yield _sse("code_chunk", {"data": preview_msg})
            # Files are sent AFTER the button-wiring auditor pass below
        else:
            generated_code = str(engineer_out or "")
            # Never stream raw project JSON into the chat; extract files even when full parse fails
            if generated_code.strip().startswith("{") and ("\"files\"" in generated_code or "'files'" in generated_code):
                file_list = None
                parsed = _safe_json_extract(generated_code)
                if isinstance(parsed, dict) and isinstance(parsed.get("files"), list):
                    file_list = [{"path": str(f.get("path", "")).strip().lstrip("/").replace("\\", "/"), "content": _sanitize_ascii_lookalikes(str(f.get("content") or ""))} for f in parsed.get("files", [])[:200] if isinstance(f, dict) and f.get("path")]
                    if file_list:
                        engineer_out = parsed
                if not file_list:
                    file_list = _extract_files_array_from_json_string(generated_code)
                if file_list:
                    try:
                        from backend.services.ai.grok_images import enhance_files_with_images
                        yield _sse("code_chunk", {"data": "Generating product images…\n\n"})
                        file_list = await enhance_files_with_images(file_list, max_images=6, user_prompt=prompt)
                    except Exception as img_err:
                        logger.warning(f"Image generation (fallback path) failed: {img_err}")

                    file_names = [f.get("path", "?") for f in file_list if isinstance(f, dict)]
                    preview_msg = f"Generated {len(file_names)} files:\n" + "\n".join(f"  - {n}" for n in file_names[:20])
                    yield _sse("code_chunk", {"data": preview_msg})
                    for f in file_list[:200]:
                        yield _sse("file", {"path": f.get("path", ""), "content": f.get("content", "")})
                    is_project = True
                    engineer_out = {"files": file_list}
            if not is_project:
                chunk_size = 512
                for i in range(0, len(generated_code), chunk_size):
                    chunk = generated_code[i: i + chunk_size]
                    yield _sse("code_chunk", {"data": chunk})

        yield _sse("layer_complete", {"layer": "engineer"})

        # Layer 3: Auditor (real AI-powered code review)
        yield _sse("layer_start", {"layer": "auditor", "description": f"Reviewing code quality… ({auditor_model_id})"})
        audit_result = {"status": "OK", "issues": [], "fixes": {}}
        if is_project:
            try:
                from backend.services.ai.auditor import audit_code
                audit_client = _make_client(layer="auditor")
                audit_result = await audit_code(
                    generated_code=engineer_out,
                    blueprint=blueprint,
                    user_request=full_context,
                    api_client=audit_client,
                    model=auditor_model_id,
                )
                if audit_result.get("status") == "FIX" and audit_result.get("issues"):
                    issues_summary = "; ".join(
                        i.get("description", "")[:80] for i in audit_result["issues"][:5]
                    )
                    yield _sse("code_chunk", {"data": f"\nAudit found issues: {issues_summary}\n"})
            except Exception as audit_err:
                logger.warning(f"Auditor failed (non-blocking): {audit_err}")
                audit_result = {"status": "OK", "issues": [], "notes": f"Audit skipped: {audit_err}"}
        yield _sse("layer_complete", {"layer": "auditor", "result": audit_result.get("status", "OK")})

        # Send final files to frontend (after audit)
        if is_project:
            final_files = engineer_out.get("files", [])
            for f in final_files[:200]:
                yield _sse("file", {"path": f.get("path", ""), "content": f.get("content", "")})

        # Layer 4: Corrector (hallucination detection + verification badge)
        yield _sse("layer_start", {"layer": "corrector", "description": "Verifying accuracy…"})
        corrector_result = {"verified": True, "confidence": 1.0, "has_hallucination": False}
        try:
            from backend.services.ai.corrector import correct_and_verify
            code_text = json.dumps([f.get("path") for f in engineer_out.get("files", [])]) if is_project else str(engineer_out)
            _, corrector_result = await correct_and_verify(
                response=code_text,
                context={"blueprint": blueprint, "prompt": full_context, "audit": audit_result},
                files_accessed=[f.get("path", "") for f in engineer_out.get("files", [])] if is_project else [],
            )
        except Exception as corr_err:
            logger.warning(f"Corrector failed (non-blocking): {corr_err}")
        yield _sse("layer_complete", {
            "layer": "corrector",
            "verified": corrector_result.get("verified", False),
            "confidence": corrector_result.get("confidence", 0),
        })

        # Layer 5: Assembler (final output)
        yield _sse("layer_start", {"layer": "assembler", "description": "Assembling final output…"})
        final_output = "Build complete." if is_project else str(engineer_out or "")
        # Never send raw project JSON or long output to the chat; keep it short for build mode
        if is_project or (isinstance(final_output, str) and len(final_output) > 400):
            final_output = (
                "Your project is ready. Check the **Preview** and **Code** tabs on the right."
            )
        yield _sse("layer_complete", {"layer": "assembler"})

        yield _sse("complete", {
            "content": final_output,
            "project_id": project_id,
        })

    except Exception as e:
        logger.exception(f"Build pipeline error: {e}")
        msg = str(e)
        # Don't expose raw JSON parse errors to the user
        if "Expecting" in msg and "delimiter" in msg:
            msg = "Generated output was malformed; we recovered what we could. Try again or simplify the prompt."
        elif "JSON" in msg and ("decode" in msg or "parse" in msg.lower()):
            msg = "Output parsing failed. Try running the build again."
        yield _sse("error", {"message": msg})


async def _pipeline_plan(
    prompt: str,
    messages: List[Dict[str, str]],
    model: str,
) -> AsyncGenerator[str, None]:
    """Plan mode: conversational planning using the AI model."""
    try:
        client = _make_client(layer="planning")
        actual_model = _resolve_model(model, "planning")

        yield _sse("status", "Creating plan…")

        chat_history = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages[-12:]]

        plan_messages = [
            {"role": "system", "content": (
                "You are CodeBot Planner, an expert software architect from NYPTID Industries.\n\n"
                "When the user describes what they want to build, respond with a detailed implementation plan.\n"
                "Format your response EXACTLY like this (use markdown headers and bullet points):\n\n"
                "## Summary\n"
                "One paragraph summarizing what you'll build and the high-level approach.\n\n"
                "## Clarifications\n"
                "- Any assumptions you're making\n"
                "- Questions you'd normally ask (with your assumed answers)\n\n"
                "## Approach\n"
                "Describe the technical stack, architecture, and patterns you'll use.\n\n"
                "**Complexity**: simple | medium | complex\n\n"
                "## Files\n"
                "List every file that will be created:\n"
                "- `src/index.html` — Main entry point\n"
                "- `src/styles.css` — Styles\n"
                "(etc.)\n\n"
                "## Libraries & Dependencies\n"
                "- List any npm packages, CDN scripts, or frameworks needed\n\n"
                "## Steps\n"
                "1. Step one with detail\n"
                "2. Step two with detail\n"
                "(etc.)\n\n"
                "## Risks & Notes\n"
                "- Potential issues to watch for\n\n"
                "Be specific and actionable. This plan will guide actual code generation.\n"
                "IMPORTANT: Use proper markdown formatting with ## headers, **bold**, `code`, and bullet points."
            )},
        ]
        has_user_msg = False
        for m in chat_history:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                plan_messages.append({"role": m["role"], "content": m["content"][:3000]})
                if m.get("role") == "user":
                    has_user_msg = True

        if not has_user_msg:
            plan_messages.append({"role": "user", "content": prompt})

        resp = client.chat.completions.create(
            model=actual_model,
            messages=plan_messages,
            temperature=0.3,
            max_tokens=2048,
            stream=True,
        )

        accumulated = ""
        for chunk in resp:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                accumulated += delta.content
                yield _sse("code_chunk", {"data": delta.content})

        yield _sse("complete", {"content": accumulated})

    except Exception as e:
        logger.exception(f"Plan pipeline error: {e}")
        yield _sse("error", {"message": str(e)})


async def _pipeline_ask(
    prompt: str,
    messages: List[Dict[str, str]],
    model: str,
) -> AsyncGenerator[str, None]:
    """Ask mode: conversational coding assistant."""
    try:
        yield _sse("status", "Thinking…")

        client = _make_client(layer="ask")
        actual_model = _resolve_model(model, "ask")

        sys_prompt = (
            "You are CodeBot, an expert AI coding assistant built by NYPTID Industries.\n"
            "You help developers build, debug, and understand code.\n"
            "Rules:\n"
            "- Be conversational and helpful, like a senior developer pair programming.\n"
            "- If the user's question is vague, ask a clarifying question.\n"
            "- When showing code, use clear formatting with language labels.\n"
            "- Be concise but thorough. Don't pad responses with unnecessary filler.\n"
            "- If the user wants to build something, suggest switching to Build mode."
        )

        api_messages: List[Dict[str, str]] = [{"role": "system", "content": sys_prompt}]
        for m in messages[-15:]:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role in ("user", "assistant") and content:
                api_messages.append({"role": role, "content": content[:3000]})

        resp = client.chat.completions.create(
            model=actual_model,
            messages=api_messages,
            temperature=0.4,
            max_tokens=4096,
            stream=True,
        )

        accumulated = ""
        for chunk in resp:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                accumulated += delta.content
                yield _sse("code_chunk", {"data": delta.content})

        yield _sse("complete", {"content": accumulated})

    except Exception as e:
        logger.exception(f"Ask pipeline error: {e}")
        yield _sse("error", {"message": str(e)})


@router.get(f"{API_PREFIX}/models")
async def list_models(request: Request):
    """Return all available AI models grouped by category with real fal.ai pricing."""
    from backend.config import PLAN_MODEL_ACCESS, PLAN_CREDITS, CBT_MARKUP, CBT_TOPUP_PACKS
    from backend.services.ai.provider_resolver import get_model_cost_per_1k

    # Get user plan for access control
    uid = get_session_user_id(request)
    user_plan = "none"
    if uid:
        user = get_user_by_id(uid)
        if user:
            user_plan = str(user.get("plan") or "none")

    plan_access = PLAN_MODEL_ACCESS.get(user_plan, {})
    allowed_tiers = plan_access.get("allowed_tiers", [])

    models = []
    for name, info in FAL_MODELS.items():
        cost_per_1k = info.get("cost_per_1k", 0.005)
        # CBT cost = fal cost * markup * 1000 (convert to CBT units)
        cbt_per_1k = round(cost_per_1k * CBT_MARKUP * 1000, 2)
        tier = info["tier"]
        locked = tier not in allowed_tiers if allowed_tiers else True

        models.append({
            "id": name,
            "fal_id": info["fal_id"],
            "label": info.get("label", name),
            "description": info.get("description", ""),
            "category": info["category"],
            "tier": tier,
            "cost_per_1k_usd": round(cost_per_1k, 5),
            "cbt_per_1k_tokens": cbt_per_1k,
            "locked": locked,
            "locked_reason": f"Requires {', '.join(t for t in ['pro','enterprise'] if t != user_plan)} plan" if locked else None,
        })

    return {
        "models": models,
        "layer_defaults": LAYER_MODEL_DEFAULTS,
        "fal_available": is_fal_available(),
        "user_plan": user_plan,
        "plans": {
            "builder":    {"price": 30,  "cbt": 25000,  "models": "Fast models + 5 frontier/day"},
            "pro":        {"price": 99,  "cbt": 100000, "models": "All models including frontier"},
            "enterprise": {"price": 299, "cbt": 350000, "models": "Unlimited frontier, priority"},
        },
        "topups": CBT_TOPUP_PACKS,
        "categories": {
            "coding":    {"label": "Coding",    "description": "Best for code generation", "icon": "code"},
            "reasoning": {"label": "Reasoning", "description": "Extended chain-of-thought", "icon": "brain"},
            "thinking":  {"label": "Thinking",  "description": "Deep reasoning with visible steps", "icon": "lightbulb"},
            "planning":  {"label": "Planning",  "description": "Architecture & system design", "icon": "layout"},
            "vision":    {"label": "Vision",    "description": "Image & screenshot understanding", "icon": "eye"},
            "fast":      {"label": "Fast",      "description": "Quick responses, low cost", "icon": "zap"},
        },
    }


@router.post(f"{API_PREFIX}/builder/run")
async def builder_run(request: Request):
    uid = get_session_user_id(request)
    if not uid:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    user = get_user_by_id(uid)
    if not user:
        return JSONResponse({"detail": "User not found"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return JSONResponse({"detail": "Prompt is required"}, status_code=400)

    mode = (body.get("mode") or "build").strip().lower()
    model = (body.get("model") or "").strip()
    project_id = body.get("projectId") or str(uuid.uuid4())
    project_name = body.get("projectName") or "Untitled Project"
    messages = body.get("messages") or []

    if not model:
        model = get_layer_model("engineer")

    is_admin = False
    try:
        is_admin = bool(user["is_admin"])
    except (KeyError, TypeError):
        pass

    # --- Enforce subscription + CBT balance ---
    user_plan = str(user.get("plan") or "none")
    if user_plan == "none" and not is_admin:
        return JSONResponse(
            {"detail": "Subscription required. Choose a plan to start building.", "code": "NO_PLAN"},
            status_code=402,
        )

    # Check model tier access
    from backend.config import PLAN_MODEL_ACCESS
    plan_access = PLAN_MODEL_ACCESS.get(user_plan, {})
    allowed_tiers = plan_access.get("allowed_tiers", [])
    model_info = FAL_MODELS.get(model, {})
    model_tier = model_info.get("tier", "premium")
    if model_tier not in allowed_tiers and not is_admin:
        return JSONResponse(
            {"detail": f"Your {user_plan} plan doesn't include {model_tier} models. Upgrade to Pro or Enterprise.",
             "code": "MODEL_LOCKED", "model": model, "tier": model_tier},
            status_code=403,
        )

    # Check CBT balance
    if not is_admin:
        from backend.tokens import get_user_tokens
        cbt_balance = get_user_tokens(uid)
        if cbt_balance <= 0:
            return JSONResponse(
                {"detail": "Out of CBT tokens. Purchase a top-up or upgrade your plan.",
                 "code": "NO_CBT", "balance": 0},
                status_code=402,
            )

    logger.info(f"[builder/run] mode={mode} model={model} user={uid} project={project_id}")

    if mode == "plan":
        gen = _pipeline_plan(prompt, messages, model)
    elif mode == "ask":
        gen = _pipeline_ask(prompt, messages, model)
    else:
        gen = _pipeline_build(prompt, messages, model, project_id, project_name)

    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# NPM install (add package to project files)
# ---------------------------------------------------------------------------

@router.post(f"{API_PREFIX}/builder/npm-install")
async def builder_npm_install(request: Request):
    """Run npm install <package> in a temp dir with project files; return updated package.json and package-lock.json."""
    import subprocess
    import tempfile

    uid = get_session_user_id(request)
    if not uid:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)

    files = body.get("files")
    package = (body.get("package") or body.get("packageName") or "").strip()
    if not isinstance(files, list) or not package or len(package) > 120:
        return JSONResponse({"detail": "files (array) and package (string) required"}, status_code=400)
    if not any(f.get("path", "").endswith("package.json") for f in files if isinstance(f, dict)):
        return JSONResponse({"detail": "Project must contain package.json"}, status_code=400)

    pkg_name = package.split("@")[0].strip()
    if not pkg_name or not pkg_name.replace("-", "").replace("_", "").isalnum():
        return JSONResponse({"detail": "Invalid package name"}, status_code=400)

    try:
        with tempfile.TemporaryDirectory(prefix="codebot_npm_") as tmp:
            root = pathlib.Path(tmp)
            for item in files[:200]:
                if not isinstance(item, dict):
                    continue
                path = (item.get("path") or "").strip().lstrip("/").replace("\\", "/")
                if not path or ".." in path:
                    continue
                fp = root / path
                fp.parent.mkdir(parents=True, exist_ok=True)
                content = item.get("content")
                if content is not None:
                    fp.write_text(str(content), encoding="utf-8", errors="replace")

            proc = subprocess.run(
                ["npm", "install", package, "--save", "--no-audit", "--no-fund", "--legacy-peer-deps"],
                cwd=str(root),
                capture_output=True,
                timeout=120,
                text=True,
            )
            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "")[:500]
                return JSONResponse({"detail": "npm install failed", "npm_error": err}, status_code=400)

            out_files: List[Dict[str, str]] = []
            for name in ("package.json", "package-lock.json"):
                p = root / name
                if p.exists():
                    try:
                        out_files.append({"path": name, "content": p.read_text(encoding="utf-8", errors="replace")})
                    except Exception:
                        pass

            return JSONResponse({"ok": True, "files": out_files})
    except subprocess.TimeoutExpired:
        return JSONResponse({"detail": "npm install timed out"}, status_code=504)
    except Exception as e:
        logger.exception("builder/npm-install: %s", e)
        return JSONResponse({"detail": str(e)[:200]}, status_code=500)


# ---------------------------------------------------------------------------
# Deployment endpoint
# ---------------------------------------------------------------------------

async def _deploy_to_netlify(
    files: List[Dict[str, str]],
    site_name: str,
    custom_domain: str = "",
) -> Dict[str, str]:
    """Deploy files to Netlify and return {url, siteId}."""
    import httpx

    token = _env("NETLIFY_AUTH_TOKEN")
    if not token:
        raise ValueError("NETLIFY_AUTH_TOKEN not configured")

    file_hashes: Dict[str, str] = {}
    file_contents: Dict[str, str] = {}

    for f in files:
        normalized = "/" + f["path"].lstrip("/")
        h = hashlib.sha1(f["content"].encode("utf-8")).hexdigest()
        file_hashes[normalized] = h
        file_contents[h] = f["content"]

    if "/index.html" not in file_hashes:
        for f in files:
            if f["path"].endswith((".html", ".htm")):
                h = hashlib.sha1(f["content"].encode("utf-8")).hexdigest()
                file_hashes["/index.html"] = h
                file_contents[h] = f["content"]
                break

    safe = site_name.lower()
    safe = "".join(c if c.isalnum() or c == "-" else "-" for c in safe)
    safe = safe.strip("-")[:40] or "codebot-project"
    slug = f"{safe}-{uuid.uuid4().hex[:8]}"

    payload: Dict[str, Any] = {"name": slug}
    if custom_domain:
        payload["custom_domain"] = custom_domain.lstrip("htps:/").rstrip("/")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://api.netlify.com/api/v1/sites", headers=headers, json=payload)
        if r.status_code >= 400:
            raise ValueError(f"Netlify site creation failed ({r.status_code}): {r.text[:300]}")
        site = r.json()
        site_id = site["id"]

        r2 = await client.post(
            f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
            headers=headers,
            json={"files": file_hashes},
        )
        if r2.status_code >= 400:
            raise ValueError(f"Netlify deploy creation failed ({r2.status_code}): {r2.text[:300]}")
        deploy = r2.json()
        deploy_id = deploy["id"]
        required = deploy.get("required", [])

        for h in required:
            content = file_contents.get(h)
            if not content:
                continue
            fpath = next((k for k, v in file_hashes.items() if v == h), "/unknown")
            await client.put(
                f"https://api.netlify.com/api/v1/deploys/{deploy_id}/files{fpath}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
                content=content.encode("utf-8"),
            )

        # Wait for deploy to become ready (up to 30s)
        import asyncio as _aio
        for _ in range(15):
            await _aio.sleep(2)
            check = await client.get(
                f"https://api.netlify.com/api/v1/deploys/{deploy_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if check.status_code == 200:
                state = check.json().get("state", "")
                if state == "ready":
                    deploy = check.json()
                    break
                if state == "error":
                    raise ValueError(f"Netlify deploy failed: {check.json().get('error_message', 'unknown')}")

    url = (
        f"https://{custom_domain.lstrip('htps:/').rstrip('/')}"
        if custom_domain
        else deploy.get("ssl_url") or deploy.get("url") or site.get("ssl_url") or f"https://{slug}.netlify.app"
    )
    return {"url": url, "siteId": site_id}


def _deploy_to_server(
    files: List[Dict[str, str]],
    project_name: str,
) -> Dict[str, str]:
    """Write files to ~/codebot-sites/{slug} and return {url, deployPath}."""
    safe = project_name.lower()
    safe = "".join(c if c.isalnum() or c == "-" else "-" for c in safe)
    safe = safe.strip("-")[:40] or "codebot-project"
    slug = f"{safe}-{uuid.uuid4().hex[:8]}"

    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or os.path.expanduser("~")
    deploy_dir = os.path.join(home, "codebot-sites", slug)
    os.makedirs(deploy_dir, exist_ok=True)

    for f in files:
        fp = os.path.join(deploy_dir, f["path"].lstrip("/"))
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as fh:
            fh.write(f["content"])

    host = _env("VM_DEPLOY_HOST", "chatbot.nyptidindustries.com")
    url = f"https://{host}/codebot/api/sites/{slug}/"
    return {"url": url, "deployPath": deploy_dir}


@router.post(f"{API_PREFIX}/deploy")
async def deploy_project(request: Request):
    uid = get_session_user_id(request)
    if not uid:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    target = (body.get("target") or "").strip().lower()
    project_name = body.get("projectName") or "codebot-project"
    files = body.get("files") or []
    custom_domain = (body.get("customDomain") or "").strip()

    if target not in ("netlify", "server"):
        return JSONResponse({"error": "Invalid target. Use 'netlify' or 'server'."}, status_code=400)
    if not files:
        return JSONResponse({"error": "No files to deploy. Run a build first."}, status_code=400)

    norm_files = [
        {"path": str(f.get("path", "")).strip().lstrip("/"), "content": str(f.get("content", ""))}
        for f in files if f.get("path")
    ]

    try:
        if target == "netlify":
            result = await _deploy_to_netlify(norm_files, project_name, custom_domain)
            logger.info(f"[deploy] Netlify deploy success: {result['url']}")
            return JSONResponse({"ok": True, "url": result["url"], "siteId": result["siteId"], "target": "netlify"})
        else:
            result = _deploy_to_server(norm_files, project_name)
            logger.info(f"[deploy] Server deploy success: {result['url']}")
            return JSONResponse({"ok": True, "url": result["url"], "deployPath": result["deployPath"], "target": "server"})
    except Exception as e:
        logger.exception(f"Deploy failed: {e}")
        return JSONResponse({"error": f"Deploy failed: {e}"}, status_code=500)


@router.get(f"{API_PREFIX}/sites/{{path:path}}")
async def serve_site_file(path: str):
    """Serve static files from ~/codebot-sites for VM deployments."""
    home = os.environ.get("HOME", "/home/omatic657")
    sites_dir = os.path.join(home, "codebot-sites")
    file_path = os.path.join(sites_dir, path)

    if not file_path.startswith(sites_dir):
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    if os.path.isdir(file_path):
        file_path = os.path.join(file_path, "index.html")

    if not os.path.isfile(file_path):
        return JSONResponse({"error": "Not found"}, status_code=404)

    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {
        ".html": "text/html", ".htm": "text/html", ".css": "text/css",
        ".js": "text/javascript", ".json": "application/json",
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".svg": "image/svg+xml", ".ico": "image/x-icon",
    }
    content_type = mime_map.get(ext, "application/octet-stream")

    from starlette.responses import Response
    with open(file_path, "rb") as f:
        return Response(content=f.read(), media_type=content_type)
