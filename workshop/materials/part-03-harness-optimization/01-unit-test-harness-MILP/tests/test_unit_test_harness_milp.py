"""Tests for the disaster-relief transportation MILP solver.

Covers data integrity, MILP structure, solver output validity,
and critical-town service levels.
"""

import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parents[4] / "data"
SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent / "run_unit_test_harness_milp.py"
)

CRITICAL_TOWNS = {"T03", "T04", "T07", "T12"}
CRITICAL_SERVICE_MIN = 0.95


# ---------------------------------------------------------------------------
# Helper: load CSV
# ---------------------------------------------------------------------------
def _load_csv(filename: str) -> list[dict[str, str]]:
    with open(DATA_DIR / filename, newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def depots():
    return _load_csv("depots.csv")


@pytest.fixture(scope="module")
def towns():
    return _load_csv("towns.csv")


@pytest.fixture(scope="module")
def arcs():
    return _load_csv("arcs.csv")


@pytest.fixture(scope="module")
def scenarios():
    return _load_csv("scenarios.csv")


@pytest.fixture(scope="module")
def scenario_demands():
    return _load_csv("scenario_demands.csv")


@pytest.fixture(scope="module")
def solver_output() -> dict:
    """Run the solver script once and return parsed JSON output."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, (
        f"Solver script failed.\nstderr: {result.stderr}\nstdout: {result.stdout}"
    )
    # Extract the last JSON object from stdout (may be multi-line)
    stdout = result.stdout.strip()
    # Find the last top-level '{' and parse from there
    idx = stdout.rfind("\n{")
    if idx == -1 and stdout.startswith("{"):
        idx = -1  # the whole output is JSON
    json_str = stdout[idx + 1:]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        pytest.fail(f"Could not parse JSON from solver output: {e}\nstdout: {stdout}")


# ===================================================================
# 1. DATA INTEGRITY TESTS
# ===================================================================
class TestDataIntegrity:
    def test_depot_count(self, depots):
        assert len(depots) == 6

    def test_town_count(self, towns):
        assert len(towns) == 12

    def test_scenario_count(self, scenarios):
        assert len(scenarios) == 8

    def test_probabilities_sum_to_one(self, scenarios):
        total = sum(float(s["probability"]) for s in scenarios)
        assert math.isclose(total, 1.0, abs_tol=1e-9)

    def test_all_scenario_demand_entries(self, scenarios, towns, scenario_demands):
        expected = len(scenarios) * len(towns)
        assert len(scenario_demands) == expected

    def test_critical_towns_present(self, towns):
        town_ids = {t["town_id"] for t in towns}
        assert CRITICAL_TOWNS.issubset(town_ids)

    def test_critical_towns_service_min(self, towns):
        for t in towns:
            if t["town_id"] in CRITICAL_TOWNS:
                assert float(t["service_min"]) >= CRITICAL_SERVICE_MIN

    def test_arcs_cover_all_depot_town_pairs(self, depots, towns, arcs):
        expected_pairs = {
            (d["depot_id"], t["town_id"]) for d in depots for t in towns
        }
        actual_pairs = {(a["depot_id"], a["town_id"]) for a in arcs}
        assert expected_pairs == actual_pairs


# ===================================================================
# 2. MILP STRUCTURE TESTS (via solver module import)
# ===================================================================
class TestMILPStructure:
    """Import the solver module and inspect model objects."""

    @pytest.fixture(scope="class")
    def model_artifacts(self):
        """Build and return model artifacts without solving."""
        # Import the solver module
        sys.path.insert(0, str(SCRIPT_PATH.parent))
        try:
            import run_unit_test_harness_milp as mod
        finally:
            sys.path.pop(0)

        data = mod.load_data()
        artifacts = mod.build_model(data)
        return artifacts, data

    def test_depot_open_vars_are_binary(self, model_artifacts):
        artifacts, data = model_artifacts
        y_vars = artifacts["y"]
        for d_id, var in y_vars.items():
            # xpress binary vars have vartype 'B'
            assert var.vartype == 1 or str(var.vartype) in ("1", "B"), (
                f"Depot variable {d_id} should be binary, got vartype={var.vartype}"
            )

    def test_number_of_depot_vars(self, model_artifacts):
        artifacts, data = model_artifacts
        assert len(artifacts["y"]) == 6

    def test_capacity_linked_to_open(self, model_artifacts):
        """Verify that capacity constraints exist linking shipment to y vars.

        We check that when a depot is closed (y=0), no shipments flow.
        This is structural: sum_t x[d,t,s] <= capacity[d] * y[d].
        We verify by checking the model has the right number of such constraints.
        """
        artifacts, data = model_artifacts
        # There should be one capacity constraint per depot per scenario
        n_depots = len(data["depots"])
        n_scenarios = len(data["scenarios"])
        assert len(artifacts["capacity_constrs"]) == n_depots * n_scenarios

    def test_shipment_vars_non_negative(self, model_artifacts):
        artifacts, _ = model_artifacts
        for key, var in artifacts["x"].items():
            assert var.lb >= 0, f"Shipment var {key} has negative lower bound"

    def test_shortage_vars_exist(self, model_artifacts):
        artifacts, data = model_artifacts
        n_towns = len(data["towns"])
        n_scenarios = len(data["scenarios"])
        assert len(artifacts["u"]) == n_towns * n_scenarios


# ===================================================================
# 3. SOLVER OUTPUT VALIDITY
# ===================================================================
class TestSolverOutput:
    def test_solver_status_optimal(self, solver_output):
        assert solver_output["solver_status"].lower() in (
            "optimal",
            "lp_optimal",
            "mip_optimal",
            "mip_solution",
        )

    def test_objective_is_finite_positive(self, solver_output):
        obj = solver_output["objective"]
        assert isinstance(obj, (int, float))
        assert obj > 0
        assert math.isfinite(obj)

    def test_open_depots_non_empty(self, solver_output):
        assert len(solver_output["open_depots"]) > 0

    def test_open_depots_are_valid_ids(self, solver_output):
        valid = {f"D{i:02d}" for i in range(1, 7)}
        for d in solver_output["open_depots"]:
            assert d in valid

    def test_harness_checks_passed(self, solver_output):
        assert solver_output["harness_checks_passed"] is True

    def test_output_has_required_keys(self, solver_output):
        required = {"solver_status", "objective", "open_depots", "harness_checks_passed"}
        assert required.issubset(solver_output.keys())


# ===================================================================
# 4. CRITICAL-TOWN SERVICE LEVELS
# ===================================================================
class TestCriticalTownServiceLevels:
    def test_critical_towns_served_at_95_pct(self, solver_output):
        """Verify that the solver reports critical towns meeting 95% service."""
        # The solver script includes service level info
        service = solver_output.get("critical_town_service")
        assert service is not None, "Output missing 'critical_town_service' key"
        for town_id in CRITICAL_TOWNS:
            town_service = service.get(town_id)
            assert town_service is not None, f"Missing service data for {town_id}"
            # min_ratio across all scenarios should be >= 0.95
            assert town_service["min_ratio"] >= CRITICAL_SERVICE_MIN - 1e-6, (
                f"{town_id}: min service ratio {town_service['min_ratio']:.4f} "
                f"< {CRITICAL_SERVICE_MIN}"
            )
