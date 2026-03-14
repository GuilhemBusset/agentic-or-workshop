# Result

## How to run

```bash
uv run python workshop/materials/part-02-build-multi-agent/00-single-agent-LP/run_single_agent_lp.py
```

## Output

```text
============================================================
DISASTER RELIEF TRANSPORTATION LP
============================================================
Solver status : solve=3, solution=1
Objective     : 705.42

Cost breakdown
----------------------------------------
  Expected shipping cost :     705.42
  Expected shortage pen. :       0.00
  CVaR term (weighted)   :       0.00
  VaR (eta)              :       0.00
  CVaR (unweighted)      :       0.00

Unmet demand by scenario
----------------------------------------
  S01:     0.00
  S02:     0.00
  S03:     0.00
  S04:     0.00
  S05:     0.00
  S06:     0.00
  S07:     0.00
  S08:     0.00

Critical-town service levels (min across scenarios)
----------------------------------------
  T03 (   Cedar): 100.0%
  T04 (   Dover): 100.0%
  T07 (   Grove): 100.0%
  T12 (   Lumen): 100.0%

Top shipment lanes (expected flow)
--------------------------------------------------
   Depot    Town   Exp. Flow   Unit Cost
     D04     T04       31.88        2.08
     D06     T07       29.50        2.48
     D01     T01       27.38        1.95
     D02     T02       25.62        2.05
     D06     T12       24.50        3.78
     D06     T08       23.38        2.60
     D03     T03       22.38        2.20
     D06     T06       21.25        2.02
     D06     T10       20.25        3.19
     D05     T05       19.12        2.02
     D06     T09       17.50        3.07
     D06     T11       16.88        3.32
     D05     T09        0.50        3.07

Average depot utilisation
----------------------------------------
  D01:    27.4 / 220  (12.4%)
  D02:    25.6 / 180  (14.2%)
  D03:    22.4 / 240  ( 9.3%)
  D04:    31.9 / 160  (19.9%)
  D05:    19.6 / 210  ( 9.3%)
  D06:   153.2 / 170  (90.1%)

============================================================
```

## Conclusion

### What it demonstrates

The single-agent approach represents the **minimal viable agentic pattern**: one prompt, one pass, one script. The LLM receives a concise 13-line prompt describing the problem and produces a complete, self-contained Python script (~242 lines) that loads data, builds the LP, solves it, and prints results -- all within a single `build_and_solve()` function. This pattern shows what an AI coding assistant can produce with minimal guidance. It is the natural baseline for evaluating how much value additional agentic complexity adds.

### Pros

- **Low prompt investment**: The shortest prompt of the three approaches (~13 lines) produces a working, correct solution with minimal user effort.
- **Fast iteration cycle**: A single script with no abstraction layers is easy to read end-to-end, modify, and debug. No need to trace through dataclass hierarchies or multi-function pipelines.
- **Correct core optimization**: The expected shipping cost (705.42) and routing decisions (e.g., D04->T04: 31.88, D06->T07: 29.50) are identical to the other two approaches, proving that the LP formulation is correct despite the simpler code structure.
- **Risk modeling included**: Incorporates CVaR (alpha=0.95, lambda=0.5) and shortage penalties (50/unit), producing a richer objective than a naive min-cost formulation.
- **Compact and self-contained**: At ~242 lines, the entire solution fits in a single screen of context, making it ideal for quick prototyping or teaching the LP formulation itself.
- **Zero unmet demand**: Achieves 100% service across all scenarios and all towns, including critical towns.

### Cons

- **No data validation**: The script trusts the CSV files blindly -- no checks for missing arcs, probability sums, or demand completeness. A corrupted data file would produce silent errors in the optimization.
- **Monolithic structure**: Everything lives in one function (`build_and_solve`), mixing data loading, model construction, solving, and reporting. This violates single-responsibility and makes the code harder to test or extend.
- **No type annotations or data structures**: Data is stored in raw dicts (`dict[tuple[str, str], float]`) with no named fields. The reader must infer what `demand[(s, t)]` means from context rather than from a typed schema.
- **Minimal output**: Reports only cost breakdown, unmet demand, critical-town service, top lanes, and depot utilization. No per-scenario cost decomposition, no model statistics (variable/constraint counts), no verification that the solution is feasible.
- **Objective not directly comparable**: Reports objective as 705.42 (shipping cost only), omitting fixed depot costs (17,900) that the other approaches include. This makes cross-approach comparison harder without reading the code.
- **No dual information or sensitivity analysis**: Does not extract shadow prices or constraint duals, so the user gains no insight into which constraints drive the solution or where capacity investments would pay off.
- **Depot D06 bottleneck invisible**: While the output shows D06 at 90.1% utilization, there is no explicit bottleneck flag or alert. The user must spot this manually.
