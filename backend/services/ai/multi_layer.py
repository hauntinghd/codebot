"""
Multi-layer AI orchestrator - Router → Engineer → Auditor.
No OpenAI SDK. xAI-only.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from backend.byok import decrypt_api_key

from .auditor import audit_code
from .engineer import generate_code
from .router import create_blueprint

logger = logging.getLogger("codebot")


def _user_get(u: Any, key: str, default=None):
    try:
        if hasattr(u, "keys") and key in u.keys():
            return u[key]
        if hasattr(u, "get"):
            return u.get(key, default)
    except Exception:
        pass
    return default


async def execute_multi_layer(
    user_request: str,
    user: Any,  # sqlite3.Row
    file_context: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
    code_mode: str = "functional",
) -> Dict[str, Any]:
    """
    Returns:
      {
        "assistant": str,
        "blueprint": Dict,
        "audit_result": Dict,
        "use_byok": bool,
        "router_model": str,
        "engineer_model": str,
        "auditor_model": str,
        "layers": [..]
      }
    """
    user_api_key_encrypted = _user_get(user, "api_key_encrypted", None)
    use_byok = bool(user_api_key_encrypted)

    # Router is always system-key in your current architecture (router.py should be xAI)
    logger.info("Starting Layer 1: Router")
    blueprint = await create_blueprint(
        user_request=user_request,
        file_context=file_context[:5000] if file_context else None,
        chat_history=chat_history,
    )

    # Engineer/Auditor should use BYOK if present; otherwise system key (CBT governs spend)
    user_api_key = None
    if use_byok:
        user_api_key = decrypt_api_key(str(user_api_key_encrypted))
        if not user_api_key:
            raise HTTPException(status_code=500, detail="Failed to decrypt API key. Please reset your key in Settings.")

    logger.info(f"Starting Layer 2: Engineer (BYOK={use_byok})")
    generated_code = await generate_code(
        user_request=user_request,
        blueprint=blueprint,
        file_context=file_context,
        chat_history=chat_history,
        system_prompt=system_prompt,
        user_api_key=user_api_key,
        code_mode=code_mode,
    )

    logger.info(f"Starting Layer 3: Auditor (BYOK={use_byok})")
    audit_result = await audit_code(
        generated_code=generated_code,
        blueprint=blueprint,
        user_request=user_request,
        user_api_key=user_api_key,
        code_mode=code_mode,
    )

    final_code = audit_result.get("verified_code", generated_code)

    return {
        "assistant": final_code,
        "blueprint": blueprint,
        "audit_result": audit_result,
        "use_byok": use_byok,
        "router_model": "router",
        "engineer_model": "xai",
        "auditor_model": "xai",
        "layers": ["router", "engineer", "auditor"],
    }
