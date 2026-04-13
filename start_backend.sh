#!/bin/bash
# Activate venv and ensure .env is loaded for backend
cd "$(dirname "$0")"
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
exec python -m uvicorn backend.main:app --host 127.0.0.1 --port 3000 --workers 1 --log-level info
