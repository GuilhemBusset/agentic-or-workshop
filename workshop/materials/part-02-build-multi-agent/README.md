# Part 02 - Build Multi-Agent (LP Only)

This section compares 3 agentic orchestration styles on the same transportation LP.

All strategies enforce the same pedagogical contract:
- `prompt_writer` defines the LP-only intent.
- `prompt_executor` must implement the writer intent literally.
- `tester` verifies the executor respected that intent.

## Shared LP scope
- Continuous shipment variables only.
- No binary/integer depot-opening variables.
- All depots are active input assets.
- Scenario-based demand with shortage penalties and a linear CVaR-style risk term.

## Strategy folders
- `00-single-agent-LP`: one agent that performs writer + executor + tester sequentially.
- `01-sub-agent-LP`: manager with specialized sub-agents, including writer/executor/tester.
- `02-team-of-agents-LP`: multiple candidate teams (each with writer/executor/tester) plus board selection.

## How to run
From repo root:

```bash
uv run python workshop/materials/part-02-build-multi-agent/00-single-agent-LP/run_single_agent_lp.py
uv run python workshop/materials/part-02-build-multi-agent/01-sub-agent-LP/run_sub_agent_lp.py
uv run python workshop/materials/part-02-build-multi-agent/02-team-of-agents-LP/run_team_agents_lp.py
uv run python workshop/materials/part-02-build-multi-agent/compare_all_solutions.py
```
