#!/usr/bin/env bash
set -euo pipefail
# Lightweight local launcher for a private CodeBot instance.
# This script sets safe environment variables (no live Stripe keys)
# and runs the backend on localhost without touching the repo's .env.

# Resolve directory and allow optional PORT env var
DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8080}"

# Basic local settings
export APP_BASE_URL="http://127.0.0.1:${PORT}"
# Respect existing APP_BASE_PATH if provided, otherwise default to empty for local testing
export APP_BASE_PATH="${APP_BASE_PATH:-}"
export API_PREFIX="/api"

# Ensure we do NOT use live Stripe keys locally
export STRIPE_ALLOW_LIVE="false"
export STRIPE_SECRET_KEY=""
export STRIPE_PUBLISHABLE_KEY=""
export STRIPE_WEBHOOK_SECRET=""
export STRIPE_PRICE_ID_PLUS=""
export STRIPE_PRICE_ID_PRO=""
export STRIPE_PRICE_ID_CBT_20=""
export STRIPE_PRICE_ID_CBT_60=""

# Local data directory and DB (isolated from live)
export DATA_DIR="${DIR}/data_local"
export DB_PATH="${DATA_DIR}/codebot_local.db"
mkdir -p "${DATA_DIR}"

echo "Starting CodeBot local instance at ${APP_BASE_URL}${APP_BASE_PATH} (port ${PORT})"
echo "Data directory: ${DATA_DIR}"

# Run the backend with autoreload on localhost (use python3)
# When running locally, avoid self-mounting the `api` app onto the host app.
# This prevents mounted sub-app routing from being overridden and ensures
# static asset mounts work correctly under a custom `APP_BASE_PATH`.
export SKIP_SELF_MOUNT=1

python3 -m uvicorn backend.main:app --host 127.0.0.1 --port ${PORT} --reload

# When running locally, avoid self-mounting the `api` app onto the host app.
# This prevents mounted sub-app routing from being overridden and ensures
# static asset mounts work correctly under a custom `APP_BASE_PATH`.
# NOTE: set before launching the app so main.py uses the host app instead
# of assigning `app = api`.
# export SKIP_SELF_MOUNT=1
