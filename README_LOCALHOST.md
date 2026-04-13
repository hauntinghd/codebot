# CodeBot - Run on Localhost

Quick way to run CodeBot locally for development.

## Quick Start

```bash
./run-localhost.sh
```

Then open: **http://127.0.0.1:3000/codebot/**

## What It Does

- **Backend** (Python/FastAPI) on port 8000
- **Frontend** (Next.js) on port 3000
- **DEV_MODE=true** — bypasses subscription checks so you can use chat without a paid plan
- **API proxy** — frontend proxies `/codebot/api/*` to the backend

## Ports

- Backend: `http://127.0.0.1:8000/codebot/`
- Frontend: `http://127.0.0.1:3000/codebot/`
- Health: `http://127.0.0.1:8000/codebot/health`

Override ports:
```bash
BACKEND_PORT=8080 FRONTEND_PORT=3001 ./run-localhost.sh
```

## Requirements

- Python 3.8+ with dependencies (`pip install -r requirements.txt`)
- Node.js 18+ with pnpm
- `XAI_API_KEY` in `.env` (for Grok/chat)
- Optional: `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` for login

## Data

- Local data: `./data/` (or `$DATA_DIR`)
- SQLite DB: `./data/codebot.db`

## Notes

- **backend-ts** (Node credits service on 4001) is not started. Credits/billing routes will fail if called. Chat should work.
- **Stripe** — uses keys from `.env`. Set `STRIPE_ALLOW_LIVE=false` to avoid live keys locally.
- Press **Ctrl+C** to stop both services.
