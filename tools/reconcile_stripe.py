#!/usr/bin/env python3
"""Reconcile Stripe subscriptions with local DB.

This script lists active subscriptions from Stripe and attempts to match
customers to local users via `stripe_customer_id`. It prints mismatches
and optionally updates the DB when run with `--apply`.

Requires STRIPE_SECRET_KEY in environment or .env.
"""
import os
import stripe
from backend.database import db
from dotenv import load_dotenv

load_dotenv('/home/omatic657/aicoderbot/.env')
STRIPE_KEY = os.getenv('STRIPE_SECRET_KEY')
if not STRIPE_KEY:
    print('STRIPE_SECRET_KEY not set in environment or .env')
    raise SystemExit(1)
stripe.api_key = STRIPE_KEY

from argparse import ArgumentParser

p = ArgumentParser()
p.add_argument('--apply', action='store_true', help='Apply updates to local DB where safe')
args = p.parse_args()

print('Fetching Stripe subscriptions...')
subs = stripe.Subscription.list(limit=100)

mismatches = []
updates = []

for s in subs.auto_paging_iter():
    sub_id = s.id
    status = s.status
    cust = getattr(s, 'customer', None)
    items = s.get('items', {}).get('data', []) if isinstance(s.get('items'), dict) else []
    price = items[0].get('price', {}).get('id') if items else None
    plan = 'none'
    from backend.config import STRIPE_PRICE_ID_PLUS, STRIPE_PRICE_ID_PRO
    if price == STRIPE_PRICE_ID_PLUS:
        plan = 'plus'
    elif price == STRIPE_PRICE_ID_PRO:
        plan = 'pro'

    with db() as conn:
        row = conn.execute('SELECT id, stripe_customer_id, plan FROM users WHERE stripe_customer_id = ?', (str(cust),)).fetchone()
        if row:
            uid = row['id']
            if row['plan'] != plan or row['subscription_status'] != status:
                print(f'(Stripe) {sub_id} customer {cust} -> local user {uid}: status {status} plan {plan} differs (local plan {row["plan"]})')
                mismatches.append((sub_id, cust, uid, status, plan))
                if args.apply:
                    conn.execute('UPDATE users SET subscription_status = ?, plan = ?, stripe_subscription_id = ? WHERE id = ?', (status, plan, sub_id, uid))
                    updates.append(uid)
        else:
            print(f'(Stripe) {sub_id} customer {cust} has no matching local user')
            mismatches.append((sub_id, cust, None, status, plan))

print('\nSummary:')
print(' Total subscriptions checked:', len(list(subs)))
print(' Mismatches found:', len(mismatches))
if args.apply:
    print(' Applied updates for users:', updates)
else:
    print(' Run with --apply to update local DB where safe')
