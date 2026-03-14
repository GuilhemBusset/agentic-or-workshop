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
    data = mod.load_data()
    artifacts = mod.build_model(data)
    result = mod.solve(artifacts, data)
    passed = mod.run_harness_checks(result, data)
    result["harness_checks_passed"] = passed
    return result


def test_behavior_lock_regression_snapshot() -> None:
    mod = _load_module()
    expected = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    current = _current_output(mod)

    assert current["solver_status"] == expected["solver_status"]
    assert current["open_depots"] == expected["open_depots"]
    assert current["harness_checks_passed"] is True

    assert current["objective"] == pytest.approx(expected["objective"], abs=1e-2)
