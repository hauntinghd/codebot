#!/usr/bin/env python3
"""Test Stripe webhook handling by mocking Stripe SDK calls and invoking the FastAPI route.

This script runs inside the repo and uses FastAPI's TestClient to call the webhook
endpoint while monkeypatching `stripe.Webhook.construct_event` and
`stripe.Subscription.retrieve` to avoid external network calls.
"""
import json
import time
import os
from dotenv import load_dotenv

# Ensure .env is loaded into the environment for tests
load_dotenv('/home/omatic657/aicoderbot/.env', override=True)

from backend.config import APP_BASE_PATH, STRIPE_PRICE_ID_PLUS
from backend.database import db
import stripe
from fastapi.testclient import TestClient

# Import the FastAPI app
from backend.main import api

TEST_USER_ID = "test_webhook_user_1"
TEST_EMAIL = "test_webhook_user_1@example.com"

# Ensure test user exists
with db() as conn:
    row = conn.execute("SELECT id FROM users WHERE id = ?", (TEST_USER_ID,)).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO users (id, email, pw_hash, created_at, is_admin) VALUES (?, ?, ?, ?, 0)",
            (TEST_USER_ID, TEST_EMAIL, "pwhash", int(time.time())),
        )
        print(f"Inserted test user {TEST_USER_ID}")
    else:
        print(f"Test user {TEST_USER_ID} already exists")

# Prepare a fake Stripe event (checkout.session.completed)
fake_event = {
    "id": "evt_test_123",
    "type": "checkout.session.completed",
    "data": {
        "object": {
            "id": "cs_test_123",
            "client_reference_id": TEST_USER_ID,
            "customer": "cus_test_123",
            "subscription": "sub_test_123",
            "metadata": {"user_id": TEST_USER_ID, "plan": "plus"},
        }
    },
}

# Monkeypatch Stripe signature verification to return our fake event
def fake_construct_event(payload, sig_header, secret):
    # payload is bytes; ignore and return our fake event dict
    return fake_event

# Monkeypatch Subscription.retrieve to return a fake subscription matching the plus price
def fake_subscription_retrieve(sub_id):
    return {
        "id": sub_id,
        "status": "active",
        "current_period_end": int(time.time()) + 30 * 24 * 3600,
        "items": {"data": [{"price": {"id": STRIPE_PRICE_ID_PLUS}}]},
    }

stripe.Webhook.construct_event = fake_construct_event
stripe.Subscription.retrieve = fake_subscription_retrieve

client = TestClient(api)

resp = client.post(f"{APP_BASE_PATH}/api/billing/webhook", data=json.dumps(fake_event), headers={"stripe-signature": "t=123,v1=fake"})
print("Status code:", resp.status_code)
try:
    print("Response:", resp.json())
except Exception:
    print("Response text:", resp.text)

# Verify DB update
with db() as conn:
    row = conn.execute("SELECT id, plan, stripe_customer_id, stripe_subscription_id, subscription_status FROM users WHERE id = ?", (TEST_USER_ID,)).fetchone()
    if row:
        print("User row after webhook:", dict(row))
    else:
        print("User not found after webhook test")

# Clean-up: leave the test user (optional)
# Uncomment to remove the test user after verification
# with db() as conn:
#     conn.execute("DELETE FROM users WHERE id = ?", (TEST_USER_ID,))
#     conn.execute("DELETE FROM user_credits WHERE user_id = ?", (TEST_USER_ID,))
#     print("Cleaned up test user")
