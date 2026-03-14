# Result

## How to run

```bash
uv run python workshop/materials/part-02-build-multi-agent/01-sub-agent-LP/run_sub_agent_lp.py
```

## Output

```text
======================================================================
DATA VALIDATION SUMMARY
======================================================================
  Depots:          6
  Towns:           12 (4 critical)
  Arcs:            72
  Scenarios:       8
  Demand rows:     96
  Total capacity:  1180
  Max total demand:  317 (capacity ratio: 3.7x)
  Prob. sum:       1.0000
  Status:          ALL CHECKS PASSED

======================================================================
MODEL STATISTICS
======================================================================
  Variables:       681
    x[d,t,s]:      576
    u[t,s]:        96
    eta:           1
    z[s]:          8
  Constraints:     164
    Demand sat.:   96
    Capacity:      48
    Service level: 12
    CVaR:          8

======================================================================
SOLUTION REPORT
======================================================================
  LP status:       1
  Solution status: 1

  OBJECTIVE BREAKDOWN
  --------------------------------------------------
    Fixed costs (constant):         17900.00
    Expected transport cost:          705.42
    Expected shortage penalty:          0.00
    CVaR term (lambda=10.0):             0.00
    -----------------------------------------------
    Total objective:                18605.42

  RISK MEASURES
  --------------------------------------------------
    VaR (eta) at alpha=0.95:             0.00
    CVaR at alpha=0.95:                  0.00

  PER-SCENARIO SHORTAGE COST
  --------------------------------------------------
    S01 (      Baseline):  shortage cost =       0.00   z =       0.00
    S02 (   WinterStorm):  shortage cost =       0.00   z =       0.00
    S03 (     FuelSpike):  shortage cost =       0.00   z =       0.00
    S04 (  FestivalPeak):  shortage cost =       0.00   z =       0.00
    S05 ( BridgeClosure):  shortage cost =       0.00   z =       0.00
    S06 (      HeatWave):  shortage cost =       0.00   z =       0.00
    S07 ( IndustrialDip):  shortage cost =       0.00   z =       0.00
    S08 (  RecoveryPush):  shortage cost =       0.00   z =       0.00

  DEPOT UTILIZATION
  --------------------------------------------------
    Depot  Name              Cap    Min%    Avg%    Max%
    ------------------------------------------------
    D01    North Hub         220   10.5%   12.4%   14.1%
    D02    River Hub         180   12.2%   14.2%   16.1%
    D03    Central Hub       240    7.9%    9.3%   10.4%
    D04    Valley Hub        160   16.9%   19.9%   22.5%
    D05    South Hub         210    7.6%    9.3%   12.4%
    D06    Frontier Hub      170   76.5%   90.1%  100.0%

  SERVICE LEVELS (expected fraction of demand met)
  --------------------------------------------------
    Town   Name       Type         Req  Achieved  Status
    ----------------------------------------------------
    T01    Aster      standard     70%   100.00%  OK
    T02    Birch      standard     70%   100.00%  OK
    T03    Cedar      critical     95%   100.00%  OK
    T04    Dover      critical     95%   100.00%  OK
    T05    Elm        standard     70%   100.00%  OK
    T06    Fjord      standard     70%   100.00%  OK
    T07    Grove      critical     95%   100.00%  OK
    T08    Harbor     standard     70%   100.00%  OK
    T09    Iron       standard     70%   100.00%  OK
    T10    Juniper    standard     70%   100.00%  OK
    T11    Kepler     standard     70%   100.00%  OK
    T12    Lumen      critical     95%   100.00%  OK

    All service level constraints satisfied.

  UNMET DEMAND SUMMARY (units)
  --------------------------------------------------
    Town       S01     S02     S03     S04     S05     S06     S07     S08  E[unmet]
    --------------------------------------------------------------------------------
    T01       0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.0000
    T02       0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.0000
    T03       0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.0000
    T04       0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.0000
    T05       0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.0000
    T06       0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.0000
    T07       0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.0000
    T08       0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.0000
    T09       0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.0000
    T10       0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.0000
    T11       0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.0000
    T12       0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.0000

    Total expected unmet demand: 0.0000

  PER-SCENARIO TOTAL COST (transport + shortage)
  --------------------------------------------------
    S01 (      Baseline):  transport=   664.76  shortage=     0.00  total=    664.76
    S02 (   WinterStorm):  transport=   717.87  shortage=     0.00  total=    717.87
    S03 (     FuelSpike):  transport=   658.25  shortage=     0.00  total=    658.25
    S04 (  FestivalPeak):  transport=   798.31  shortage=     0.00  total=    798.31
    S05 ( BridgeClosure):  transport=   697.60  shortage=     0.00  total=    697.60
    S06 (      HeatWave):  transport=   745.50  shortage=     0.00  total=    745.50
    S07 ( IndustrialDip):  transport=   596.73  shortage=     0.00  total=    596.73
    S08 (  RecoveryPush):  transport=   764.36  shortage=     0.00  total=    764.36

======================================================================
```

