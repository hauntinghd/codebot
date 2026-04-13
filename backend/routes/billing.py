"""Billing routes - Stripe checkout, portal, webhook."""
from __future__ import annotations

import logging
import sqlite3
from typing import Any, Dict, Optional

import stripe
from fastapi import Depends, FastAPI, HTTPException, Request
from prometheus_client import Counter

from backend.auth import current_user
from backend.config import (
    API_PREFIX,
    APP_BASE_PATH,
    APP_BASE_URL,
    STRIPE_PRICE_ID_PLUS,
    STRIPE_PRICE_ID_PRO,
    STRIPE_WEBHOOK_SECRET,
    STRIPE_PRICE_ID_CBT_500,
    STRIPE_PRICE_ID_CBT_2000,
    STRIPE_PRICE_ID_CBT_5000,
    STRIPE_PRICE_ID_CBT_20,
    STRIPE_PRICE_ID_CBT_60,
)
from backend.credits import initialize_user_credits
from backend.tokens import add_user_tokens
from backend.config import CBT_PACK_AMOUNTS, BASE_PLAN_CBT
from backend.database import _now, db
from backend.models import CheckoutOut, CreateCheckoutIn, PortalOut

logger = logging.getLogger("codebot")


def _ensure_stripe_initialized():
    """Ensure stripe.api_key is set at runtime if config provides a usable key.

    Some deployment setups may import modules in different orders; if
    `stripe.api_key` was not set during import-time configuration, try to
    initialize it lazily from the config values before making API calls.
    """
    try:
        import os as _os
        import stripe as _stripe
        if not getattr(_stripe, 'api_key', None):
            key = _os.getenv('STRIPE_SECRET_KEY', '')
            allow_live = str(_os.getenv('STRIPE_ALLOW_LIVE', 'false')).lower() in ('1', 'true', 'yes')
            if key:
                if key.startswith('sk_test_') or key.startswith('rk_test_'):
                    _stripe.api_key = key
                    logger.info('[Stripe] Initialized stripe.api_key from env (test key)')
                elif allow_live and (key.startswith('sk_live_') or key.startswith('rk_live_')):
                    _stripe.api_key = key
                    logger.info('[Stripe] Initialized stripe.api_key from env (live key)')
    except Exception:
        logger.debug('Failed to lazily initialize Stripe API key', exc_info=True)

# Prometheus metrics for billing/webhook
WEBHOOK_SIGNATURE_FAILURES = Counter(
    "codebot_billing_webhook_signature_failures_total",
    "Total number of Stripe webhook signature verification failures",
)
WEBHOOK_EVENTS_PROCESSED = Counter(
    "codebot_billing_webhook_events_processed_total",
    "Total number of Stripe webhook events successfully processed",
)
WEBHOOK_EVENTS_ERRORS = Counter(
    "codebot_billing_webhook_events_errors_total",
    "Total number of Stripe webhook events that raised an internal error",
)


def _plan_to_price(plan: str) -> str:
    """Map plan name to Stripe price ID."""
    p = (plan or "").strip().lower()
    import os as _os
    plus = STRIPE_PRICE_ID_PLUS or _os.getenv('STRIPE_PRICE_ID_PLUS', '')
    pro = STRIPE_PRICE_ID_PRO or _os.getenv('STRIPE_PRICE_ID_PRO', '')
    cbt20 = STRIPE_PRICE_ID_CBT_20 or _os.getenv('STRIPE_PRICE_ID_CBT_20', '')
    cbt60 = STRIPE_PRICE_ID_CBT_60 or _os.getenv('STRIPE_PRICE_ID_CBT_60', '')

    if p in ("plus", "pioneer", "builder"):
        return plus
    if p in ("pro", "voyager"):
        return pro
    if p in ("enterprise",):
        return _os.getenv("STRIPE_PRICE_ID_ENTERPRISE", "")
    if p in ("pack20", "pack_20", "cbt20", "cbt_20"):
        return cbt20
    if p in ("pack60", "pack_60", "cbt60", "cbt_60"):
        return cbt60
    # Top-up packs
    if p in ("pack_5k",):
        return _os.getenv("STRIPE_PRICE_ID_CBT_5K", "")
    if p in ("pack_25k",):
        return _os.getenv("STRIPE_PRICE_ID_CBT_25K", "")
    if p in ("pack_100k",):
        return _os.getenv("STRIPE_PRICE_ID_CBT_100K", "")
    if p in ("pack_500k",):
        return _os.getenv("STRIPE_PRICE_ID_CBT_500K", "")
    return ""


