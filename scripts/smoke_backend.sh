#!/usr/bin/env bash
set -euo pipefail

echo "== systemd status =="
systemctl is-active codebot-api.service
systemctl is-active codebot-credits.service

echo "== listening ports =="
ss -lptn | rg -n ":8000|:4001" || true

echo "== FastAPI OpenAPI =="
curl -fsS "http://127.0.0.1:8000/codebot/openapi.json" >/dev/null
echo "OK: openapi.json"

echo "== Credits health (best-effort) =="
# If you have /health on credits, this will pass. If not, we just print a warning.
if curl -fsS "http://127.0.0.1:4001/health" >/dev/null; then
  echo "OK: credits /health"
else
  echo "WARN: credits /health endpoint not found (this is OK if you don't expose one)"
fi

echo "== Done =="
