"""Hugging Face discovery helpers: whoami and model probing."""
from __future__ import annotations

import logging
import requests
from typing import List, Optional

logger = logging.getLogger("codebot.hf_discovery")


def whoami(token: str) -> dict:
    """Return whoami information for the provided HF token."""
    url = "https://huggingface.co/api/whoami-v2"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, timeout=15)
    try:
        return resp.json()
    except Exception:
        return {"status_code": resp.status_code, "text": resp.text}


def probe_model(token: str, model: str, timeout: int = 30) -> bool:
    """Probe a single model via the HF router inference endpoint. Return True if inference returns HTTP 200."""
    url = f"https://router.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    payload = {"inputs": "Hello world", "options": {"wait_for_model": True}, "parameters": {"max_new_tokens": 8}}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except Exception as e:
        logger.debug("Probe model %s request failed: %s", model, e)
        return False
    if resp.status_code == 200:
        return True
    logger.debug("Probe model %s returned %s: %s", model, resp.status_code, resp.text[:200])
    return False


def find_working_model(token: str, candidates: Optional[List[str]] = None, limit: int = 30) -> Optional[str]:
    """Try to find a working model from candidates; if none provided, query the HF models list and probe the top results.

    Returns the first model id that responds with HTTP 200 to an inference probe, or None.
    """
    if candidates is None:
        candidates = [
            "google/flan-ul2",
            "google/flan-t5-large",
            "bigscience/bloomz-560m",
            "bigscience/bloomz-1b1",
            "gpt2",
            "bigcode/starcoder",
            "tiiuae/falcon-7b-instruct",
            "mistralai/mistral-7b-instruct-v0.1",
            "openassistant/gpt-oa-3",
        ]

    # First, try curated candidates
    for m in candidates:
        if not m:
            continue
        logger.info("Probing candidate HF model: %s", m)
        if probe_model(token, m):
            logger.info("Model %s is available for inference", m)
            return m

    # Fall back to querying the HF models list and probe top results
    try:
        url = f"https://huggingface.co/api/models?sort=downloads&limit={limit}"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, timeout=15)
        models = resp.json() if resp.status_code == 200 else []
        for item in models:
            model_id = item.get("modelId") or item.get("id") or item.get("_id")
            if not model_id:
                continue
            logger.info("Probing HF model from list: %s", model_id)
            if probe_model(token, model_id):
                logger.info("Model %s is available for inference", model_id)
                return model_id
    except Exception as e:
        logger.warning("Model discovery query failed: %s", e)

    return None
