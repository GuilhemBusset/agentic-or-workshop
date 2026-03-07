from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "workshop").is_dir() and (parent / "tests").is_dir():
            return parent
    raise RuntimeError("Repository root not found")


ROOT = _repo_root()
SCRIPT_PATH = ROOT / Path(
    "workshop/materials/part-03-harness-optimization/02-contract-regression-harness-MILP/run_contract_regression_harness_milp.py"
)


def test_harness_loads_only_core_csv_files() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert '"depots.csv"' in text
    assert '"towns.csv"' in text
    assert '"arcs.csv"' in text
    assert '"scenarios.csv"' in text
    assert '"scenario_demands.csv"' in text

    # This harness must not rely on non-core score/design/rule tables.
    assert '"designs.csv"' not in text
    assert '"scenario_flows.csv"' not in text
    assert '"scenario_scores.csv"' not in text
    assert '"constraint_rules.csv"' not in text
    assert '"objective_rules.csv"' not in text
    assert '"schema_catalog.csv"' not in text
