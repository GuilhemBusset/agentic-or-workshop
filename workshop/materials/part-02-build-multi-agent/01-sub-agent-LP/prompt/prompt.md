# Prompt Used (Sub-Agent, LP-Only, Zero-Context)

You start with zero prior knowledge of this project.

## Mandatory Context Loading
Read and summarize:
1. `workshop/materials/part-01-explorer-paradigm/00-problem/exercise-statement.md`
2. `workshop/data/README.md`
3. `workshop/data`

## Team To Spawn (Required)
- `manager_agent`: orchestration only
- `planner_sub_agent`: chooses parameters and reporting scope
- `prompt_writer_sub_agent`: writes strict LP contract
- `data_sub_agent`: prepares deterministic inputs
- `prompt_executor_sub_agent`: executes model exactly per writer contract
- `tester_sub_agent`: verifies contract compliance
- `reporter_sub_agent`: formats final output

## LP Contract Requirements
Writer contract must enforce:
- continuous transportation variables only
- no binary/integer decisions
- no facility-open optimization
- all depots active
- shortage penalties and CVaR-style risk term allowed
- critical town minimum service 95%

## Executor Rule
Executor must fail fast if any contract field implies MILP behavior.

## Tester Rule
Tester must produce explicit checks for:
- solver status is LP optimal (`lp_*`)
- integer variable count is zero
- all depots active
- literal writer intent respected
- critical service constraints respected
- objective decomposition consistency

## Output Contract
Print:
- prompt writer intent
- solver status
- objective value
- active depots
- expected transport cost
- expected shortage penalty
- expected unmet demand
- CVaR-style shortage indicator
- worst scenario unmet demand
- prompt contract respected
- tester checks passed
- top expected lanes

## Implementation Constraints
- Keep all code in one Python file.
- Use `xpress`.
- Script runnable with `uv run python <script.py>`.
- Deterministic behavior.
