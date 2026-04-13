-- Make purchases.user_id accept non-UUID identifiers (e.g. "dev-user-1")
ALTER TABLE public.purchases
  ALTER COLUMN user_id TYPE text
  USING user_id::text;

DROP INDEX IF EXISTS public.idx_purchases_user;
CREATE INDEX idx_purchases_user ON public.purchases(user_id);
