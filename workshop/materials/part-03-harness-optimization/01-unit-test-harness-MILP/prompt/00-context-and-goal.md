# 00 - Execution Prompt (Unit-Test Harness, MILP)

You are a coding agent. Execute this task end-to-end with no assumed prior context.

## Mission
Build a **unit-test harness first** for a disaster-relief MILP, then implement the solver/harness code until all tests pass.

The harness is the quality gate.  
Your goal is not "just produce MILP code"; your goal is "produce MILP code that satisfies explicit, automated tests."

## Problem Context (Self-Contained)
A humanitarian agency must serve 12 towns from 6 candidate depots under uncertain demand (8 scenarios with probabilities).

Decisions:
1. Open/close depots (binary).
2. For each scenario, route shipments from open depots to towns.
3. Allow unmet demand with penalty.

Requirements:
- Critical towns are exactly `T03`, `T04`, `T07`, `T12`.
- Critical towns must receive at least 95% service in every scenario.
- Depot capacity is usable only if the depot is open.
- Objective minimizes:
  fixed opening cost
  + expected transport cost
  + expected shortage penalty
  + CVaR-style shortage risk term.

## Data Inputs
Use CSVs in:
`workshop/data/`

Expected files include:
- `depots.csv`
- `towns.csv`
- `arcs.csv`
- `scenarios.csv`
- `scenario_demands.csv`

## Required Output Artifacts
1. Solver/harness script:
`workshop/materials/part-03-harness-optimization/01-unit-test-harness-MILP/run_unit_test_harness_milp.py`
2. Unit tests:
`workshop/materials/part-03-harness-optimization/01-unit-test-harness-MILP/tests/test_unit_test_harness_milp.py`

## Required Architecture
Implement a simple linear pipeline in the script with these functions:
- `prompt_writer_agent()`: returns a contract/spec object for the MILP intent.
- `build_data()`: loads and validates input data.
- `prompt_executor_agent(contract, data)`: builds and solves the MILP.
- `unit_test_agent(contract, summary, data)`: performs in-code invariant checks and returns pass/fail details.

Keep outputs deterministic (stable ordering, no randomness).

## Harness-First Workflow (Mandatory)
Follow strict **red -> green -> refactor**:

1. Write/replace unit tests first.
2. Run tests and confirm they fail.
3. Implement/adjust code to satisfy failing tests.
4. Re-run tests.
5. Repeat until all tests pass.
6. Run the script once to verify parseable final output.

Do not skip step 2.

## What the Tests Must Assert
Define tests that enforce at least:
- Contract declares MILP and requires binary depot-open variables.
- Data shape is correct (`6 depots`, `12 towns`, `8 scenarios`) and scenario probabilities sum to 1.
- Critical-town set matches exactly `{T03, T04, T07, T12}`.
- Executor returns a valid solve summary (status, objective, open depots, cost breakdown, unmet/risk metrics).
- In-script `unit_test_agent` passes for a valid solution.
- `unit_test_agent` fails when summary is intentionally corrupted (for example objective inconsistency).
- Executor rejects invalid contract variants (for example non-MILP model class).

## Runtime Commands
From repo root:

```bash
uv run pytest workshop/materials/part-03-harness-optimization/01-unit-test-harness-MILP/tests -q
uv run python workshop/materials/part-03-harness-optimization/01-unit-test-harness-MILP/run_unit_test_harness_milp.py
```

## Completion Criteria
Task is complete only when all are true:
- Tests pass.
- Script runs successfully.
- Output includes parseable metrics such as:
  solver status, objective, open depots/count, cost components, unmet-demand metrics, risk metric, contract respected, harness checks passed.
