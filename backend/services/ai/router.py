"""
Layer 1: Router - Creates a structured blueprint.
System default uses xAI (OpenAI-compatible). BYOK is handled elsewhere.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from openai import OpenAI

logger = logging.getLogger("codebot")


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _system_llm_client() -> OpenAI:
    """
    System default: uses fal.ai if FAL_KEY is set (access to all frontier models),
    otherwise falls back to xAI.
    """
    from backend.services.ai.provider_resolver import resolve_provider_and_key, make_llm_client
    provider, api_key = resolve_provider_and_key(None, None)
    return make_llm_client(provider, api_key)


async def create_blueprint(
    user_request: str,
    file_context: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Analyze request and create structured blueprint.

    Returns:
        {
            "files_to_edit": List[str],
            "libraries_needed": List[str],
            "risks": List[str],
            "approach": str,
            "complexity": "simple" | "medium" | "complex"
        }
    """
    user_request = (user_request or "").strip()
    if not user_request:
        raise HTTPException(status_code=400, detail="user_request required")

    client = _system_llm_client()

    from backend.services.ai.provider_resolver import get_layer_model, get_fal_model_id, is_fal_available
    default_router = get_layer_model("router")
    router_model = _env("ROUTER_MODEL", get_fal_model_id(default_router) if is_fal_available() else "grok-4-1-fast-reasoning")

    router_prompt = f"""You are a Senior Software Architect planning code changes. Analyze the user's request and create a structured blueprint.

USER REQUEST:
{user_request}

{f'FILE CONTEXT AVAILABLE:{chr(10)}{file_context[:2000]}...' if file_context else ''}

Create a JSON blueprint with this exact structure:
{{
  "files_to_edit": ["list", "of", "file", "paths"],
  "libraries_needed": ["list", "of", "required", "libraries"],
  "risks": ["list", "of", "potential", "risks"],
  "approach": "Brief description of the approach",
  "complexity": "simple" | "medium" | "complex"
}}

IMPORTANT:
- Do NOT write code yet. Only plan.
- For ANY website, web app, store, or multi-page project: use complexity "complex" and list ALL files in files_to_edit.
- For e-commerce or multi-page sites, include: index.html, styles.css, app.js, products.html, contact.html, featured.html, content.html, terms.html (and login.html if user asks for accounts).
- When the user requests a FULL-STACK site (Stripe checkout, database, user accounts/auth, backend, checkout, payment), also include backend files in files_to_edit: server.js, package.json, .env.example, README.md. Optionally include db.js or auth.js if you want separate modules. The engineer will generate a Node Express server with Stripe, auth, and a simple DB.
- Be specific about file paths — include every HTML, CSS, JS, and backend file the project needs.
- Identify all dependencies and libraries needed.
- List potential risks (breaking changes, security issues, performance).
- When in doubt, prefer "complex" and more files_to_edit so the engineer generates a complete project.

Output ONLY valid JSON, no markdown, no code blocks."""

    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": "You are a Senior Software Architect. Output only valid JSON blueprints, no explanations.",
        },
        {"role": "user", "content": router_prompt},
    ]

    # Add recent chat history for context (last 5)
    if chat_history:
        for msg in chat_history[-5:]:
            role = msg.get("role")
            if role in ("user", "assistant"):
                messages.append(
                    {
                        "role": role,
                        "content": str(msg.get("content", ""))[:500],
                    }
                )

    try:
        resp = client.chat.completions.create(
            model=router_model,
            messages=messages,  # type: ignore
            temperature=0.2,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        blueprint_text = resp.choices[0].message.content or "{}"

        try:
            blueprint = json.loads(blueprint_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse blueprint JSON: %s", blueprint_text[:200])
            blueprint = {
                "files_to_edit": [],
                "libraries_needed": [],
                "risks": ["Unable to parse blueprint"],
                "approach": "Proceed with standard code generation",
                "complexity": "medium",
            }

        blueprint.setdefault("files_to_edit", [])
        blueprint.setdefault("libraries_needed", [])
        blueprint.setdefault("risks", [])
        blueprint.setdefault("approach", "Standard implementation")
        blueprint.setdefault("complexity", "medium")

        logger.info(
            "Router blueprint created: model=%s complexity=%s files=%s",
            router_model,
            blueprint.get("complexity"),
            len(blueprint.get("files_to_edit", [])),
        )
        return blueprint

    except Exception as e:
        logger.error("Router layer error: %s", e, exc_info=True)
        return {
            "files_to_edit": [],
            "libraries_needed": [],
            "risks": [f"Router error: {str(e)}"],
            "approach": "Fallback: proceed with standard code generation",
            "complexity": "medium",
        }
