from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "workshop").is_dir() and (parent / "tests").is_dir():
            return parent
    raise RuntimeError("Repository root not found")


ROOT = _repo_root()
SCRIPT_PATH = ROOT / Path(
    "workshop/materials/part-03-harness-optimization/01-unit-test-harness-MILP/run_unit_test_harness_milp.py"
)
FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "behavior_lock_output.json"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("harness_milp_lock", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _current_output(mod) -> dict:
    contract = mod.prompt_writer_agent()
    data = mod.build_data()
    summary = mod.prompt_executor_agent(contract, data)
    harness_result = mod.unit_test_agent(contract, summary, data)
    return {
        "solver_status": summary["solver_status"],
        "objective": summary["objective"],
        "open_depots": summary["open_depots"],
        "open_depot_count": summary["open_depot_count"],
        "cost_breakdown": summary["cost_breakdown"],
        "unmet_metrics": summary["unmet_metrics"],
        "risk_metrics": summary["risk_metrics"],
        "contract_respected": summary["contract_respected"],
        "harness_checks_passed": harness_result["passed"],
        "harness_passed_count": harness_result["passed_count"],
        "harness_total_count": harness_result["total_count"],
        "harness_failures": harness_result["failures"],
    }


def test_behavior_lock_regression_snapshot() -> None:
    mod = _load_module()
    expected = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    current = _current_output(mod)

    assert set(current.keys()) == set(expected.keys())
    assert current["solver_status"] == expected["solver_status"]
    assert current["open_depots"] == expected["open_depots"]
    assert current["open_depot_count"] == expected["open_depot_count"]
    assert current["contract_respected"] is True
    assert current["harness_checks_passed"] is True
    assert current["harness_total_count"] == expected["harness_total_count"]
    assert current["harness_passed_count"] == expected["harness_passed_count"]
    assert current["harness_failures"] == expected["harness_failures"]

    assert current["objective"] == pytest.approx(expected["objective"], abs=1e-7)

    for key in [
        "fixed_opening_cost",
        "expected_transport_cost",
        "expected_shortage_penalty",
        "cvar_risk_term",
        "total_recomputed",
    ]:
        assert current["cost_breakdown"][key] == pytest.approx(
            expected["cost_breakdown"][key], abs=1e-7
        )

    assert current["unmet_metrics"]["expected_unmet"] == pytest.approx(
        expected["unmet_metrics"]["expected_unmet"], abs=1e-9
    )
    assert current["unmet_metrics"]["max_scenario_unmet"] == pytest.approx(
        expected["unmet_metrics"]["max_scenario_unmet"], abs=1e-9
    )
    assert (
        current["unmet_metrics"]["total_unmet_by_scenario"]
        == expected["unmet_metrics"]["total_unmet_by_scenario"]
    )

    for key in ["alpha", "eta", "cvar_shortage"]:
        assert current["risk_metrics"][key] == pytest.approx(
            expected["risk_metrics"][key], abs=1e-9
        )
