"""
backend/helpers/internet_policy.py

Minimal policy gate for "internet access" / "browsing" behavior used by chat routes.

Goals:
- Must exist so imports never crash startup.
- Provide conservative, predictable defaults.
- Allow future expansion without changing call sites.

The chat route expects:
- check_internet_policy(...)
- validate_response(...)

This module intentionally does not enforce anything heavy; it returns structured guidance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class InternetPolicyResult:
    allowed: bool = True
    reason: str = ""
    # Optional hints the caller can use (e.g., UI toggle / logging)
    mode: str = "allow"  # allow | deny | restricted


def check_internet_policy(
    *,
    user: Optional[Dict[str, Any]] = None,
    route: str = "",
    requested: bool = False,
    dev_mode: bool = True,
) -> InternetPolicyResult:
    """
    Decide whether internet/browsing should be allowed.

    Conservative logic:
    - In DEV_MODE: allow by default.
    - If caller explicitly requests: allow by default.
    - If user is missing: allow (we don't want to block boot/usage).
    You can later enforce plan-based restrictions here.
    """
    # If you later implement plan gating, this is where it belongs.
    if dev_mode:
        return InternetPolicyResult(allowed=True, reason="dev_mode", mode="allow")

    # Example placeholder for future:
    # if user and user.get("plan") in {"free"} and requested:
    #     return InternetPolicyResult(allowed=False, reason="plan_restricted", mode="deny")

    return InternetPolicyResult(allowed=True, reason="default_allow", mode="allow")


def validate_response(
    text: str,
    *,
    policy: Optional[InternetPolicyResult] = None,
) -> str:
    """
    Validate/sanitize a model response.

    For now: no-op passthrough. This exists to match expected call sites.
    If you later add rules (e.g., redaction), implement them here.
    """
    # If you later want to enforce "no URLs" or redact secrets, do it here.
    return text or ""
