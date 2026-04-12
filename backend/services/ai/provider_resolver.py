"""
Provider resolver — routes CodeBot to the optimal AI model via fal.ai.

Two fal.ai endpoints:
  - openrouter/router: returns usage.cost (preferred, used for billing)
  - fal-ai/any-llm:    no cost data but works for all models (fallback)

Some models require reasoning=true on OpenRouter (o3, gpt-5-*, gemini-2.5-pro, deepseek-r1).
"""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

from fastapi import HTTPException
from openai import OpenAI

logger = logging.getLogger("codebot")


def _get_env(name: str) -> str:
    return (os.getenv(name) or "").strip()


# ---------------------------------------------------------------------------
# Model registry — every model verified working on fal.ai 2026-04-12
# Pricing: real measured avg $/1k tokens from OpenRouter usage.cost field
# ---------------------------------------------------------------------------

FAL_MODELS = {
    # ====== CODING — best for code generation ======
    "claude-opus-4-6": {
        "fal_id": "anthropic/claude-opus-4-6",
        "category": "coding",
        "tier": "frontier",
        "label": "Claude Opus 4.6",
        "description": "Anthropic's most powerful model. Best-in-class coding.",
        "cost_per_1k": 0.01568,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },
    "claude-sonnet-4-6": {
        "fal_id": "anthropic/claude-sonnet-4-6",
        "category": "coding",
        "tier": "frontier",
        "label": "Claude Sonnet 4.6",
        "description": "Excellent coding, faster and cheaper than Opus.",
        "cost_per_1k": 0.00933,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },
    "claude-sonnet-4.5": {
        "fal_id": "anthropic/claude-sonnet-4.5",
        "category": "coding",
        "tier": "premium",
        "label": "Claude Sonnet 4.5",
        "description": "Strong coding model, great balance of speed and quality.",
        "cost_per_1k": 0.00933,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },
    "gpt-5": {
        "fal_id": "openai/gpt-5-chat",
        "category": "coding",
        "tier": "frontier",
        "label": "GPT-5",
        "description": "OpenAI's flagship. Top-tier code generation.",
        "cost_per_1k": 0.00878,
        "endpoint": "openrouter",
        "reasoning_required": True,
    },
    "gpt-4.1": {
        "fal_id": "openai/gpt-4.1",
        "category": "coding",
        "tier": "premium",
        "label": "GPT-4.1",
        "description": "OpenAI's optimized coding model. Fast and accurate.",
        "cost_per_1k": 0.00716,
        "endpoint": "openrouter",
        "reasoning_required": True,
    },
    "deepseek-v3.1": {
        "fal_id": "deepseek/deepseek-v3.1-terminus",
        "category": "coding",
        "tier": "premium",
        "label": "DeepSeek V3.1",
        "description": "DeepSeek's latest. Strong open-source coding model.",
        "cost_per_1k": 0.00100,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },

    # ====== REASONING — extended chain-of-thought ======
    "o3": {
        "fal_id": "openai/o3",
        "category": "reasoning",
        "tier": "frontier",
        "label": "OpenAI o3",
        "description": "OpenAI's strongest reasoning model. Deep thinking.",
        "cost_per_1k": 0.00651,
        "endpoint": "openrouter",
        "reasoning_required": True,
    },
    "gemini-2.5-pro": {
        "fal_id": "google/gemini-2.5-pro",
        "category": "reasoning",
        "tier": "frontier",
        "label": "Gemini 2.5 Pro",
        "description": "Google's frontier reasoning model. 1M context window.",
        "cost_per_1k": 0.00808,
        "endpoint": "openrouter",
        "reasoning_required": True,
    },
    "deepseek-r1": {
        "fal_id": "deepseek/deepseek-r1",
        "category": "reasoning",
        "tier": "premium",
        "label": "DeepSeek R1",
        "description": "DeepSeek's reasoning specialist. Shows thinking steps.",
        "cost_per_1k": 0.00208,
        "endpoint": "openrouter",
        "reasoning_required": True,
    },

    # ====== THINKING — deep extended reasoning ======
    "claude-sonnet-4.5-thinking": {
        "fal_id": "anthropic/claude-sonnet-4.5",
        "category": "thinking",
        "tier": "frontier",
        "label": "Claude Sonnet 4.5 (Thinking)",
        "description": "Claude with extended thinking for complex problems.",
        "cost_per_1k": 0.00933,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },
    "gemini-2.5-pro-thinking": {
        "fal_id": "google/gemini-2.5-pro",
        "category": "thinking",
        "tier": "frontier",
        "label": "Gemini 2.5 Pro (Thinking)",
        "description": "Gemini with deep reasoning for architecture decisions.",
        "cost_per_1k": 0.00808,
        "endpoint": "openrouter",
        "reasoning_required": True,
    },
    "deepseek-r1-thinking": {
        "fal_id": "deepseek/deepseek-r1",
        "category": "thinking",
        "tier": "premium",
        "label": "DeepSeek R1 (Thinking)",
        "description": "Deep reasoning with visible chain-of-thought. Budget-friendly.",
        "cost_per_1k": 0.00208,
        "endpoint": "openrouter",
        "reasoning_required": True,
    },

    # ====== PLANNING — architecture & system design ======
    "gemini-2.5-pro-planning": {
        "fal_id": "google/gemini-2.5-pro",
        "category": "planning",
        "tier": "frontier",
        "label": "Gemini 2.5 Pro (Planning)",
        "description": "Best for architecture blueprints. 1M context window.",
        "cost_per_1k": 0.00808,
        "endpoint": "openrouter",
        "reasoning_required": True,
    },
    "claude-opus-4-6-planning": {
        "fal_id": "anthropic/claude-opus-4-6",
        "category": "planning",
        "tier": "frontier",
        "label": "Claude Opus 4.6 (Planning)",
        "description": "Anthropic's best for complex system architecture.",
        "cost_per_1k": 0.01568,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },
    "o3-planning": {
        "fal_id": "openai/o3",
        "category": "planning",
        "tier": "frontier",
        "label": "OpenAI o3 (Planning)",
        "description": "Strongest reasoning for technical architecture.",
        "cost_per_1k": 0.00651,
        "endpoint": "openrouter",
        "reasoning_required": True,
    },

    # ====== VISION — multimodal image understanding ======
    "gemini-2.5-flash-vision": {
        "fal_id": "google/gemini-2.5-flash",
        "category": "vision",
        "tier": "premium",
        "label": "Gemini 2.5 Flash (Vision)",
        "description": "Fast multimodal. Understands screenshots and UI.",
        "cost_per_1k": 0.00203,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },
    "gpt-4o-vision": {
        "fal_id": "openai/gpt-4o",
        "category": "vision",
        "tier": "premium",
        "label": "GPT-4o (Vision)",
        "description": "OpenAI's multimodal model. Strong image analysis.",
        "cost_per_1k": 0.00500,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },
    "llama-4-maverick-vision": {
        "fal_id": "meta-llama/llama-4-maverick",
        "category": "vision",
        "tier": "premium",
        "label": "Llama 4 Maverick (Vision)",
        "description": "Meta's open multimodal. Budget vision model.",
        "cost_per_1k": 0.00069,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },

    # ====== FAST / CHEAP — high speed, low cost ======
    "claude-haiku-4.5": {
        "fal_id": "anthropic/claude-haiku-4.5",
        "category": "fast",
        "tier": "fast",
        "label": "Claude Haiku 4.5",
        "description": "Fast Anthropic model. Great for quick tasks.",
        "cost_per_1k": 0.00311,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },
    "gemini-2.5-flash": {
        "fal_id": "google/gemini-2.5-flash",
        "category": "fast",
        "tier": "fast",
        "label": "Gemini 2.5 Flash",
        "description": "Google's fast model. Excellent quality per dollar.",
        "cost_per_1k": 0.00203,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },
    "gpt-5-mini": {
        "fal_id": "openai/gpt-5-mini",
        "category": "fast",
        "tier": "fast",
        "label": "GPT-5 Mini",
        "description": "Compact GPT-5. Good coding at low cost.",
        "cost_per_1k": 0.00172,
        "endpoint": "openrouter",
        "reasoning_required": True,
    },
    "llama-4-scout": {
        "fal_id": "meta-llama/llama-4-scout",
        "category": "fast",
        "tier": "fast",
        "label": "Llama 4 Scout",
        "description": "Meta's efficient model. Extremely cheap.",
        "cost_per_1k": 0.00026,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },
    "gemini-2.5-flash-lite": {
        "fal_id": "google/gemini-2.5-flash-lite",
        "category": "fast",
        "tier": "fast",
        "label": "Gemini 2.5 Flash Lite",
        "description": "Cheapest capable model. Great for simple tasks.",
        "cost_per_1k": 0.00034,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },
    "gpt-5-nano": {
        "fal_id": "openai/gpt-5-nano",
        "category": "fast",
        "tier": "fast",
        "label": "GPT-5 Nano",
        "description": "Smallest GPT-5. Ultra-fast, ultra-cheap.",
        "cost_per_1k": 0.00034,
        "endpoint": "openrouter",
        "reasoning_required": True,
    },
    "gpt-oss-120b": {
        "fal_id": "openai/gpt-oss-120b",
        "category": "fast",
        "tier": "fast",
        "label": "GPT-OSS 120B",
        "description": "OpenAI's open-source model. Cheapest OpenAI option.",
        "cost_per_1k": 0.00015,
        "endpoint": "openrouter",
        "reasoning_required": True,
    },
    "llama-4-maverick": {
        "fal_id": "meta-llama/llama-4-maverick",
        "category": "fast",
        "tier": "fast",
        "label": "Llama 4 Maverick",
        "description": "Meta's largest Llama 4. Strong open-source option.",
        "cost_per_1k": 0.00069,
        "endpoint": "openrouter",
        "reasoning_required": False,
    },
}