## Conclusion

### What it demonstrates

The sub-agent approach represents the **decomposition-by-concern pattern**: the prompt defines four specialized sub-agents (Problem Understander, Data Understander, Implementer, Reviewer), each focusing on one aspect of the task. The LLM orchestrates these internally, producing a single script (~493 lines) that is noticeably more structured than the single-agent output. This pattern shows how breaking a problem into cognitive roles -- understanding, data analysis, implementation, review -- leads to deeper analysis and richer output, even though the final artifact is still one file.

### Pros

- **Data validation layer**: Includes a dedicated `validate_data()` function with checks for cardinality (6 depots, 12 towns, 72 arcs, 8 scenarios, 96 demands), probability sums, arc completeness, demand completeness, and foreign-key integrity. This catches data issues before they corrupt the optimization.
- **Clean functional decomposition**: Four well-separated functions (`load_data`, `validate_data`, `build_model`, `report_solution`) with a clear `main()` entry point. Each function has a single responsibility, making the code testable and maintainable.
- **Model statistics reported**: Explicitly prints variable counts (681 total: 576 x[d,t,s] + 96 u[t,s] + 1 eta + 8 z[s]) and constraint counts (164: 96 demand + 48 capacity + 12 service + 8 CVaR). This gives the reader insight into the problem structure.
- **Richer reporting**: Per-scenario cost decomposition (transport + shortage), depot utilization with min/avg/max percentages, per-town service levels with required vs. achieved, and a full unmet demand matrix across all towns and scenarios.
- **Stronger risk modeling**: Uses higher penalty (100 vs. 50) and much stronger CVaR weight (lambda=10.0 vs. 0.5), producing a model that is more risk-averse. Fixed costs (17,900) are included in the objective, making the total (18,605.42) directly interpretable.
- **Expected-value service constraints**: Formulates service as E[unmet] <= (1 - service_min) * E[demand] for all towns, not just critical ones. This is a different (and arguably more practical) formulation than per-scenario hard constraints.
- **Correct core optimization**: Same expected shipping cost (705.42) and identical routing decisions as the other approaches, confirming mathematical equivalence on this instance.

### Cons

- **Still procedural, not typed**: Data is stored in nested dicts (`dict[str, dict]`) rather than dataclasses. The reader must trace through the code to understand what fields `depots[d]` contains. No frozen dataclasses, no type-safe access.
- **No solution verification**: Unlike the team-of-agents approach, there is no audit step that checks demand balance, capacity respect, or objective decomposition consistency after solving. The user trusts the solver output without independent verification.
- **No dual extraction**: Shadow prices and constraint duals are not retrieved. The report cannot tell the user which constraints are binding or where marginal cost improvements are available.
- **~2x code volume for incremental insight**: At 493 lines (vs. 242), the code roughly doubles in size. The additional value -- validation, model stats, richer reporting -- is real but the code-to-insight ratio starts to show diminishing returns compared to the leap from approach 02.
- **Prompt complexity doubles**: The prompt grows from ~13 lines to ~19 lines with four sub-agent definitions. The prompt engineering investment is moderate but the sub-agent boundaries require careful design to avoid redundancy.
- **No bottleneck or SPOF detection**: D06 at 90.1% utilization is reported but not flagged. Single-source dependencies (every town served by exactly one dominant depot) are not identified, missing a key operational risk insight.
