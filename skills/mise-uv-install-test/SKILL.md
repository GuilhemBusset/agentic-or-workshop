---
name: mise-uv-install-test
description: Provision and verify this uv-managed Python project using mise and uv. Use when asked to install dependencies, bootstrap the pinned Python toolchain, sync the lockfile environment, and confirm tests pass with pytest in this repository.
---

# Mise UV Install Test

Run the repository setup and verification flow exactly in this order.

## Workflow

1. Activate mise in the shell:
```bash
eval "$(mise activate bash)"
```
2. Install the pinned toolchain from `.mise.toml`:
```bash
mise install
```
3. Ensure `uv` is available. Prefer `uv` on PATH; otherwise use `mise exec`:
```bash
uv --version || mise install uv
```
4. Sync project dependencies from `uv.lock`:
```bash
uv sync
```
Fallback for restricted sandboxes:
```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync
```
5. Run tests:
```bash
uv run pytest
```
Fallback for restricted sandboxes:
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest
```

## Scripted Path

Use `scripts/install_and_test.sh` to run the full workflow in one command:
```bash
bash skills/mise-uv-install-test/scripts/install_and_test.sh
```

## Reporting

Report:
- whether toolchain install succeeded,
- whether dependency sync succeeded,
- test summary (`N passed`, failures, and warnings).

If a step fails, include the failing command and the shortest actionable fix.
