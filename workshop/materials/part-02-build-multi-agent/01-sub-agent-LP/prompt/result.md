# Result

Command run:

```bash
uv run python workshop/materials/part-02-build-multi-agent/01-sub-agent-LP/run_sub_agent_lp.py
```

Output:

```text
=== Sub-Agent LP Result ===
Prompt writer intent: Do not create integer or binary variables. Keep all depots active and solve transportation only.
Solver status: lp_optimal
Objective value: 15709.18
Active depots: D01, D02, D03, D04, D05, D06
Expected transport cost: 9453.13
Expected shortage penalty: 674.55
Expected unmet demand: 56.21
CVaR-style shortage indicator: 232.56
Worst scenario unmet demand: 277.75
Prompt contract respected: True
Tester checks passed: 6/6
Top expected shipment lanes:
  - D01 -> T07: 152.06
  - D02 -> T02: 129.72
  - D06 -> T12: 128.25
  - D03 -> T03: 125.69
  - D03 -> T09: 124.69
  - D05 -> T05: 106.88
  - D02 -> T08: 89.83
  - D06 -> T06: 89.06
```
