# Prompt

Solve the disaster-relief transportation problem described in `workshop/materials/part-01-explorer-paradigm/00-problem/exercise-statement.md` using the CSV data files in `workshop/data/` (depots.csv, towns.csv, arcs.csv, scenarios.csv, scenario_demands.csv).

Structure your solution as a manager orchestrating specialized sub-agents, where each sub-agent handles a single concern:

- A **planner** sub-agent that selects the risk parameters: shortage_penalty=15.0, cvar_alpha=0.85, risk_weight=20.0.
- A **data** sub-agent that loads all inputs from the CSV files using Python's csv module.
- A **prompt writer** sub-agent that produces a formal contract specifying the model must be pure LP -- continuous variables only, no integer/binary decisions, all depots active, and critical towns (T03, T04, T07, T12) must receive at least 95% service.
- An **executor** sub-agent that builds and solves the LP model using xpress. It should refuse to proceed if the contract specifies anything that would make the model a MILP.
- A **tester** sub-agent that validates the solution: solver status is LP-optimal, no integer variables exist, all depots are active, critical service constraints are met, and the objective decomposes correctly into transport cost + shortage penalty + risk term.
- A **reporter** sub-agent that prints the final results.

The manager calls each sub-agent in sequence, passing outputs between them. Keep everything in a single Python file runnable with `uv run python <script.py>`.
