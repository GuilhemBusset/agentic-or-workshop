# Prompt Used (Team of Agents, LP-Only, Zero-Context)

Use a **team of agents** to solve the problem described in `workshop/materials/part-01-explorer-paradigm/00-problem/exercise-statement.md` using data from `workshop/data/` (depots.csv, towns.csv, arcs.csv, scenarios.csv, scenario_demands.csv). **Do not read any other files in the repository — no other scripts, no other prompts, no other results.** Each agent is spawned sequentially, with the output of one feeding the next.

## Agent 1 — Problem Analyst
Read the problem statement and all data files. Understand the structure, relationships, constraints, and objectives. Produce a detailed analysis document covering: what the data contains (schemas, ranges, relationships between files), what the optimization problem is, what risk modeling is needed, and what outputs the final script should produce. This agent does not write code — it writes the problem understanding that all downstream agents will build on. Its output must be self-contained so that no downstream agent needs to re-read the data files.

## Agent 2 — Task Architect
Using only Agent 1's analysis (do not read the data files), produce a detailed technical specification for a production-grade Python script. Production-grade means: frozen dataclasses with full type annotations for all data structures and function signatures, single-responsibility functions, validated inputs, named constraints for traceability, and a clean `main()` entry point. The specification should define every module boundary, every data structure, every function signature, and the expected printed output format. This agent does not write code — it writes the blueprint.

## Agent 3 — Implementor
Using Agent 2's specification, implement the full script. Follow the spec exactly: data structures, function signatures, constraint naming, output format. Use `xpress` as the solver. Continuous variables only, all depots active. The script must be a single executable Python file using only `xpress`, `csv`, and `pathlib`.

## Agent 4 — Reviewer
Review the implemented script against Agent 2's specification. Verify: all spec requirements are met, type annotations are correct and complete, naming is consistent, no duplicated logic, no prompt concepts ("agent", "team", "board") leak into the code. Fix any issues and produce the final version.

Run with `uv run python workshop/materials/part-02-build-multi-agent/02-team-of-agents-LP/run_team_agents_lp.py`.
