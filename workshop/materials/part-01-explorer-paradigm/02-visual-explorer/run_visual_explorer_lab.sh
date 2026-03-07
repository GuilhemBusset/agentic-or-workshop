#!/usr/bin/env bash
# bash workshop/materials/part-01-explorer-paradigm/02-visual-explorer/run_visual_explorer_lab.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || (cd "$SCRIPT_DIR/../../../.." && pwd))"
cd "$ROOT_DIR"

if command -v mise >/dev/null 2>&1; then
  eval "$(mise activate bash)" || true
fi

DATA_HOST="${DATA_HOST:-0.0.0.0}"
DATA_PORT="${DATA_PORT:-8018}"
LAB_SOURCE_FILE="$SCRIPT_DIR/00-visual-explorer-live-lab.html"
LAB_RUNTIME_FILE="$SCRIPT_DIR/00-visual-explorer-live-lab.runtime.html"
CSV_SERVER_FILE="$SCRIPT_DIR/live_csv_server.py"
CSV_LOG="/tmp/visual_explorer_csv_server.log"

uv sync >/dev/null

pick_available_port() {
  local host="$1"
  local preferred_port="$2"
  uv run python - "$host" "$preferred_port" <<'PY'
import socket
import sys

host = sys.argv[1]
preferred_port = int(sys.argv[2])
candidate_ports = [preferred_port, *range(preferred_port + 1, preferred_port + 200)]

for port in candidate_ports:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            continue
        print(port)
        raise SystemExit(0)

raise SystemExit(1)
PY
}

SELECTED_DATA_PORT="$(pick_available_port "$DATA_HOST" "$DATA_PORT" || true)"
if [[ -z "$SELECTED_DATA_PORT" ]]; then
  echo "Could not find an available port near ${DATA_PORT} for CSV server." >&2
  exit 1
fi

DATA_BASE_URL="http://127.0.0.1:${SELECTED_DATA_PORT}/workshop/data"

mkdir -p "$(dirname "$LAB_RUNTIME_FILE")"
sed \
  -e "s|<!-- DATA_BASE_BOOTSTRAP -->|<script>window.VISUAL_EXPLORER_DATA_BASE='${DATA_BASE_URL}';</script>|g" \
  "$LAB_SOURCE_FILE" >"$LAB_RUNTIME_FILE"

cleanup() {
  if [[ -n "${CSV_PID:-}" ]] && kill -0 "$CSV_PID" >/dev/null 2>&1; then
    kill "$CSV_PID" >/dev/null 2>&1 || true
  fi
  rm -f "$LAB_RUNTIME_FILE" >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

uv run python "$CSV_SERVER_FILE" \
  --host "$DATA_HOST" \
  --port "$SELECTED_DATA_PORT" \
  --root "$ROOT_DIR" >"$CSV_LOG" 2>&1 &
CSV_PID=$!

sleep 1

if ! kill -0 "$CSV_PID" >/dev/null 2>&1; then
  echo "CSV server failed to start. Log: $CSV_LOG" >&2
  exit 1
fi

cat <<MSG
Visual Explorer Live CSV Lab is running.

VS Code Live Preview file:
  ${LAB_RUNTIME_FILE}
  (Open this file with "Open with Live Preview" in VS Code)

Live CSV source:
  ${DATA_BASE_URL}

Optional direct browser URL:
  http://127.0.0.1:${SELECTED_DATA_PORT}/workshop/materials/part-01-explorer-paradigm/02-visual-explorer/00-visual-explorer-live-lab.html?dataBase=${DATA_BASE_URL}

$(if [[ "$SELECTED_DATA_PORT" != "$DATA_PORT" ]]; then
  echo "Requested port ${DATA_PORT} was unavailable. Using ${SELECTED_DATA_PORT}."
fi)

Logs:
  CSV server: $CSV_LOG

Press Ctrl+C to stop the CSV server and remove the runtime preview file.
MSG

wait "$CSV_PID"
