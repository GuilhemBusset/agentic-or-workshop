# Prompt Used (Team of Agents, Adversarial Board MILP, Zero-Context)

Use a **team of agents** to build an adversarial board harness for the disaster-relief network problem described below, using data from `workshop/data/` (depots.csv, towns.csv, arcs.csv, scenarios.csv, scenario_demands.csv). **Do not read any other files in the repository -- no other scripts, no other prompts, no other results.** Each agent is spawned sequentially, with the output of one feeding the next.

## Problem

A disaster-relief supply network with 6 candidate depots, 12 towns, and 8 demand scenarios with probabilities. Binary depot-open decisions determine which depots are built. Under each scenario, shipments flow from open depots to towns along available arcs, subject to depot capacity (only usable when open). Unmet demand is penalized. Towns T03, T04, T07, and T12 are critical and must receive at least 95% of their demand in every scenario. The objective combines fixed depot opening costs, expected transport costs, expected shortage penalties, and a CVaR-based shortage risk term.

## Agent 1 -- Problem Analyst

Read all five data files. Understand schemas, ranges, relationships, and the full structure of the two-stage stochastic MILP: first-stage binary depot decisions, second-stage continuous recourse (shipments, unmet demand) per scenario. Document what makes a solution feasible (capacity linking, critical-town service floors, probability weights) and what the objective components are. Identify the levers that control risk-cost tradeoff -- CVaR confidence level, CVaR weight in the objective, shortage penalty multiplier -- and how varying them produces structurally different solutions. This agent does not write code. Its output must be self-contained so no downstream agent needs to re-read the data files.

## Agent 2 -- Harness Architect

Using only Agent 1's analysis (do not read the data files), produce a detailed technical specification for the full adversarial board pipeline. Design at least 3 candidate parameterizations that span the risk-cost spectrum by varying the CVaR weight, shortage penalty, or both, with exact parameter values so results are deterministic. For each candidate, define the MILP formulation and the outputs it must produce: open depots, objective components, per-town service levels, and solver status. Design the adversarial stress-testing phase: each candidate's depot decisions are frozen and robustness is evaluated under worsened demand conditions by re-solving recourse only. Design a deterministic scoring rule that combines baseline performance and stress resilience to rank candidates, selecting the candidate with the best overall balance of cost and robustness. Specify how the board handles the case where no candidate passes feasibility and service-level checks. This agent does not write code -- it writes the blueprint.

## Agent 3 -- Implementor

Using Agent 2's specification, implement the full harness as a single executable Python file. The script must: solve each candidate independently, run the stress test on each, compute board scores, select a winner, and write a JSON report with per-candidate metrics (parameters, objective components, service levels, stress results, board score) and the final winner with justification. Use both `xpress` and `pulp` as solver backends -- some candidates should be solved with one, some with the other -- to verify that results and rankings are solver-agnostic. The script must use only `xpress`, `pulp`, `csv`, `pathlib`, and `json`. Write a companion pytest test file that verifies: the report contains all candidates with their parameters, stress metrics, and board scores; at least three candidates are evaluated; the winner passes all service-level checks; and scores and winner are deterministic across repeated runs.

## Agent 4 -- Reviewer

Review the implemented script and tests against Agent 2's specification. Verify: all spec requirements are met, type annotations are correct and complete, naming is consistent, no duplicated logic, no prompt concepts ("agent", "team", "board harness") leak into the code, the scoring rule matches the architect's design, stress tests correctly freeze depot decisions, and the JSON report is complete. Fix any issues and produce the final versions.

Run with `uv run python workshop/materials/part-03-harness-optimization/03-adversarial-board-harness-MILP/run_adversarial_board_harness_milp.py`.

Tests with `uv run pytest workshop/materials/part-03-harness-optimization/03-adversarial-board-harness-MILP/tests/test_adversarial_board_harness_milp.py`.
