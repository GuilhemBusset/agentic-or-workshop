from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


SCRIPT_PATH = Path(
    "workshop/materials/part-03-harness-optimization/03-adversarial-board-harness-MILP/run_adversarial_board_harness_milp.py"
)
REPORT_PATH = SCRIPT_PATH.parent / "adversarial_board_report.json"
REQUIRED_CANDIDATES = {
    "candidate_cost_lean",
    "candidate_balanced",
    "candidate_resilience",
}
REQUIRED_CONTRACT_CHECKS = [
    "C01_model_class_milp",
    "C02_binary_open_decisions",
    "C03_critical_towns_exact",
    "C04_critical_service_floor",
    "C05_capacity_only_if_open",
    "C06_objective_component_consistency",
    "C07_probability_contract",
    "C08_solver_status_ok",
]


def _load_module():
    spec = importlib.util.spec_from_file_location("harness_milp", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import harness module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run_report(write_report: bool) -> dict:
    module = _load_module()
    return module.run_adversarial_board_harness(
        write_report=write_report,
        print_console_summary=False,
    )


def test_report_contains_candidates_parameters_contracts_stress_and_scores():
    report = _run_report(write_report=True)

    assert REPORT_PATH.exists()
    on_disk = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert report["winner"]["candidate_id"] == on_disk["winner"]["candidate_id"]

    assert "candidates" in report
    assert len(report["candidates"]) >= 3

    candidate_ids = {entry["candidate_id"] for entry in report["candidates"]}
    assert REQUIRED_CANDIDATES.issubset(candidate_ids)

    param_tuples = {
        (
            entry["parameters"]["shortage_penalty_multiplier"],
            entry["parameters"]["cvar_weight"],
        )
        for entry in report["candidates"]
        if entry["candidate_id"] in REQUIRED_CANDIDATES
    }
    assert len(param_tuples) == 3

    for entry in report["candidates"]:
        assert "parameters" in entry
        assert "contract_checks" in entry
        assert "baseline_summary" in entry
        assert "stress_summary" in entry
        assert "board_score" in entry
        assert "board_score_components" in entry
        assert "contract_eligible_for_board" in entry

        check_ids = [check["id"] for check in entry["contract_checks"]]
        assert check_ids == REQUIRED_CONTRACT_CHECKS

        stress_summary = entry["stress_summary"]
        assert stress_summary["demand_multiplier"] == pytest.approx(1.20, abs=1e-12)
        assert "objective" in stress_summary
        assert "objective_components" in stress_summary
        assert "unmet_metrics" in stress_summary
        assert "total_unmet" in stress_summary["unmet_metrics"]
        assert "critical_unmet" in stress_summary["unmet_metrics"]


def test_board_score_formula_applied_for_each_contract_eligible_candidate():
    report = _run_report(write_report=False)
    weights = report["board_scoring"]["weights"]

    for entry in report["candidates"]:
        if not entry["contract_eligible_for_board"]:
            assert entry["board_score"] is None
            continue

        components = entry["board_score_components"]
        expected = (
            weights["normalized_baseline_objective"]
            * components["normalized_baseline_objective"]
            + weights["normalized_stressed_total_unmet"]
            * components["normalized_stressed_total_unmet"]
            + weights["normalized_stressed_critical_unmet"]
            * components["normalized_stressed_critical_unmet"]
            + weights["normalized_open_depot_count"]
            * components["normalized_open_depot_count"]
        )
        assert entry["board_score"] == pytest.approx(expected, abs=1e-12)


def test_tie_break_logic_critical_then_total_then_lexicographic():
    module = _load_module()

    eligible_entries = [
        {
            "candidate_id": "candidate_zeta",
            "baseline_summary": {"objective": 100.0, "open_depot_count": 2},
            "stress_summary": {
                "unmet_metrics": {"total_unmet": 10.0, "critical_unmet": 4.0}
            },
        },
        {
            "candidate_id": "candidate_alpha",
            "baseline_summary": {"objective": 100.0, "open_depot_count": 2},
            "stress_summary": {
                "unmet_metrics": {"total_unmet": 10.0, "critical_unmet": 4.0}
            },
        },
        {
            "candidate_id": "candidate_mid",
            "baseline_summary": {"objective": 100.0, "open_depot_count": 2},
            "stress_summary": {
                "unmet_metrics": {"total_unmet": 9.0, "critical_unmet": 5.0}
            },
        },
    ]

    # Force all board scores to tie so only explicit tie-break rules apply.
    board_scoring = {
        "candidate_scores": {
            "candidate_alpha": {"board_score": 1.0},
            "candidate_mid": {"board_score": 1.0},
            "candidate_zeta": {"board_score": 1.0},
        }
    }

    decision = module.select_winner(eligible_entries, board_scoring)
    ranking_ids = [item["candidate_id"] for item in decision["eligible_ranking"]]

    assert decision["winner_candidate_id"] == "candidate_alpha"
    assert ranking_ids == ["candidate_alpha", "candidate_zeta", "candidate_mid"]


def test_winner_is_contract_eligible_and_selected_from_ranking():
    report = _run_report(write_report=False)

    winner_id = report["winner"]["candidate_id"]
    winner_entries = [
        entry for entry in report["candidates"] if entry["candidate_id"] == winner_id
    ]

    assert len(winner_entries) == 1
    assert winner_entries[0]["contract_eligible_for_board"] is True
    assert winner_entries[0]["selected_as_winner"] is True

    ranking_top = report["board_decision"]["eligible_ranking"][0]["candidate_id"]
    assert ranking_top == winner_id


def test_deterministic_winner_and_scores_across_repeated_runs():
    report_a = _run_report(write_report=False)
    report_b = _run_report(write_report=False)

    assert report_a["winner"]["candidate_id"] == report_b["winner"]["candidate_id"]
    assert report_a["winner"]["board_score"] == pytest.approx(
        report_b["winner"]["board_score"], abs=1e-12
    )

    scores_a = {
        entry["candidate_id"]: entry["board_score"]
        for entry in report_a["candidates"]
        if entry["board_score"] is not None
    }
    scores_b = {
        entry["candidate_id"]: entry["board_score"]
        for entry in report_b["candidates"]
        if entry["board_score"] is not None
    }

    assert scores_a == pytest.approx(scores_b, abs=1e-12)
