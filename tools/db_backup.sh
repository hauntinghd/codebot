#!/usr/bin/env bash
set -euo pipefail
# Simple DB backup script for CodeBot
BACKUP_DIR="/var/backups/codebot"
DB_PATH="/home/omatic657/aicoderbot/data/codebot.db"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
mkdir -p "$BACKUP_DIR"
chown -R $USER:$USER "$BACKUP_DIR" || true
# Use sqlite3 .backup for safe copy
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/codebot.db.$TIMESTAMP'"
# Keep 14 days of daily backups
find "$BACKUP_DIR" -type f -name 'codebot.db.*' -mtime +14 -delete
# Optionally compress most recent
gzip -f "$BACKUP_DIR/codebot.db.$TIMESTAMP" || true
chmod 600 "$BACKUP_DIR/codebot.db.$TIMESTAMP.gz" || true
echo "ok"