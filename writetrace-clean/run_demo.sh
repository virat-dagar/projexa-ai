#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=5500

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

echo "Starting WriteTrace clean demo..."
echo "Backend:  http://127.0.0.1:$BACKEND_PORT"
echo "Frontend: http://127.0.0.1:$FRONTEND_PORT"
echo

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

"$PYTHON_BIN" -m uvicorn app:app --host 127.0.0.1 --port "$BACKEND_PORT" --app-dir "$BACKEND_DIR" &
BACKEND_PID=$!

python3 -m http.server "$FRONTEND_PORT" --directory "$FRONTEND_DIR" &
FRONTEND_PID=$!

sleep 2

if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
  echo "Backend failed to start. Check whether dependencies are installed and whether port $BACKEND_PORT is free."
  exit 1
fi

if ! kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
  echo "Frontend failed to start. Check whether port $FRONTEND_PORT is free."
  exit 1
fi

echo "Both servers are running."
echo "Open http://127.0.0.1:$FRONTEND_PORT in your browser."
echo "Press Ctrl+C here when the demo is finished."
echo

wait
