# Part 03 - Harness Optimization (MILP, Controlled Context)

This section keeps the same disaster-relief optimization problem, but moves from LP-style modeling to a true MILP with binary depot-open decisions.

The goal is to show how harness design changes development confidence, failure detection, and policy selection while keeping the solver context controlled and explicit.

## Controlled Context (shared across harnesses)
All harnesses enforce the same core modeling contract:
- Binary `open_depot` decisions.
- Scenario-wise shipment and unmet-demand recourse.
- Critical-town service floor for `T03`, `T04`, `T07`, `T12`.
- Objective built from fixed opening cost, expected transport, expected shortage penalty, and CVaR-style shortage risk.

## Harnesses in this folder
- `01-unit-test-harness-MILP`: fastest harness, validates local invariants immediately after one solve.
- `02-contract-regression-harness-MILP`: adds explicit contract checks plus deterministic regression scenarios (all-open baseline, perturbation checks, stressed demand recourse).
- `03-adversarial-board-harness-MILP`: evaluates multiple candidate policies, stress-tests each, and uses a deterministic board-scoring rule to select a winner.

## What is different between these harnesses?
- `01-unit-test-harness-MILP`:
  - Scope: one model + one direct validation pass.
  - Strength: quick feedback loop during implementation.
  - Weakness: narrower coverage of regressions and selection tradeoffs.
- `02-contract-regression-harness-MILP`:
  - Scope: baseline model plus contract/regression matrix.
  - Strength: stronger confidence against silent regressions.
  - Weakness: more checks to maintain as contract evolves.
- `03-adversarial-board-harness-MILP`:
  - Scope: multi-candidate generation, stress evaluation, board decision.
  - Strength: makes tradeoffs explicit and reproducible at policy-selection time.
  - Weakness: highest complexity and longest runtime.

## Other harness approaches to consider
- Property-based harnesses: generate many randomized but contract-valid instances and assert invariant families.
- Metamorphic harnesses: assert directional behavior under structured perturbations (e.g., higher demand should not reduce unmet shortage under fixed design).
- Scenario fuzzing harnesses: adversarially synthesize extreme scenario mixes to probe robustness.
- Historical backtesting harnesses: replay archived instances and compare current outputs to locked baselines.
- Differential solver harnesses: solve with multiple MILP backends and compare objective/components within tolerance.
- Cost-of-failure harnesses: rank candidate solutions by explicit consequence models, not only objective value.

## How to run
From repo root:

```bash
uv run python workshop/materials/part-03-harness-optimization/01-unit-test-harness-MILP/run_unit_test_harness_milp.py
uv run python workshop/materials/part-03-harness-optimization/02-contract-regression-harness-MILP/run_contract_regression_harness_milp.py
uv run python workshop/materials/part-03-harness-optimization/03-adversarial-board-harness-MILP/run_adversarial_board_harness_milp.py
uv run python workshop/materials/part-03-harness-optimization/compare_all_harnesses.py
```

`compare_all_harnesses.py` auto-discovers and runs all harness solver scripts in this folder (`*/run_*.py` with `harness` in path), then prints a normalized comparison table.
