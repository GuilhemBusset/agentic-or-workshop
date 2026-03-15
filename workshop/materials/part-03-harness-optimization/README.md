# Part 03 - Harness Optimization (MILP)

This section keeps the same disaster-relief optimization problem, but moves from LP-style modeling to a true MILP with binary depot-open decisions.

The goal is to show how three fundamentally different harness philosophies change development confidence, failure detection, and policy selection -- each representing a distinct axis of quality assurance for optimization code.

## Shared problem context
All harnesses solve the same MILP:
- Binary `open_depot` decisions.
- Scenario-wise shipment and unmet-demand recourse.
- Critical-town service floor for `T03`, `T04`, `T07`, `T12`.
- Objective built from fixed opening cost, expected transport, expected shortage penalty, and CVaR-style shortage risk.

## Harnesses in this folder

### `00-unit-test-harness-MILP` -- Specification-driven (single prompt)
Write tests first, implement solver until all tests pass. Validates absolute correctness of a single solve against known expected properties: data shapes, critical town sets, solver status, objective structure.

- **Philosophy**: "I know the right answer for these cases."
- **Agentic paradigm**: Single prompt.

### `01-metamorphic-harness-MILP` -- Relational correctness (sub-agents)
Solve a baseline, apply structured perturbations, assert that output changes follow predictable directions. For example: increasing demand must not decrease unmet shortage; reducing costs must not increase the objective. No reference solutions needed.

- **Philosophy**: "I don't know the exact answer, but I know how answers should relate."
- **Agentic paradigm**: Sub-agents.

### `02-adversarial-board-harness-MILP` -- Competitive selection (team of agents)
Generate multiple candidate solutions with different risk/cost tradeoffs, stress-test each under adversarial conditions, and select a winner through transparent deterministic scoring.

- **Philosophy**: "I have multiple candidates -- which is best?"
- **Agentic paradigm**: Team of agents.

## What makes each harness distinct?

| Dimension | Unit-Test TDD | Metamorphic | Adversarial Board |
|-----------|--------------|-------------|-------------------|
| Requires known answer? | Yes | No | No |
| Output type | Pass/Fail | Pass/Fail | Ranking |
| Tests what? | Exact behavior | Structural properties | Relative quality |
| Developer role | Specifies expected output | Specifies relations | Specifies eval criteria |
| Complexity | Low (1 solve) | Medium (N+1 solves) | High (2N solves + scoring) |

## How to run
From repo root:

```bash
uv run python workshop/materials/part-03-harness-optimization/00-unit-test-harness-MILP/run_unit_test_harness_milp.py
uv run python workshop/materials/part-03-harness-optimization/01-metamorphic-harness-MILP/run_metamorphic_harness_milp.py
uv run python workshop/materials/part-03-harness-optimization/02-adversarial-board-harness-MILP/run_adversarial_board_harness_milp.py
```
