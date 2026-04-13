-- Initial schema for CodeBot credit system
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
  user_id uuid NOT NULL,
  plan varchar(50) NOT NULL,
  status varchar(20) NOT NULL,
  current_period_start timestamptz NOT NULL,
  current_period_end timestamptz NOT NULL,
  PRIMARY KEY (user_id)
);

-- purchases table
CREATE TABLE IF NOT EXISTS purchases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  pack_sku varchar(20) NOT NULL,
  amount_usd int NOT NULL,
  cbt_granted int NOT NULL,
  stripe_checkout_session_id varchar(255) UNIQUE,
  stripe_payment_intent_id varchar(255) UNIQUE,
  status varchar(20) NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- credit_ledger
CREATE TABLE IF NOT EXISTS credit_ledger (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  source varchar(50) NOT NULL,
  amount_cbt int NOT NULL,
  expires_at timestamptz NULL,
  metadata jsonb NULL,
  created_at timestamptz DEFAULT now()
);

-- index for fast balance queries
CREATE INDEX IF NOT EXISTS idx_credit_ledger_user ON credit_ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id);

-- uniqueness to prevent duplicate monthly grant for period
CREATE TABLE IF NOT EXISTS monthly_grants (
  user_id uuid NOT NULL,
  period_start timestamptz NOT NULL,
  source varchar(50) NOT NULL,
  UNIQUE(user_id, period_start, source)
);
