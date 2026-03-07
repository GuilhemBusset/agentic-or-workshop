# 02 - Team of Agents LP

## What it demonstrates
A board evaluates several candidate teams. Each candidate team contains:
- `prompt_writer_team`
- `prompt_executor_team`
- `tester_team`

The board selects one tested candidate plan.

## Prompting peculiarity
- Multiple writer/executor/tester pods are run with different risk weights.
- Each pod must satisfy the same LP-only contract before it can compete.

## Strengths
- Best for teaching governance and cross-team comparison.
- Shows how orchestration changes behavior even with identical LP constraints.

## Limitations
- Highest complexity.
- More runtime due to repeated solves.

## Run
```bash
uv run python workshop/materials/part-02-build-multi-agent/02-team-of-agents-LP/run_team_agents_lp.py
```
