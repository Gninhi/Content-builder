#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"

if [[ ! -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  echo "[ERROR] Virtual environment not found at $PROJECT_ROOT/.venv" >&2
  exit 1
fi

export APP_ENV="${APP_ENV:-development}"
export ENV="${ENV:-development}"

echo "[1/3] Aligning database schema with Alembic..."
"$PROJECT_ROOT/.venv/bin/alembic" upgrade head

if lsof -iTCP:"$API_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "[2/3] Backend FastAPI already listening on http://${API_HOST}:${API_PORT}"
else
  echo "[2/3] Starting Backend FastAPI on http://${API_HOST}:${API_PORT}..."
  nohup "$PROJECT_ROOT/.venv/bin/uvicorn" apps.api.main:app \
    --host "$API_HOST" \
    --port "$API_PORT" \
    --reload \
    > "$PROJECT_ROOT/storage/api_dev.log" 2>&1 &
  API_PID=$!
  echo "      Backend PID: $API_PID (logs: storage/api_dev.log)"
fi

for _ in {1..25}; do
  if curl -fsS "http://${API_HOST}:${API_PORT}/health" >/dev/null 2>&1; then
    echo "      Healthcheck OK: $(curl -fsS "http://${API_HOST}:${API_PORT}/health")"
    break
  fi
  sleep 0.4
done

if lsof -iTCP:"$WEB_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "[3/3] Frontend Vite already listening on http://localhost:${WEB_PORT}"
else
  echo "[3/3] Starting Frontend Vite on http://localhost:${WEB_PORT}..."
  (
    cd "$PROJECT_ROOT/apps/web"
    nohup npm run dev -- --port "$WEB_PORT" > "$PROJECT_ROOT/storage/web_dev.log" 2>&1 &
    echo "      Frontend PID: $! (logs: storage/web_dev.log)"
  )
fi

echo "Done. API: http://${API_HOST}:${API_PORT} | Web: http://localhost:${WEB_PORT}"

