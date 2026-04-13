#!/usr/bin/env python3
"""Set and encrypt a BYOK API key for a user.

Usage:
  python tools/set_byok_key.py --email owner@example.com --key xai-XXXX --provider grok

This script will locate the user by email (or the first admin user if no email provided),
encrypt the provided API key using the repository's `backend.byok.encrypt_api_key` and
store it into the `users` table as `api_key_encrypted` and `api_key_provider`.

WARNING: This bypasses the HTTP-level plan checks and requires that you trust the script.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.byok import encrypt_api_key, validate_api_key_format
from backend.database import db


def find_user_by_email(email: str):
    with db() as conn:
        row = conn.execute("SELECT id, email, is_admin FROM users WHERE email = ?", (email,)).fetchone()
        return row


def find_first_admin():
    with db() as conn:
        row = conn.execute("SELECT id, email, is_admin FROM users WHERE is_admin = 1 LIMIT 1").fetchone()
        return row


def set_key_for_user(user_id, encrypted_key: str, provider: str):
    with db() as conn:
        conn.execute(
            "UPDATE users SET api_key_encrypted = ?, api_key_provider = ? WHERE id = ?",
            (encrypted_key, provider, user_id),
        )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--email", help="User email to assign BYOK to (optional)")
    p.add_argument("--key", required=True, help="API key to store (your xAI key)")
    p.add_argument("--provider", default="grok", help="Provider name (default: grok)")
    args = p.parse_args()

    provider = args.provider.lower()
    api_key = args.key.strip()

    if not validate_api_key_format(api_key, provider):
        print("Warning: API key format may be invalid for provider", provider)

    target = None
    if args.email:
        target = find_user_by_email(args.email)
        if not target:
            print(f"No user found with email {args.email}")
            sys.exit(2)
    else:
        target = find_first_admin()
        if not target:
            print("No admin user found; please provide --email for the target user")
            sys.exit(2)

    encrypted = encrypt_api_key(api_key)
    # target may be sqlite3.Row or tuple; handle both
    try:
        user_id = target["id"]
        email = target["email"]
    except Exception:
        # fallback for tuple-like result
        user_id = target[0]
        email = target[1] if len(target) > 1 else None

    set_key_for_user(user_id, encrypted, provider)
    print(f"Successfully set BYOK for user {email} (provider={provider})")


if __name__ == "__main__":
    main()
