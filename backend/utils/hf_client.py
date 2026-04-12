import os
import time
import requests
import logging
from typing import Callable, Optional

logger = logging.getLogger("codebot.hf_client")


def _get_hf_token() -> str:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
    if not token:
        raise RuntimeError("Missing HF token: set HF_TOKEN or HUGGINGFACEHUB_API_TOKEN")
    return token



def _call_hf_inference(prompt: str, model: str, max_new_tokens: int = 512, temperature: float = 0.2, timeout: int = 60) -> str:
    token = _get_hf_token()
    router_endpoint = os.environ.get("HF_ROUTER_ENDPOINT", "https://router.huggingface.co/v1/chat/completions")
    model_id = model or os.environ.get("HF_PLANNING_MODEL") or os.environ.get("HF_CODE_MODEL")
    if not model_id:
        raise RuntimeError("No model id specified for HF router call")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    payload = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": int(max_new_tokens),
        "temperature": float(temperature),
    }
    resp = requests.post(router_endpoint, headers=headers, json=payload, timeout=timeout)
    if resp.status_code == 200:
        try:
            j = resp.json()
            # OpenAI-compatible: choices[0].message.content
            if "choices" in j and j["choices"] and "message" in j["choices"][0]:
                return j["choices"][0]["message"]["content"]
            # Fallback: text
            if "text" in j:
                return j["text"]
            return resp.text or ""
        except Exception:
            return resp.text or ""
    else:
        logger.error(f"HF router call failed: %s %s", resp.status_code, resp.text[:200])
        resp.raise_for_status()


def get_planning_client(model: Optional[str] = None) -> Callable[[str, str], str]:
    """Return a callable client for planning.

    The returned callable signature is: client(prompt: str, context_or_title: str) -> str
    It will call Hugging Face Inference API using HF_TOKEN.
    """

    def client(prompt: str, _context: str = "") -> str:
        m = model or os.environ.get("PLANNING_MODEL") or os.environ.get("HF_PLANNING_MODEL") or "Qwen/Qwen2.5-3B-Instruct"
        return _call_hf_inference(prompt, model=m, max_new_tokens=int(os.environ.get("HF_MAX_TOKENS", 1024)), temperature=float(os.environ.get("HF_TEMPERATURE", 0.2)))

    return client


def speech_to_text(audio_bytes: bytes, model: Optional[str] = None, language: Optional[str] = None, timeout: int = 120) -> str:
    """Call HF inference for speech-to-text. Returns the transcribed text.

    This posts raw audio bytes to the model inference endpoint and attempts
    to parse common response shapes.
    """
    token = _get_hf_token()
    m = model or os.environ.get("HF_SPEECH_MODEL", "openai/whisper-large-v2")
    url = f"https://router.huggingface.co/models/{m}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    content_type = os.environ.get("HF_SPEECH_CONTENT_TYPE", "application/octet-stream")
    try:
        resp = requests.post(url, headers={**headers, "Content-Type": content_type}, data=audio_bytes, timeout=timeout)
    except requests.RequestException as e:
        logger.error("HF speech request failed: %s", e)
        raise RuntimeError(f"HF speech request failed: {e}")

    if resp.status_code != 200:
        logger.warning("HF speech model %s returned status %s", m, resp.status_code)
        try:
            j = resp.json()
            for k in ("text", "transcription", "output", "result"):
                if k in j and isinstance(j[k], str):
                    return j[k]
        except Exception:
            pass
        resp.raise_for_status()

    try:
        j = resp.json()
        if isinstance(j, dict):
            for k in ("text", "transcription", "generated_text", "output"):
                if k in j and isinstance(j[k], str):
                    return j[k]
        if isinstance(j, list) and j and isinstance(j[0], dict):
            first = j[0]
            for k in ("generated_text", "text", "output"):
                if k in first and isinstance(first[k], str):
                    return first[k]
        return resp.text or ""
    except Exception as e:
        logger.error("Failed to parse HF speech response: %s", e)
        raise RuntimeError(f"Failed to parse HF speech response: {e}")
