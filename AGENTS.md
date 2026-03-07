# Repository Guidelines

## Purpose
This repo is used to teach agentic coding to PhD students in optimization research.

## Environment and Toolchain
This project is `uv`-managed and uses `mise` for Python version management.
- Python compatibility is `>=3.12` (`requires-python`).
- Workshop shells are pinned to `3.12` via `.mise.toml` and `.python-version`.
- Use `uv` for setup, dependency management, and command execution.
- Do not use `pip install` or manual `venv` commands for normal workflow.

## Project Shape
- There is no single `main.py` entrypoint at the repository root.
- Most runnable scripts live under `workshop/materials/**/run_*.py`.
- Tests live under `tests/` and `workshop/materials/**/tests/`.
- Non-regression coverage lives in `tests/non_regression/`.

## Task-Scoped Navigation (Workshop Rule)
- Treat the user prompt as the navigation boundary.
- Only explore files/directories explicitly mentioned in the prompt.
- If the prompt says "work in `abc/`", only read/edit within `abc/` and its children.
- Do not run repository-wide discovery commands (`rg --files`, `find .`, broad `ls -R`) unless explicitly requested.
- If additional context outside the boundary is required, stop and ask for permission before expanding scope.
- If no path is provided, ask the user for the target folder/file before exploring.
- Prefer targeted commands, for example:
  - `ls abc`
  - `rg "pattern" abc`
  - `uv run pytest abc/tests`

## Standard Workflow
1. Activate `mise` in your shell.
2. Sync environment: `uv sync`
3. Run target script: `uv run python <path-to-runner.py>`
4. Add a dependency: `uv add <package>`
5. Add a dev dependency: `uv add --dev <package>`
6. Update lockfile after dependency changes: `uv lock`
7. Format code: `uv run ruff format .`
8. Lint code: `uv run ruff check .`
9. Type check code: `uv run ty check`

## Testing
- Preferred framework: `pytest`.
- Place tests in `tests/` or `workshop/materials/**/tests/` with names `test_*.py`.
- Run the full suite with: `uv run pytest`
- Run non-regression checks with: `uv run pytest tests/non_regression -q`
- When possible, run targeted tests first (`uv run pytest <path>`), then the full suite.

## Quality Gate (Before PR/Commit)
1. `uv sync`
2. `uv run ruff format .`
3. `uv run ruff check .`
4. `uv run ty check`
5. `uv run pytest`
6. If workshop behavior changed: `uv run pytest tests/non_regression -q`

Current `pre-commit` runs non-regression checks only (`uv run pytest tests/non_regression -q`), not the full quality gate.

## Style
- Python `>=3.12`.
- Follow PEP 8 with 4-space indentation.
- Use `snake_case` for functions/variables and `PascalCase` for classes.
- Keep modules small and single-purpose.
- Use type hints for new/modified Python code where practical.
