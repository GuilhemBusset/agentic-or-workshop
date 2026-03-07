#!/usr/bin/env python3
"""Lightweight validator for workshop CSV data."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TableSpec:
    name: str
    key_columns: tuple[str, ...]
    nonnegative_columns: tuple[str, ...]


TABLE_SPECS: tuple[TableSpec, ...] = (
    TableSpec("depots.csv", ("depot_id",), ("capacity", "fixed_cost")),
    TableSpec("towns.csv", ("town_id",), ("base_demand", "service_min")),
    TableSpec("arcs.csv", ("arc_id",), ("shipping_cost", "distance")),
    TableSpec("scenarios.csv", ("scenario_id",), ("probability",)),
    TableSpec("scenario_demands.csv", ("scenario_id", "town_id"), ("demand",)),
)


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def check_keys(
    name: str, rows: list[dict[str, str]], key_columns: tuple[str, ...]
) -> list[str]:
    if not key_columns:
        return []
    missing_cols = [
        col for col in key_columns if col not in (rows[0].keys() if rows else [])
    ]
    if missing_cols:
        return [f"{name}: missing key columns: {', '.join(missing_cols)}"]
    counter = Counter(tuple(row[col] for col in key_columns) for row in rows)
    duplicates = [k for k, count in counter.items() if count > 1]
    if duplicates:
        sample = ", ".join(str(x) for x in duplicates[:5])
        return [
            f"{name}: duplicate key rows found ({len(duplicates)}), sample: {sample}"
        ]
    return []


def check_nonnegative(
    name: str,
    rows: list[dict[str, str]],
    columns: tuple[str, ...],
) -> list[str]:
    errors: list[str] = []
    if not columns or not rows:
        return errors
    header = rows[0].keys()
    for col in columns:
        if col not in header:
            errors.append(f"{name}: missing nonnegative column '{col}'")
            continue
        for idx, row in enumerate(rows, start=2):
            raw = row[col]
            try:
                if float(raw) < 0:
                    errors.append(f"{name}:{idx}: {col} is negative ({raw})")
            except ValueError:
                errors.append(f"{name}:{idx}: {col} is not numeric ({raw})")
    return errors


def check_fk_rows(
    rows: list[dict[str, str]], col: str, valid: set[str], table: str, ref: str
) -> list[str]:
    errors: list[str] = []
    for idx, row in enumerate(rows, start=2):
        value = row.get(col, "")
        if value not in valid:
            errors.append(f"{table}:{idx}: {col}='{value}' missing in {ref}")
    return errors


def run_validation(data_dir: Path) -> tuple[bool, list[str], list[str]]:
    info: list[str] = []
    errors: list[str] = []
    tables: dict[str, list[dict[str, str]]] = {}

    for spec in TABLE_SPECS:
        path = data_dir / spec.name
        if not path.exists():
            errors.append(f"Missing file: {spec.name}")
            continue
        rows = load_rows(path)
        tables[spec.name] = rows
        info.append(f"{spec.name}: {len(rows)} rows")
        errors.extend(check_keys(spec.name, rows, spec.key_columns))
        errors.extend(check_nonnegative(spec.name, rows, spec.nonnegative_columns))

    depots = {r["depot_id"] for r in tables.get("depots.csv", []) if "depot_id" in r}
    towns = {r["town_id"] for r in tables.get("towns.csv", []) if "town_id" in r}
    scenarios = {
        r["scenario_id"] for r in tables.get("scenarios.csv", []) if "scenario_id" in r
    }
    if "arcs.csv" in tables:
        errors.extend(
            check_fk_rows(
                tables["arcs.csv"], "depot_id", depots, "arcs.csv", "depots.csv"
            )
        )
        errors.extend(
            check_fk_rows(tables["arcs.csv"], "town_id", towns, "arcs.csv", "towns.csv")
        )
    if "scenario_demands.csv" in tables:
        errors.extend(
            check_fk_rows(
                tables["scenario_demands.csv"],
                "scenario_id",
                scenarios,
                "scenario_demands.csv",
                "scenarios.csv",
            )
        )
        errors.extend(
            check_fk_rows(
                tables["scenario_demands.csv"],
                "town_id",
                towns,
                "scenario_demands.csv",
                "towns.csv",
            )
        )

    return (len(errors) == 0), info, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate workshop CSV data package.")
    parser.add_argument(
        "--data-dir",
        default=Path(__file__).resolve().parent,
        type=Path,
        help="Directory containing CSV files (default: script directory).",
    )
    args = parser.parse_args()

    ok, info, errors = run_validation(args.data_dir)

    print("Validation summary:")
    for line in info:
        print(f"  - {line}")

    if ok:
        print("Result: PASS")
        return 0

    print("Result: FAIL")
    for err in errors:
        print(f"  - {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
