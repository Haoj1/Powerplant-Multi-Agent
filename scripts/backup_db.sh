#!/bin/bash
# Backup the current monitoring database.
# Usage: ./scripts/backup_db.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Load only SQLITE_PATH from .env (avoid exporting comments/invalid lines)
if [ -f .env ]; then
  SQLITE_PATH=$(grep -E '^SQLITE_PATH=' .env 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'")
fi

DB_PATH="${SQLITE_PATH:-data/monitoring.db}"
if [ ! -f "$DB_PATH" ]; then
  echo "Database not found: $DB_PATH"
  exit 1
fi

BACKUP_DIR="data/backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/monitoring_$TIMESTAMP.db"

cp "$DB_PATH" "$BACKUP_FILE"
echo "Backed up: $DB_PATH -> $BACKUP_FILE"
