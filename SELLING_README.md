Quick guide: Make CodeBot sellable (30-minute checklist)

- Safety first (BYOK / xAI):
  - The backend enforces that Stripe and BYOK live keys are not used accidentally.
  - DEV_MODE disables BYOK by default and sets `BYOK_HARD_LIMIT_DOLLARS=0.0`.
  - If you need to enable live BYOK or live Stripe keys, set explicit environment flags (see below).

- Stripe (use test mode while verifying):
  1. In your environment, set STRIPE_SECRET_KEY to a test key `sk_test_...` and STRIPE_PUBLISHABLE_KEY to `pk_test_...`.
  2. Do NOT set `STRIPE_ALLOW_LIVE=true` unless you intentionally want to enable live charges.
  3. Start the backend and create a Checkout session via the UI; webhook endpoint is at `/codebot/api/billing/webhook`.

- Preventing accidental live charges:
  - `backend/config.py` now requires either a test key (sk_test_) or `STRIPE_ALLOW_LIVE=true` to use a live key.
  - Any backup `.env` files with secrets have been redacted in this repository copy.

- Run locally (development / test mode):

  # Start backend (DEV mode enabled via .dev_mode or DEV_MODE=true)
  python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8080 --reload

  # Start frontend preview (Vite) or serve built app at /codebot/
  cd frontend
  npm install
  npm run build
  npx vite preview --port 4173

  # Preview: http://localhost:4173/codebot/

- Run Playwright E2E (uses dev test-login endpoint; will NOT use BYOK):

  # install browsers (one-time)
  npx playwright install --with-deps

  # run headless
  PLAYWRIGHT_HEADLESS=1 npx playwright test e2e/tests/oauth.spec.ts -g "Dev-login E2E"

- How to enable live Stripe keys (production only):
  1. Place live keys in production environment variables (do NOT commit them).
  2. Set `STRIPE_ALLOW_LIVE=true` in the production environment to explicitly opt in.
  3. Ensure TLS (HTTPS) termination in front of the app and secure secrets in your secret manager.

- Next recommended steps to finish productizing:
  - Add production Stripe webhook verification + deploy behind TLS.
  - Add CI that runs Playwright E2E with `DEV_MODE=true` so tests never hit live BYOK or live Stripe.
  - Add monitoring/alerting and validate legal/privacy for sale.

If you want, I can add a small GitHub Actions workflow that builds the frontend, starts the backend with DEV_MODE=true, and runs the Playwright E2E tests next. Would you like me to add that now?