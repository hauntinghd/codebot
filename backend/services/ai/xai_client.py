"""
xAI client (OpenAI-compatible API) WITHOUT the OpenAI Python SDK.
Stability rules:
- Single implementation used across router/engineer/auditor/fallback
- Always returns plain dicts (JSON-safe)
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _base_url() -> str:
    return _env("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/")


def _api_key_system() -> str:
    k = _env("XAI_API_KEY")
    if not k:
        raise HTTPException(status_code=500, detail="Missing XAI_API_KEY in environment.")
    return k


async def chat_completions_create(
    *,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 4000,
    timeout_s: float = 60.0,
) -> Dict[str, Any]:
    """
    Calls: POST {base}/chat/completions
    Returns response JSON dict.
    """
    url = f"{_base_url()}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid xAI API key.")
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"xAI request failed: {e}") from e


def extract_text(resp_json: Dict[str, Any]) -> str:
    try:
        return str(resp_json["choices"][0]["message"]["content"] or "")
    except Exception:
        return ""


def extract_usage(resp_json: Dict[str, Any]) -> Dict[str, int]:
    usage = resp_json.get("usage") or {}
    return {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
    }


def resolve_key_and_model(
    *,
    user_api_key: Optional[str],
) -> tuple[str, str, bool]:
    """
    Policy:
    - If user_api_key provided => BYOK
    - else => system key
    Model comes from env XAI_MODEL_DEFAULT.
    """
    model = _env("XAI_MODEL_DEFAULT", "grok-4-1-fast-reasoning")
    if user_api_key:
        return user_api_key, model, True
    return _api_key_system(), model, False
