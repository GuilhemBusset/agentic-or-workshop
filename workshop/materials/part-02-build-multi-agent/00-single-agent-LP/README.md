# 00 - Single Agent LP

## What it demonstrates
A single agent runs three mandatory roles in one linear pass:
- `prompt_writer`
- `prompt_executor`
- `tester`

## Prompting peculiarity
- One broad prompt still exists, but the script now forces an explicit internal contract.
- The executor cannot proceed unless the writer contract is LP-only.

## Strengths
- Minimal orchestration overhead.
- Fast to explain and run in class.
- Clear baseline for comparing richer multi-agent setups.

## Limitations
- Limited independence between roles (all in one pipeline).
- Lower diversity of candidate solutions.

## Run
```bash
uv run python workshop/materials/part-02-build-multi-agent/00-single-agent-LP/run_single_agent_lp.py
```
