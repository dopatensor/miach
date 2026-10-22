#!/usr/bin/env bash
# Run Miach locally for the demo: http://localhost:8000 (frontend + API, no internet needed).
#
#   ./demo.sh            start (installs and builds only what is missing; needs internet the first time)
#   ./demo.sh --rebuild  rebuild the frontend first (after pulling new code)
#   PORT=8001 ./demo.sh  use another port
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8000}"
URL="http://localhost:$PORT"
PY="${PYTHON:-python3}"

say() { printf '\033[1;33m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

command -v "$PY" >/dev/null || die "python3 not found (need Python 3.11+)"

if ! "$PY" -c "import fastapi, uvicorn, sklearn, joblib, pandas" 2>/dev/null; then
  say "installing backend dependencies (needs internet once)"
  "$PY" -m pip install -q -r backend/requirements.txt || die "pip install failed; connect to the internet and retry"
fi

if [[ "${1:-}" == "--rebuild" || ! -f frontend/dist/index.html ]]; then
  command -v npm >/dev/null || die "npm not found (need Node 18+) to build the frontend"
  if [[ ! -d frontend/node_modules ]]; then
    say "installing frontend dependencies (needs internet once)"
    (cd frontend && npm ci --no-audit --no-fund) || die "npm ci failed; connect to the internet and retry"
  fi
  say "building the frontend"
  (cd frontend && npm run build) >/dev/null 2>&1 || die "frontend build failed; run 'cd frontend && npm run build' to see why"
fi

if curl -s -o /dev/null "$URL/api/health" 2>/dev/null; then
  die "something is already running on port $PORT; stop it or use PORT=8001 ./demo.sh"
fi

say "starting Miach on $URL (Ctrl+C to stop)"
cd backend
"$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --log-level warning &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT INT TERM

for _ in $(seq 1 60); do
  curl -s -o /dev/null "$URL/api/health" && break
  kill -0 "$SERVER" 2>/dev/null || die "server stopped during startup (see messages above)"
  sleep 1
done
curl -s -o /dev/null "$URL/api/health" || die "server did not answer within 60 s"

say "ready: $URL/designer"
if command -v open >/dev/null; then open "$URL/designer"            # macOS
elif command -v xdg-open >/dev/null; then xdg-open "$URL/designer" >/dev/null 2>&1 || true
fi
wait "$SERVER"
