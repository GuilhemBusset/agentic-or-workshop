from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(
    "workshop/materials/part-03-harness-optimization/01-unit-test-harness-MILP/run_unit_test_harness_milp.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("harness_milp", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return _load_module()


@pytest.fixture(scope="module")
def contract(mod):
    return mod.prompt_writer_agent()


@pytest.fixture(scope="module")
def data(mod):
    return mod.build_data()


def test_contract_declares_milp_with_binary_open_vars(contract):
    assert contract["model_class"] == "MILP"
    assert contract["decision_variables"]["open_depot_binary"] is True


def test_data_shape_and_probabilities(data):
    assert len(data["depots"]) == 6
    assert len(data["towns"]) == 12
    assert len(data["scenarios"]) == 8
    assert len(data["scenario_demands"]) == 8 * 12
    assert data["probability_sum"] == pytest.approx(1.0, abs=1e-9)


def test_critical_towns_exact(contract, data):
    expected = {"T03", "T04", "T07", "T12"}
    assert set(contract["critical_towns"]) == expected
    assert set(data["critical_towns"]) == expected


def test_executor_returns_valid_summary(mod, contract, data):
    summary = mod.prompt_executor_agent(contract, data)

    required_top_level = {
        "solver_status",
        "objective",
        "open_depots",
        "open_depot_count",
        "cost_breakdown",
        "unmet_metrics",
        "risk_metrics",
        "contract_respected",
    }
    assert required_top_level.issubset(summary.keys())

    assert isinstance(summary["open_depots"], list)
    assert summary["open_depot_count"] == len(summary["open_depots"])

    cost = summary["cost_breakdown"]
    for key in [
        "fixed_opening_cost",
        "expected_transport_cost",
        "expected_shortage_penalty",
        "cvar_risk_term",
        "total_recomputed",
    ]:
        assert key in cost
        assert isinstance(cost[key], float)

    unmet = summary["unmet_metrics"]
    for key in ["expected_unmet", "max_scenario_unmet", "total_unmet_by_scenario"]:
        assert key in unmet

    risk = summary["risk_metrics"]
    for key in ["alpha", "eta", "cvar_shortage"]:
        assert key in risk


def test_unit_test_agent_passes_for_valid_solution(mod, contract, data):
    summary = mod.prompt_executor_agent(contract, data)
    verdict = mod.unit_test_agent(contract, summary, data)
    assert verdict["passed"] is True
    assert verdict["failures"] == []


def test_unit_test_agent_fails_on_corrupted_objective(mod, contract, data):
    summary = mod.prompt_executor_agent(contract, data)
    broken_summary = dict(summary)
    broken_summary["objective"] = summary["objective"] + 123.0

    verdict = mod.unit_test_agent(contract, broken_summary, data)
    assert verdict["passed"] is False
    assert any("objective" in failure.lower() for failure in verdict["failures"])


def test_executor_rejects_non_milp_contract(mod, contract, data):
    bad_contract = dict(contract)
    bad_contract["model_class"] = "LP"

    with pytest.raises(ValueError, match="MILP"):
        mod.prompt_executor_agent(bad_contract, data)
