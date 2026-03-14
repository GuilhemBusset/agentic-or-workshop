# Prompt

Solve a disaster-relief network MILP using data from `workshop/data/` (depots.csv, towns.csv, arcs.csv, scenarios.csv, scenario_demands.csv). **Do not read any other files in the repository.** The model decides which of 6 candidate depots to open (binary), routes shipments to 12 towns across 8 probabilistic demand scenarios, and allows penalized unmet demand. Critical towns T03, T04, T07, T12 must receive at least 95% service per scenario. The objective minimizes fixed opening cost + expected transport cost + expected shortage penalty + CVaR shortage risk.

Validate the solver with **metamorphic testing**: solve a baseline instance, then apply structured perturbations and assert that output changes follow predictable directions. Design at least three metamorphic relations -- for example: scaling up demands (with depot design fixed) must not decrease total unmet demand; reducing depot fixed costs must not increase the optimal objective; doubling depot capacities must not increase the optimal objective. Each relation solves a perturbed variant and compares against the baseline.

Break the work into specialized sub-agents. Each sub-agent focuses on one concern and goes deeper than a single flat prompt would.

## Sub-agent 1 -- Relation Designer
Read the data files and analyse the MILP structure. Design the metamorphic relations: define each perturbation, which variables to fix or free, and the directional assertion. Identify edge cases (infeasibility, degeneracy) and how each relation should handle them.

## Sub-agent 2 -- Solver Implementer
Using the relation designs, implement the baseline MILP solver and the perturbation harness. Use `xpress` as the solver. The script should cleanly separate baseline solving from metamorphic checks so each relation is independently runnable.

## Sub-agent 3 -- Test and Report Builder
Write pytest tests that verify both solver correctness and metamorphic relation outcomes. Produce a JSON report containing baseline metrics (objective, open depots, cost breakdown, unmet demand) and per-relation pass/fail with observed vs expected directions.

## Sub-agent 4 -- Reviewer
Review the solver, tests, and report against the relation designs. Verify metamorphic assertions are sound, edge cases are handled, and code quality is clean. Ensure no prompt concepts leak into the code -- it should read as natural Python with a clear `main()`.

Produce an executable solver script, a pytest test file, and a JSON report. Run with `uv run python workshop/materials/part-03-harness-optimization/02-metamorphic-harness-MILP/run_metamorphic_harness_milp.py`. Tests at `workshop/materials/part-03-harness-optimization/02-metamorphic-harness-MILP/tests/test_metamorphic_harness_milp.py`.
