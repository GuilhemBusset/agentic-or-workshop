# Result

## How to run

```bash
uv run python workshop/materials/part-02-build-multi-agent/02-team-of-agents-LP/run_team_agents_lp.py
```

## Output

```text
=== Team-of-Agents LP Result ===
Candidate comparison:
  - Pod-A (cost-focused) | risk_w=10.0 short_p=8.0 | obj=705.42 | exp_unmet=0.00 | worst_unmet=0.00 | contract_ok=True | checks=6/6 | gov_score=705.42
  - Pod-B (balanced) | risk_w=24.0 short_p=12.0 | obj=705.42 | exp_unmet=0.00 | worst_unmet=0.00 | contract_ok=True | checks=6/6 | gov_score=705.42
  - Pod-C (risk-averse) | risk_w=40.0 short_p=20.0 | obj=705.42 | exp_unmet=0.00 | worst_unmet=0.00 | contract_ok=True | checks=6/6 | gov_score=705.42

Board-selected plan:
Prompt writer intent: Do not use binary/integer variables and do not optimize depot opening decisions.
Solver status: lp_optimal
Selected candidate: Pod-A (cost-focused)
Selected risk weight: 10.0
Selected shortage penalty: 8.0
Objective value: 705.42
Active depots: D01, D02, D03, D04, D05, D06
Expected transport cost: 705.42
Expected shortage penalty: 0.00
Expected unmet demand: 0.00
CVaR-style shortage indicator: 0.00
Worst scenario unmet demand: 0.00
Prompt contract respected: True
Tester checks passed: 6/6
Governance score: 705.42
Top expected shipment lanes:
  - D04 -> T04: 31.88
  - D06 -> T07: 29.50
  - D01 -> T01: 27.38
  - D02 -> T02: 25.62
  - D06 -> T12: 24.50
  - D06 -> T08: 23.38
  - D03 -> T03: 22.38
  - D06 -> T06: 21.25
```

## Conclusion

**What it demonstrates**: Multiple competing pods (each with its own writer, executor, and tester) explore different risk configurations. A board evaluates all tested candidates using a governance score and selects the best. This shows how the team paradigm enables solution diversity and transparent decision-making.

**Pros**:
- Solution diversity: three pods explore cost-focused, balanced, and risk-averse strategies.
- Governance layer: the board provides transparent selection criteria.
- Independent verification per pod: each candidate is tested before it can compete.
- Best for teaching how orchestration affects decision quality and accountability.

**Cons**:
- Highest complexity: more code, more roles, more interfaces.
- More runtime due to repeated solves (one LP per candidate).
- With the current dataset, all candidates produce identical solutions because total depot capacity (1180 units) far exceeds maximum scenario demand (~317 units). The risk parameters only differentiate candidates under capacity pressure.
- The prompt is the longest of the three, requiring the most guidance from the user.
