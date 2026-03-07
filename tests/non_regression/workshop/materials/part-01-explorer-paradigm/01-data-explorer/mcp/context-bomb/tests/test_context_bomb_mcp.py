from __future__ import annotations

import importlib.util
from pathlib import Path


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "workshop").is_dir() and (parent / "tests").is_dir():
            return parent
    raise RuntimeError("Repository root not found")


REPO_ROOT = _repo_root()
SERVER_PATH = (
    REPO_ROOT
    / "workshop"
    / "materials"
    / "part-01-explorer-paradigm"
    / "01-data-explorer"
    / "mcp"
    / "context-bomb"
    / "server.py"
)


def load_server_module():
    spec = importlib.util.spec_from_file_location("context_bomb_server", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load context bomb server module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_context_bomb_payload_is_large():
    server_module = load_server_module()
    total_chars = sum(
        len(server_module._build_bomb_slice(i))
        for i in range(server_module.TOOL_COUNT)
    )
    assert total_chars >= 50_000


def test_context_bomb_status_tool_returns_metadata():
    server_module = load_server_module()
    payload = server_module.bomb_status()

    assert "active" in payload["answer"].lower()
    assert payload["tool_count"] == server_module.TOOL_COUNT
    assert payload["blocks_per_tool"] == server_module.BLOCKS_PER_TOOL
    assert payload["total_blocks"] == server_module.TOOL_COUNT * server_module.BLOCKS_PER_TOOL
