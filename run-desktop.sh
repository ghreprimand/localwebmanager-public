#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PORT=8000
URL="http://localhost:${PORT}"

# Activate the project venv
if [[ -d .venv ]]; then
  source .venv/bin/activate
fi

# If already running on this port, just open the browser
if curl -s -o /dev/null -w '' --max-time 1 "${URL}/api/services" 2>/dev/null; then
  xdg-open "$URL" 2>/dev/null &
  exit 0
fi

# Start the server in the background
uvicorn localwebmanager.app:app --host 127.0.0.1 --port "$PORT" &
SERVER_PID=$!

# Wait for the server to be ready (up to 5s)
for i in $(seq 1 50); do
  if curl -s -o /dev/null -w '' --max-time 1 "${URL}/api/services" 2>/dev/null; then
    break
  fi
  sleep 0.1
done

# Open in default browser
xdg-open "$URL" 2>/dev/null &

# Keep running so the .desktop launcher doesn't kill the server
wait "$SERVER_PID"
