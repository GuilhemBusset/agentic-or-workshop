from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "run_contract_regression_harness_milp.py"
)


CONTRACT_IDS = {
    "C01_model_class_milp",
    "C02_critical_towns_exact",
    "C03_critical_service_floor",
    "C04_capacity_only_if_open",
    "C05_objective_component_consistency",
    "C06_probability_contract",
    "C07_solver_status_ok",
}

REGRESSION_IDS = {
    "R01_baseline_contract_checked_solve",
    "R02_all_open_baseline_comparison",
    "R03_fixed_cost_bump_perturbation",
    "R04_stressed_demand_fixed_design_recourse",
}


def _load_module():
    spec = importlib.util.spec_from_file_location("contract_harness", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load harness module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_required_check_ids_exist_and_pass() -> None:
    module = _load_module()
    report = module.run_harness(write_report=False)

    contract_ids = {item["id"] for item in report["checks"]["contract"]}
    regression_ids = {item["id"] for item in report["checks"]["regression"]}

    assert contract_ids == CONTRACT_IDS
    assert regression_ids == REGRESSION_IDS
    assert all(item["passed"] for item in report["checks"]["contract"])
    assert all(item["passed"] for item in report["checks"]["regression"])
    assert report["overall_passed"] is True


def test_report_structure_and_deterministic_key_shape() -> None:
    module = _load_module()
    report = module.run_harness(write_report=False)

    assert list(report.keys()) == [
        "harness_id",
        "schema_version",
        "checks",
        "baseline",
        "all_open_comparison",
        "fixed_cost_bump",
        "stressed_demand_fixed_design_recourse",
        "overall_passed",
    ]
    assert list(report["checks"].keys()) == ["contract", "regression"]

    for check in report["checks"]["contract"] + report["checks"]["regression"]:
        assert list(check.keys()) == ["id", "passed", "details"]


def test_main_writes_report_file(tmp_path: Path) -> None:
    module = _load_module()
    output = tmp_path / "contract_regression_report.json"

    report = module.run_harness(output_path=output, write_report=True)

    assert output.exists()
    disk_report = json.loads(output.read_text(encoding="utf-8"))
    assert disk_report["overall_passed"] == report["overall_passed"]
    assert "baseline" in disk_report
    assert "all_open_comparison" in disk_report
    assert "fixed_cost_bump" in disk_report
    assert "stressed_demand_fixed_design_recourse" in disk_report


def test_intentional_objective_corruption_fails_c05() -> None:
    module = _load_module()
    report = module.run_harness(write_report=False, objective_corruption=1.0)

    c05 = next(
        item
        for item in report["checks"]["contract"]
        if item["id"] == "C05_objective_component_consistency"
    )
    assert c05["passed"] is False
