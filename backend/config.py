"""Backend configuration - environment variables and constants."""
from __future__ import annotations

DEV_MODE = False

import base64
import logging
import os
import re
import secrets
from pathlib import Path
from typing import Optional

import stripe
from backend.utils.hf_client import get_planning_client

# Load environment variables from .env file in project root if it exists
from dotenv import load_dotenv
import os as _os
_env_file = Path(__file__).parent.parent.parent / ".env"
if not _env_file.exists():
    # fallback: try one level up (legacy)
    _env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file, override=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("codebot")


def _env(name: str, default: str = "") -> str:
    """Get environment variable with default."""
    v = os.getenv(name, default)
    return v if v else default


# App paths and URLs
APP_BASE_PATH = (_env("APP_BASE_PATH", "/codebot") or "/codebot").rstrip("/")
APP_BASE_URL = _env("APP_BASE_URL", "https://chatbot.nyptidindustries.com").rstrip("/")
API_PREFIX = "/api"

# Directories
DATA_DIR = Path(_env("DATA_DIR", "./data")).resolve()
DB_PATH = Path(_env("DB_PATH", str(DATA_DIR / "codebot.db"))).resolve()
PROJECTS_DIR = Path(_env("PROJECTS_DIR", str(DATA_DIR / "projects"))).resolve()
UPLOADS_DIR = Path(_env("UPLOADS_DIR", str(DATA_DIR / "uploads"))).resolve()
STATIC_DIR = Path(_env("STATIC_DIR", "")).resolve() if _env("STATIC_DIR", "") else None
OFFLINE_FLAG_FILE = DATA_DIR / "offline_mode.flag"
OFFLINE_MODE_DEFAULT = _env("OFFLINE_MODE", "false").lower() in ("true", "1", "yes")

# Platform-level feature flags
ALLOW_WEBSITE_PROJECTS = _env("ALLOW_WEBSITE_PROJECTS", "false").lower() in ("true", "1", "yes")

# JWT and session secrets
_jwt_secret_env = _env("JWT_SECRET", "")
if not _jwt_secret_env:
    _jwt_secret_value = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8")
else:
    _jwt_secret_value = _jwt_secret_env
JWT_SECRET: str = _jwt_secret_value

ACCESS_TOKEN_TTL_SECONDS = int(_env("ACCESS_TOKEN_TTL_SECONDS", "900"))  # 15 min
REFRESH_TOKEN_TTL_SECONDS = int(_env("REFRESH_TOKEN_TTL_SECONDS", "2592000"))  # 30 days
SESSION_SECRET = _env("SESSION_SECRET", JWT_SECRET or secrets.token_urlsafe(32))

# OpenAI configuration
OPENAI_API_KEY = _env("OPENAI_API_KEY", "")
OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_MODEL_BEST = _env("OPENAI_MODEL_BEST", "gpt-4o")
OPENAI_MODEL_MINI = _env("OPENAI_MODEL_MINI", "gpt-4o-mini")

# HuggingFace configuration
HUGGINGFACEHUB_API_TOKEN = _env("HUGGINGFACEHUB_API_TOKEN", "")

# fal.ai configuration (unlocks ALL frontier models via OpenRouter)
FAL_KEY = _env("FAL_KEY", "")

