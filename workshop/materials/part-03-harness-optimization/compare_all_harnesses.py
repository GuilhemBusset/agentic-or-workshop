"""Run and compare all Part-03 harness solver scripts found in this folder."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


@dataclass
class HarnessResult:
    name: str
    script_path: Path
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str
    parse_source: str
    solver_status: str | None
    objective: float | None
    open_depot_count: int | None
    expected_unmet: float | None
    checks_passed: int | None
    checks_total: int | None
    verdict: str
    notes: str


@dataclass
class ParsedSummary:
    solver_status: str | None = None
    objective: float | None = None
    open_depot_count: int | None = None
    expected_unmet: float | None = None
    checks_passed: int | None = None
    checks_total: int | None = None
    verdict: str = "UNKNOWN"
    notes: str = ""


def discover_solver_scripts() -> list[Path]:
    scripts = [
        path
        for path in sorted(ROOT.glob("*/run_*.py"))
        if "harness" in path.parent.name.lower() or "harness" in path.name.lower()
    ]
    return scripts


def _report_files(script_dir: Path) -> list[Path]:
    return sorted(path for path in script_dir.glob("*report*.json") if path.is_file())


def _report_mtimes(script_dir: Path) -> dict[Path, int]:
    return {path: path.stat().st_mtime_ns for path in _report_files(script_dir)}


def _load_changed_report(
    script_dir: Path,
    mtimes_before: dict[Path, int],
) -> dict[str, Any] | None:
    changed: list[Path] = []
    for path in _report_files(script_dir):
        current_mtime = path.stat().st_mtime_ns
        if path not in mtimes_before or current_mtime > mtimes_before[path]:
            changed.append(path)

    if not changed:
        return None

    latest = max(changed, key=lambda path: path.stat().st_mtime_ns)
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _try_parse_json_from_stdout(stdout: str) -> dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None

    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _count_open_depots(raw: Any) -> int | None:
    if isinstance(raw, list):
        return len(raw)
    if isinstance(raw, dict):
        total = 0
        for value in raw.values():
            maybe_float = _as_float(value)
            if maybe_float is None:
                return None
            if maybe_float >= 0.5:
                total += 1
        return total
    return _as_int(raw)


def _parse_unit_harness(payload: dict[str, Any]) -> ParsedSummary | None:
    required_keys = {"solver_status", "objective", "harness_checks_passed"}
    if not required_keys.issubset(payload):
        return None

    checks_total = _as_int(payload.get("harness_total_count"))
    checks_passed = _as_int(payload.get("harness_passed_count"))
    if checks_total is None:
        checks_total = 1
    if checks_passed is None:
        checks_passed = (
            checks_total if bool(payload.get("harness_checks_passed")) else 0
        )

    return ParsedSummary(
        solver_status=str(payload.get("solver_status")),
        objective=_as_float(payload.get("objective")),
        open_depot_count=_count_open_depots(
            payload.get("open_depot_count", payload.get("open_depots"))
        ),
        expected_unmet=_as_float(
            payload.get("unmet_metrics", {}).get("expected_unmet")
            if isinstance(payload.get("unmet_metrics"), dict)
            else None
        ),
        checks_passed=checks_passed,
        checks_total=checks_total,
        verdict="PASS" if bool(payload.get("harness_checks_passed")) else "FAIL",
        notes=f"contract_respected={bool(payload.get('contract_respected', False))}",
    )


def _parse_contract_regression(payload: dict[str, Any]) -> ParsedSummary | None:
    if "checks" not in payload or "baseline" not in payload:
        return None

    checks_block = payload.get("checks")
    if not isinstance(checks_block, dict):
        return None
    contract_checks = checks_block.get("contract", [])
    regression_checks = checks_block.get("regression", [])
    if not isinstance(contract_checks, list) or not isinstance(regression_checks, list):
        return None

    all_checks = contract_checks + regression_checks
    passed = sum(
        1 for check in all_checks if isinstance(check, dict) and check.get("passed")
    )
    total = len(all_checks)

    baseline = payload.get("baseline", {})
    if not isinstance(baseline, dict):
        baseline = {}

    return ParsedSummary(
        solver_status=(
            str(baseline.get("solver_status"))
            if baseline.get("solver_status") is not None
            else None
        ),
        objective=_as_float(baseline.get("objective")),
        open_depot_count=_count_open_depots(baseline.get("open_depots")),
        expected_unmet=_as_float(baseline.get("expected_unmet_demand")),
        checks_passed=passed,
        checks_total=total,
        verdict="PASS" if bool(payload.get("overall_passed")) else "FAIL",
        notes=f"overall_passed={bool(payload.get('overall_passed'))}",
    )


def _parse_adversarial_board(payload: dict[str, Any]) -> ParsedSummary | None:
    if "winner" not in payload or "candidates" not in payload:
        return None

    winner = payload.get("winner", {})
    candidates = payload.get("candidates", [])
    if not isinstance(winner, dict) or not isinstance(candidates, list):
        return None

    winner_id = winner.get("candidate_id")
    selected: dict[str, Any] | None = None
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("candidate_id") == winner_id:
            selected = candidate
            break
    if selected is None:
        return None

    baseline = selected.get("baseline_summary", {})
    if not isinstance(baseline, dict):
        baseline = {}

    contract_checks = selected.get("contract_checks", [])
    if not isinstance(contract_checks, list):
        contract_checks = []
    checks_total = len(contract_checks)
    checks_passed = sum(
        1
        for check in contract_checks
        if isinstance(check, dict) and check.get("passed")
    )
    eligible = bool(selected.get("contract_eligible_for_board"))

    unmet_metrics = baseline.get("unmet_metrics", {})
    if not isinstance(unmet_metrics, dict):
        unmet_metrics = {}

    return ParsedSummary(
        solver_status=(
            str(baseline.get("status")) if baseline.get("status") is not None else None
        ),
        objective=_as_float(baseline.get("objective")),
        open_depot_count=_count_open_depots(
            baseline.get("open_depot_count", baseline.get("open_depots"))
        ),
        expected_unmet=_as_float(unmet_metrics.get("total_unmet")),
        checks_passed=checks_passed,
        checks_total=checks_total,
        verdict="PASS" if eligible else "FAIL",
        notes=f"winner={winner_id}",
    )


def _parse_key_value_summary(stdout: str) -> ParsedSummary | None:
    values: dict[str, str] = {}
    for line in stdout.splitlines():
        match = re.match(r"^([A-Za-z0-9_]+)=([^\n]+)$", line.strip())
        if match:
            values[match.group(1)] = match.group(2).strip()

    if not values:
        return None

    verdict_raw = values.get("overall_harness_verdict")
    verdict = "UNKNOWN"
    if verdict_raw is not None:
        verdict = "PASS" if verdict_raw.upper() == "PASS" else "FAIL"

    return ParsedSummary(
        solver_status=values.get("solver_status"),
        objective=_as_float(values.get("baseline_objective", values.get("objective"))),
        open_depot_count=None,
        expected_unmet=_as_float(values.get("stressed_expected_unmet")),
        checks_passed=None,
        checks_total=None,
        verdict=verdict,
        notes="stdout key-value summary",
    )


def _parse_summary(payload: dict[str, Any] | None, stdout: str) -> ParsedSummary:
    if payload is not None:
        for parser in (
            _parse_unit_harness,
            _parse_contract_regression,
            _parse_adversarial_board,
        ):
            parsed = parser(payload)
            if parsed is not None:
                return parsed

    fallback = _parse_key_value_summary(stdout)
    if fallback is not None:
        return fallback

    return ParsedSummary()


def run_script(path: Path) -> HarnessResult:
    before = _report_mtimes(path.parent)
    started = time.monotonic()
    completed = subprocess.run(
        [sys.executable, str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    duration_seconds = time.monotonic() - started

    payload = _try_parse_json_from_stdout(completed.stdout)
    parse_source = "stdout-json"
    if payload is None:
        payload = _load_changed_report(path.parent, before)
        parse_source = "report-json" if payload is not None else "stdout-text"

    parsed = _parse_summary(payload, completed.stdout)
    if completed.returncode != 0 and parsed.verdict == "UNKNOWN":
        parsed.verdict = "FAIL"

    return HarnessResult(
        name=path.parent.name,
        script_path=path,
        exit_code=completed.returncode,
        duration_seconds=duration_seconds,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
        parse_source=parse_source,
        solver_status=parsed.solver_status,
        objective=parsed.objective,
        open_depot_count=parsed.open_depot_count,
        expected_unmet=parsed.expected_unmet,
        checks_passed=parsed.checks_passed,
        checks_total=parsed.checks_total,
        verdict=parsed.verdict,
        notes=parsed.notes,
    )


def _fmt_float(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def _fmt_int(value: int | None) -> str:
    return "-" if value is None else str(value)


def _fmt_checks(passed: int | None, total: int | None) -> str:
    if passed is None or total is None:
        return "-"
    return f"{passed}/{total}"


def _tail(text: str, lines: int = 3) -> str:
    rows = [line for line in text.splitlines() if line.strip()]
    if not rows:
        return "-"
    return " | ".join(rows[-lines:])


def print_comparison(results: list[HarnessResult]) -> None:
    print("=== Part-03 Harness Comparison (MILP) ===")
    print(f"Discovered {len(results)} harness solver script(s).")
    print()

    name_w = max(len(result.name) for result in results) + 2
    header = (
        f"{'Harness':<{name_w}}"
        f"{'Exit':>9}"
        f"{'Sec':>8}"
        f"{'Objective':>12}"
        f"{'Open':>8}"
        f"{'Unmet':>10}"
        f"{'Checks':>10}"
        f"{'Verdict':>10}"
    )
    print(header)
    print("-" * len(header))

    for result in results:
        exit_label = "OK" if result.exit_code == 0 else f"ERR({result.exit_code})"
        print(
            f"{result.name:<{name_w}}"
            f"{exit_label:>9}"
            f"{result.duration_seconds:>8.2f}"
            f"{_fmt_float(result.objective):>12}"
            f"{_fmt_int(result.open_depot_count):>8}"
            f"{_fmt_float(result.expected_unmet):>10}"
            f"{_fmt_checks(result.checks_passed, result.checks_total):>10}"
            f"{result.verdict:>10}"
        )

    print()
    comparable = [
        result
        for result in results
        if result.objective is not None and result.expected_unmet is not None
    ]
    if len(comparable) >= 2:
        baseline = comparable[0]
        print(f"Baseline harness for deltas: {baseline.name}")
        for result in comparable[1:]:
            if (
                result.objective is None
                or baseline.objective is None
                or result.expected_unmet is None
                or baseline.expected_unmet is None
            ):
                continue
            delta_obj = result.objective - baseline.objective
            delta_unmet = result.expected_unmet - baseline.expected_unmet
            print(
                f"- {result.name}: objective delta={delta_obj:+.2f}, "
                f"unmet delta={delta_unmet:+.2f}"
            )
        print()

    for result in results:
        status = result.solver_status if result.solver_status is not None else "n/a"
        print(
            f"[{result.name}] source={result.parse_source} | "
            f"status={status} | script={result.script_path.relative_to(ROOT)}"
        )
        if result.notes:
            print(f"[{result.name}] {result.notes}")
        if result.exit_code != 0:
            print(f"[{result.name}] stderr_tail={_tail(result.stderr)}")
        elif not result.stdout:
            print(f"[{result.name}] stdout_tail=-")


def main() -> int:
    scripts = discover_solver_scripts()
    if not scripts:
        print("No harness solver scripts were discovered.")
        return 1

    results = [run_script(path) for path in scripts]
    print_comparison(results)

    return 0 if all(result.exit_code == 0 for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