# Default model for each pipeline layer (user can override per-request)
LAYER_MODEL_DEFAULTS = {
    "router":    "gemini-2.5-flash",              # Fast + cheap for planning
    "engineer":  "claude-opus-4-6",               # Best coding
    "auditor":   "claude-sonnet-4.5",             # Strong review, cheaper
    "corrector": "deepseek-r1",                   # Verification + reasoning
    "vision":    "gemini-2.5-flash-vision",       # Fast vision
    "planning":  "gemini-2.5-pro-planning",       # Architecture
    "ask":       "claude-sonnet-4-6",             # Conversational
    "fast":      "gemini-2.5-flash-lite",         # Quick tasks
}


# ---------------------------------------------------------------------------
# Provider resolution
# ---------------------------------------------------------------------------

def resolve_provider_and_key(
    user_provider: Optional[str],
    user_key: Optional[str],
) -> Tuple[str, str]:
    if user_provider and user_key:
        return user_provider.strip().lower(), user_key.strip()
    fal_key = _get_env("FAL_KEY")
    if fal_key:
        return "fal", fal_key
    sys_xai = _get_env("XAI_API_KEY")
    if sys_xai:
        return "xai", sys_xai
    raise HTTPException(status_code=500, detail="No AI provider configured. Set FAL_KEY or XAI_API_KEY.")


