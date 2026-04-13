#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAST_PTR="$ROOT/_releases/LAST_BACKEND_SNAPSHOT.txt"

if [[ ! -f "$LAST_PTR" ]]; then
  echo "ERROR: No snapshot pointer found. Run: ./scripts/snapshot_backend.sh"
  exit 1
fi

SNAP="$(cat "$LAST_PTR")"
if [[ ! -f "$SNAP" ]]; then
  echo "ERROR: Snapshot tarball missing: $SNAP"
  exit 1
fi

echo "Restarting services..."
sudo systemctl restart codebot-api.service
sudo systemctl restart codebot-credits.service

echo "Running smoke test..."
if "$ROOT/scripts/smoke_backend.sh"; then
  echo "DEPLOY OK ✅"
  exit 0
fi

echo "Smoke test failed ❌ — rolling back from snapshot: $SNAP"
cd "$ROOT"
tar -xzf "$SNAP"

echo "Restarting services after rollback..."
sudo systemctl restart codebot-api.service
sudo systemctl restart codebot-credits.service

echo "Re-running smoke test after rollback..."
"$ROOT/scripts/smoke_backend.sh"
echo "ROLLBACK COMPLETE ✅"
