"""Tests for the adversarial board harness MILP.

Validates report structure, contract checks, winner selection,
board scoring, determinism, and stress test properties.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Ensure the runner module is importable
_RUNNER_DIR = Path(__file__).resolve().parent.parent
if str(_RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(_RUNNER_DIR))

from run_adversarial_board_harness_milp import run_adversarial_board_harness  # noqa: E402

# ---------------------------------------------------------------------------
# Module-scoped fixture: run the harness once
# ---------------------------------------------------------------------------

_REQUIRED_TOP_LEVEL_KEYS = {
    "harness",
    "data_inputs",
    "constants",
    "candidates",
    "board_scoring",
    "board_decision",
    "winner",
}

_REQUIRED_CANDIDATE_FIELDS = {
    "candidate_id",
    "parameters",
    "solver_backend",
    "contract_checks",
    "contract_eligible_for_board",
    "baseline_summary",
    "stress_summary",
    "board_score",
    "board_score_components",
    "selected_as_winner",
}

_REQUIRED_PARAMETER_KEYS = {
    "shortage_penalty_multiplier",
    "effective_shortage_penalty",
    "cvar_weight",
    "cvar_alpha",
}

_REQUIRED_BASELINE_KEYS = {
    "demand_multiplier",
    "status",
    "objective",
    "objective_components",
    "open_depots",
    "open_depot_count",
    "unmet_metrics",
}

_REQUIRED_STRESS_KEYS = {
    "demand_multiplier",
    "frozen_open_design",
    "status",
    "objective",
    "objective_components",
    "open_depots",
    "open_depot_count",
    "unmet_metrics",
}

_CONTRACT_IDS = [
    "C01_model_class_milp",
    "C02_binary_open_decisions",
    "C03_critical_towns_exact",
    "C04_critical_service_floor",
    "C05_capacity_only_if_open",
    "C06_objective_component_consistency",
    "C07_probability_contract",
    "C08_solver_status_ok",
]


@pytest.fixture(scope="module")
def report() -> dict:
    """Run the harness once (no file output, no console) and return the report."""
    return run_adversarial_board_harness(
        write_report=False, print_console_summary=False
    )


# ===================================================================
# TestReportStructure
# ===================================================================
class TestReportStructure:
    def test_at_least_three_candidates(self, report: dict) -> None:
        assert len(report["candidates"]) >= 3

    def test_required_top_level_keys(self, report: dict) -> None:
        assert _REQUIRED_TOP_LEVEL_KEYS.issubset(report.keys())

    def test_each_candidate_has_required_fields(self, report: dict) -> None:
        for cand in report["candidates"]:
            assert _REQUIRED_CANDIDATE_FIELDS.issubset(cand.keys()), (
                f"Candidate {cand.get('candidate_id', '?')} missing keys: "
                f"{_REQUIRED_CANDIDATE_FIELDS - cand.keys()}"
            )

    def test_parameters_have_required_keys(self, report: dict) -> None:
        for cand in report["candidates"]:
            assert _REQUIRED_PARAMETER_KEYS.issubset(cand["parameters"].keys()), (
                f"Candidate {cand['candidate_id']} parameters missing keys: "
                f"{_REQUIRED_PARAMETER_KEYS - cand['parameters'].keys()}"
            )

    def test_baseline_summary_has_required_keys(self, report: dict) -> None:
        for cand in report["candidates"]:
            assert _REQUIRED_BASELINE_KEYS.issubset(cand["baseline_summary"].keys()), (
                f"Candidate {cand['candidate_id']} baseline_summary missing keys: "
                f"{_REQUIRED_BASELINE_KEYS - cand['baseline_summary'].keys()}"
            )

    def test_stress_summary_has_required_keys(self, report: dict) -> None:
        for cand in report["candidates"]:
            assert _REQUIRED_STRESS_KEYS.issubset(cand["stress_summary"].keys()), (
                f"Candidate {cand['candidate_id']} stress_summary missing keys: "
                f"{_REQUIRED_STRESS_KEYS - cand['stress_summary'].keys()}"
            )


# ===================================================================
# TestContractChecks
# ===================================================================
class TestContractChecks:
    def test_all_candidates_have_eight_contract_checks(self, report: dict) -> None:
        for cand in report["candidates"]:
            assert len(cand["contract_checks"]) == 8, (
                f"Candidate {cand['candidate_id']} has "
                f"{len(cand['contract_checks'])} checks, expected 8"
            )

    def test_contract_check_ids_match_constants(self, report: dict) -> None:
        expected_ids = set(report["constants"]["contract_check_ids"])
        for cand in report["candidates"]:
            actual_ids = {ch["id"] for ch in cand["contract_checks"]}
            assert actual_ids == expected_ids, (
                f"Candidate {cand['candidate_id']} check IDs mismatch: "
                f"extra={actual_ids - expected_ids}, "
                f"missing={expected_ids - actual_ids}"
            )


# ===================================================================
# TestWinnerValidity
# ===================================================================
class TestWinnerValidity:
    def test_winner_exists(self, report: dict) -> None:
        assert report["winner"]["candidate_id"] is not None

    def test_winner_is_eligible(self, report: dict) -> None:
        winner_id = report["winner"]["candidate_id"]
        for cand in report["candidates"]:
            if cand["candidate_id"] == winner_id:
                assert cand["contract_eligible_for_board"] is True
                return
        pytest.fail(f"Winner {winner_id} not found in candidates")

    def test_winner_passes_all_contract_checks(self, report: dict) -> None:
        winner_id = report["winner"]["candidate_id"]
        for cand in report["candidates"]:
            if cand["candidate_id"] == winner_id:
                for ch in cand["contract_checks"]:
                    assert ch["passed"] is True, (
                        f"Winner {winner_id} failed check {ch['id']}: "
                        f"{ch.get('details', '')}"
                    )
                return
        pytest.fail(f"Winner {winner_id} not found in candidates")


# ===================================================================
# TestBoardScoring
# ===================================================================
class TestBoardScoring:
    def test_all_board_scores_between_zero_and_one(self, report: dict) -> None:
        for cand in report["candidates"]:
            if cand["board_score"] is not None:
                assert 0.0 - 1e-9 <= cand["board_score"] <= 1.0 + 1e-9, (
                    f"Candidate {cand['candidate_id']} board_score "
                    f"{cand['board_score']} out of [0, 1]"
                )

    def test_winner_has_lowest_board_score(self, report: dict) -> None:
        winner_id = report["winner"]["candidate_id"]
        winner_score = report["winner"]["board_score"]
        for cand in report["candidates"]:
            if cand["board_score"] is not None:
                assert winner_score <= cand["board_score"] + 1e-9, (
                    f"Winner {winner_id} score {winner_score} > "
                    f"candidate {cand['candidate_id']} score {cand['board_score']}"
                )


# ===================================================================
# TestDeterminism
# ===================================================================
class TestDeterminism:
    def test_deterministic_across_runs(self) -> None:
        r1 = run_adversarial_board_harness(
            write_report=False, print_console_summary=False
        )
        r2 = run_adversarial_board_harness(
            write_report=False, print_console_summary=False
        )
        assert r1["winner"]["candidate_id"] == r2["winner"]["candidate_id"]
        if r1["winner"]["board_score"] is not None:
            assert math.isclose(
                r1["winner"]["board_score"],
                r2["winner"]["board_score"],
                abs_tol=1e-6,
            )


# ===================================================================
# TestStressTest
# ===================================================================
class TestStressTest:
    def test_stress_demand_multiplier_is_1_2(self, report: dict) -> None:
        for cand in report["candidates"]:
            assert cand["stress_summary"]["demand_multiplier"] == 1.2

    def test_stress_frozen_design_matches_baseline(self, report: dict) -> None:
        for cand in report["candidates"]:
            baseline_open = set(cand["baseline_summary"]["open_depots"])
            frozen = cand["stress_summary"]["frozen_open_design"]
            frozen_open = {d for d, v in frozen.items() if v == 1}
            assert baseline_open == frozen_open, (
                f"Candidate {cand['candidate_id']}: "
                f"baseline depots {baseline_open} != frozen {frozen_open}"
            )

    def test_stress_objective_at_least_baseline(self, report: dict) -> None:
        for cand in report["candidates"]:
            bs_obj = cand["baseline_summary"]["objective"]
            st_obj = cand["stress_summary"]["objective"]
            # Stress (higher demand, frozen depots) should be at least as costly
            assert st_obj >= bs_obj - 1e-2, (
                f"Candidate {cand['candidate_id']}: stress obj {st_obj:.4f} "
                f"< baseline obj {bs_obj:.4f}"
            )
