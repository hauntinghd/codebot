#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
echo "Building frontend..."
cd "$ROOT_DIR/frontend"
if [ -f package-lock.json ] || [ -f pnpm-lock.yaml ]; then
  npm ci
else
  npm install
fi
npm run build

echo "Copying build to /var/www/codebot..."
sudo mkdir -p /var/www/codebot
sudo rm -rf /var/www/codebot/*
sudo cp -r "$ROOT_DIR/static/app/"* /var/www/codebot/

echo "Reloading nginx and restarting backend service..."
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl restart codebot.service

echo "Deploy complete."
