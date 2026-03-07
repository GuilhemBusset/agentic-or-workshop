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
SCRIPT_PATH = ROOT / Path(
    "workshop/materials/part-03-harness-optimization/03-adversarial-board-harness-MILP/run_adversarial_board_harness_milp.py"
)
FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "behavior_lock_report.json"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "harness_milp_board_lock", SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import harness module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_behavior_lock_board_report_regression() -> None:
    module = _load_module()
    current = module.run_adversarial_board_harness(
        write_report=False,
        print_console_summary=False,
    )
    expected = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert current["harness"] == expected["harness"]
    assert current["data_inputs"] == expected["data_inputs"]

    assert current["winner"]["candidate_id"] == expected["winner"]["candidate_id"]
    assert current["winner"]["board_score"] == pytest.approx(
        expected["winner"]["board_score"], abs=1e-10
    )

    current_ranking = [
        x["candidate_id"] for x in current["board_decision"]["eligible_ranking"]
    ]
    expected_ranking = [
        x["candidate_id"] for x in expected["board_decision"]["eligible_ranking"]
    ]
    assert current_ranking == expected_ranking

    current_candidates = {
        entry["candidate_id"]: entry for entry in current["candidates"]
    }
    expected_candidates = {
        entry["candidate_id"]: entry for entry in expected["candidates"]
    }
    assert set(current_candidates) == set(expected_candidates)

    for candidate_id in sorted(current_candidates):
        c = current_candidates[candidate_id]
        e = expected_candidates[candidate_id]

        assert c["contract_eligible_for_board"] is True
        assert all(check["passed"] for check in c["contract_checks"])
        assert [x["id"] for x in c["contract_checks"]] == [
            x["id"] for x in e["contract_checks"]
        ]

        assert c["baseline_summary"]["objective"] == pytest.approx(
            e["baseline_summary"]["objective"], abs=1e-7
        )
        assert c["stress_summary"]["unmet_metrics"]["total_unmet"] == pytest.approx(
            e["stress_summary"]["unmet_metrics"]["total_unmet"], abs=1e-7
        )
        assert c["stress_summary"]["unmet_metrics"]["critical_unmet"] == pytest.approx(
            e["stress_summary"]["unmet_metrics"]["critical_unmet"], abs=1e-7
        )
