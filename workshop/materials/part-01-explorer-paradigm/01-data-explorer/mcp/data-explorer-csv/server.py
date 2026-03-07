from __future__ import annotations

import re
import time
from io import StringIO
from pathlib import Path
from typing import Any

import duckdb
from mcp.server.fastmcp import FastMCP
from rich.console import Console
from rich.table import Table

PREVIEW_LIMIT = 50
SERVER_INSTRUCTIONS = """
Purpose:
- Query one CSV file from workshop/data via safe, read-only SQL.
- Inspect schema metadata for one CSV file from workshop/data.

Tool contract:
- Use tool `query_csv(file_path, query)`.
- Use tool `describe_csv_schema(file_path)`.
- `file_path` must be a relative `.csv` path under `workshop/data`.
- `query` must be a single read-only `SELECT` or `WITH` statement.
- Query must reference table alias `csv_data`.

Safety:
- Reject absolute paths and path traversal.
- Reject non-CSV files.
- Reject non-read-only SQL and forbidden keywords.

Output:
- On success: answer, source_refs, columns, rows, row_count, preview_truncated, rich_table, elapsed_ms.
- On error: error_code, error_message, source_refs, confidence, followups.
""".strip()

QUERY_CSV_TOOL_DESCRIPTION = """
Execute one read-only SQL query against one CSV in `workshop/data`.

Input requirements:
- file_path: relative CSV path, e.g. `depots.csv` or `scenario_demands.csv`
- query: single SQL statement that starts with `SELECT` or `WITH` and references `csv_data`

Behavior:
- Loads the selected CSV as DuckDB alias `csv_data`
- Executes query safely (read-only only)
- Returns structured result with table preview and source reference

Common failure reasons:
- absolute path or `..` traversal
- non-CSV input file
- non-read-only SQL (`INSERT`, `UPDATE`, `DELETE`, etc.)
- query does not reference `csv_data`
""".strip()

DESCRIBE_CSV_SCHEMA_TOOL_DESCRIPTION = """
Inspect schema and basic profiling stats for one CSV in `workshop/data`.

Input requirements:
- file_path: relative CSV path, e.g. `depots.csv` or `scenario_demands.csv`

Behavior:
- Loads the selected CSV as DuckDB alias `csv_data`
- Returns column names, inferred data types, nullability, null counts, and distinct counts
- Returns total row count with source reference

Common failure reasons:
- absolute path or `..` traversal
- non-CSV input file
- file not found under `workshop/data`
""".strip()

FORBIDDEN_SQL_KEYWORDS = re.compile(
    r"\b("
    r"insert|update|delete|create|alter|drop|truncate|replace|copy|attach|detach|"
    r"pragma|vacuum|call|merge|grant|revoke|set|install|load|export|import"
    r")\b",
    flags=re.IGNORECASE,
)

READ_ONLY_PREFIX = re.compile(r"^\s*(select|with)\b", flags=re.IGNORECASE)

mcp = FastMCP("data-explorer-csv", instructions=SERVER_INSTRUCTIONS)


