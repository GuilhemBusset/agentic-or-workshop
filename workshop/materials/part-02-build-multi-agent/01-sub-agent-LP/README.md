# 01 - Sub-Agent LP

## What it demonstrates
A manager orchestrates multiple sub-agents, with mandatory writer/executor/tester roles:
- `planner_sub_agent`
- `prompt_writer_sub_agent`
- `data_sub_agent`
- `prompt_executor_sub_agent`
- `tester_sub_agent`
- `reporter_sub_agent`

## Prompting peculiarity
- The writer contract is generated from planner outputs.
- The executor is blocked if the contract drifts away from LP-only intent.
- Tester emits explicit pass/fail checks.

## Strengths
- Clear separation of concerns.
- Better pedagogical traceability than the single-agent pipeline.

## Limitations
- More orchestration and interface management.
- More places for contract mismatch bugs.

## Run
```bash
uv run python workshop/materials/part-02-build-multi-agent/01-sub-agent-LP/run_sub_agent_lp.py
```
