"""Stripe integration for CodeBot subscriptions.

Plans:
- Pioneer ($50/mo): 10,000 credits/mo + rollover
- Voyager ($250/mo): 75,000 credits/mo + unlimited rollover
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import stripe

logger = logging.getLogger("codebot")

# Plan configurations
PLANS = {
    "pioneer": {
        "name": "Pioneer",
        "description": "Team velocity boost",
        "price_usd": 50,
        "credits_per_month": 10000,
        "credits_rollover": True,
        "features": [
            "10,000 credits/mo + rollover",
            "Analyze up to 50K LOC per project (optimized context pipeline)",
            "Priority queue + hot reload previews",
            "BYOK with zero platform credits (per-call audit logs)",
            "Multi-file project analysis + reports",
            "Offline-first enforced: optional doc lookups only when approved",
        ],
    },
    "voyager": {
        "name": "Voyager",
        "description": "Enterprise-grade scale",
        "price_usd": 250,
        "credits_per_month": 75000,
        "credits_rollover": True,
        "features": [
            "75,000 credits/mo + unlimited rollover",
            "Full codebase ingestion (200K+ LOC) with optimized context pipeline",
            "Unlimited uploads + concurrency slots",
            "Architecture review + automation docs",
            "Dedicated support + early features + SSO ready",
        ],
    },
}

class StripeManager:
    """Manage Stripe subscriptions and payments."""

    def __init__(self, api_key: str):
        """Initialize Stripe manager."""
        if not api_key:
            logger.warning("Stripe API key not configured")
            self.enabled = False
            return

        stripe.api_key = api_key
        self.enabled = True
        logger.info("Stripe initialized successfully")

    def create_product(
        self, plan_key: str, idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a Stripe product for a plan."""
        if not self.enabled:
            raise RuntimeError("Stripe not configured")

        plan = PLANS.get(plan_key)
        if not plan:
            raise ValueError(f"Unknown plan: {plan_key}")

        try:
            product = stripe.Product.create(
                name=plan["name"],
                description=plan["description"],
                type="service",
                metadata={
                    "plan_key": plan_key,
                    "credits_per_month": plan["credits_per_month"],
                    "credits_rollover": str(plan["credits_rollover"]),
                },
                idempotency_key=idempotency_key,
            )
            logger.info(f"Created Stripe product for {plan_key}: {product.id}")
            return product
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create product: {e}")
            raise

    def create_price(
        self,
        product_id: str,
        plan_key: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Stripe price (recurring) for a product."""
        if not self.enabled:
            raise RuntimeError("Stripe not configured")

        plan = PLANS.get(plan_key)
        if not plan:
            raise ValueError(f"Unknown plan: {plan_key}")

        try:
            price = stripe.Price.create(
                product=product_id,
                unit_amount=int(plan["price_usd"] * 100),  # Convert to cents
                currency="usd",
                recurring={
                    "interval": "month",
                    "interval_count": 1,
                },
                metadata={
                    "plan_key": plan_key,
                },
                idempotency_key=idempotency_key,
            )
            logger.info(f"Created Stripe price for {plan_key}: {price.id}")
            return price
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create price: {e}")
            raise

    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a subscription for a customer."""
        if not self.enabled:
            raise RuntimeError("Stripe not configured")

        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                metadata=metadata or {},
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"],
            )
            logger.info(f"Created subscription for customer {customer_id}: {subscription.id}")
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            raise

    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel a subscription."""
        if not self.enabled:
            raise RuntimeError("Stripe not configured")

        try:
            subscription = stripe.Subscription.delete(subscription_id)
            logger.info(f"Cancelled subscription: {subscription_id}")
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise

    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription details."""
        if not self.enabled:
            raise RuntimeError("Stripe not configured")

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve subscription: {e}")
            raise

    def create_customer(
        self,
        email: str,
        user_id: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a Stripe customer."""
        if not self.enabled:
            raise RuntimeError("Stripe not configured")

        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={
                    "user_id": user_id,
                    **(metadata or {}),
                },
            )
            logger.info(f"Created Stripe customer for {user_id}: {customer.id}")
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create customer: {e}")
            raise

    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        """Create a checkout session."""
        if not self.enabled:
            raise RuntimeError("Stripe not configured")

        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
            )
            logger.info(f"Created checkout session: {session.id}")
            return session
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise

    def verify_webhook(self, payload: bytes, signature: str, webhook_secret: str) -> Dict[str, Any]:
        """Verify and parse a webhook event."""
        if not self.enabled:
            raise RuntimeError("Stripe not configured")

        try:
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
            return event
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error(f"Webhook verification failed: {e}")
            raise

    @staticmethod
    def get_plan_details(plan_key: str) -> Dict[str, Any]:
        """Get plan details (public)."""
        plan = PLANS.get(plan_key)
        if not plan:
            return {}

        return {
            "key": plan_key,
            "name": plan["name"],
            "description": plan["description"],
            "price_usd": plan["price_usd"],
            "credits_per_month": plan["credits_per_month"],
            "credits_rollover": plan["credits_rollover"],
            "features": plan["features"],
        }

    @staticmethod
    def list_plans() -> Dict[str, Dict[str, Any]]:
        """List all available plans."""
        return {key: StripeManager.get_plan_details(key) for key in PLANS.keys()}


__all__ = ["StripeManager", "PLANS"]