def _update_user_subscription_from_stripe(
    user_id: str,
    *,
    customer_id: Optional[str],
    subscription_id: Optional[str],
) -> None:
    """Update user subscription from Stripe webhook event."""
    if not stripe.api_key:
        return
    if not subscription_id:
        return

    sub = stripe.Subscription.retrieve(subscription_id)
    status = str(sub.get("status") or "none")
    cpe = int(sub.get("current_period_end") or 0)
    plan = "none"

    try:
        items = sub.get("items", {}).get("data", []) if isinstance(sub.get("items"), dict) else []
        price = items[0].get("price", {}).get("id") if items else None
        # Map back to plan name for your UI
        if price == STRIPE_PRICE_ID_PLUS:
            plan = "plus"
        elif price == STRIPE_PRICE_ID_PRO:
            plan = "pro"
    except Exception:
        plan = "none"

    with db() as conn:
        conn.execute(
            """
            UPDATE users
            SET stripe_customer_id = COALESCE(?, stripe_customer_id),
                stripe_subscription_id = COALESCE(?, stripe_subscription_id),
                subscription_status = ?,
                current_period_end = ?,
                plan = ?
            WHERE id = ?
            """,
            (customer_id, subscription_id, status, cpe, plan, user_id),
        )

    # Initialize credits for new subscription
    if status in ("active", "trialing") and plan != "none":
        initialize_user_credits(user_id, plan)


