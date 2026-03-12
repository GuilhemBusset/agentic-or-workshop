"""Run and compare the three LP strategy implementations side-by-side.

Usage:
    uv run python workshop/materials/part-02-build-multi-agent/compare_all_solutions.py
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


@dataclass
class StrategyResult:
    name: str
    script_path: Path
    raw_output: str
    status: str
    objective: float
    active_depots: str
    expected_transport_cost: float
    expected_shortage_penalty: float
    expected_unmet_demand: float
    cvar_shortage_indicator: float
    worst_scenario_unmet: float
    prompt_contract_respected: bool
    selected_risk_weight: float | None = None
    candidate_count: int = 0


def run_script(path: Path) -> str:
    completed = subprocess.run(
        [sys.executable, str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _extract(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        raise ValueError(f"Could not parse '{label}' from output.")
    return match.group(1).strip()


def parse_result(name: str, script_path: Path, raw_output: str) -> StrategyResult:
    status = _extract(r"Solver status:\s*(.+)", raw_output, "status")
    objective = float(
        _extract(r"Objective value:\s*([0-9.]+)", raw_output, "objective")
    )
    active_depots = _extract(r"Active depots:\s*(.+)", raw_output, "active depots")
    expected_transport_cost = float(
        _extract(
            r"Expected transport cost:\s*([0-9.]+)",
            raw_output,
            "expected transport cost",
        )
    )
    expected_shortage_penalty = float(
        _extract(
            r"Expected shortage penalty:\s*([0-9.]+)",
            raw_output,
            "expected shortage penalty",
        )
    )
    expected_unmet_demand = float(
        _extract(
            r"Expected unmet demand:\s*([0-9.]+)", raw_output, "expected unmet demand"
        )
    )
    cvar_shortage_indicator = float(
        _extract(
            r"CVaR-style shortage indicator:\s*([0-9.]+)",
            raw_output,
            "cvar shortage indicator",
        )
    )
    worst_scenario_unmet = float(
        _extract(
            r"Worst scenario unmet demand:\s*([0-9.]+)",
            raw_output,
            "worst scenario unmet",
        )
    )
    prompt_contract_respected = (
        _extract(
            r"Prompt contract respected:\s*(True|False)",
            raw_output,
            "prompt contract respected",
        )
        == "True"
    )

    selected_risk_weight: float | None = None
    selected_match = re.search(r"Selected risk weight:\s*([0-9.]+)", raw_output)
    if selected_match:
        selected_risk_weight = float(selected_match.group(1))

    candidate_count = len(re.findall(r"risk_w=", raw_output))

    return StrategyResult(
        name=name,
        script_path=script_path,
        raw_output=raw_output,
        status=status,
        objective=objective,
        active_depots=active_depots,
        expected_transport_cost=expected_transport_cost,
        expected_shortage_penalty=expected_shortage_penalty,
        expected_unmet_demand=expected_unmet_demand,
        cvar_shortage_indicator=cvar_shortage_indicator,
        worst_scenario_unmet=worst_scenario_unmet,
        prompt_contract_respected=prompt_contract_respected,
        selected_risk_weight=selected_risk_weight,
        candidate_count=candidate_count,
    )


def print_comparison(results: list[StrategyResult]) -> None:
    print("=== Cross-Strategy Comparison ===")
    print()

    name_w = max(len(r.name) for r in results) + 2
    header = (
        f"{'Strategy':<{name_w}}"
        f"{'Objective':>12}"
        f"{'Exp Unmet':>12}"
        f"{'CVaR':>12}"
        f"{'Worst Unmet':>14}"
        f"{'Active Depots':>15}"
        f"{'Contract':>11}"
    )
    print(header)
    print("-" * len(header))

    for r in results:
        active_count = len([x for x in r.active_depots.split(",") if x.strip()])
        print(
            f"{r.name:<{name_w}}"
            f"{r.objective:>12.2f}"
            f"{r.expected_unmet_demand:>12.2f}"
            f"{r.cvar_shortage_indicator:>12.2f}"
            f"{r.worst_scenario_unmet:>14.2f}"
            f"{active_count:>15d}"
            f"{str(r.prompt_contract_respected):>11}"
        )

    print()
    baseline = results[0]
    print(f"Baseline strategy: {baseline.name}")
    for r in results[1:]:
        delta_obj = r.objective - baseline.objective
        delta_unmet = r.expected_unmet_demand - baseline.expected_unmet_demand
        print(
            f"- {r.name}: objective delta={delta_obj:+.2f}, expected unmet delta={delta_unmet:+.2f} vs baseline"
        )

    print()
    for r in results:
        print(
            f"[{r.name}] status={r.status} | contract_respected={r.prompt_contract_respected}"
        )
        if r.selected_risk_weight is not None:
            print(
                f"[{r.name}] explored {r.candidate_count} candidates; "
                f"selected risk weight={r.selected_risk_weight:.1f}"
            )


def main() -> None:
    strategy_scripts = [
        (
            "00-single-agent",
            ROOT / "00-single-agent-LP" / "run_single_agent_lp.py",
        ),
        (
            "01-sub-agent",
            ROOT / "01-sub-agent-LP" / "run_sub_agent_lp.py",
        ),
        (
            "02-team-of-agents",
            ROOT / "02-team-of-agents-LP" / "run_team_agents_lp.py",
        ),
    ]

    results: list[StrategyResult] = []
    for name, path in strategy_scripts:
        output = run_script(path)
        results.append(parse_result(name=name, script_path=path, raw_output=output))

    print_comparison(results)


if __name__ == "__main__":
    main()
