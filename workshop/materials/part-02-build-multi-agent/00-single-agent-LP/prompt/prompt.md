# Prompt Used (Single Agent, LP-Only, Zero-Context)

You start with zero prior knowledge of this project.

## Mandatory Context Loading
Before writing code, read these sources in order:
1. `workshop/materials/part-01-explorer-paradigm/00-problem/exercise-statement.md`
2. `workshop/data/README.md`
3. `workshop/data`

## Team To Spawn (Required)
Even in a single-agent strategy, create these three explicit roles:
- `prompt_writer`: writes a strict LP contract.
- `prompt_executor`: implements the writer contract exactly.
- `tester`: verifies the executor respected the contract.

## LP Contract Requirements
The writer must require all of the following:
- Transportation LP only (continuous nonnegative variables).
- No binary/integer variables.
- No depot-open decision optimization.
- All depots treated as active input assets.
- Scenario-wise flows and unmet-demand penalties are allowed.
- Critical towns `T03`, `T04`, `T07`, `T12` must keep at least 95% service.

## Executor Rule
The executor must refuse to proceed if the writer contract is not LP-only.

## Tester Rule
Tester must emit pass/fail checks for:
- LP status (`lp_*`)
- no integer variables used
- all depots active
- critical service rule respected
- objective component consistency

## Output Contract
Print at least:
- prompt writer intent sentence
- solver status
- objective value
- active depots
- expected transport cost
- expected shortage penalty
- expected unmet demand
- CVaR-style shortage indicator
- worst scenario unmet demand
- prompt contract respected (True/False)
- tester checks passed
- top expected shipment lanes

## Implementation Constraints
- Single executable Python file.
- Use `xpress`.
- Run with `uv run python <script.py>`.
- Deterministic output for workshop reproducibility.
