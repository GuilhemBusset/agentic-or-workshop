from __future__ import annotations

import importlib.util
from pathlib import Path

import anyio
import pytest


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
    / "data-explorer-csv"
    / "server.py"
)


def load_server_module():
    spec = importlib.util.spec_from_file_location("data_explorer_server", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load server module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def server_module():
    return load_server_module()


def test_resolve_csv_path_allows_workshop_data(server_module):
    path = server_module.resolve_csv_path("depots.csv")
    assert path.name == "depots.csv"
    assert path.is_file()


def test_resolve_csv_path_blocks_traversal(server_module):
    with pytest.raises(ValueError, match="Path traversal"):
        server_module.resolve_csv_path("../depots.csv")


def test_resolve_csv_path_blocks_absolute_path(server_module):
    with pytest.raises(ValueError, match="Absolute paths"):
        server_module.resolve_csv_path(
            str((REPO_ROOT / "workshop" / "data" / "depots.csv").resolve())
        )


def test_validate_sql_rejects_non_select(server_module):
    with pytest.raises(ValueError, match="SELECT/WITH"):
        server_module.validate_sql("DELETE FROM csv_data")


def test_validate_sql_rejects_multi_statement(server_module):
    with pytest.raises(ValueError, match="one SQL statement"):
        server_module.validate_sql("SELECT * FROM csv_data; SELECT 1")


def test_validate_sql_requires_csv_data_alias(server_module):
    with pytest.raises(ValueError, match="csv_data"):
        server_module.validate_sql("SELECT 1")


def test_execute_csv_query_happy_path(server_module):
    result = server_module.execute_csv_query(
        "depots.csv",
        "SELECT depot_id, capacity FROM csv_data ORDER BY capacity DESC LIMIT 3",
    )

    assert result["confidence"] == "high"
    assert result["row_count"] == 3
    assert result["columns"] == ["depot_id", "capacity"]
    assert len(result["rows"]) == 3
    assert "workshop/data/depots.csv" in result["source_refs"]
    assert "Query Preview" in result["rich_table"]


def test_execute_csv_query_unknown_column_returns_error_payload(server_module):
    result = server_module.query_csv(
        "depots.csv",
        "SELECT does_not_exist FROM csv_data",
    )

    assert result["error_code"] == "TOOL_EXECUTION_ERROR"
    assert "does_not_exist" in result["error_message"]
    assert result["confidence"] == "low"


def test_describe_csv_schema_happy_path(server_module):
    result = server_module.describe_csv_schema("depots.csv")

    assert result["confidence"] == "high"
    assert result["row_count"] == 6
    assert isinstance(result["columns"], list)
    assert len(result["columns"]) == 4

    first_col = result["columns"][0]
    assert first_col["name"] == "depot_id"
    assert "data_type" in first_col
    assert "null_count" in first_col
    assert "distinct_count" in first_col


def test_describe_csv_schema_invalid_file_returns_error(server_module):
    result = server_module.describe_csv_schema("../depots.csv")
    assert result["error_code"] == "TOOL_EXECUTION_ERROR"
    assert "Path traversal" in result["error_message"]
    assert result["confidence"] == "low"


def test_mcp_tool_contract_and_invocation(server_module):
    async def _call_tool() -> tuple[dict, dict]:
        tools = await server_module.mcp.list_tools()
        tool_names = {tool.name for tool in tools}
        assert "query_csv" in tool_names
        assert "describe_csv_schema" in tool_names

        raw_query_result = await server_module.mcp.call_tool(
            "query_csv",
            {
                "file_path": "depots.csv",
                "query": "SELECT depot_id, capacity FROM csv_data ORDER BY capacity DESC LIMIT 2",
            },
        )

        raw_schema_result = await server_module.mcp.call_tool(
            "describe_csv_schema",
            {"file_path": "depots.csv"},
        )

        def _unwrap(raw_result):
            if isinstance(raw_result, dict):
                return raw_result
            if (
                isinstance(raw_result, tuple)
                and len(raw_result) == 2
                and isinstance(raw_result[1], dict)
            ):
                return raw_result[1]
            raise AssertionError(f"Unexpected tool result shape: {type(raw_result)}")

        return _unwrap(raw_query_result), _unwrap(raw_schema_result)

    query_result, schema_result = anyio.run(_call_tool)

    assert query_result["columns"] == ["depot_id", "capacity"]
    assert query_result["row_count"] == 2
    assert len(query_result["rows"]) == 2

    assert schema_result["row_count"] == 6
    assert isinstance(schema_result["columns"], list)
