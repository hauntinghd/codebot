from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


BASIC = "basic"
PRO = "pro"
ELITE = "elite"


@dataclass
class SubscriptionInfo:
    active: bool
    plan: str


def _normalize_plan(plan: Any) -> str:
    p = str(plan or BASIC).strip().lower()
    # allow variants
    if p in ("starter", "standard"):
        return BASIC
    if p in ("premium",):
        return PRO
    return p


def get_subscription_info(user: Optional[Dict[str, Any]] = None, *, dev_mode: bool = True) -> SubscriptionInfo:
    """
    Centralized subscription read. Uses the user dict/row provided by auth layer.
    dev_mode defaults to True because your logs show DEV_MODE=True.
    """
    if not user:
        return SubscriptionInfo(active=bool(dev_mode), plan=BASIC)

    plan = _normalize_plan(user.get("plan") if isinstance(user, dict) else getattr(user, "plan", BASIC))
    is_admin = 0
    try:
        is_admin = int(user.get("is_admin", 0)) if isinstance(user, dict) else int(getattr(user, "is_admin", 0))
    except Exception:
        is_admin = 0

    # If admin: always active.
    if is_admin == 1:
        return SubscriptionInfo(active=True, plan=plan or BASIC)

    # Subscription flags commonly used
    active_flag = None
    if isinstance(user, dict):
        active_flag = user.get("is_subscribed", None)
        if active_flag is None:
            active_flag = user.get("subscribed", None)
        if active_flag is None:
            active_flag = user.get("subscription_active", None)

    if active_flag is None:
        # In dev mode allow, otherwise require explicit true.
        return SubscriptionInfo(active=bool(dev_mode), plan=plan or BASIC)

    try:
        active = bool(int(active_flag))
    except Exception:
        active = bool(active_flag)

    return SubscriptionInfo(active=active, plan=plan or BASIC)


def has_min_plan(user: Optional[Dict[str, Any]] = None, plan: str = BASIC, *, dev_mode: bool = True) -> Tuple[bool, str]:
    """
    Returns (ok, actual_plan).
    """
    info = get_subscription_info(user, dev_mode=dev_mode)
    if not info.active:
        return False, info.plan

    order = {BASIC: 0, PRO: 1, ELITE: 2}
    want = order.get(_normalize_plan(plan), 0)
    have = order.get(_normalize_plan(info.plan), 0)
    return have >= want, info.plan


def is_subscribed(user: Optional[Dict[str, Any]] = None, *, dev_mode: bool = True) -> bool:
    """
    Legacy name used in some codebases.
    """
    return bool(get_subscription_info(user, dev_mode=dev_mode).active)


# -------------------------------------------------------------------
# Compatibility alias expected by backend/routes/chat.py
# -------------------------------------------------------------------
def is_active_subscription(user: Optional[Dict[str, Any]] = None, *, dev_mode: bool = True) -> bool:
    return bool(get_subscription_info(user, dev_mode=dev_mode).active)
