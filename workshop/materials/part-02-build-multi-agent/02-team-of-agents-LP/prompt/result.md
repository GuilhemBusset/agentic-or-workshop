# Result

Command run:

```bash
uv run python workshop/materials/part-02-build-multi-agent/02-team-of-agents-LP/run_team_agents_lp.py
```

Output:

```text
=== Team-of-Agents LP Result ===
Candidate comparison:
  - risk_weight=8.0 | objective=11988.18 | expected_unmet=56.21 | worst_unmet=277.75 | contract_ok=True | checks=6/6 | score=14293.93
  - risk_weight=24.0 | objective=15709.18 | expected_unmet=56.21 | worst_unmet=277.75 | contract_ok=True | checks=6/6 | score=14293.93
  - risk_weight=45.0 | objective=20593.00 | expected_unmet=56.21 | worst_unmet=277.75 | contract_ok=True | checks=6/6 | score=14293.93

Board-selected plan:
Prompt writer intent: Do not use binary/integer variables and do not optimize depot opening decisions.
Solver status: lp_optimal
Selected risk weight: 8.0
Objective value: 11988.18
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
