# Coding Agents for Optimization Research

This repository contains workshop material for teaching PhD students in optimization research how to use coding agents effectively.

## Session Goal

Learn to use coding agents with confidence, choose the right interaction pattern for each engineering task, and ship production-minded workflows.

## Who This Is For

- PhD students and researchers in optimization
- Engineers who want practical agent-assisted coding workflows
- Participants looking for hands-on workshop material

## What You Should Get From This Repo

- Confidence collaborating with coding agents
- A playbook for choosing the right prompting/interaction pattern
- A reliable local setup that can run workshop exercises and checks

## Repository Entry Points

- Workshop guide: [workshop/README.md](workshop/README.md)
- Session goal page: [workshop/introduction/00-session-goal.html](workshop/introduction/00-session-goal.html)
- Non-regression checks: `tests/non_regression/`

## Quick Start

From the repository root (after installing `mise` and `uv`; see full setup below):

```bash
eval "$(mise activate bash)"   # use zsh/fish variant if needed
mise install
uv sync
uv run pytest tests/non_regression -q
```

If this passes, your workshop environment is ready.

## Full Setup (Step by Step)

### 1. Install `mise`

Official docs: https://mise.jdx.dev/getting-started.html

Activate it in your current shell and verify:

```bash
eval "$(mise activate bash)"
mise --version
```

### 2. Install project Python (3.12)

This repository pins Python via `.mise.toml` and `.python-version`.

```bash
mise install
mise exec -- python --version
```

Expected output: `Python 3.12.x`.

### 3. Install `uv`

Official docs: https://docs.astral.sh/uv/getting-started/installation/

```bash
uv --version
```

### 4. Install project dependencies

```bash
uv sync
```

### 5. Install Codex and/or Claude Code CLI

Use official documentation for installation and authentication:

- OpenAI - Codex CLI docs: https://developers.openai.com/codex/quickstart?setup=cli
- Anthropic - Claude Code docs: https://code.claude.com/docs/en/overview

Verify CLI availability:

```bash
codex --version    # if using Codex CLI
claude --version   # if using Claude Code CLI
```

Quick smoke checks:

```bash
codex --help    # if using Codex CLI
claude --help   # if using Claude Code CLI
```

### 6. Verify everything runs

Baseline verification (recommended for all workshop participants):

```bash
uv run python --version
uv run pytest tests/non_regression -q
uv run pytest -q
```

Additional contributor checks:

```bash
uv run ruff check .
uv run ty check
```

Note: `uv run ty check` may report diagnostics in some workshop exercises; see [AGENTS.md](AGENTS.md) for contributor workflow expectations.

### 7. Run workshop material

Most runnable scripts are under `workshop/materials/**/run_*.py`.

```bash
uv run python workshop/materials/<module>/run_<exercise>.py
```

## Optional: Xpress Solver Check

`xpress` is proprietary/commercial software. See [THIRD_PARTY.md](THIRD_PARTY.md) for licensing details.

```bash
uv run python -c "import xpress; print(xpress.__version__)"
uv run python -c "import xpress as xp; p=xp.problem(name='license_check'); x=p.addVariable(name='x'); p.setObjective(x, sense=xp.minimize); p.addConstraint(x>=1); p.solve(); print(p.getProbStatusString())"
```

## References

- Contributor and agent workflow details: [AGENTS.md](AGENTS.md)