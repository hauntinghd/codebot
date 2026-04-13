Safe enabling of live Stripe keys and BYOK (production only)

1) NEVER commit any live secrets to the repository. Use a secrets manager or environment variables on the server.

2) Stripe live keys:
   - Set `STRIPE_SECRET_KEY` to the live `sk_live_...` value in your production environment only.
   - Set `STRIPE_PUBLISHABLE_KEY` to the live `pk_live_...` value.
   - Set `STRIPE_ALLOW_LIVE=true` in the production environment to explicitly opt in to using live keys.
   - Ensure `STRIPE_WEBHOOK_SECRET` is set to the live webhook secret in production and configure your webhook receiver URL to use HTTPS.

3) BYOK / xAI providers:
   - The backend respects `DEFAULT_BYOK_PROVIDER` and `BYOK_HARD_LIMIT_DOLLARS`.
   - To enable BYOK in production, set `DEFAULT_BYOK_PROVIDER` (e.g., `grok`) and a conservative `BYOK_HARD_LIMIT_DOLLARS` (e.g., 50.0), monitor usage carefully.
   - For additional safety, only allow BYOK from a managed server role or set `BYOK_ALLOW_LIVE=true` in production (implement centrally in your deployment controller).

4) Deployment checklist before turning on live billing:
   - TLS configured with valid certs and HSTS.
   - Secrets stored in a secret manager and not present in repo.
   - Webhooks configured and verified via Stripe dashboard.
   - Monitoring/alerts for billing anomalies.
   - Run staging tests with `DEV_MODE=true` first to validate flows without live charges.

If you want, I can also add a small admin-only toggle endpoint to enable live Stripe/BYOK in a controlled manner (requires production admin auth).