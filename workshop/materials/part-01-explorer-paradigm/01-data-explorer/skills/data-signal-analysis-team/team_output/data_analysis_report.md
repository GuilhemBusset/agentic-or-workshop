# Autonomous Data Analysis Report

## Objective and Scope
Analyze `workshop/data` to extract the most decision-relevant signals for the disaster relief planning dataset, using only `data-explorer-csv` (`describe_csv_schema`, `query_csv`).

## Data Inventory
- `depots.csv`: 6 rows, 6 columns
- `towns.csv`: 12 rows, 6 columns
- `arcs.csv`: 72 rows, 7 columns
- `scenarios.csv`: 8 rows, 4 columns
- `scenario_demands.csv`: 96 rows, 3 columns
- `designs.csv`: 18 rows, 5 columns
- `scenario_flows.csv`: 288 rows, 6 columns
- `scenario_scores.csv`: 15 rows, 6 columns
- `constraint_rules.csv`: 6 rows, 11 columns
- `objective_rules.csv`: 4 rows, 8 columns
- `schema_catalog.csv`: 11 rows, 6 columns

## Key Quality and Consistency Checks
- Scenario probabilities are valid and normalized: 8 scenarios, each probability `0.125`, total probability `1.0`.
- Key cardinalities are internally consistent:
  - `arcs.csv`: `72` rows, `72` distinct `arc_id`, `72` distinct depot-town pairs.
  - `scenario_demands.csv`: `96` rows, `96` distinct scenario-town keys (`8 x 12`).
  - `designs.csv`: `18` rows, `18` distinct design-depot keys (`3 x 6`).
  - `scenario_flows.csv`: `288` rows, `288` distinct design-scenario-town keys (`3 x 8 x 12`).
- Flow balance consistency in `scenario_flows.csv`: for each design/scenario, `SUM(flow + unmet)` equals scenario total demand (matches `scenario_demands.csv` totals).
- Score consistency:
  - `scenario_scores.expected_unmet` aligns with average unmet from `scenario_flows` (within rounding).
  - `scenario_scores.worst_unmet` aligns exactly with worst unmet from `scenario_flows`.

## Core Signals
- Demand profile:
  - Total base demand from `towns.csv`: `264`.
  - Critical towns: `T03, T04, T07, T12` with service minimum `0.95`.
  - Critical demand share: `102 / 264 = 38.6%`.
  - Scenario total demand range from `237` to `317` (average `280.125`, range `80`).
- Capacity and facility profile:
  - Total depot capacity: `1180` (min `160`, max `240`).
  - Total fixed cost across depots: `17900`.
- Transport lane profile:
  - Full depot-town coverage (`72 = 6 x 12` lanes).
  - Shipping cost range: `1.95` to `5.02` (average `3.181`).
- Design profile:
  - Open depots by design: `G01=3`, `G02=4`, `G03=5`.
  - Open sets: `G01(D01,D03,D05)`, `G02(+D06)`, `G03(+D02)`.
  - `D04` is never opened in any design.
- Outcome profile:
  - From `scenario_scores.csv`:
    - `G01`: expected_cost `2767.42`, expected_unmet `15.62`, worst_unmet `18`, risk_score `3487.42`.
    - `G02`: expected_cost `2134.21`, expected_unmet `11.38`, worst_unmet `12`, risk_score `2614.21`.
    - `G03`: expected_cost `792.97`, expected_unmet `0`, worst_unmet `0`, risk_score `792.97`.
  - Overall service rates from `scenario_flows.csv`:
    - `G01`: average `0.9443`.
    - `G02`: average `0.9594`.
    - `G03`: `1.0` in all scenarios.

## Most Important Findings
1. Data integrity is strong for core scenario/design/flow structures: key cardinalities and balancing relationships are consistent across all major operational tables.
2. Demand uncertainty is material: scenario totals vary by `80` units (`237` to `317`), so model behavior must be evaluated under stress scenarios, not only averages.
3. Critical service pressure is high: critical towns represent `38.6%` of base demand and all require `95%` minimum service, making shortage allocation decisions highly constrained.
4. The transport network is dense and complete (all depot-town pairs available), but cost heterogeneity is large (`1.95` to `5.02`), which can strongly influence allocation and design quality.
5. Design progression is monotonic by depot count (`3 -> 4 -> 5`), and `D04` is dominated in the provided candidates (never opened, never used in scenario flows).
6. `G03` dominates the provided score table: it achieves zero unmet demand across all scenarios and also has the lowest expected cost and risk score.
7. `scenario_scores` and `scenario_flows` are mutually coherent on unmet-demand metrics (expected/worst), supporting trust in the scored summaries.
8. Risk premium behavior is explicit in the score table: `risk_score - expected_cost` equals `720` (G01), `480` (G02), `0` (G03), tracking unmet-risk exposure.

## Caveats
- Analysis was intentionally data-only; no optimization model was built or solved.
- `query_csv` operates on one CSV at a time, so cross-file foreign key validation was done via aligned aggregates and key counts rather than direct SQL joins.
- Critical-town service compliance by design/scenario cannot be fully verified from `scenario_flows.csv` alone because criticality flags are in `towns.csv`.

## Source Evidence
- Finding 1:
  - `arcs.csv`: key uniqueness query (`COUNT(*)`, `COUNT(DISTINCT arc_id)`, `COUNT(DISTINCT depot_id||town_id)`).
  - `scenario_demands.csv`: scenario-town key count query.
  - `designs.csv`: design-depot key count query.
  - `scenario_flows.csv`: design-scenario-town key count query.
- Finding 2:
  - `scenario_demands.csv`: scenario demand totals by scenario and min/max/avg/range query.
- Finding 3:
  - `towns.csv`: grouped summary by `priority_flag`; critical town list query with `service_min`.
- Finding 4:
  - `arcs.csv`: coverage and shipping cost summary; top-5 cheapest and top-5 most expensive lanes.
- Finding 5:
  - `designs.csv`: open depot counts by design; open depot list by design; times-open by depot query.
  - `scenario_flows.csv`: assignments/flow by depot query.
- Finding 6:
  - `scenario_scores.csv`: design-level pivot of expected cost/unmet/risk metrics.
  - `scenario_flows.csv`: unmet by design and scenario; service-rate summaries.
- Finding 7:
  - `scenario_flows.csv`: average/worst/p95 unmet derived from unmet-by-scenario table.
  - `scenario_scores.csv`: comparison against `expected_unmet`, `worst_unmet`, `p95_unmet`.
- Finding 8:
  - `scenario_scores.csv`: derived `risk_premium = risk_score - expected_cost` query.