# Model pricing — REAL measured costs from fal.ai (avg $/1k tokens, 2026-04-12)
# Used for CBT deduction: cost_per_request = tokens_used / 1000 * cost_per_1k
MODEL_PRICING = {
    # Frontier coding
    "anthropic/claude-opus-4-6":    {"cost_per_1k": 0.01568},
    "anthropic/claude-sonnet-4-6":  {"cost_per_1k": 0.00933},
    "anthropic/claude-sonnet-4.5":  {"cost_per_1k": 0.00933},
    "openai/gpt-5-chat":            {"cost_per_1k": 0.00878},
    "openai/gpt-4.1":               {"cost_per_1k": 0.00716},
    "deepseek/deepseek-v3.1-terminus": {"cost_per_1k": 0.00100},
    # Reasoning
    "openai/o3":                    {"cost_per_1k": 0.00651},
    "google/gemini-2.5-pro":        {"cost_per_1k": 0.00808},
    "deepseek/deepseek-r1":         {"cost_per_1k": 0.00208},
    # Vision
    "openai/gpt-4o":                {"cost_per_1k": 0.00500},
    "google/gemini-2.5-flash":      {"cost_per_1k": 0.00203},
    "meta-llama/llama-4-maverick":  {"cost_per_1k": 0.00069},
    # Fast/cheap
    "anthropic/claude-haiku-4.5":   {"cost_per_1k": 0.00311},
    "openai/gpt-5-mini":            {"cost_per_1k": 0.00172},
    "meta-llama/llama-4-scout":     {"cost_per_1k": 0.00026},
    "google/gemini-2.5-flash-lite": {"cost_per_1k": 0.00034},
    "openai/gpt-5-nano":            {"cost_per_1k": 0.00034},
    "openai/gpt-oss-120b":          {"cost_per_1k": 0.00015},
    # xAI fallback
    "grok-4-1-fast-reasoning":      {"cost_per_1k": 0.00200},
}

# CBT markup multiplier — our margin on top of fal.ai cost
CBT_MARKUP = float(_env("CBT_MARKUP", "1.4"))  # 40% margin

# BYOK / xAI defaults
# Hard dollar cap to protect BYOK funds (owner-settable via env)
BYOK_HARD_LIMIT_DOLLARS = float(_env("BYOK_HARD_LIMIT_DOLLARS", "8.0"))
# Default BYOK provider to prefer when set
DEFAULT_BYOK_PROVIDER = _env("DEFAULT_BYOK_PROVIDER", "grok")
# Default model to use for xAI/grok when BYOK provider is grok
XAI_DEFAULT_MODEL = _env("XAI_DEFAULT_MODEL", "grok-4-1-fast-reasoning")
# Number of days to spread BYOK hard limit across (for daily allowance)
BYOK_DAYS_SPREAD = int(_env("BYOK_DAYS_SPREAD", "14"))

# ---------------------------------------------------------------------------
# Subscription tiers — 100% paid. No free tier.
# ---------------------------------------------------------------------------
# CBT (CodeBot Tokens) = internal credit unit. 1 CBT ≈ $0.001 of AI cost.
# Users burn CBT per request based on actual model cost * CBT_MARKUP.
#
# Tier structure:
#   Builder  ($30/mo)  — 25,000 CBT — fast/cheap models included, frontier limited
#   Pro      ($99/mo)  — 100,000 CBT — all models, higher limits
#   Enterprise ($299/mo) — 350,000 CBT — unlimited frontier, priority, white-label

PLAN_CREDITS = {
    "none": 0,          # No plan = no access (must subscribe)
    "builder": 25000,   # $30/mo → 25k CBT
    "pro": 100000,      # $99/mo → 100k CBT
    "enterprise": 350000, # $299/mo → 350k CBT
}

# Which models each plan can access
PLAN_MODEL_ACCESS = {
    "builder": {
        "allowed_tiers": ["fast"],              # Only fast/cheap models
        "frontier_daily_limit": 5,              # 5 frontier calls/day as trial
    },
    "pro": {
        "allowed_tiers": ["fast", "premium", "frontier"],  # All models
        "frontier_daily_limit": 200,
    },
    "enterprise": {
        "allowed_tiers": ["fast", "premium", "frontier"],  # All models
        "frontier_daily_limit": 999999,         # Unlimited
    },
}

# Max tokens per AI call by plan
PLAN_MAX_TOKENS_PER_CALL = {
    "none": 0,
    "builder": 16384,    # 16k output tokens
    "pro": 65536,        # 64k output tokens
    "enterprise": 131072, # 128k output tokens
}

