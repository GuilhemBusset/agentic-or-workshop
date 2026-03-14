# Prompt Used (Single Agent, LP-Only)

Solve the problem described in `workshop/materials/part-01-explorer-paradigm/00-problem/exercise-statement.md` using data from `workshop/data/` (depots.csv, towns.csv, arcs.csv, scenarios.csv, scenario_demands.csv). **Do not read any other files in the repository — no other scripts, no other prompts, no other results.**

Write a single Python script that solves the disaster-relief transportation LP:
- Read all data from the CSVs.
- Use `xpress` to build and solve a minimum-cost transportation LP with continuous variables only.
- All depots are active (no facility-location decisions).
- Add shortage penalties for unmet demand and a CVaR risk term.
- Critical towns must receive at least 95% of their demand in every scenario.
- Print solver status, objective, cost breakdown, and top shipment lanes.

Produce a single executable Python file using `xpress`, `csv`, and `pathlib`. Run with `uv run python workshop/materials/part-02-build-multi-agent/00-single-agent-LP/run_single_agent_lp.py`.
