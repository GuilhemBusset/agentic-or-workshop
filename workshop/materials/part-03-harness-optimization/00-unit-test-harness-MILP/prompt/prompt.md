# Prompt Used (Single Agent, Unit-Test TDD)

Solve a disaster-relief transportation MILP using data from `workshop/data/` (depots.csv, towns.csv, arcs.csv, scenarios.csv, scenario_demands.csv). **Do not read any other files in the repository -- no other scripts, no other prompts, no other results.**

Use a test-first approach: write `pytest` tests before the solver, then implement until all tests pass. Tests should cover data integrity (6 depots, 12 towns, 8 scenarios, probabilities summing to 1), MILP structure (binary depot-open variables, capacity linked to open/close), solver output validity, and critical-town service levels.

Build a MILP that decides which depots to open (binary), routes shipments from open depots to towns under 8 demand scenarios, and minimizes fixed opening cost + expected transport cost + shortage penalties + a CVaR shortage risk term. Critical towns T03, T04, T07, T12 must receive at least 95% of their demand in every scenario. Unmet demand at any town incurs a penalty.

Produce two files:
- Solver script: `workshop/materials/part-03-harness-optimization/00-unit-test-harness-MILP/run_unit_test_harness_milp.py`
- Test file: `workshop/materials/part-03-harness-optimization/00-unit-test-harness-MILP/tests/test_unit_test_harness_milp.py`

Use `xpress` for the solver and `pytest` for tests. The script must print a JSON object containing at minimum: `solver_status`, `objective`, `open_depots`, and `harness_checks_passed` (boolean indicating all in-script validation checks pass). Run tests with `uv run pytest workshop/materials/part-03-harness-optimization/00-unit-test-harness-MILP/tests -q` and the script with `uv run python workshop/materials/part-03-harness-optimization/00-unit-test-harness-MILP/run_unit_test_harness_milp.py`.
