from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "workshop").is_dir() and (parent / "tests").is_dir():
            return parent
    raise RuntimeError("Repository root not found")


ROOT = _repo_root()
MODULE_PATH = ROOT / Path(
    "workshop/materials/part-03-harness-optimization/02-contract-regression-harness-MILP/run_contract_regression_harness_milp.py"
)
FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "behavior_lock_report.json"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("contract_harness_lock", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load harness module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_behavior_lock_report_regression() -> None:
    module = _load_module()
    current = module.run_harness(write_report=False)
    expected = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert current["harness_id"] == expected["harness_id"]
    assert current["schema_version"] == expected["schema_version"]
    assert current["overall_passed"] is True

    assert current["baseline"]["solver_status"] == expected["baseline"]["solver_status"]
    assert current["baseline"]["open_depots"] == expected["baseline"]["open_depots"]

    assert current["baseline"]["objective"] == pytest.approx(
        expected["baseline"]["objective"], abs=1e-7
    )
    assert current["all_open_comparison"]["all_open_objective"] == pytest.approx(
        expected["all_open_comparison"]["all_open_objective"], abs=1e-7
    )

    stressed = current["stressed_demand_fixed_design_recourse"]["stressed_recourse"]
    stressed_expected = expected["stressed_demand_fixed_design_recourse"][
        "stressed_recourse"
    ]
    assert stressed["solver_status"] == stressed_expected["solver_status"]
    assert stressed["expected_unmet_demand"] == pytest.approx(
        stressed_expected["expected_unmet_demand"], abs=1e-7
    )
    assert stressed["total_unmet_demand"] == pytest.approx(
        stressed_expected["total_unmet_demand"], abs=1e-7
    )

    contract_ids = [item["id"] for item in current["checks"]["contract"]]
    regression_ids = [item["id"] for item in current["checks"]["regression"]]
    assert contract_ids == [item["id"] for item in expected["checks"]["contract"]]
    assert regression_ids == [item["id"] for item in expected["checks"]["regression"]]
    assert all(item["passed"] for item in current["checks"]["contract"])
    assert all(item["passed"] for item in current["checks"]["regression"])
