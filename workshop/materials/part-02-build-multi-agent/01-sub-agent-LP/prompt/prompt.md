# Prompt

Solve the problem described in `workshop/materials/part-01-explorer-paradigm/00-problem/exercise-statement.md` using data from `workshop/data/` (depots.csv, towns.csv, arcs.csv, scenarios.csv, scenario_demands.csv). **Do not read any other files in the repository — no other scripts, no other prompts, no other results.**

Break the work into specialized sub-agents. Each sub-agent focuses on one concern and goes deeper than a single flat prompt would. You orchestrate them as you see fit — sequentially, in parallel where dependencies allow, or a mix of both.

## Sub-agent 1 — Problem Understander
Read and analyse the problem statement. Identify the optimization structure, decision variables, constraints, objective components, and risk modeling requirements. Produce a thorough problem analysis that downstream sub-agents will build on.

## Sub-agent 2 — Data Understander
Read and analyse all data files. Understand the structure, relationships, ranges, and edge cases. Identify what validation checks are needed, what derived statistics would be useful, and how the data maps to the problem formulation.

## Sub-agent 3 — Implementer
Using the problem and data understanding, implement a complete Python script. Use `xpress` as the solver. Continuous variables only, all depots active. The script should reflect the depth of understanding from the previous sub-agents — richer validation, deeper analysis, more comprehensive reporting than a naive single-pass implementation would produce.

## Sub-agent 4 — Reviewer
Review the implemented script against the problem and data analyses. Verify correctness, completeness, and code quality. Fix any issues. Ensure no prompt concepts ("sub-agent", "manager", "pipeline") leak into the code — it should read as clean, natural Python with a clear `main()`.

Produce a single executable Python file using `xpress`, `csv`, and `pathlib`. Run with `uv run python workshop/materials/part-02-build-multi-agent/01-sub-agent-LP/run_sub_agent_lp.py`.