def register_routes(api: FastAPI):
    """Register billing routes."""

    @api.post(f"{API_PREFIX}/billing/create-checkout-session", response_model=CheckoutOut)
    async def create_checkout_session(
        payload: CreateCheckoutIn,
        u: sqlite3.Row = Depends(current_user),
    ) -> CheckoutOut:
        _ensure_stripe_initialized()
        if not stripe.api_key:
            raise HTTPException(status_code=500, detail="Stripe is not configured. Please contact support.")

        price_id = _plan_to_price(payload.plan)
        if not price_id:
            raise HTTPException(
                status_code=400,
                detail=f"Plan '{payload.plan}' is not available. Please contact support or try a different plan.",
            )

        user_id = str(u["id"])
        email = str(u["email"])
        success_url = f"{APP_BASE_URL}{APP_BASE_PATH}/?checkout=success"
        cancel_url = f"{APP_BASE_URL}{APP_BASE_PATH}/?checkout=cancel"

        # Create Checkout Session
        try:
            # Support optional automatic tax calculation if enabled
            from backend.config import STRIPE_ENABLE_TAX
            session_kwargs = dict(
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=user_id,
                customer_email=email,
                metadata={"user_id": user_id, "plan": payload.plan.lower()},
            )
            if str(STRIPE_ENABLE_TAX).lower() in ("1", "true", "yes"):
                session_kwargs["automatic_tax"] = {"enabled": True}

            sess = stripe.checkout.Session.create(**session_kwargs)
            return CheckoutOut(url=str(sess.url))
        except Exception as e:
            error_type = type(e).__name__
            if "Stripe" in error_type or "stripe" in str(type(e)).lower():
                raise HTTPException(status_code=502, detail=f"Payment processing error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    @api.post(f"{API_PREFIX}/_internal/billing/create-checkout-session", response_model=CheckoutOut)
    async def create_checkout_session_internal(payload: CreateCheckoutIn, u: sqlite3.Row = Depends(current_user)) -> CheckoutOut:
        return await create_checkout_session(payload, u)

    # Usage-based: credits 500, 2000, 5000 only (price IDs from Stripe)
    _CREDITS_TO_PRICE = {
        500: STRIPE_PRICE_ID_CBT_500,
        2000: STRIPE_PRICE_ID_CBT_2000,
        5000: STRIPE_PRICE_ID_CBT_5000,
    }

    @api.post(f"{API_PREFIX}/billing/credits/checkout", response_model=CheckoutOut)
    async def create_credits_checkout(payload: Dict[str, Any], u: sqlite3.Row = Depends(current_user)) -> CheckoutOut:
        """Create a one-time checkout session to purchase CBT credits (500, 2000, 5000). Usage-based only."""
        _ensure_stripe_initialized()
        if not stripe.api_key:
            raise HTTPException(status_code=500, detail="Stripe is not configured. Please contact support.")

        credits = payload.get("credits")
        if credits is not None:
            try:
                credits = int(credits)
            except (TypeError, ValueError):
                credits = None
        if credits not in _CREDITS_TO_PRICE:
            raise HTTPException(
                status_code=400,
                detail="Invalid credits. Use 500, 2000, or 5000.",
            )

        price_id = _CREDITS_TO_PRICE[credits]
        if not price_id:
            raise HTTPException(status_code=500, detail="Credit tier not configured. Please contact support.")

        success_url = f"{APP_BASE_URL}{APP_BASE_PATH}/account?checkout=success"
        cancel_url = f"{APP_BASE_URL}{APP_BASE_PATH}/account/upgrade"

        try:
            sess = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="payment",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=str(u["id"]),
                customer_email=str(u.get("email") or ""),
                metadata={"user_id": str(u["id"]), "pack_sku": f"CREDITS_{credits}", "cbt": str(credits)},
            )
            return CheckoutOut(url=str(sess.url))
        except Exception as e:
            error_type = type(e).__name__
            if "Stripe" in error_type or "stripe" in str(type(e)).lower():
                raise HTTPException(status_code=502, detail=f"Payment processing error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    # Also expose an internal path that bypasses the Node proxy so the Python
    # backend can create CBT pack checkout sessions directly if needed.
    @api.post(f"{API_PREFIX}/_internal/billing/credits/checkout", response_model=CheckoutOut)
    async def create_credits_checkout_internal(payload: Dict[str, Any], u: sqlite3.Row = Depends(current_user)) -> CheckoutOut:
        return await create_credits_checkout(payload, u)

    @api.get(f"{API_PREFIX}/billing/portal", response_model=PortalOut)
    async def billing_portal(u: sqlite3.Row = Depends(current_user)) -> PortalOut:
        _ensure_stripe_initialized()
        if not stripe.api_key:
            raise HTTPException(status_code=500, detail="Stripe is not configured")

        cust_id = str(u["stripe_customer_id"] or "")
        if not cust_id:
            # Auto-create Stripe customer for this user
            try:
                customer = stripe.Customer.create(
                    email=str(u["email"]),
                    metadata={"user_id": str(u["id"]), "source": "codebot"},
                )
                cust_id = str(customer.id)
                with db() as conn:
                    conn.execute("UPDATE users SET stripe_customer_id = ? WHERE id = ?", (cust_id, str(u["id"])))
                logger.info(f"[Stripe] Auto-created customer {cust_id} for user {u['id']}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Could not create Stripe customer: {e}")

        return_url = f"{APP_BASE_URL}{APP_BASE_PATH}/"
        try:
            ps = stripe.billing_portal.Session.create(customer=cust_id, return_url=return_url)
            return PortalOut(url=str(ps.url))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Stripe error: {str(e)}")

    @api.post(f"{API_PREFIX}/billing/webhook")
    async def stripe_webhook(request: Request) -> Dict[str, Any]:
        if not STRIPE_WEBHOOK_SECRET:
            raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")

        payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")

        try:
            event = stripe.Webhook.construct_event(
                payload=payload, sig_header=sig_header, secret=STRIPE_WEBHOOK_SECRET
            )
        except Exception:
            WEBHOOK_SIGNATURE_FAILURES.inc()
            raise HTTPException(status_code=400, detail="Invalid Stripe signature")

        etype = str(event.get("type") or "")
        obj = event.get("data", {}).get("object", {})

        # Common identifiers
        user_id = None
        customer_id = None
        subscription_id = None

        # checkout.session.completed includes metadata we set
        if etype == "checkout.session.completed":
            user_id = (obj.get("metadata") or {}).get("user_id") or obj.get("client_reference_id")
            customer_id = obj.get("customer")
            subscription_id = obj.get("subscription")

            if user_id:
                _update_user_subscription_from_stripe(
                    str(user_id), customer_id=str(customer_id or ""), subscription_id=str(subscription_id or "")
                )

            # Attempt to detect one-time token pack purchases or subscription price
            try:
                session_id = obj.get("id") or obj.get("session")
                if session_id and stripe.api_key:
                    sess = stripe.checkout.Session.retrieve(session_id, expand=["line_items"])
                    # Determine purchased price id
                    price_id = None
                    try:
                        items = getattr(sess, "line_items", None)
                        if items and getattr(items, "data", None):
                            price_id = items.data[0].get("price", {}).get("id")
                    except Exception:
                        price_id = None

                    # If this was a subscription to the base $50 plan, allocate CBT
                    if price_id == STRIPE_PRICE_ID_PLUS and user_id:
                        try:
                            add_user_tokens(str(user_id), int(BASE_PLAN_CBT), "Monthly plan CBT allocation")
                        except Exception:
                            logger.exception("Failed to add base plan CBT for user %s", user_id)

                    # If this was a one-time CBT pack, allocate tokens
                    if price_id and price_id in CBT_PACK_AMOUNTS and user_id:
                        amount = int(CBT_PACK_AMOUNTS.get(price_id) or 0)
                        if amount > 0:
                            try:
                                add_user_tokens(str(user_id), amount, f"CBT pack purchase: +{amount} CBT")
                            except Exception:
                                logger.exception("Failed to add CBT pack tokens for user %s", user_id)
            except Exception:
                logger.debug("Failed to inspect checkout session for CBT allocation", exc_info=True)

        try:
            # Count successful processing of the event
            WEBHOOK_EVENTS_PROCESSED.inc()
        except Exception:
            WEBHOOK_EVENTS_ERRORS.inc()

        # subscription updates/deletes
        if etype in ("customer.subscription.updated", "customer.subscription.deleted", "customer.subscription.created"):
            subscription_id = obj.get("id")
            customer_id = obj.get("customer")
            # Find user by customer id if we don't have user_id
            if customer_id:
                with db() as conn:
                    row = conn.execute(
                        "SELECT id FROM users WHERE stripe_customer_id = ?", (str(customer_id),)
                    ).fetchone()
                    if row:
                        user_id = str(row["id"])
            if user_id and subscription_id:
                _update_user_subscription_from_stripe(
                    user_id, customer_id=str(customer_id or ""), subscription_id=str(subscription_id or "")
                )

        # invoice events can signal paid/failed
        if etype in ("invoice.paid", "invoice.payment_failed"):
            customer_id = obj.get("customer")
            subscription_id = obj.get("subscription")
            if customer_id:
                with db() as conn:
                    row = conn.execute(
                        "SELECT id FROM users WHERE stripe_customer_id = ?", (str(customer_id),)
                    ).fetchone()
                    if row:
                        user_id = str(row["id"])
            if user_id and subscription_id:
                _update_user_subscription_from_stripe(
                    user_id, customer_id=str(customer_id or ""), subscription_id=str(subscription_id or "")
                )

        return {"ok": True, "type": etype}


    @api.post(f"{API_PREFIX}/billing/refund")
    async def refund_payment(payload: Dict[str, Any], u: sqlite3.Row = Depends(current_user)) -> Dict[str, Any]:
        """Admin endpoint to issue refunds. Accepts `charge_id` or `payment_intent` and optional `amount` in cents."""
        # Require admin
        try:
            # Defensive access: `u` may be a dict-like or sqlite3.Row
            if hasattr(u, "get"):
                is_admin_flag = int(u.get("is_admin") or 0)
            else:
                is_admin_flag = int(u["is_admin"] if "is_admin" in u.keys() else 0)
            if is_admin_flag != 1:
                raise HTTPException(status_code=403, detail="Admin privileges required")
        except Exception:
            raise HTTPException(status_code=403, detail="Admin privileges required")

        charge_id = payload.get("charge_id") or payload.get("payment_intent")
        amount = payload.get("amount")  # optional amount in cents
        if not charge_id:
            raise HTTPException(status_code=400, detail="`charge_id` or `payment_intent` is required")

        try:
            # If payment_intent provided, refund by payment_intent
            kwargs = {}
            if isinstance(amount, int) and amount > 0:
                kwargs["amount"] = int(amount)

            if payload.get("payment_intent"):
                res = stripe.Refund.create(payment_intent=str(charge_id), **kwargs)
            else:
                res = stripe.Refund.create(charge=str(charge_id), **kwargs)
            return {"ok": True, "refund": dict(res)}
        except Exception as e:
            logger.exception("Refund failed: %s", e)
            raise HTTPException(status_code=502, detail=f"Refund failed: {e}")

