# Prompt Used (Team of Agents, LP-Only, Zero-Context)

Read the disaster-relief problem statement at `workshop/materials/part-01-explorer-paradigm/00-problem/exercise-statement.md` and the data files in `workshop/data/` (depots.csv, towns.csv, arcs.csv, scenarios.csv, scenario_demands.csv).

Solve this problem using a **team-of-agents** paradigm: create three competing solution pods, each with a different risk posture. Every pod has its own model builder, tester, and writer. A board then evaluates all pods and picks the best one.

The three pods should use these configurations:
- **Pod A (cost-focused)**: risk_weight=10.0, shortage_penalty=8.0
- **Pod B (balanced)**: risk_weight=24.0, shortage_penalty=12.0
- **Pod C (risk-averse)**: risk_weight=40.0, shortage_penalty=20.0

All pods share cvar_alpha=0.80 and critical_service_floor=0.95.

Each pod must build a pure LP model (continuous variables only, no binary/integer variables). All depots stay active -- do not optimize depot-opening decisions. Critical towns (T03, T04, T07, T12) must receive at least 95% of their demand. Use `xpress` as the solver. Per-scenario demands come directly from `scenario_demands.csv`.

Each pod's tester verifies: LP-optimal status, no integer variables, all depots active, literal intent respected, critical service met, and objective consistency.

The board selects among contract-respecting candidates using the governance score:
`governance_score = expected_transport + expected_penalty + 15.0 * worst_scenario_unmet`

Output a comparison table of all candidates (showing risk_weight, shortage_penalty, objective, governance score), then print the selected plan details: candidate name, risk weight, shortage penalty, objective, depot list, cost breakdown, CVaR indicator, contract/tester status, and top expected shipment lanes.

Produce a single executable Python file using `xpress`, reading data from CSV files via `csv` and `pathlib`. Run with `uv run python <script.py>`.
