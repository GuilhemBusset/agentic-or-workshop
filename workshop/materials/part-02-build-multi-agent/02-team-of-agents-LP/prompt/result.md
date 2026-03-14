# Result

## How to run

```bash
uv run python workshop/materials/part-02-build-multi-agent/02-team-of-agents-LP/run_team_agents_lp.py
```

## Output

```text
========================================================================
  DISASTER RELIEF NETWORK -- LP SOLUTION REPORT
========================================================================

------------------------------------------------------------------------
  DATA VALIDATION
------------------------------------------------------------------------
  All checks passed.

------------------------------------------------------------------------
  SOLVER SUMMARY
------------------------------------------------------------------------
  Status              : lp_optimal
  Objective value     : 18,605.42
  Variables           : 672
  Constraints         : 176
  Penalty per unit    : 1000.0

------------------------------------------------------------------------
  COST BREAKDOWN
------------------------------------------------------------------------
  Fixed cost (all depots) :         17,900
  Expected shipping cost  :         705.42
  Expected penalty cost   :           0.00
  Expected total unmet    :           0.00
                            --------------
  Total (recomputed)      :      18,605.42

------------------------------------------------------------------------
  PER-SCENARIO BREAKDOWN
------------------------------------------------------------------------
  Scenario  Description         Shipping     Penalty       Total    Unmet
  S01       Baseline              664.76        0.00      664.76     0.00
  S02       WinterStorm           717.87        0.00      717.87     0.00
  S03       FuelSpike             658.25        0.00      658.25     0.00
  S04       FestivalPeak          798.31        0.00      798.31     0.00
  S05       BridgeClosure         697.60        0.00      697.60     0.00
  S06       HeatWave              745.50        0.00      745.50     0.00
  S07       IndustrialDip         596.73        0.00      596.73     0.00
  S08       RecoveryPush          764.36        0.00      764.36     0.00

  Worst cost scenario : S04 (FestivalPeak)
  Worst unmet scenario: S01 (Baseline)

------------------------------------------------------------------------
  DEPOT UTILIZATION
------------------------------------------------------------------------
  Depot  Name              Cap  AvgUtil  MaxUtil  MaxScen  Status
  D06    Frontier Hub      170   90.1%   100.0%      S04  BOTTLENECK
  D04    Valley Hub        160   19.9%    22.5%      S04  ok
  D02    River Hub         180   14.2%    16.1%      S04  ok
  D01    North Hub         220   12.4%    14.1%      S04  ok
  D05    South Hub         210    9.3%    12.4%      S04  ok
  D03    Central Hub       240    9.3%    10.4%      S04  ok
  Bottleneck alerts: 1 depot(s)

------------------------------------------------------------------------
  TOWN SERVICE PROFILES
------------------------------------------------------------------------
  Town  Name       Crit  DemMin DemMax DemMean E[Unmet] WorstUnmet Dominant  Share  SPOF
  T01   Aster      N         23     31    27.4     0.00       0.00      D01100.0%     Y
  T02   Birch      N         22     29    25.6     0.00       0.00      D02100.0%     Y
  T03   Cedar      Y         19     25    22.4     0.00       0.00      D03100.0%     Y
  T04   Dover      Y         27     36    31.9     0.00       0.00      D04100.0%     Y
  T05   Elm        N         16     22    19.1     0.00       0.00      D05100.0%     Y
  T06   Fjord      N         18     24    21.2     0.00       0.00      D06100.0%     Y
  T07   Grove      Y         25     34    29.5     0.00       0.00      D06100.0%     Y
  T08   Harbor     N         20     26    23.4     0.00       0.00      D06100.0%     Y
  T09   Iron       N         15     20    18.0     0.00       0.00      D06 97.2%     Y
  T10   Juniper    N         17     23    20.2     0.00       0.00      D06100.0%     Y
  T11   Kepler     N         14     19    16.9     0.00       0.00      D06100.0%     Y
  T12   Lumen      Y         21     28    24.5     0.00       0.00      D06100.0%     Y
  Single-point-of-failure towns: 12

------------------------------------------------------------------------
  CAPACITY SHADOW PRICES (non-zero)
------------------------------------------------------------------------
  All capacity constraints non-binding.

------------------------------------------------------------------------
  DEMAND SHADOW PRICES (scenario S01)
------------------------------------------------------------------------
  dem_T01_S01 :     0.2437
  dem_T02_S01 :     0.2562
  dem_T03_S01 :     0.2750
  dem_T04_S01 :     0.2600
  dem_T05_S01 :     0.2525
  dem_T06_S01 :     0.2525
  dem_T07_S01 :     0.3100
  dem_T08_S01 :     0.3250
  dem_T09_S01 :     0.3837
  dem_T10_S01 :     0.3987
  dem_T11_S01 :     0.4150
  dem_T12_S01 :     0.4725

------------------------------------------------------------------------
  SERVICE CONSTRAINT DUALS (non-zero)
------------------------------------------------------------------------
  All service constraints non-binding.

------------------------------------------------------------------------
  TOP EXPECTED SHIPMENT LANES
------------------------------------------------------------------------
  Depot  Town         ExpFlow    Cost  Dist
  D04    T04            31.88    2.08    47
  D06    T07            29.50    2.48    60
  D01    T01            27.38    1.95    43
  D02    T02            25.62    2.05    46
  D06    T12            24.50    3.78   102
  D06    T08            23.38    2.60    64
  D03    T03            22.38    2.20    51
  D06    T06            21.25    2.02    45
  D06    T10            20.25    3.19    83
  D05    T05            19.12    2.02    45
  D06    T09            17.50    3.07    79
  D06    T11            16.88    3.32    87
  D05    T09             0.50    3.07    79

------------------------------------------------------------------------
  AUDIT RESULTS
------------------------------------------------------------------------
  [PASS] lp_optimal_status
  [PASS] all_depots_active
  [PASS] critical_service_met
  [PASS] demand_balance_verified
  [PASS] capacity_respected
  [PASS] objective_decomposition_consistent
  Checks passed: 6/6
  Overall       : ALL CLEAR

========================================================================
  END OF REPORT
========================================================================
```