# CBT top-up packs (one-time purchase)
CBT_TOPUP_PACKS = {
    "pack_5k":   {"cbt": 5000,   "price_usd": 5},
    "pack_25k":  {"cbt": 25000,  "price_usd": 20},
    "pack_100k": {"cbt": 100000, "price_usd": 70},
    "pack_500k": {"cbt": 500000, "price_usd": 300},
}

# Stripe configuration
STRIPE_SECRET_KEY = _env("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = _env("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = _env("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID_PLUS = _env("STRIPE_PRICE_ID_PLUS", "")  # Pioneer - $50/mo
STRIPE_PRICE_ID_PRO = _env("STRIPE_PRICE_ID_PRO", "")   # Voyager - $250/mo
STRIPE_ENABLE_TAX = _env("STRIPE_ENABLE_TAX", "false").lower() in ("1","true","yes")
# Usage-based credit tiers (500, 2000, 5000 CBT) — price IDs from Stripe
STRIPE_PRICE_ID_CBT_500 = _env("STRIPE_PRICE_ID_CBT_500", "price_1T2jazBL8lRmwao27DRVcEzX")
STRIPE_PRICE_ID_CBT_2000 = _env("STRIPE_PRICE_ID_CBT_2000", "price_1T2jbMBL8lRmwao2fRFTEwOj")
STRIPE_PRICE_ID_CBT_5000 = _env("STRIPE_PRICE_ID_CBT_5000", "price_1T2jbeBL8lRmwao2E1hoyfP7")
# Legacy (optional)
STRIPE_PRICE_ID_CBT_20 = _env("STRIPE_PRICE_ID_CBT_20", "")
STRIPE_PRICE_ID_CBT_60 = _env("STRIPE_PRICE_ID_CBT_60", "")

# Safety: require explicit opt-in to use live Stripe keys in non-production
STRIPE_ALLOW_LIVE = _env("STRIPE_ALLOW_LIVE", "false").lower() in ("1", "true", "yes")

# CBT / token pack settings
BASE_PLAN_CBT = int(_env("BASE_PLAN_CBT", "25000"))
# Price ID -> CBT amount granted (usage-based tiers)
CBT_PACK_AMOUNTS = {
    STRIPE_PRICE_ID_CBT_500: 500,
    STRIPE_PRICE_ID_CBT_2000: 2000,
    STRIPE_PRICE_ID_CBT_5000: 5000,
}
if STRIPE_PRICE_ID_CBT_20:
    CBT_PACK_AMOUNTS[STRIPE_PRICE_ID_CBT_20] = int(_env("CBT_PACK_20_AMOUNT", "10000"))
if STRIPE_PRICE_ID_CBT_60:
    CBT_PACK_AMOUNTS[STRIPE_PRICE_ID_CBT_60] = int(_env("CBT_PACK_60_AMOUNT", "30000"))

# NOTE: Google OAuth removed by request — no client IDs are read here anymore.
# Google OAuth (re-enable when client ID/secret provided)
GOOGLE_OAUTH_CLIENT_ID = _env("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = _env("GOOGLE_OAUTH_CLIENT_SECRET", "")
# Default redirect URI for OAuth callbacks (can be overridden)
GOOGLE_OAUTH_REDIRECT = _env("GOOGLE_OAUTH_REDIRECT", f"{APP_BASE_URL}{APP_BASE_PATH}/api/auth/oauth/google/callback")

# Simple flag to indicate OAuth is available
OAUTH_ENABLED = bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)

if OAUTH_ENABLED:
    logger.info("OAuth enabled via environment variables (GOOGLE_OAUTH_CLIENT_ID present)")
else:
    logger.warning("OAuth disabled: GOOGLE_OAUTH_CLIENT_ID or GOOGLE_OAUTH_CLIENT_SECRET not set")

# CORS
ALLOWED_ORIGINS = [o.strip() for o in _env("ALLOWED_ORIGINS", f"{APP_BASE_URL},http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]

# File upload limits
MAX_UPLOAD_BYTES = int(_env("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))  # 25MB
MAX_FILE_READ_BYTES = int(_env("MAX_FILE_READ_BYTES", str(200 * 1024)))  # 200KB

# DEV_MODE is now always False at the top...

# Chat and token limits
MAX_CHAT_MESSAGES_CONTEXT = int(_env("MAX_CHAT_MESSAGES_CONTEXT", "20"))
MAX_CONTEXT_TOKENS = int(_env("MAX_CONTEXT_TOKENS", "20000"))  # Safe limit: 20k tokens
TOKENS_PER_CHAR = 0.25  # Rough estimate: ~4 chars per token

# Validation regexes
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_use_stripe = False
if STRIPE_SECRET_KEY:
    if STRIPE_SECRET_KEY.startswith("sk_test_") or STRIPE_SECRET_KEY.startswith("rk_test_"):
        _use_stripe = True
    elif STRIPE_ALLOW_LIVE and (STRIPE_SECRET_KEY.startswith("sk_live_") or STRIPE_SECRET_KEY.startswith("rk_live_")):
        _use_stripe = True

if _use_stripe:
    stripe.api_key = STRIPE_SECRET_KEY
    logger.info(f"[Stripe] Stripe initialized with key {'test' if STRIPE_SECRET_KEY.startswith('sk_test_') else 'live'} mode. Price IDs: PLUS={STRIPE_PRICE_ID_PLUS}, CBT_500/2000/5000 configured.")
else:
    if STRIPE_SECRET_KEY:
        logger.warning(f"[Stripe] Stripe secret key provided but not used: live keys require STRIPE_ALLOW_LIVE=true. STRIPE_ALLOW_LIVE={STRIPE_ALLOW_LIVE}")
    else:
        logger.warning("[Stripe] No Stripe secret key provided. Stripe will not be enabled.")

# Log Stripe configuration status for easier debugging at startup
import sys as _sys
_stripe_status = "enabled" if _use_stripe else "disabled"
print(f"[CodeBot] STRIPE status: {_stripe_status} (key present={'yes' if STRIPE_SECRET_KEY else 'no'})", file=_sys.stderr)

# Netlify deployment configuration
NETLIFY_API_TOKEN = _env("NETLIFY_API_TOKEN", "")
NETLIFY_SITE_ID = _env("NETLIFY_SITE_ID", "")
CUSTOM_DOMAIN_BASE = _env("CUSTOM_DOMAIN_BASE", "nyptidindustries.com")

# Initialize Hugging Face planning client (callable) if token present
HF_CLIENT = None
try:
    if HUGGINGFACEHUB_API_TOKEN:
        # Try automatic discovery of a working planning model when token is present
        try:
            from backend.utils.hf_discovery import whoami, find_working_model
            token = HUGGINGFACEHUB_API_TOKEN
            try:
                info = whoami(token)
                logger.info("HuggingFace token owner: %s", info.get("user", info.get("type", "unknown")))
            except Exception:
                logger.debug("Failed to fetch whoami info for HF token")

            # If an HF_PLANNING_MODEL env var is already set, prefer it; otherwise discover
            env_model = os.environ.get("HF_PLANNING_MODEL") or os.environ.get("PLANNING_MODEL")
            chosen_model = env_model
            if not chosen_model:
                chosen_model = find_working_model(token)
                if chosen_model:
                    # Persist chosen model in the running env for downstream clients
                    os.environ.setdefault("HF_PLANNING_MODEL", chosen_model)
                    logger.info("Discovered working HF planning model: %s", chosen_model)

            HF_CLIENT = get_planning_client(model=chosen_model)
        except Exception as e:
            logger.warning("HF discovery failed: %s", e)
            HF_CLIENT = get_planning_client()
except Exception:
    HF_CLIENT = None

def is_offline_mode() -> bool:
    return OFFLINE_FLAG_FILE.exists() or OFFLINE_MODE_DEFAULT


# --- injected for auth compatibility ---
REFRESH_TOKEN_TTL_DAYS = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "30"))  # 30 days


# --- injected for auth compatibility (do not remove) ---
