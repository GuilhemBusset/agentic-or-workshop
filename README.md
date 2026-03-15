# Coding Agents for Optimization Research

Workshop material for teaching PhD students in optimization research how to use coding agents effectively.

## Session Goal

Learn to use coding agents with confidence, choose the right interaction pattern for each engineering task, and ship production-minded workflows.

## Who This Is For

- PhD students and researchers in optimization
- Engineers who want practical agent-assisted coding workflows
- Participants looking for hands-on workshop material

## What You Will Learn

- Confidence collaborating with coding agents
- A playbook for choosing the right prompting/interaction pattern
- How agent team structure (single, sub-agent, team) affects implementation quality
- Three quality-assurance paradigms for optimization code (unit-test, metamorphic, adversarial board)

## Prerequisites

| Tool | Purpose | Install docs |
|------|---------|-------------|
| [mise](https://mise.jdx.dev/getting-started.html) | Python version management | `curl https://mise.jdx.dev/install.sh \| sh` |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Python package & environment management | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Claude Code CLI](https://code.claude.com/docs/en/overview) | Anthropic coding agent | See official docs |
| [Codex CLI](https://developers.openai.com/codex/quickstart?setup=cli) | OpenAI coding agent (optional) | See official docs |

## Quick Start

```bash
# 1. Activate mise and install pinned Python 3.12
eval "$(mise activate bash)"   # use zsh/fish variant if needed
mise install

# 2. Install all project dependencies
uv sync

# 3. Verify the environment
uv run pytest tests/non_regression -q
```

If the tests pass, your workshop environment is ready.

## Full Setup (Step by Step)

### 1. Install and activate `mise`

```bash
eval "$(mise activate bash)"
mise --version
```

### 2. Install project Python (3.12)

The repository pins Python 3.12 via `.mise.toml` and `.python-version`.

```bash
mise install
mise exec -- python --version   # expect Python 3.12.x
```

### 3. Install `uv`

```bash
uv --version
```

### 4. Install project dependencies

```bash
uv sync
```

This creates a virtual environment and installs all runtime and dev dependencies from `pyproject.toml`.

> **Note:** Always use `uv` for dependency management. Do not use `pip install` or manual `venv` commands -- they bypass the lockfile and can cause version mismatches.

### 5. Install a coding agent CLI

Install at least one of the following and authenticate:

```bash
# Claude Code
claude --version
claude --help

# Codex (optional)
codex --version
codex --help
```

### 6. Set up pre-commit hooks

```bash
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

Pre-commit enforces:
- **Non-regression tests** must pass before every commit
- **Conventional commit messages** in the format `type(scope): description`
  - Allowed types: `feat`, `fix`, `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `perf`, `test`, `revert`
  - Example: `feat(part-02): add CSV data loader`

### 7. Verify everything works

```bash
uv run python --version          # Python 3.12.x
uv run pytest tests/non_regression -q   # non-regression checks
uv run pytest -q                 # full test suite
uv run ruff check .              # linter
uv run ruff format --check .     # formatting check
uv run ty check                  # type checker
```

## Workshop Curriculum

### Part 0 -- Fundamentals

| Module | Topic | Format |
|--------|-------|--------|
| `00-llm-architecture` | Autoregressive token generation, attention, KV cache | Interactive slides |
| `01-context-window` | Context window management in agentic systems | Interactive lab |
| `02-prompt-quality` | Prompt quality progression (mediocre -> normal -> great) | Lecture + lab |
| `03-coding-agent` | Agent architecture, reliability controls, workflow | Guide |

### Part 1 -- Explorer Paradigm

| Module | Topic | Format |
|--------|-------|--------|
| `00-problem` | Disaster-relief network planning problem statement | Reading |
| `01-data-explorer` | SQL-based CSV exploration via MCP servers (DuckDB) | Tools + skills |
| `02-visual-explorer` | Interactive CSV browser (FastAPI/Uvicorn) | Interactive lab |

### Part 2 -- Build Multi-Agent (LP)

All three modules solve the same disaster-relief LP (continuous variables, all depots active) using different agent structures:

| Module | Paradigm | Agents |
|--------|----------|--------|
| `00-single-agent-LP` | Single prompt | 1 flat prompt |
| `01-sub-agent-LP` | Sub-agents | 4 specialized (Problem, Data, Implementer, Reviewer) |
| `02-team-of-agents-LP` | Team of agents | 4 sequential, zero shared context |

### Part 3 -- Harness Optimization (MILP)

Three quality-assurance paradigms for the same MILP (with binary depot-open decisions):

| Module | Harness | Philosophy |
|--------|---------|------------|
| `01-unit-test-harness-MILP` | Unit-test (TDD) | "I know the right answer for these cases" |
| `02-metamorphic-harness-MILP` | Metamorphic | "I don't know the exact answer, but I know how answers should relate" |
| `03-adversarial-board-harness-MILP` | Adversarial board | "I have multiple candidates -- which is best?" |

## Running Workshop Exercises

All commands run from the repository root.

```bash
# Part 2 -- LP exercises
uv run python workshop/materials/part-02-build-multi-agent/00-single-agent-LP/run_single_agent_lp.py
uv run python workshop/materials/part-02-build-multi-agent/01-sub-agent-LP/run_sub_agent_lp.py
uv run python workshop/materials/part-02-build-multi-agent/02-team-of-agents-LP/run_team_agents_lp.py

# Part 3 -- MILP harness exercises
uv run python workshop/materials/part-03-harness-optimization/01-unit-test-harness-MILP/run_unit_test_harness_milp.py
uv run python workshop/materials/part-03-harness-optimization/02-metamorphic-harness-MILP/run_metamorphic_harness_milp.py
uv run python workshop/materials/part-03-harness-optimization/03-adversarial-board-harness-MILP/run_adversarial_board_harness_milp.py

# Interactive labs (shell scripts)
bash workshop/materials/part-00-fundamental/02-prompt-quality/run_single_prompt_lab.sh
bash workshop/materials/part-01-explorer-paradigm/02-visual-explorer/run_visual_explorer_lab.sh

# Validate the dataset
uv run python workshop/data/validate_data.py
```

## Dataset

The workshop uses a disaster-relief network planning problem:

- **6 depots**, **12 towns** (4 critical: T03, T04, T07, T12), **8 scenarios**
- Data files live in `workshop/data/`: `depots.csv`, `towns.csv`, `arcs.csv`, `scenarios.csv`, `scenario_demands.csv`
- Critical towns must receive >=95% of demand
- Validate with: `uv run python workshop/data/validate_data.py`

See [workshop/data/README.md](workshop/data/README.md) for the full specification.

## Common Commands Reference

| Task | Command |
|------|---------|
| Sync environment | `uv sync` |
| Run a script | `uv run python <path>` |
| Run all tests | `uv run pytest` |
| Run non-regression tests | `uv run pytest tests/non_regression -q` |
| Run a specific test file | `uv run pytest <path/to/test_file.py>` |
| Run exercise-specific tests | `uv run pytest workshop/materials/<module>/tests/` |
| Format code | `uv run ruff format .` |
| Lint code | `uv run ruff check .` |
| Auto-fix lint issues | `uv run ruff check --fix .` |
| Type check | `uv run ty check` |
| Add a dependency | `uv add <package>` |
| Add a dev dependency | `uv add --dev <package>` |
| Update lockfile | `uv lock` |
| Validate dataset | `uv run python workshop/data/validate_data.py` |

## Quality Gate (Before PR/Commit)

> **Note:** Pre-commit hooks only run non-regression tests and commit message validation -- not the full quality gate. Run the checks below manually before opening a PR.

```bash
uv sync
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest
uv run pytest tests/non_regression -q   # if workshop behavior changed
```

## Project Structure

```
.
├── AGENTS.md                  # Agent/contributor guidelines
├── CLAUDE.md                  # Claude Code configuration
├── THIRD_PARTY.md             # Third-party license notes (xpress)
├── pyproject.toml             # Project metadata and dependencies
├── uv.lock                   # Locked dependency versions
├── .mise.toml                # Python 3.12 pin
├── .python-version           # Python version for tooling compatibility
├── .pre-commit-config.yaml   # Non-regression + commit-msg hooks
├── tests/
│   └── non_regression/       # Snapshot & contract tests for workshop code
└── workshop/
    ├── README.md             # Workshop index
    ├── introduction/         # Session goal + intro slides
    ├── data/                 # CSV dataset + validator
    └── materials/
        ├── part-00-fundamental/         # LLM basics, prompts, agents
        ├── part-01-explorer-paradigm/   # Problem & data exploration
        ├── part-02-build-multi-agent/   # LP with 3 agent paradigms
        ├── part-03-harness-optimization/ # MILP with 3 QA harnesses
        └── shared/                      # Styling guidelines
```

## Xpress Solver (Optional)

The workshop uses the [FICO Xpress](https://www.fico.com/en/products/fico-xpress-optimization) solver. This is proprietary software -- see [THIRD_PARTY.md](THIRD_PARTY.md) for licensing details.

```bash
# Check if xpress is available
uv run python -c "import xpress; print(xpress.__version__)"

# Run a license/solver smoke test
uv run python -c "
import xpress as xp
p = xp.problem(name='license_check')
x = p.addVariable(name='x')
p.setObjective(x, sense=xp.minimize)
p.addConstraint(x >= 1)
p.solve()
print(p.getProbStatusString())
"
```

## Dependencies

### Runtime

| Package | Purpose |
|---------|---------|
| `xpress` | FICO Xpress optimization solver |
| `pulp` | Open-source LP/MILP modeling |
| `duckdb` | In-process SQL engine for CSV data exploration |
| `fastapi` | Web framework for interactive labs |
| `uvicorn` | ASGI server for FastAPI |
| `mcp` | Model Context Protocol tooling |
| `rich` | Terminal formatting and output |

### Development

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `ruff` | Linter and formatter |
| `ty` | Type checker |
| `pre-commit` | Git hook management |

## References

- Workshop guide: [workshop/README.md](workshop/README.md)
- Dataset specification: [workshop/data/README.md](workshop/data/README.md)
- Contributor guidelines: [AGENTS.md](AGENTS.md)
- Third-party licenses: [THIRD_PARTY.md](THIRD_PARTY.md)
- Session goal: [workshop/introduction/00-session-goal.html](workshop/introduction/00-session-goal.html)

## License

[MIT](LICENSE)
