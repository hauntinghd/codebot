#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$ROOT/_releases/backend_snapshot_$STAMP.tgz"

echo "Creating snapshot: $OUT"
tar -czf "$OUT" \
  backend-ts/src/codebot5 \
  backend-ts/package.json \
  backend-ts/pnpm-lock.yaml \
  backend-ts/tsconfig.json \
  backend/main.py \
  backend/routes 2>/dev/null || true

echo "$OUT" > "$ROOT/_releases/LAST_BACKEND_SNAPSHOT.txt"
echo "Saved LAST snapshot pointer."