## Conclusion

### What it demonstrates

The team-of-agents approach represents the **full pipeline pattern**: four sequential agents (Problem Analyst, Task Architect, Implementor, Reviewer), each with strict boundaries. Critically, the analyst and architect produce analysis and specifications without writing code, and the implementor follows the spec without re-reading data files. This separation of concerns mirrors a real engineering team and produces the most structured output (~924 lines) with typed dataclasses, named constraints, dual extraction, and a built-in audit pipeline. This pattern shows how enforcing cognitive separation -- understanding vs. designing vs. coding vs. reviewing -- leads to production-grade code quality and the deepest analytical output.

### Pros

- **Production-grade code structure**: Seven frozen dataclasses (`Depot`, `Town`, `Arc`, `Scenario`, `ProblemData`, `ModelArtifacts`, `Solution`, `CostBreakdown`, `DepotProfile`, `TownProfile`, `AuditResult`) provide type-safe, self-documenting data access. Every function has full type annotations and a clear single responsibility.
- **Built-in audit pipeline**: Six automated checks (LP optimal status, all depots active, critical service met, demand balance verified, capacity respected, objective decomposition consistent) independently verify the solution. This catches solver bugs and formulation errors that the other approaches would miss silently.
- **Dual value extraction**: Retrieves shadow prices for capacity, demand, and service constraints. The report shows demand shadow prices (e.g., T12 at 0.4725 is the most expensive marginal unit) and confirms all capacity constraints are non-binding -- critical insight for capacity planning.
- **Operational risk analysis**: Identifies D06 as a BOTTLENECK (100% utilization in S04) and flags all 12 towns as single-point-of-failure (SPOF), meaning each town depends on one dominant depot for 97-100% of supply. This analysis goes beyond optimization into operational resilience.
- **Richest reporting**: Per-scenario breakdown with worst-case identification, town service profiles with demand ranges and dominant depot shares, capacity shadow prices, service constraint duals, top shipment lanes with distances, and a full audit summary.
- **Correct core optimization**: Same expected shipping cost (705.42) and identical routing decisions, confirming that the additional code complexity does not alter the mathematical solution.
- **Named constraints**: All constraints have explicit names (e.g., `cap_D01_S01`, `dem_T01_S01`, `svc_T03_S01`), enabling traceability between the model and the report.
- **Highest penalty signals intent**: Penalty of 1000 per unit of unmet demand (vs. 50 or 100) makes the model strongly prioritize service fulfillment. In this instance all three produce zero unmet demand, but under tighter capacity the higher penalty would yield different solutions.

### Cons

- **~4x code volume**: At 924 lines (vs. 242 for single-agent), the code is nearly four times larger. Much of this is dataclass definitions, lookup-dict construction, and reporting infrastructure. The core LP formulation (~60 lines) is a small fraction of the total.
- **No CVaR risk modeling**: Unlike the other two approaches, this script does not include CVaR auxiliary variables (eta, z[s]) or a risk term in the objective. The model minimizes expected cost + penalty only, without tail-risk control. On this instance the difference is invisible (zero shortages everywhere), but under stress scenarios CVaR would produce a different solution.
- **Fewer variables and constraints**: 672 variables and 176 constraints vs. 681 variables and 164 constraints in approach 01. The difference is exactly the 9 missing CVaR variables (1 eta + 8 z[s]) offset by 12 more service constraints (per-scenario for critical towns only, vs. expected-value for all towns).
- **Higher prompt engineering investment**: While the prompt is ~17 lines, it requires carefully designing the separation between analyst, architect, implementor, and reviewer. The architect agent must produce a spec detailed enough for the implementor to follow without data access -- this is a non-trivial prompt design challenge.
- **Overhead in data loading**: The `load_data()` function (lines 161-298) builds 14 separate lookup dictionaries from the raw CSV data, plus validation warnings. This is robust but verbose -- the single-agent achieves the same data access in ~30 lines.
- **Diminishing returns on this problem instance**: Because total capacity (1,180) vastly exceeds maximum demand (317, ratio 3.7x), all approaches produce zero unmet demand and identical routing. The elaborate audit, SPOF analysis, and bottleneck detection add value for insight but do not change the solution. On a tighter instance, these analyses would be more impactful.
