# CSV Data Explorer MCP Server

Local MCP server for workshop CSV exploration using DuckDB and Rich.

## Tool surface

- `query_csv(file_path: str, query: str)`
  - `file_path`: relative CSV path under `workshop/data` (example: `depots.csv`)
  - `query`: a single read-only SQL statement (`SELECT` or `WITH`) that must reference `csv_data`
- `describe_csv_schema(file_path: str)`
  - `file_path`: relative CSV path under `workshop/data` (example: `depots.csv`)
  - returns inferred schema + column profiling stats for that CSV

## MCP behavior contract

- This MCP does not translate natural language to SQL.
- Codex should convert user intent into SQL, then call `query_csv`.
- One call = one CSV file.
- SQL must target `csv_data` alias only.
- Result rows are previewed (default max 50 rows), with full `row_count`.
- `describe_csv_schema` can be called first to discover column names/types before generating SQL.

## Safety rules

- Only files under `workshop/data` are allowed.
- Absolute paths and path traversal are rejected.
- Only `.csv` files are allowed.
- Only a single read-only SQL statement is allowed.
- SQL containing write/admin keywords is rejected.

## Run

From repository root:

```bash
uv run python workshop/materials/part-01-explorer-paradigm/01-data-explorer/mcp/data-explorer-csv/server.py
```

The server runs on MCP `stdio` transport.

## Example query shape

Use `query_csv` with:

- `file_path`: `depots.csv`
- `query`: `SELECT depot_id, capacity FROM csv_data ORDER BY capacity DESC LIMIT 3`

## Prompt examples (for Codex / Claude Code)

Use prompts like these in Codex or Claude Code so it calls `query_csv`:

1. `Using query_csv, show the top 3 depots by capacity from depots.csv.`
Expected tool args:
```json
{
  "file_path": "depots.csv",
  "query": "SELECT depot_id, name, capacity FROM csv_data ORDER BY capacity DESC LIMIT 3"
}
```

2. `Using query_csv, compute total demand for scenario S01 from scenario_demands.csv.`
Expected tool args:
```json
{
  "file_path": "scenario_demands.csv",
  "query": "SELECT scenario_id, SUM(demand) AS total_demand FROM csv_data WHERE scenario_id = 'S01' GROUP BY scenario_id"
}
```

3. `Using query_csv, list the 10 cheapest arcs from arcs.csv.`
Expected tool args:
```json
{
  "file_path": "arcs.csv",
  "query": "SELECT depot_id, town_id, shipping_cost, distance FROM csv_data ORDER BY shipping_cost ASC, distance ASC LIMIT 10"
}
```

4. `Using query_csv, list all high-risk scenarios with their probability from scenarios.csv.`
Expected tool args:
```json
{
  "file_path": "scenarios.csv",
  "query": "SELECT scenario_id, description, probability, risk_level FROM csv_data WHERE risk_level = 'high' ORDER BY scenario_id"
}
```

5. `Using describe_csv_schema, inspect schema for towns.csv before writing SQL.`
Expected tool args:
```json
{
  "file_path": "towns.csv"
}
```

## Prompt quality guide

Good prompt traits:
- explicitly asks to use `query_csv`
- names the source file under `workshop/data`
- states filters/grouping/sorting intent
- asks for specific output fields

Good:
- `Use query_csv on scenarios.csv and return scenario_id + probability for risk_level = 'high', sorted by probability descending.`

Weak (likely to require follow-up):
- `What is the riskiest scenario?`
- `Check costs quickly.`

When ambiguous, prefer clarifying prompts such as:
- `Use query_csv on scenario_demands.csv and compare total demand across scenarios, grouped by scenario_id.`

## Output

Success payload includes:

- `answer`
- `source_refs`
- `columns`
- `rows`
- `row_count`
- `preview_truncated`
- `rich_table`
- `elapsed_ms`
- `assumptions`
- `confidence`
- `followups`

Schema payload (`describe_csv_schema`) includes:

- `answer`
- `source_refs`
- `row_count`
- `columns` (`name`, `data_type`, `nullable`, `null_count`, `non_null_count`, `distinct_count`)
- `elapsed_ms`
- `assumptions`
- `confidence`
- `followups`

Error payload includes:

- `error_code`
- `error_message`
- `source_refs`
- `confidence`
- `followups`

## Local MCP client config example

```json
{
  "mcpServers": {
    "data-explorer-csv": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "workshop/materials/part-01-explorer-paradigm/01-data-explorer/mcp/data-explorer-csv/server.py"
      ]
    }
  }
}
```

## Codex CLI registration

For Codex CLI, register the server explicitly:

```bash
codex mcp add data-explorer-csv -- \
  uv --directory "$(git rev-parse --show-toplevel)" run python \
  workshop/materials/part-01-explorer-paradigm/01-data-explorer/mcp/data-explorer-csv/server.py
```

Verify:

```bash
codex mcp list
```

Deactivate (remove from Codex MCP registry):

```bash
codex mcp remove data-explorer-csv
```

## Claude Code CLI registration

For Claude Code CLI, register the server explicitly:

```bash
claude mcp add data-explorer-csv -- \
  uv --directory "$(git rev-parse --show-toplevel)" run python \
  workshop/materials/part-01-explorer-paradigm/01-data-explorer/mcp/data-explorer-csv/server.py
```

Verify:

```bash
claude mcp list
```

Deactivate (remove from Claude Code MCP registry):

```bash
claude mcp remove data-explorer-csv
```

## Related demo: noisy MCP risk

To demonstrate how one low-value MCP can degrade the whole experience, use:

- `workshop/materials/part-01-explorer-paradigm/01-data-explorer/mcp/context-bomb/README.md`
- server name: `data-explorer-context-bomb`
- tool: `bomb_status` (trivial), with intentionally oversized instructions
