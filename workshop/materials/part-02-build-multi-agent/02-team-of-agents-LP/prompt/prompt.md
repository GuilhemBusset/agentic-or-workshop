# Prompt Used (Team of Agents, LP-Only, Zero-Context)

You start with zero prior knowledge of this project.

## Mandatory Context Loading
Load:
1. `workshop/materials/part-01-explorer-paradigm/00-problem/exercise-statement.md`
2. `workshop/data/README.md`
3. `workshop/data`

## Team Topology To Spawn
Create multiple candidate pods. Every pod must contain:
- `prompt_writer_team`
- `prompt_executor_team`
- `tester_team`

Global roles:
- `strategy_team`: defines candidate set (for example different risk weights)
- `data_team`: shared deterministic LP data
- `board_team`: selects one tested candidate
- `reporter_team`: publishes comparison + selected plan

## LP Contract Requirements (per pod)
Each writer must require:
- LP only (continuous variables)
- no binary/integer variables
- no depot-open optimization
- all depots active
- critical town service floor 95%

## Executor Rule
Each executor must follow its writer contract literally and refuse non-LP instructions.

## Tester Rule
Each tester must output pass/fail for:
- LP status
- no integer variables
- all depots active
- literal intent respected
- critical service respected
- objective consistency

## Board Rule
Select among candidates with `contract_respected=True` using a transparent governance score.

## Output Contract
Print:
- candidate comparison table
- selected risk weight
- selected plan metrics
- prompt contract respected for selected plan
- tester checks passed for selected plan
- top expected shipment lanes

## Implementation Constraints
- Single executable Python file.
- Use `xpress`.
- Run with `uv run python <script.py>`.
- Deterministic data and deterministic selection logic.
