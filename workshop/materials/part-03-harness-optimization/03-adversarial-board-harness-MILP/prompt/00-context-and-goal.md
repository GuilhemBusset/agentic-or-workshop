# 00 - Execution Prompt (Adversarial Board Harness, MILP)

You are a coding agent. Execute this task end-to-end with zero prior chat/session context.

## Primary Goal
Solve the disaster-relief MILP and deliver an **adversarial board harness** that:
1. Generates multiple candidate plans,
2. Stress-tests each plan adversarially,
3. Applies explicit board scoring/selection rules,
4. Selects and explains a transparent winner.

This is not unit-test-only and not contract-regression-only.
Governance-style candidate competition and board selection are mandatory.

## Canonical Problem Source
Use this as source of truth:
`workshop/materials/part-01-explorer-paradigm/00-problem/exercise-statement.md`

## Self-Contained Problem Summary
Model a disaster-relief network with:
- 6 candidate depots, 12 towns, 8 demand scenarios with probabilities.
- Binary depot-open design decisions.
- Scenario recourse shipment and unmet-demand decisions.
- Critical towns exactly `T03`, `T04`, `T07`, `T12`, each requiring at least 95% service in every scenario.
- Capacity usable only when depot is open.
- Objective with fixed opening + expected transport + expected shortage penalty + CVaR-style shortage risk.

## Data Inputs
Read only these files from:
`workshop/data/`
- `depots.csv`
- `towns.csv`
- `arcs.csv`
- `scenarios.csv`
- `scenario_demands.csv`

## Workspace Scope (Mandatory)
Work only in:
`workshop/materials/part-03-harness-optimization/03-adversarial-board-harness-MILP/`

Do not modify unrelated files.
Do not depend on prior run logs or previous harness outputs.

## Access and Discovery Guardrails (Mandatory)
- Allowed reads outside target folder are limited to:
  - `workshop/materials/part-01-explorer-paradigm/00-problem/exercise-statement.md`
  - `workshop/data/depots.csv`
  - `workshop/data/towns.csv`
  - `workshop/data/arcs.csv`
  - `workshop/data/scenarios.csv`
  - `workshop/data/scenario_demands.csv`
- Do not run broad repository scans (for example recursive `rg` over `workshop/materials`).
- Do not inspect other harness folders as implementation references.
- Do not delete, rename, or truncate pre-existing files in this folder (including historical `agent-run-logs/*`).
- Even if required artifacts already exist, rewrite them in this run from this prompt’s requirements (do not treat existing implementations as final).

## Required Artifacts
1. Script:
`workshop/materials/part-03-harness-optimization/03-adversarial-board-harness-MILP/run_adversarial_board_harness_milp.py`
2. Tests:
`workshop/materials/part-03-harness-optimization/03-adversarial-board-harness-MILP/tests/test_adversarial_board_harness_milp.py`
3. Deterministic report:
`workshop/materials/part-03-harness-optimization/03-adversarial-board-harness-MILP/adversarial_board_report.json`

## Required Candidate Set (Deterministic)
Create at least 3 candidates with fixed deterministic policy parameters:
- `candidate_cost_lean`
- `candidate_balanced`
- `candidate_resilience`

Candidates must differ by explicit risk/cost tradeoff settings (for example CVaR weight and/or shortage penalty multipliers).
Document exact parameter values in report.

## Per-Candidate Contract Checks (Mandatory)
For each candidate, run and report pass/fail for:
- `C01_model_class_milp`
- `C02_binary_open_decisions`
- `C03_critical_towns_exact`
- `C04_critical_service_floor`
- `C05_capacity_only_if_open`
- `C06_objective_component_consistency`
- `C07_probability_contract`
- `C08_solver_status_ok`

Any candidate failing contract checks remains in report but is marked ineligible for board win.

## Adversarial Stress Evaluation (Mandatory)
For every contract-eligible candidate:
- Freeze its depot-open design.
- Apply deterministic stressed demand multiplier `1.20` to all town-scenario demands.
- Re-optimize recourse only.
- Record stress metrics: total unmet demand, critical unmet demand, stressed objective/components, status.

## Board Scoring and Winner Selection (Mandatory)
Use explicit deterministic scoring for each contract-eligible candidate:

`board_score = 0.40 * normalized_baseline_objective + 0.35 * normalized_stressed_total_unmet + 0.20 * normalized_stressed_critical_unmet + 0.05 * normalized_open_depot_count`

Rules:
- Lower score is better.
- Normalization must be deterministic and documented in code/report.
- In ties (within tolerance), break by:
  1) lower stressed critical unmet,
  2) lower stressed total unmet,
  3) lexicographic candidate id.
- If zero candidates are contract-eligible, fail harness with explicit diagnostics.

## Tests Must Cover
At minimum, tests must verify:
- report contains all candidates with parameters, contract results, stress metrics, board score.
- at least three deterministic candidates are evaluated.
- board scoring formula and tie-break logic are applied.
- winner is contract-eligible.
- deterministic winner and scores across repeated runs.

## Runtime Commands (from repo root)
```bash
uv sync
uv run pytest workshop/materials/part-03-harness-optimization/03-adversarial-board-harness-MILP/tests -q
uv run python workshop/materials/part-03-harness-optimization/03-adversarial-board-harness-MILP/run_adversarial_board_harness_milp.py
```

## Mandatory Iteration Loop
Repeat until all completion criteria pass:
1. Implement or refine code/tests.
2. Run required commands.
3. If any check/test fails, fix root cause.
4. Re-run commands.
5. Stop only when all artifacts/checks are green.

Do not stop after first feasible solve if board behavior is incomplete.

## Completion Criteria (All Required)
- Tests pass.
- Script runs successfully.
- Output includes per-candidate contract status, adversarial stress metrics, board scores, and final winner.
- `adversarial_board_report.json` exists and is deterministic with transparent winner diagnostics.
- Winner selection is reproducible and justified by explicit board rules.
