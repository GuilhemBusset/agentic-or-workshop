# Result

## How to run

```bash
uv run python workshop/materials/part-02-build-multi-agent/01-sub-agent-LP/run_sub_agent_lp.py
```

## Output

```text
=== Sub-Agent LP Result ===
Prompt writer intent: Do not create integer or binary variables. Keep all depots active and solve transportation only.
Solver status: lp_optimal
Objective value: 705.42
Active depots: D01, D02, D03, D04, D05, D06
Expected transport cost: 705.42
Expected shortage penalty: 0.00
Expected unmet demand: 0.00
CVaR-style shortage indicator: 0.00
Worst scenario unmet demand: 0.00
Prompt contract respected: True
Tester checks passed: 6/6
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

**What it demonstrates**: A manager orchestrates specialized sub-agents (planner, data loader, prompt writer, executor, tester, reporter). Each sub-agent owns a single concern. The planner selects different risk parameters (shortage_penalty=15.0, cvar_alpha=0.85, risk_weight=20.0) than the single-agent baseline to show that the decomposition enables independent parameter tuning.

**Pros**:
- Clear separation of concerns: each sub-agent has a well-defined responsibility.
- The planner can tune parameters independently of the model builder.
- The tester provides independent verification with explicit pass/fail checks.
- Better pedagogical traceability: you can see exactly what each sub-agent decided.

**Cons**:
- More orchestration code and interface management than the single-agent approach.
- Still produces a single solution (no diversity of candidates).
- More places for contract mismatch bugs between sub-agents.
- The manager is a fixed sequential pipeline -- no parallelism or adaptive routing.
