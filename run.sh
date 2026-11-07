#!/usr/bin/env bash
# NYAYMITRA 2.0 — local launcher.
# Usage: ./run.sh [port]      (defaults to 8000; binds 0.0.0.0 so containers/previews work)
set -euo pipefail

PORT="${1:-8000}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  echo "==> creating virtual environment"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> installing dependencies"
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements.txt

echo "==> migrating database"
python scripts/init_db.py --json >/dev/null

echo "==> NYAYMITRA listening on http://0.0.0.0:${PORT} (docs: /api/docs)"
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT"
