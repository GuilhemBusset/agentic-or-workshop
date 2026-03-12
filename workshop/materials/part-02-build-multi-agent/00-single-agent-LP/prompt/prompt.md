# Prompt Used (Single Agent, LP-Only)

Read the problem statement in `workshop/materials/part-01-explorer-paradigm/00-problem/exercise-statement.md` and the data files in `workshop/data/`.

Write a single Python script that solves the disaster-relief transportation LP:
- Read all data from the CSVs (depots, towns, arcs, scenarios, scenario_demands).
- Use `xpress` to build and solve a minimum-cost transportation LP with continuous variables only.
- All depots are active (no facility-location decisions).
- Add shortage penalties for unmet demand and a CVaR risk term.
- Critical towns must receive at least 95% of their demand in every scenario.
- Print solver status, objective, cost breakdown, and top shipment lanes.
