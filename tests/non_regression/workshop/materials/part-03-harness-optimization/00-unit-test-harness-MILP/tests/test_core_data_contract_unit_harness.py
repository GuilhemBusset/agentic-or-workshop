from __future__ import annotations

import csv
from pathlib import Path


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "workshop").is_dir() and (parent / "tests").is_dir():
            return parent
    raise RuntimeError("Repository root not found")


ROOT = _repo_root()
DATA_DIR = ROOT / "workshop" / "data"


def _header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle))


def test_core_files_exist_for_harness() -> None:
    for name in [
        "depots.csv",
        "towns.csv",
        "arcs.csv",
        "scenarios.csv",
        "scenario_demands.csv",
    ]:
        assert (DATA_DIR / name).is_file(), f"Missing required core file: {name}"


def test_required_headers_for_harness_inputs() -> None:
    assert set(_header(DATA_DIR / "depots.csv")) >= {
        "depot_id",
        "capacity",
        "fixed_cost",
    }
    assert set(_header(DATA_DIR / "towns.csv")) >= {
        "town_id",
        "priority_flag",
        "service_min",
    }
    assert set(_header(DATA_DIR / "arcs.csv")) >= {
        "depot_id",
        "town_id",
        "shipping_cost",
    }
    assert set(_header(DATA_DIR / "scenarios.csv")) >= {"scenario_id", "probability"}
    assert set(_header(DATA_DIR / "scenario_demands.csv")) >= {
        "scenario_id",
        "town_id",
        "demand",
    }