def _repo_root() -> Path:
    """Find repository root by locating the directory that owns workshop/data."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "workshop" / "data").is_dir():
            return parent
    raise RuntimeError("Unable to locate repository root containing workshop/data")


def data_root() -> Path:
    return _repo_root() / "workshop" / "data"


def resolve_csv_path(file_path: str) -> Path:
    if not file_path:
        raise ValueError("file_path is required")

    base_dir = data_root().resolve()
    rel_path = Path(file_path)
    if rel_path.is_absolute():
        raise ValueError(
            "Absolute paths are not allowed; use paths under workshop/data"
        )

    resolved = (base_dir / rel_path).resolve()
    if base_dir not in resolved.parents and resolved != base_dir:
        raise ValueError(
            "Path traversal is not allowed; file must stay under workshop/data"
        )

    if resolved.suffix.lower() != ".csv":
        raise ValueError("Only .csv files are allowed")

    if not resolved.exists() or not resolved.is_file():
        raise ValueError(f"CSV file not found: {file_path}")

    return resolved


def validate_sql(query: str) -> str:
    if not query or not query.strip():
        raise ValueError("query is required")

    normalized = query.strip()
    if normalized.endswith(";"):
        normalized = normalized[:-1].strip()

    if ";" in normalized:
        raise ValueError("Only one SQL statement is allowed")

    if not READ_ONLY_PREFIX.match(normalized):
        raise ValueError("Only SELECT/WITH read-only SQL is allowed")

    if FORBIDDEN_SQL_KEYWORDS.search(normalized):
        raise ValueError("Query includes forbidden SQL keywords")

    if re.search(r"\bcsv_data\b", normalized, flags=re.IGNORECASE) is None:
        raise ValueError("Query must reference the csv_data table alias")

    return normalized


def render_rich_table(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    table = Table(title="Query Preview")
    for col in columns:
        table.add_column(str(col))
    for row in rows:
        table.add_row(*["" if value is None else str(value) for value in row])

    buffer = StringIO()
    console = Console(
        file=buffer, record=True, color_system=None, force_terminal=False, width=120
    )
    console.print(table)
    return buffer.getvalue().strip()


def quote_identifier(name: str) -> str:
    return f'"{name.replace('"', '""')}"'


def execute_csv_query(
    file_path: str, query: str, preview_limit: int = PREVIEW_LIMIT
) -> dict[str, Any]:
    csv_path = resolve_csv_path(file_path)
    safe_sql = validate_sql(query)
    bounded_limit = max(1, int(preview_limit))
    escaped_csv_path = str(csv_path).replace("'", "''")

    start = time.perf_counter()

    with duckdb.connect(database=":memory:") as con:
        con.execute(
            f"CREATE VIEW csv_data AS SELECT * FROM read_csv_auto('{escaped_csv_path}', HEADER=TRUE)"
        )

        total_rows_row = con.execute(
            f"SELECT COUNT(*) AS total_rows FROM ({safe_sql}) AS __query_count"
        ).fetchone()
        if total_rows_row is None:
            raise RuntimeError("Unable to retrieve row count from DuckDB query")
        total_rows = total_rows_row[0]

        preview_rows = con.execute(
            f"SELECT * FROM ({safe_sql}) AS __query_preview LIMIT {bounded_limit}"
        ).fetchall()
        columns = [col[0] for col in con.description]

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    rich_table = render_rich_table(columns, preview_rows)

    return {
        "answer": f"Returned {total_rows} rows from {csv_path.name}.",
        "assumptions": [
            "Query executed against the CSV registered as table alias csv_data."
        ],
        "source_refs": [f"workshop/data/{csv_path.name}"],
        "confidence": "high",
        "followups": [
            "Refine WHERE clauses or LIMIT for narrower exploration if needed."
        ],
        "columns": columns,
        "rows": [list(row) for row in preview_rows],
        "row_count": total_rows,
        "preview_truncated": total_rows > bounded_limit,
        "rich_table": rich_table,
        "elapsed_ms": elapsed_ms,
    }


def execute_describe_csv_schema(file_path: str) -> dict[str, Any]:
    csv_path = resolve_csv_path(file_path)
    escaped_csv_path = str(csv_path).replace("'", "''")
    start = time.perf_counter()

    with duckdb.connect(database=":memory:") as con:
        con.execute(
            f"CREATE VIEW csv_data AS SELECT * FROM read_csv_auto('{escaped_csv_path}', HEADER=TRUE)"
        )
        schema_rows = con.execute("DESCRIBE SELECT * FROM csv_data").fetchall()
        row_count_row = con.execute("SELECT COUNT(*) FROM csv_data").fetchone()

        if row_count_row is None:
            raise RuntimeError("Unable to retrieve row count from DuckDB schema query")
        row_count = row_count_row[0]

        column_profiles: list[dict[str, Any]] = []
        for col_name, col_type, nullable, *_ in schema_rows:
            col_ident = quote_identifier(str(col_name))

            null_count_row = con.execute(
                f"SELECT COUNT(*) FROM csv_data WHERE {col_ident} IS NULL"
            ).fetchone()
            distinct_count_row = con.execute(
                f"SELECT COUNT(DISTINCT {col_ident}) FROM csv_data"
            ).fetchone()

            if null_count_row is None or distinct_count_row is None:
                raise RuntimeError(
                    f"Unable to profile column '{col_name}' in DuckDB schema query"
                )

            null_count = null_count_row[0]
            distinct_count = distinct_count_row[0]

            column_profiles.append(
                {
                    "name": col_name,
                    "data_type": col_type,
                    "nullable": nullable == "YES",
                    "null_count": null_count,
                    "non_null_count": row_count - null_count,
                    "distinct_count": distinct_count,
                }
            )

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    return {
        "answer": f"Schema for {csv_path.name} has {len(column_profiles)} columns and {row_count} rows.",
        "assumptions": [
            "Schema is inferred by DuckDB read_csv_auto and may coerce CSV values."
        ],
        "source_refs": [f"workshop/data/{csv_path.name}"],
        "confidence": "high",
        "followups": [
            "Use query_csv with table alias csv_data to filter/aggregate these columns."
        ],
        "row_count": row_count,
        "columns": column_profiles,
        "elapsed_ms": elapsed_ms,
    }


def error_payload(message: str, file_path: str, tool_name: str) -> dict[str, Any]:
    source_ref = (
        f"workshop/data/{Path(file_path).name}" if file_path else "workshop/data"
    )
    if tool_name == "describe_csv_schema":
        followups = [
            "Use a valid CSV path under workshop/data (for example `depots.csv`)."
        ]
    else:
        followups = [
            "Use a valid CSV path under workshop/data and a single read-only SELECT/WITH query on csv_data."
        ]

    return {
        "error_code": "TOOL_EXECUTION_ERROR",
        "error_message": message,
        "source_refs": [source_ref],
        "confidence": "low",
        "followups": followups,
    }


@mcp.tool(
    name="query_csv",
    description=QUERY_CSV_TOOL_DESCRIPTION,
)
def query_csv(file_path: str, query: str) -> dict[str, Any]:
    """
    Run one safe SQL query against one CSV registered as `csv_data`.

    Args:
        file_path: Relative path to CSV under `workshop/data` (for example `depots.csv`).
        query: One read-only SQL statement (`SELECT`/`WITH`) referencing `csv_data`.
    """
    try:
        return execute_csv_query(file_path=file_path, query=query)
    except Exception as exc:  # pragma: no cover - covered via behavior tests
        return error_payload(str(exc), file_path, tool_name="query_csv")


@mcp.tool(
    name="describe_csv_schema",
    description=DESCRIBE_CSV_SCHEMA_TOOL_DESCRIPTION,
)
def describe_csv_schema(file_path: str) -> dict[str, Any]:
    """
    Return inferred schema and basic profiling statistics for one CSV.

    Args:
        file_path: Relative path to CSV under `workshop/data` (for example `depots.csv`).
    """
    try:
        return execute_describe_csv_schema(file_path=file_path)
    except Exception as exc:  # pragma: no cover - covered via behavior tests
        return error_payload(str(exc), file_path, tool_name="describe_csv_schema")


if __name__ == "__main__":
    mcp.run(transport="stdio")
