#!/bin/bash
# Backup current DB, create fresh eval DB, and switch to it.
# Usage: ./scripts/use_eval_db.sh
# Then start services with: SQLITE_PATH=data/monitoring_eval.db ./scripts/start_all_agents.sh
# Or: export SQLITE_PATH=data/monitoring_eval.db && python simulator-service/main.py ...

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Load only SQLITE_PATH from .env (avoid exporting comments/invalid lines)
if [ -f .env ]; then
  SQLITE_PATH=$(grep -E '^SQLITE_PATH=' .env 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'")
fi

CURRENT_DB="${SQLITE_PATH:-data/monitoring.db}"
EVAL_DB="data/monitoring_eval.db"

# 1. Backup current DB if it exists
if [ -f "$CURRENT_DB" ]; then
  BACKUP_DIR="data/backups"
  mkdir -p "$BACKUP_DIR"
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  cp "$CURRENT_DB" "$BACKUP_DIR/monitoring_$TIMESTAMP.db"
  echo "Backed up: $CURRENT_DB -> $BACKUP_DIR/monitoring_$TIMESTAMP.db"
fi

# 2. Create fresh eval DB (init schema + vec0 for RAG)
echo "Creating fresh eval DB: $EVAL_DB"
rm -f "$EVAL_DB"
python scripts/init_db.py "$EVAL_DB"

# 3. Optional: clear evaluation JSONL for clean run
EVAL_DIR="evaluation"
for f in scenario_runs.jsonl manual_triggers.jsonl; do
  if [ -f "$EVAL_DIR/$f" ]; then
    rm "$EVAL_DIR/$f"
    echo "Cleared $EVAL_DIR/$f"
  fi
done

echo ""
echo "=========================================="
echo "Eval DB ready: $EVAL_DB"
echo "=========================================="
echo ""
echo "Start services with eval DB:"
echo "  export SQLITE_PATH=$EVAL_DB"
echo "  ./scripts/start_all_agents.sh"
echo ""
echo "Or add to .env:"
echo "  SQLITE_PATH=$EVAL_DB"
echo ""
echo "RAG: Vector index (vec0) is in the same DB. New alerts/diagnoses"
echo "     will be indexed automatically during eval runs."
echo ""
