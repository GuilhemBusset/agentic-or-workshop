# Workshop Data Package

This folder contains the core CSV contract for the workshop problem.

## Dataset scale
- Depots: 6
- Towns: 12
- Scenarios: 8

## Files
- `depots.csv`: canonical depot master data.
- `towns.csv`: canonical town demand and criticality data.
- `arcs.csv`: depot-town shipping lanes and costs.
- `scenarios.csv`: scenario metadata and probabilities.
- `scenario_demands.csv`: scenario-by-town demand table.

## Canonical policy
This dataset assumes critical-first service as the baseline policy. `towns.priority_flag=critical` and `towns.service_min` are retained for service-floor contracts.

## Validation
Run the lightweight validator from the repo root:

```bash
uv run python workshop/data/validate_data.py
```

Optional:

```bash
uv run python workshop/data/validate_data.py --data-dir workshop/data
```
