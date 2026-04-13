-- src/db/migrations/002_update_credit_system.sql

ALTER TABLE subscriptions ALTER COLUMN plan TYPE TEXT;
ALTER TABLE subscriptions ALTER COLUMN status TYPE TEXT;

-- Update credit_ledger for new CBT logic (no schema change needed if already integer)

-- Update purchases for new pack values (no schema change needed if already integer)

-- Optionally, add a feature flag for PRO_250
-- (No DB change needed, handled in config)
