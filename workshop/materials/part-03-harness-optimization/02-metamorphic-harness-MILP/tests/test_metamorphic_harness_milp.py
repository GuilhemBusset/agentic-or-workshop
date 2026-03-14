"""Tests for the metamorphic testing harness MILP solver."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(
    "workshop/materials/part-03-harness-optimization/"
    "02-metamorphic-harness-MILP/run_metamorphic_harness_milp.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("metamorphic_harness", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["metamorphic_harness"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return _load_module()


@pytest.fixture(scope="module")
def data(mod):
    return mod.load_data()


@pytest.fixture(scope="module")
def baseline(mod, data):
    return mod.solve_milp(data, model_name="test_baseline")


@pytest.fixture(scope="module")
def report(mod):
    return mod.run_harness()


# ---------------------------------------------------------------------------
# Baseline solver correctness
# ---------------------------------------------------------------------------


class TestBaselineSolver:
    def test_solver_finds_optimal(self, baseline):
        assert baseline.feasible
        status = baseline.status.lower()
        assert "optimal" in status or status.startswith("mip_")

    def test_objective_is_positive(self, baseline):
        assert baseline.objective > 0

    def test_at_least_one_depot_open(self, baseline):
        assert len(baseline.open_depots) >= 1

    def test_cost_breakdown_sums_to_objective(self, baseline):
        recomputed = (
            baseline.fixed_opening_cost
            + baseline.expected_transport_cost
            + baseline.expected_shortage_penalty
            + baseline.cvar_risk_term
        )
        assert abs(recomputed - baseline.objective) < 1e-3

    def test_fixed_cost_matches_opened_depots(self, baseline, data):
        expected_fc = sum(data.fixed_cost[d] for d in baseline.open_depots)
        assert abs(baseline.fixed_opening_cost - expected_fc) < 1e-3

    def test_unmet_is_non_negative(self, baseline):
        assert baseline.expected_unmet >= -1e-9

    def test_data_dimensions(self, data):
        assert len(data.depots) == 6
        assert len(data.towns) == 12
        assert len(data.scenarios) == 8
        assert data.critical_towns == {"T03", "T04", "T07", "T12"}


# ---------------------------------------------------------------------------
# Metamorphic relation tests
# ---------------------------------------------------------------------------


class TestMetamorphicRelations:
    def test_capacity_halving(self, mod, data, baseline):
        result = mod.relation_capacity_halving(data, baseline)
        assert result.passed, (
            f"capacity_halving failed: perturbed={result.perturbed_value:.6f} "
            f"< baseline={result.baseline_value:.6f}"
        )

    def test_fixed_cost_halving(self, mod, data, baseline):
        result = mod.relation_fixed_cost_halving(data, baseline)
        assert result.passed, (
            f"fixed_cost_halving failed: perturbed={result.perturbed_value:.6f} "
            f"> baseline={result.baseline_value:.6f}"
        )

    def test_demand_scaling(self, mod, data, baseline):
        result = mod.relation_demand_scaling(data, baseline)
        assert result.passed, f"demand_scaling failed: {result.description}"

    def test_penalty_under_scarcity(self, mod, data, baseline):
        result = mod.relation_penalty_under_scarcity(data, baseline)
        assert result.passed, (
            f"penalty_under_scarcity failed: perturbed={result.perturbed_value:.6f} "
            f"> baseline={result.baseline_value:.6f}"
        )

    def test_tightened_critical_floor(self, mod, data, baseline):
        result = mod.relation_tightened_critical_floor(data, baseline)
        assert result.passed, (
            f"tightened_critical_floor failed: perturbed={result.perturbed_value:.6f} "
            f"< baseline={result.baseline_value:.6f}"
        )


# ---------------------------------------------------------------------------
# Full harness report
# ---------------------------------------------------------------------------


class TestHarnessReport:
    def test_report_has_baseline(self, report):
        assert "baseline" in report
        assert report["baseline"]["feasible"] is True

    def test_report_has_all_relations(self, mod, report):
        assert len(report["relations"]) == len(mod.ALL_RELATIONS)

    def test_all_relations_passed(self, report):
        for rel in report["relations"]:
            assert rel["passed"], (
                f"Relation {rel['name']} failed: {rel.get('error', rel['description'])}"
            )

    def test_report_all_passed_flag(self, report):
        assert report["all_passed"] is True

    def test_report_is_serializable(self, report):
        serialized = json.dumps(report)
        deserialized = json.loads(serialized)
        assert deserialized == report

    def test_report_file_written(self, mod):
        report_path = Path(__file__).resolve().parents[1] / "metamorphic_report.json"
        mod.main()
        assert report_path.exists()
        content = json.loads(report_path.read_text())
        assert content["baseline"]["feasible"] is True
