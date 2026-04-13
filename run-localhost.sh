#!/usr/bin/env bash
# CodeBot - Run on localhost for development
# Usage: ./run-localhost.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Ports ---
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

# --- Local env (overrides .env for local dev) ---
export APP_BASE_URL="http://127.0.0.1:${BACKEND_PORT}"
export APP_BASE_PATH="/codebot"
export APP_BASE_PATH="${APP_BASE_PATH:-/codebot}"
export DATA_DIR="${DATA_DIR:-$SCRIPT_DIR/data}"
export DB_PATH="${DB_PATH:-$DATA_DIR/codebot.db}"
export DEV_MODE="${DEV_MODE:-true}"

# Allow CORS from frontend
export CODEBOT_ALLOWED_ORIGINS="http://localhost:${FRONTEND_PORT},http://127.0.0.1:${FRONTEND_PORT},http://localhost:${BACKEND_PORT},http://127.0.0.1:${BACKEND_PORT}"

# Ensure data dir
mkdir -p "$DATA_DIR"

# Don't use live Stripe keys locally (unless you have test keys in .env)
export STRIPE_ALLOW_LIVE="${STRIPE_ALLOW_LIVE:-false}"

echo "=========================================="
echo "  CodeBot - Local Development"
echo "=========================================="
echo "  Backend:  http://127.0.0.1:${BACKEND_PORT}${APP_BASE_PATH}/"
echo "  Frontend: http://127.0.0.1:${FRONTEND_PORT}${APP_BASE_PATH}/"
echo "  Health:   http://127.0.0.1:${BACKEND_PORT}${APP_BASE_PATH}/health"
echo "  DEV_MODE: $DEV_MODE (bypasses subscription)"
echo "=========================================="
echo ""

# Start backend
echo "Starting backend on port ${BACKEND_PORT}..."
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port "${BACKEND_PORT}" &
BACKEND_PID=$!
sleep 3

# Check backend
if ! curl -s "http://127.0.0.1:${BACKEND_PORT}${APP_BASE_PATH}/health" | grep -q ok; then
    echo "Backend failed to start. Check logs."
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi
echo "Backend running (PID $BACKEND_PID)"

# Start frontend (proxy API to backend)
echo "Starting frontend on port ${FRONTEND_PORT}..."
export NEXT_PUBLIC_BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"
cd apps/codebot-builder
# Use 'dev' for hot reload; no build needed
PORT="${FRONTEND_PORT}" pnpm dev &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"
sleep 5

echo ""
echo "CodeBot is ready!"
echo "  Open: http://127.0.0.1:${FRONTEND_PORT}${APP_BASE_PATH}/"
echo ""
echo "Press Ctrl+C to stop both services."
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