# ---------------------------------------------------------------------------
# fal.ai LLM Client — dual-endpoint with cost tracking
# ---------------------------------------------------------------------------

class FalLLMClient:
    """
    Wraps fal.ai to provide an OpenAI-compatible interface.
    Uses openrouter/router (has cost tracking) with fallback to fal-ai/any-llm.
    """

    ENDPOINT_OPENROUTER = "https://fal.run/openrouter/router"
    ENDPOINT_ANY_LLM = "https://fal.run/fal-ai/any-llm"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.chat = self
        self.completions = self

    def create(self, model: str, messages: list, temperature: float = 0.3,
               max_tokens: int = 4096, stream: bool = False,
               response_format: Optional[dict] = None, **kwargs):
        import httpx

        # Convert messages to fal prompt format
        system_prompt = ""
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_prompt += ("\n" + content if system_prompt else content)
            elif role == "user":
                prompt_parts.append(content)
            elif role == "assistant":
                prompt_parts.append(f"[Previous assistant response]:\n{content}")
        prompt = "\n\n".join(prompt_parts)

        # Resolve model info
        fal_model = get_fal_model_id(model)
        model_info = FAL_MODELS.get(model) or {}
        needs_reasoning = model_info.get("reasoning_required", False)
        preferred_endpoint = model_info.get("endpoint", "openrouter")

        # Force JSON output via system prompt injection
        if response_format and response_format.get("type") == "json_object":
            system_prompt = (system_prompt or "") + "\n\nCRITICAL: Output ONLY valid JSON. No markdown fences, no explanation."

        payload = {
            "model": fal_model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            payload["system_prompt"] = system_prompt
        if needs_reasoning:
            payload["reasoning"] = True

        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

        # Try OpenRouter first (has cost data), fall back to any-llm
        url = self.ENDPOINT_OPENROUTER if preferred_endpoint == "openrouter" else self.ENDPOINT_ANY_LLM
        data = None
        try:
            with httpx.Client(timeout=180.0) as http:
                resp = http.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if data.get("detail") or data.get("error"):
                    raise ValueError(str(data.get("detail") or data.get("error"))[:200])
        except Exception as e:
            if url == self.ENDPOINT_OPENROUTER:
                logger.warning(f"[fal] OpenRouter failed for {fal_model}, falling back to any-llm: {e}")
                payload.pop("reasoning", None)
                try:
                    with httpx.Client(timeout=180.0) as http:
                        resp = http.post(self.ENDPOINT_ANY_LLM, json=payload, headers=headers)
                        resp.raise_for_status()
                        data = resp.json()
                except Exception as e2:
                    raise HTTPException(status_code=502, detail=f"fal.ai call failed: {e2}")
            else:
                raise HTTPException(status_code=502, detail=f"fal.ai call failed: {e}")

        output_text = data.get("output") or ""
        reasoning_text = data.get("reasoning")
        usage = data.get("usage") or {}

        # Strip markdown code fences if model wrapped JSON in them
        stripped = output_text.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            # Remove first line (```json) and last line (```)
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            elif lines[0].startswith("```"):
                lines = lines[1:]
            output_text = "\n".join(lines).strip()

        # If reasoning model returned empty output, use reasoning as output
        if not output_text.strip() and reasoning_text:
            output_text = reasoning_text

        # If no usage from fal, estimate from model pricing
        if not usage.get("cost") and model_info.get("cost_per_1k"):
            est_tokens = len(prompt) // 4 + len(output_text) // 4
            usage["cost"] = model_info["cost_per_1k"] * est_tokens / 1000

        return _FalResponse(output_text, usage, fal_model, reasoning_text, stream)


class _FalResponse:
    """OpenAI-compatible response object from fal.ai."""
    def __init__(self, text, usage_data, model_name, reasoning_text, is_stream):
        self.model = model_name
        self.reasoning = reasoning_text
        self.usage = _FalUsage(usage_data)
        self.choices = [_FalChoice(text)]
        self._is_stream = is_stream

    def __iter__(self):
        """Support for `for chunk in resp:` streaming pattern."""
        yield self


class _FalChoice:
    def __init__(self, text):
        self.message = _FalMessage(text)
        self.delta = _FalMessage(text)
        self.index = 0
        self.finish_reason = "stop"


class _FalMessage:
    def __init__(self, content):
        self.content = content
        self.role = "assistant"


class _FalUsage:
    def __init__(self, u):
        self.prompt_tokens = u.get("prompt_tokens", 0)
        self.completion_tokens = u.get("completion_tokens", 0)
        self.total_tokens = u.get("total_tokens", 0)
        self.cost = u.get("cost", 0)


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def make_llm_client(provider: str, api_key: str):
    provider = (provider or "").strip().lower()
    if provider == "fal":
        return FalLLMClient(api_key=api_key)
    if provider == "xai":
        base_url = _get_env("XAI_BASE_URL") or "https://api.x.ai/v1"
        return OpenAI(api_key=api_key, base_url=base_url)
    if provider == "openai":
        return OpenAI(api_key=api_key)
    raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")


# ---------------------------------------------------------------------------
# Model helpers
# ---------------------------------------------------------------------------

def get_fal_model_id(model_name: str) -> str:
    """Resolve CodeBot model name -> fal.ai model ID."""
    entry = FAL_MODELS.get(model_name)
    if entry:
        return entry["fal_id"]
    if "/" in model_name:
        return model_name
    return model_name


def get_layer_model(layer: str) -> str:
    """Get default model for a pipeline layer, respecting env overrides."""
    env_key = f"CODEBOT_LAYER_{layer.upper()}_MODEL"
    override = _get_env(env_key)
    if override:
        return override
    return LAYER_MODEL_DEFAULTS.get(layer, "claude-sonnet-4.5")


def is_fal_available() -> bool:
    return bool(_get_env("FAL_KEY"))


def get_model_cost_per_1k(model_name: str) -> float:
    """Return $/1k tokens for a model (for CBT deduction)."""
    entry = FAL_MODELS.get(model_name)
    if entry:
        return entry.get("cost_per_1k", 0.005)
    return 0.005  # default fallback


# ---------------------------------------------------------------------------
# BYOK helpers (unchanged)
# ---------------------------------------------------------------------------

def get_user_byok_from_row(u) -> Tuple[Optional[str], Optional[str]]:
    def _get(col: str) -> Optional[str]:
        try:
            if u is None:
                return None
            if isinstance(u, dict):
                return u.get(col)
            if hasattr(u, "keys"):
                keys = u.keys()
                if col in keys:
                    return u[col]
            if hasattr(u, col):
                return getattr(u, col)
            return None
        except Exception:
            return None
    provider = _get("api_provider") or _get("provider")
    enc = _get("api_key_encrypted") or _get("api_key_enc")
    return (str(provider) if provider else None, str(enc) if enc else None)
