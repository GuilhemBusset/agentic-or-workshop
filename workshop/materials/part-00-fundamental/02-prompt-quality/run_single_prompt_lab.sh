#!/usr/bin/env bash
# JUDGE_BACKEND=codex bash workshop/materials/part-00-fundamental/02-prompt-quality/run_single_prompt_lab.sh
# JUDGE_BACKEND=claude-code bash workshop/materials/part-00-fundamental/02-prompt-quality/run_single_prompt_lab.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || (cd "$SCRIPT_DIR/../../../.." && pwd))"
cd "$ROOT_DIR"

JUDGE_HOST="${JUDGE_HOST:-0.0.0.0}"
JUDGE_PORT="${JUDGE_PORT:-8008}"
JUDGE_BACKEND="${JUDGE_BACKEND:-codex}"
LAB_SOURCE_FILE="$SCRIPT_DIR/00-explorer-single-shot-lab.html"
LAB_RUNTIME_FILE="$SCRIPT_DIR/00-explorer-single-shot-lab.runtime.html"
JUDGE_SERVICE_FILE="$SCRIPT_DIR/llm_judge_service.py"

case "$JUDGE_BACKEND" in
  codex)
    if ! command -v codex >/dev/null 2>&1; then
      echo "codex CLI not found in PATH. Install/login first." >&2
      exit 1
    fi
    ;;
  claude-code)
    if ! command -v claude >/dev/null 2>&1; then
      echo "claude CLI not found in PATH. Install Claude Code first." >&2
      exit 1
    fi
    ;;
  *)
    echo "Unknown JUDGE_BACKEND='$JUDGE_BACKEND'. Use 'codex' or 'claude-code'." >&2
    exit 1
    ;;
esac

uv sync >/dev/null

JUDGE_LOG="/tmp/prompt_judge_backend.log"

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

SELECTED_JUDGE_PORT="$(pick_available_port "$JUDGE_HOST" "$JUDGE_PORT" || true)"
if [[ -z "$SELECTED_JUDGE_PORT" ]]; then
  echo "Could not find an available port near ${JUDGE_PORT} for the judge backend." >&2
  exit 1
fi

mkdir -p "$(dirname "$LAB_RUNTIME_FILE")"
sed \
  -e "s|http://127.0.0.1:8008/judge|http://127.0.0.1:${SELECTED_JUDGE_PORT}/judge|g" \
  -e "s|Local FastAPI (:8008)|Local FastAPI (:${SELECTED_JUDGE_PORT})|g" \
  "$LAB_SOURCE_FILE" >"$LAB_RUNTIME_FILE"

cleanup() {
  if [[ -n "${JUDGE_PID:-}" ]] && kill -0 "$JUDGE_PID" >/dev/null 2>&1; then
    kill "$JUDGE_PID" >/dev/null 2>&1 || true
  fi
  rm -f "$LAB_RUNTIME_FILE" >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

JUDGE_HOST="$JUDGE_HOST" JUDGE_PORT="$SELECTED_JUDGE_PORT" JUDGE_BACKEND="$JUDGE_BACKEND" \
  uv run python "$JUDGE_SERVICE_FILE" >"$JUDGE_LOG" 2>&1 &
JUDGE_PID=$!

sleep 1

if ! kill -0 "$JUDGE_PID" >/dev/null 2>&1; then
  echo "Judge backend failed to start. Log: $JUDGE_LOG" >&2
  exit 1
fi

cat <<MSG
Single Prompt Judge Lab is running.

Backend: ${JUDGE_BACKEND}

VS Code Live Preview file:
  ${LAB_RUNTIME_FILE}
  (Open this file with "Open with Live Preview" in VS Code)

Judge endpoint:
  http://localhost:${SELECTED_JUDGE_PORT}/judge

$(if [[ "$SELECTED_JUDGE_PORT" != "$JUDGE_PORT" ]]; then
  echo "Requested port ${JUDGE_PORT} was unavailable. Using ${SELECTED_JUDGE_PORT}."
fi)

Logs:
  Backend: $JUDGE_LOG

Press Ctrl+C to stop the backend and remove the runtime preview file.
MSG

wait "$JUDGE_PID"
