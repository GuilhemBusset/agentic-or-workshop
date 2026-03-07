# 00 - Execution Prompt (Contract + Regression Harness, MILP)

You are a coding agent. Execute end-to-end with zero prior chat/session context.

## Mission
Deliver a deterministic MILP solution plus a **contract + regression harness**.

- `contract` = enforce explicit invariants now.
- `regression` = run controlled comparisons/stress cases to detect behavioral drift.

This is not a one-shot solve.

## Canonical Problem Source
Use only this statement as optimization source-of-truth:
`workshop/materials/part-01-explorer-paradigm/00-problem/exercise-statement.md`

## Self-Contained Problem Summary
Model a disaster-relief network with:
- 6 candidate depots, 12 towns, 8 demand scenarios with probabilities.
- Binary depot-open design decisions.
- Scenario recourse shipment and unmet-demand decisions.
- Critical towns exactly `T03`, `T04`, `T07`, `T12` with minimum 95% service in every scenario.
- Depot capacity usable only if depot is open.
- Objective = fixed opening + expected transport + expected shortage penalty + CVaR-style shortage risk.

## Data Inputs
Load only these files from:
`workshop/data/`
- `depots.csv`
- `towns.csv`
- `arcs.csv`
- `scenarios.csv`
- `scenario_demands.csv`

## Workspace Scope (Hard Constraint)
Only read/write in:
`workshop/materials/part-03-harness-optimization/02-contract-regression-harness-MILP/`

Do not inspect or depend on:
- `agent-run-logs/`
- `01-unit-test-harness-MILP/`
- `03-adversarial-board-harness-MILP/`
- other workshop parts for style mining.
- any existing implementation files in this folder as authoritative references; treat this task as a fresh implementation.

## File Preservation Rule (Hard Constraint)
- Do not delete, rename, or truncate any pre-existing files in this folder (including any historical `agent-run-logs/*`).
- Only create/update the required artifacts for this task.
- Even if required artifacts already exist, rewrite them in this run from this prompt’s requirements (do not treat existing implementations as final).

## Discovery Budget (Hard Constraint)
Before coding, run only these discovery actions:
1. Read canonical problem statement once.
2. Inspect target folder once.
3. Show first 12 lines of each required CSV.

After that, start implementation immediately.
Do not run broad repo scans (`rg` over `/workshop/materials`), and do not run exploratory REPL snippets (`uv run python - <<'PY' ...`) before first implementation pass.

## Required Artifacts
1. Script:
`workshop/materials/part-03-harness-optimization/02-contract-regression-harness-MILP/run_contract_regression_harness_milp.py`
2. Tests:
`workshop/materials/part-03-harness-optimization/02-contract-regression-harness-MILP/tests/test_contract_regression_harness_milp.py`
3. Deterministic report:
`workshop/materials/part-03-harness-optimization/02-contract-regression-harness-MILP/contract_regression_report.json`

## Required Script Structure
Implement composable functions (names may vary):
- data loading + validation
- model build/solve for baseline and controlled variants
- contract checks (`contract_check_*`)
- regression checks (`regression_check_*`)
- report assembly + console summary

Use deterministic ordering everywhere.

## Contract Checks (Must Execute and Pass)
Emit explicit IDs + pass/fail:
- `C01_model_class_milp`
- `C02_critical_towns_exact`
- `C03_critical_service_floor`
- `C04_capacity_only_if_open`
- `C05_objective_component_consistency`
- `C06_probability_contract`
- `C07_solver_status_ok`

## Regression Checks (Must Execute and Pass)
Emit explicit IDs + pass/fail:

1. `R01_baseline_contract_checked_solve`
- Baseline solve + all `C01..C07`.

2. `R02_all_open_baseline_comparison`
- Forced-all-open solve/evaluation.
- Invariant: baseline objective <= all-open objective + tolerance.

3. `R03_fixed_cost_bump_perturbation`
- Bump all fixed costs by +25%.
- Re-solve bumped model.
- Invariant: bumped optimum <= baseline-design evaluated under bumped costs + tolerance.

4. `R04_stressed_demand_fixed_design_recourse`
- Freeze baseline open-depot design.
- Multiply all demands by 1.15.
- Re-optimize recourse only.
- Require feasible solve and report stressed unmet metrics.

## Test Requirements
Tests must verify:
- all required `C01..C07` and `R01..R04` IDs exist,
- report structure and deterministic key shape,
- normal run passes required checks,
- intentional objective corruption fails `C05`.

## Runtime Commands (Run Exactly)
From repo root:

```bash
uv sync
uv run pytest workshop/materials/part-03-harness-optimization/02-contract-regression-harness-MILP/tests -q
uv run python workshop/materials/part-03-harness-optimization/02-contract-regression-harness-MILP/run_contract_regression_harness_milp.py
```

## Iteration Loop (Mandatory)
Repeat until green:
1. Implement/refine artifacts.
2. Run required commands.
3. Fix any failures.
4. Re-run all commands.

Do not stop after first solve if required checks/tests are missing.

## Completion Criteria (All Required)
- Tests pass.
- Script runs successfully.
- Console output includes explicit check IDs + pass/fail + deterministic metrics.
- `contract_regression_report.json` exists and includes baseline, contract results, all-open comparison, fixed-cost bump, stressed-demand fixed-design recourse, and overall harness verdict.
- No placeholders.
