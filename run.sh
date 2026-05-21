#!/usr/bin/env bash
# dochat — start backend + frontend
# Usage: ./run.sh

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}▶ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠  $*${NC}"; }

# ── Activate venv ─────────────────────────────────
source "$VENV/bin/activate"

# ── Start API ─────────────────────────────────────
log "Starting FastAPI backend on http://localhost:8000 ..."
cd "$ROOT/core"
uvicorn app:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!
echo $API_PID > /tmp/dochat_api.pid

# ── Start UI ──────────────────────────────────────
sleep 2
log "Starting Streamlit UI on http://localhost:8501 ..."
cd "$ROOT"
streamlit run ui.py --server.port 8501 --server.headless true &
UI_PID=$!
echo $UI_PID > /tmp/dochat_ui.pid

# ── Info ──────────────────────────────────────────
echo ""
log "dochat is running:"
echo "   API  →  http://localhost:8000"
echo "   Docs →  http://localhost:8000/docs"
echo "   UI   →  http://localhost:8501"
echo ""
warn "Press Ctrl+C to stop."

# ── Cleanup on exit ───────────────────────────────
cleanup() {
    echo ""
    log "Shutting down..."
    kill "$(cat /tmp/dochat_api.pid)" 2>/dev/null || true
    kill "$(cat /tmp/dochat_ui.pid)"  2>/dev/null || true
    rm -f /tmp/dochat_api.pid /tmp/dochat_ui.pid
}
trap cleanup EXIT INT TERM

wait
