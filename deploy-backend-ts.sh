#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ====== CONFIG YOU MUST SET (we will fill these from your command output) ======
SERVICE_NAME="${SERVICE_NAME:-CHANGE_ME.service}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8091/health}"
# ============================================================================

TS="$(date +%Y%m%d_%H%M%S)"
SNAP="$ROOT/_releases/backend-ts_$TS.tar.gz"
LAST_GOOD_FILE="$ROOT/_releases/backend-ts_last_good.txt"

rollback () {
  echo ""
  echo "⚠️ DEPLOY FAILED — rolling back..."
  if [[ -f "$LAST_GOOD_FILE" ]]; then
    LAST_SNAP="$(cat "$LAST_GOOD_FILE")"
    echo "Restoring snapshot: $LAST_SNAP"
    rm -rf "$ROOT/backend-ts"
    mkdir -p "$ROOT/backend-ts"
    tar -xzf "$LAST_SNAP" -C "$ROOT"
    echo "Restarting service: $SERVICE_NAME"
    sudo systemctl restart "$SERVICE_NAME" || true
    echo "Health check: $HEALTH_URL"
    curl -fsS "$HEALTH_URL" >/dev/null && echo "✅ Rolled back + healthy." || echo "❌ Rollback health check failed."
  else
    echo "❌ No last-good snapshot file found: $LAST_GOOD_FILE"
  fi
}

trap rollback ERR

echo "Creating snapshot: $SNAP"
tar -czf "$SNAP" -C "$ROOT" backend-ts
echo "$SNAP" > "$LAST_GOOD_FILE"

echo "Install deps + smoke..."
pushd "$ROOT/backend-ts" >/dev/null
pnpm -s install
node scripts/smoke.mjs
popd >/dev/null

echo "Restarting service: $SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Health check: $HEALTH_URL"
curl -fsS "$HEALTH_URL" >/dev/null

trap - ERR
echo "✅ Deploy complete."
