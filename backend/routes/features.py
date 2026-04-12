"""Minimal features routes used during recovery.

This stub implements lightweight endpoints that are safe to import and
execute while we stabilize the rest of the backend. It intentionally avoids
heavy templating and any third-party client calls that may fail at import time.
"""

from __future__ import annotations

from typing import Any, Dict
import logging

from fastapi import Depends, FastAPI, File, UploadFile
from starlette.requests import Request

from backend.auth import current_user, require_subscribed

logger = logging.getLogger("codebot")


def register_routes(api: FastAPI):
    @api.post("/health/features")
    async def features_health() -> Dict[str, Any]:
        return {"ok": True, "features": "minimal-stub"}

    @api.post("/speech/transcribe")
    async def transcribe_speech(
        request: Request,
        audio: UploadFile = File(...),
        u=Depends(current_user),
    ) -> Dict[str, Any]:
        _ = await audio.read()
        return {"ok": True, "text": "transcription-unavailable"}

    @api.post("/deploy/netlify")
    async def deploy_to_netlify(payload: Dict[str, Any], request: Request, u=Depends(require_subscribed)) -> Dict[str, Any]:
        return {"ok": True, "deploy_id": None, "note": "stubbed"}

    @api.post("/code/analyze")
    async def analyze_code_quality(payload: Dict[str, Any], request: Request, u=Depends(require_subscribed)) -> Dict[str, Any]:
        return {"ok": True, "analysis": "unavailable (stub)"}
