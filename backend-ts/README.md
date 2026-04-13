CodeBot Credits + Billing (TypeScript)

Usage
- Copy `.env.example` to `.env` and set `DATABASE_URL`, `STRIPE_SECRET_KEY`, and `STRIPE_WEBHOOK_SECRET`.
- Install: `cd backend-ts && npm ci`
- Run migrations: start the service and POST to `/api/credits/migrate` (or run `node dist/migrate.js` after building).
- Start: `npm run dev` or `npm run build && npm start`.

Notes
- This module is an independent TypeScript microservice providing credit ledger, Stripe checkout, and webhook grant logic.
- It uses Postgres and requires `pg` to be able to connect.
