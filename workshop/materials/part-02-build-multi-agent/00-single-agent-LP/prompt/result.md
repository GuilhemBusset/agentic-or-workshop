# Result

## How to run

```bash
uv run python workshop/materials/part-02-build-multi-agent/00-single-agent-LP/run_single_agent_lp.py
```

## Output

```text
=== Single-Agent LP Result ===
Solver status: lp_optimal
Objective value: 705.42
Active depots: D01, D02, D03, D04, D05, D06
Expected transport cost: 705.42
Expected shortage penalty: 0.00
Expected unmet demand: 0.00
CVaR-style shortage indicator: 0.00
Worst scenario unmet demand: 0.00
Prompt contract respected: True
Tester checks passed: 5/5
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

**What it demonstrates**: A single short prompt produces one monolithic script. No role decomposition, no internal contracts. The agent reads the data, builds the LP, solves it, and prints results in one pass.

**Pros**:
- Minimal overhead, fastest to run.
- Simplest to understand -- one prompt, one script, one pass.
- Good baseline for comparing richer multi-agent setups.

**Cons**:
- No separation of concerns: hard to trace which decisions came from where.
- No parameter exploration: you get one solution with one fixed set of parameters.
- No independent verification step built into the architecture.
- The agent makes all modeling choices implicitly; nothing forces it to justify or validate them.
