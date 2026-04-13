Local private instance (safe testing)
===================================

Purpose: run a private copy of CodeBot on localhost for testing changes without touching the live deployment or the repository `.env`.

Quick start
-----------

1. Make the launcher executable:

```bash
chmod +x start_local.sh
```

2. Start the private instance (runs on http://127.0.0.1:8080):

```bash
./start_local.sh
```

Notes
-----
- The script sets empty Stripe keys and `STRIPE_ALLOW_LIVE=false` so it will not use live billing by default.
- Local data is stored in `data_local/` and the SQLite DB is `data_local/codebot_local.db` to avoid interfering with production data.
- If you want to test Stripe flows locally, add your Stripe test keys to the environment before running the launcher. Example:

```bash
export STRIPE_SECRET_KEY="sk_test_..."
export STRIPE_PUBLISHABLE_KEY="pk_test_..."
./start_local.sh
```

- The UI will be served at `http://127.0.0.1:8080/codebot`.

Security
--------
- Do not put live production keys in the repository or in the default `.env` when using this script.
