#!/usr/bin/env bash
set -euo pipefail

if ! command -v mise >/dev/null 2>&1; then
  echo "error: mise is required but was not found on PATH" >&2
  exit 1
fi

eval "$(mise activate bash)"

mise install

if ! command -v uv >/dev/null 2>&1; then
  mise install uv
fi

run_uv() {
  if command -v uv >/dev/null 2>&1; then
    uv "$@"
  else
    mise exec uv@latest -- uv "$@"
  fi
}

if [[ -z "${UV_CACHE_DIR:-}" ]]; then
  export UV_CACHE_DIR=/tmp/uv-cache
fi

run_uv sync
run_uv run pytest
