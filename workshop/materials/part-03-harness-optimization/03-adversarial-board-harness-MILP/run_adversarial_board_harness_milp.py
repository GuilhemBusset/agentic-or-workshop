"""Adversarial board harness MILP for disaster-relief network design."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from functools import cmp_to_key
from pathlib import Path
from typing import Any

import pulp

REQUIRED_CRITICAL_TOWNS = ("T03", "T04", "T07", "T12")
CONTRACT_CHECK_IDS = [
    "C01_model_class_milp",
    "C02_binary_open_decisions",
    "C03_critical_towns_exact",
    "C04_critical_service_floor",
    "C05_capacity_only_if_open",
    "C06_objective_component_consistency",
    "C07_probability_contract",
    "C08_solver_status_ok",
]

BASE_SHORTAGE_PENALTY = 25.0
CVAR_ALPHA = 0.80
CRITICAL_SERVICE_FLOOR = 0.95
STRESS_DEMAND_MULTIPLIER = 1.20
BOARD_TIE_TOLERANCE = 1e-9
NORMALIZATION_EPSILON = 1e-12
CHECK_TOLERANCE = 1e-5


@dataclass(frozen=True)
class CandidatePolicy:
    candidate_id: str
    shortage_penalty_multiplier: float
    cvar_weight: float

    @property
    def shortage_penalty(self) -> float:
        return BASE_SHORTAGE_PENALTY * self.shortage_penalty_multiplier


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _data_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data"


def load_problem_data(data_dir: Path | None = None) -> dict[str, Any]:
    root = data_dir or _data_dir()

    depots_raw = _read_csv(root / "depots.csv")
    towns_raw = _read_csv(root / "towns.csv")
    arcs_raw = _read_csv(root / "arcs.csv")
    scenarios_raw = _read_csv(root / "scenarios.csv")
    demands_raw = _read_csv(root / "scenario_demands.csv")

    depots = sorted(row["depot_id"] for row in depots_raw)
    towns = sorted(row["town_id"] for row in towns_raw)
    scenarios = sorted(row["scenario_id"] for row in scenarios_raw)

    capacity = {row["depot_id"]: float(row["capacity"]) for row in depots_raw}
    fixed_cost = {row["depot_id"]: float(row["fixed_cost"]) for row in depots_raw}
    shipping_cost = {
        (row["depot_id"], row["town_id"]): float(row["shipping_cost"])
        for row in arcs_raw
    }
    scenario_prob = {
        row["scenario_id"]: float(row["probability"]) for row in scenarios_raw
    }
    demand = {
        (row["scenario_id"], row["town_id"]): float(row["demand"])
        for row in demands_raw
    }
    critical_towns = sorted(
        row["town_id"]
        for row in towns_raw
        if row["priority_flag"].strip().lower() == "critical"
    )

    if len(depots) != 6:
        raise ValueError(f"Expected 6 depots, found {len(depots)}")
    if len(towns) != 12:
        raise ValueError(f"Expected 12 towns, found {len(towns)}")
    if len(scenarios) != 8:
        raise ValueError(f"Expected 8 scenarios, found {len(scenarios)}")

    for depot in depots:
        for town in towns:
            if (depot, town) not in shipping_cost:
                raise ValueError(f"Missing arc for ({depot}, {town})")
    for scenario in scenarios:
        for town in towns:
            if (scenario, town) not in demand:
                raise ValueError(f"Missing demand for ({scenario}, {town})")

    return {
        "depots": depots,
        "towns": towns,
        "scenarios": scenarios,
        "capacity": capacity,
        "fixed_cost": fixed_cost,
        "shipping_cost": shipping_cost,
        "scenario_prob": scenario_prob,
        "demand": demand,
        "critical_towns": critical_towns,
    }


def build_candidate_policies() -> list[CandidatePolicy]:
    return [
        CandidatePolicy(
            candidate_id="candidate_cost_lean",
            shortage_penalty_multiplier=0.85,
            cvar_weight=5.0,
        ),
        CandidatePolicy(
            candidate_id="candidate_balanced",
            shortage_penalty_multiplier=1.00,
            cvar_weight=11.0,
        ),
        CandidatePolicy(
            candidate_id="candidate_resilience",
            shortage_penalty_multiplier=1.30,
            cvar_weight=18.0,
        ),
    ]


def _float_value(value: Any) -> float:
    return 0.0 if value is None else float(value)


def _scenario_demands(
    data: dict[str, Any],
    demand_multiplier: float,
) -> dict[tuple[str, str], float]:
    return {
        (scenario, town): demand_multiplier * float(data["demand"][(scenario, town)])
        for scenario in data["scenarios"]
        for town in data["towns"]
    }


def solve_milp(
    *,
    candidate: CandidatePolicy,
    data: dict[str, Any],
    model_name: str,
    demand_multiplier: float = 1.0,
    fixed_open_values: dict[str, int] | None = None,
) -> dict[str, Any]:
    depots: list[str] = list(data["depots"])
    towns: list[str] = list(data["towns"])
    scenarios: list[str] = list(data["scenarios"])

    capacity: dict[str, float] = dict(data["capacity"])
    fixed_cost: dict[str, float] = dict(data["fixed_cost"])
    shipping_cost: dict[tuple[str, str], float] = dict(data["shipping_cost"])
    scenario_prob: dict[str, float] = dict(data["scenario_prob"])
    demand = _scenario_demands(data, demand_multiplier)

    problem = pulp.LpProblem(model_name, pulp.LpMinimize)

    open_depot = {
        depot: pulp.LpVariable(f"open_{depot}", lowBound=0, upBound=1, cat="Binary")
        for depot in depots
    }
    ship = {
        (depot, town, scenario): pulp.LpVariable(
            f"ship_{depot}_{town}_{scenario}", lowBound=0
        )
        for depot in depots
        for town in towns
        for scenario in scenarios
    }
    unmet = {
        (town, scenario): pulp.LpVariable(f"unmet_{town}_{scenario}", lowBound=0)
        for town in towns
        for scenario in scenarios
    }
    eta = pulp.LpVariable("cvar_eta", lowBound=0)
    z = {
        scenario: pulp.LpVariable(f"cvar_z_{scenario}", lowBound=0)
        for scenario in scenarios
    }

    if fixed_open_values is not None:
        for depot in depots:
            problem += open_depot[depot] == int(fixed_open_values[depot])

    for depot in depots:
        for scenario in scenarios:
            problem += (
                pulp.lpSum(ship[(depot, town, scenario)] for town in towns)
                <= capacity[depot] * open_depot[depot]
            )

    for town in towns:
        for scenario in scenarios:
            problem += (
                pulp.lpSum(ship[(depot, town, scenario)] for depot in depots)
                + unmet[(town, scenario)]
                == demand[(scenario, town)]
            )

    for town in REQUIRED_CRITICAL_TOWNS:
        for scenario in scenarios:
            problem += (
                pulp.lpSum(ship[(depot, town, scenario)] for depot in depots)
                >= CRITICAL_SERVICE_FLOOR * demand[(scenario, town)]
            )

    for scenario in scenarios:
        shortage_total = pulp.lpSum(unmet[(town, scenario)] for town in towns)
        problem += z[scenario] >= shortage_total - eta

    fixed_opening_cost_expr = pulp.lpSum(
        fixed_cost[depot] * open_depot[depot] for depot in depots
    )
    expected_transport_cost_expr = pulp.lpSum(
        scenario_prob[scenario]
        * shipping_cost[(depot, town)]
        * ship[(depot, town, scenario)]
        for depot in depots
        for town in towns
        for scenario in scenarios
    )
    expected_shortage_penalty_expr = candidate.shortage_penalty * pulp.lpSum(
        scenario_prob[scenario] * unmet[(town, scenario)]
        for town in towns
        for scenario in scenarios
    )
    cvar_shortage_risk_expr = candidate.cvar_weight * (
        eta
        + (1.0 / (1.0 - CVAR_ALPHA))
        * pulp.lpSum(scenario_prob[scenario] * z[scenario] for scenario in scenarios)
    )

    objective_expr = (
        fixed_opening_cost_expr
        + expected_transport_cost_expr
        + expected_shortage_penalty_expr
        + cvar_shortage_risk_expr
    )
    problem += objective_expr

    solver = pulp.PULP_CBC_CMD(msg=False, threads=1, options=["randomSeed 0"])
    status_code = problem.solve(solver)
    status_text = pulp.LpStatus.get(status_code, str(status_code))

    open_values = {
        depot: _float_value(var.value()) for depot, var in open_depot.items()
    }
    ship_values = {key: _float_value(var.value()) for key, var in ship.items()}
    unmet_values = {key: _float_value(var.value()) for key, var in unmet.items()}
    z_values = {scenario: _float_value(z[scenario].value()) for scenario in scenarios}
    eta_value = _float_value(eta.value())

    objective_value = _float_value(pulp.value(problem.objective))
    fixed_opening_cost = _float_value(pulp.value(fixed_opening_cost_expr))
    expected_transport_cost = _float_value(pulp.value(expected_transport_cost_expr))
    expected_shortage_penalty = _float_value(pulp.value(expected_shortage_penalty_expr))
    cvar_shortage_risk = _float_value(pulp.value(cvar_shortage_risk_expr))

    return {
        "model_name": model_name,
        "status_code": int(status_code),
        "status": status_text,
        "is_milp": bool(problem.isMIP()),
        "binary_variable_count": len(depots),
        "objective_value": objective_value,
        "objective_components": {
            "fixed_opening_cost": fixed_opening_cost,
            "expected_transport_cost": expected_transport_cost,
            "expected_shortage_penalty": expected_shortage_penalty,
            "cvar_shortage_risk": cvar_shortage_risk,
            "total_objective": objective_value,
        },
        "open_values": open_values,
        "ship_values": ship_values,
        "unmet_values": unmet_values,
        "z_values": z_values,
        "eta_value": eta_value,
        "demand": demand,
        "demand_multiplier": demand_multiplier,
    }


def _solution_unmet_metrics(solution: dict[str, Any]) -> dict[str, float]:
    unmet_values: dict[tuple[str, str], float] = solution["unmet_values"]
    total_unmet = sum(unmet_values.values())
    critical_unmet = sum(
        unmet_values[(town, scenario)]
        for town in REQUIRED_CRITICAL_TOWNS
        for scenario in sorted({sc for (_, sc) in unmet_values})
    )
    return {
        "total_unmet": float(total_unmet),
        "critical_unmet": float(critical_unmet),
    }


def _objective_consistency_check(
    *,
    candidate: CandidatePolicy,
    data: dict[str, Any],
    solution: dict[str, Any],
) -> tuple[bool, str]:
    depots: list[str] = list(data["depots"])
    towns: list[str] = list(data["towns"])
    scenarios: list[str] = list(data["scenarios"])

    fixed_cost: dict[str, float] = dict(data["fixed_cost"])
    shipping_cost: dict[tuple[str, str], float] = dict(data["shipping_cost"])
    scenario_prob: dict[str, float] = dict(data["scenario_prob"])

    open_values: dict[str, float] = dict(solution["open_values"])
    ship_values: dict[tuple[str, str, str], float] = dict(solution["ship_values"])
    unmet_values: dict[tuple[str, str], float] = dict(solution["unmet_values"])
    z_values: dict[str, float] = dict(solution["z_values"])
    eta_value = float(solution["eta_value"])

    calc_fixed = sum(fixed_cost[depot] * open_values[depot] for depot in depots)
    calc_transport = sum(
        scenario_prob[scenario]
        * shipping_cost[(depot, town)]
        * ship_values[(depot, town, scenario)]
        for depot in depots
        for town in towns
        for scenario in scenarios
    )
    calc_shortage = candidate.shortage_penalty * sum(
        scenario_prob[scenario] * unmet_values[(town, scenario)]
        for town in towns
        for scenario in scenarios
    )
    calc_cvar = candidate.cvar_weight * (
        eta_value
        + (1.0 / (1.0 - CVAR_ALPHA))
        * sum(scenario_prob[scenario] * z_values[scenario] for scenario in scenarios)
    )
    calc_total = calc_fixed + calc_transport + calc_shortage + calc_cvar

    model_objective = float(solution["objective_value"])
    if abs(calc_total - model_objective) > CHECK_TOLERANCE:
        return (
            False,
            "Independent objective rebuild mismatch "
            f"(calc={calc_total:.8f}, model={model_objective:.8f})",
        )

    components: dict[str, float] = dict(solution["objective_components"])
    component_sum = (
        components["fixed_opening_cost"]
        + components["expected_transport_cost"]
        + components["expected_shortage_penalty"]
        + components["cvar_shortage_risk"]
    )
    if abs(component_sum - model_objective) > CHECK_TOLERANCE:
        return (
            False,
            "Reported objective component sum mismatch "
            f"(sum={component_sum:.8f}, model={model_objective:.8f})",
        )

    return True, "Objective components and independent rebuild are consistent"


def run_contract_checks(
    *,
    candidate: CandidatePolicy,
    data: dict[str, Any],
    solution: dict[str, Any],
) -> list[dict[str, Any]]:
    depots: list[str] = list(data["depots"])
    towns: list[str] = list(data["towns"])
    scenarios: list[str] = list(data["scenarios"])
    capacity: dict[str, float] = dict(data["capacity"])
    scenario_prob: dict[str, float] = dict(data["scenario_prob"])
    critical_towns_data = set(data["critical_towns"])

    open_values: dict[str, float] = dict(solution["open_values"])
    ship_values: dict[tuple[str, str, str], float] = dict(solution["ship_values"])
    unmet_values: dict[tuple[str, str], float] = dict(solution["unmet_values"])
    demand: dict[tuple[str, str], float] = dict(solution["demand"])

    checks: list[dict[str, Any]] = []

    checks.append(
        {
            "id": "C01_model_class_milp",
            "passed": bool(
                solution["is_milp"] and solution["binary_variable_count"] >= 1
            ),
            "details": "Model is built as MILP with binary depot-open variables",
        }
    )

    open_binary_ok = all(
        min(abs(value), abs(value - 1.0)) <= CHECK_TOLERANCE
        for value in open_values.values()
    )
    checks.append(
        {
            "id": "C02_binary_open_decisions",
            "passed": open_binary_ok,
            "details": "All depot-open decisions are binary at solution tolerance",
        }
    )

    exact_critical_ok = critical_towns_data == set(REQUIRED_CRITICAL_TOWNS)
    checks.append(
        {
            "id": "C03_critical_towns_exact",
            "passed": exact_critical_ok,
            "details": "Critical towns exactly match {T03, T04, T07, T12}",
        }
    )

    critical_floor_ok = True
    for town in REQUIRED_CRITICAL_TOWNS:
        for scenario in scenarios:
            served = demand[(scenario, town)] - unmet_values[(town, scenario)]
            if (
                served + CHECK_TOLERANCE
                < CRITICAL_SERVICE_FLOOR * demand[(scenario, town)]
            ):
                critical_floor_ok = False
                break
        if not critical_floor_ok:
            break
    checks.append(
        {
            "id": "C04_critical_service_floor",
            "passed": critical_floor_ok,
            "details": "Critical towns receive at least 95% service in every scenario",
        }
    )

    capacity_ok = True
    for depot in depots:
        for scenario in scenarios:
            shipped = sum(ship_values[(depot, town, scenario)] for town in towns)
            if shipped - CHECK_TOLERANCE > capacity[depot] * open_values[depot]:
                capacity_ok = False
                break
        if not capacity_ok:
            break
    checks.append(
        {
            "id": "C05_capacity_only_if_open",
            "passed": capacity_ok,
            "details": "Depot capacity can be used only when depot is open",
        }
    )

    objective_ok, objective_message = _objective_consistency_check(
        candidate=candidate,
        data=data,
        solution=solution,
    )
    checks.append(
        {
            "id": "C06_objective_component_consistency",
            "passed": objective_ok,
            "details": objective_message,
        }
    )

    probability_sum = sum(scenario_prob.values())
    probability_ok = abs(probability_sum - 1.0) <= CHECK_TOLERANCE and all(
        scenario_prob[scenario] > 0.0 for scenario in scenarios
    )
    checks.append(
        {
            "id": "C07_probability_contract",
            "passed": probability_ok,
            "details": f"Scenario probabilities are valid; sum={probability_sum:.8f}",
        }
    )

    solver_ok = solution["status"].lower() == "optimal"
    checks.append(
        {
            "id": "C08_solver_status_ok",
            "passed": solver_ok,
            "details": f"Solver status is '{solution['status']}'",
        }
    )

    id_sequence = [item["id"] for item in checks]
    if id_sequence != CONTRACT_CHECK_IDS:
        raise RuntimeError(f"Contract check ordering mismatch: {id_sequence}")

    return checks


def summarize_solution(solution: dict[str, Any]) -> dict[str, Any]:
    open_values: dict[str, float] = dict(solution["open_values"])
    open_depots = sorted(depot for depot, value in open_values.items() if value >= 0.5)

    return {
        "status": solution["status"],
        "objective": float(solution["objective_value"]),
        "objective_components": {
            key: float(value)
            for key, value in dict(solution["objective_components"]).items()
        },
        "open_depot_count": len(open_depots),
        "open_depots": open_depots,
        "unmet_metrics": _solution_unmet_metrics(solution),
        "demand_multiplier": float(solution["demand_multiplier"]),
    }


def _normalize(values: dict[str, float]) -> tuple[dict[str, float], dict[str, float]]:
    minimum = min(values.values())
    maximum = max(values.values())

    if abs(maximum - minimum) <= NORMALIZATION_EPSILON:
        normalized = {candidate_id: 0.0 for candidate_id in values}
    else:
        normalized = {
            candidate_id: (value - minimum) / (maximum - minimum)
            for candidate_id, value in values.items()
        }

    return normalized, {"min": float(minimum), "max": float(maximum)}


def compute_board_scores(eligible_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    weights = {
        "normalized_baseline_objective": 0.40,
        "normalized_stressed_total_unmet": 0.35,
        "normalized_stressed_critical_unmet": 0.20,
        "normalized_open_depot_count": 0.05,
    }

    baseline_objective_raw = {
        candidate["candidate_id"]: float(candidate["baseline_summary"]["objective"])
        for candidate in eligible_candidates
    }
    stressed_total_unmet_raw = {
        candidate["candidate_id"]: float(
            candidate["stress_summary"]["unmet_metrics"]["total_unmet"]
        )
        for candidate in eligible_candidates
    }
    stressed_critical_unmet_raw = {
        candidate["candidate_id"]: float(
            candidate["stress_summary"]["unmet_metrics"]["critical_unmet"]
        )
        for candidate in eligible_candidates
    }
    open_depot_count_raw = {
        candidate["candidate_id"]: float(
            candidate["baseline_summary"]["open_depot_count"]
        )
        for candidate in eligible_candidates
    }

    baseline_norm, baseline_bounds = _normalize(baseline_objective_raw)
    total_unmet_norm, total_unmet_bounds = _normalize(stressed_total_unmet_raw)
    critical_unmet_norm, critical_unmet_bounds = _normalize(stressed_critical_unmet_raw)
    open_count_norm, open_count_bounds = _normalize(open_depot_count_raw)

    candidate_scores: dict[str, dict[str, float]] = {}
    for candidate_id in sorted(baseline_objective_raw):
        components = {
            "normalized_baseline_objective": baseline_norm[candidate_id],
            "normalized_stressed_total_unmet": total_unmet_norm[candidate_id],
            "normalized_stressed_critical_unmet": critical_unmet_norm[candidate_id],
            "normalized_open_depot_count": open_count_norm[candidate_id],
        }
        board_score = (
            weights["normalized_baseline_objective"]
            * components["normalized_baseline_objective"]
            + weights["normalized_stressed_total_unmet"]
            * components["normalized_stressed_total_unmet"]
            + weights["normalized_stressed_critical_unmet"]
            * components["normalized_stressed_critical_unmet"]
            + weights["normalized_open_depot_count"]
            * components["normalized_open_depot_count"]
        )
        candidate_scores[candidate_id] = {
            **components,
            "board_score": float(board_score),
            "raw_baseline_objective": float(baseline_objective_raw[candidate_id]),
            "raw_stressed_total_unmet": float(stressed_total_unmet_raw[candidate_id]),
            "raw_stressed_critical_unmet": float(
                stressed_critical_unmet_raw[candidate_id]
            ),
            "raw_open_depot_count": float(open_depot_count_raw[candidate_id]),
        }

    return {
        "weights": weights,
        "normalization": {
            "method": "min_max",
            "formula": "normalized=(x-min)/(max-min); if max-min<=epsilon then normalized=0.0",
            "epsilon": NORMALIZATION_EPSILON,
            "lower_is_better": True,
            "metric_bounds": {
                "baseline_objective": baseline_bounds,
                "stressed_total_unmet": total_unmet_bounds,
                "stressed_critical_unmet": critical_unmet_bounds,
                "open_depot_count": open_count_bounds,
            },
        },
        "candidate_scores": candidate_scores,
    }


def select_winner(
    eligible_candidates: list[dict[str, Any]],
    board_scoring: dict[str, Any],
) -> dict[str, Any]:
    score_map: dict[str, dict[str, float]] = dict(board_scoring["candidate_scores"])

    ranking_pool: list[dict[str, Any]] = []
    for candidate in eligible_candidates:
        candidate_id = candidate["candidate_id"]
        score_info = score_map[candidate_id]
        ranking_pool.append(
            {
                "candidate_id": candidate_id,
                "board_score": float(score_info["board_score"]),
                "stressed_critical_unmet": float(
                    candidate["stress_summary"]["unmet_metrics"]["critical_unmet"]
                ),
                "stressed_total_unmet": float(
                    candidate["stress_summary"]["unmet_metrics"]["total_unmet"]
                ),
                "baseline_objective": float(candidate["baseline_summary"]["objective"]),
                "open_depot_count": int(
                    candidate["baseline_summary"]["open_depot_count"]
                ),
            }
        )

    def _compare(left: dict[str, Any], right: dict[str, Any]) -> int:
        score_delta = left["board_score"] - right["board_score"]
        if abs(score_delta) > BOARD_TIE_TOLERANCE:
            return -1 if score_delta < 0 else 1

        critical_delta = (
            left["stressed_critical_unmet"] - right["stressed_critical_unmet"]
        )
        if abs(critical_delta) > BOARD_TIE_TOLERANCE:
            return -1 if critical_delta < 0 else 1

        total_delta = left["stressed_total_unmet"] - right["stressed_total_unmet"]
        if abs(total_delta) > BOARD_TIE_TOLERANCE:
            return -1 if total_delta < 0 else 1

        if left["candidate_id"] < right["candidate_id"]:
            return -1
        if left["candidate_id"] > right["candidate_id"]:
            return 1
        return 0

    ranked = sorted(ranking_pool, key=cmp_to_key(_compare))
    winner = ranked[0]

    return {
        "tie_tolerance": BOARD_TIE_TOLERANCE,
        "tie_break_order": [
            "lower stressed critical unmet",
            "lower stressed total unmet",
            "lexicographic candidate_id",
        ],
        "eligible_ranking": ranked,
        "winner_candidate_id": winner["candidate_id"],
        "winner_board_score": winner["board_score"],
    }


def _evaluate_candidate(
    *,
    candidate: CandidatePolicy,
    data: dict[str, Any],
) -> dict[str, Any]:
    baseline_solution = solve_milp(
        candidate=candidate,
        data=data,
        model_name=f"baseline_{candidate.candidate_id}",
        demand_multiplier=1.0,
        fixed_open_values=None,
    )
    contract_checks = run_contract_checks(
        candidate=candidate,
        data=data,
        solution=baseline_solution,
    )
    contract_eligible = all(check["passed"] for check in contract_checks)

    baseline_summary = summarize_solution(baseline_solution)

    frozen_open = {
        depot: int(round(value))
        for depot, value in dict(baseline_solution["open_values"]).items()
    }

    stress_solution = solve_milp(
        candidate=candidate,
        data=data,
        model_name=f"stress_{candidate.candidate_id}",
        demand_multiplier=STRESS_DEMAND_MULTIPLIER,
        fixed_open_values=frozen_open,
    )
    stress_summary = summarize_solution(stress_solution)
    stress_summary["frozen_open_design"] = frozen_open

    return {
        "candidate_id": candidate.candidate_id,
        "parameters": {
            "shortage_penalty_multiplier": candidate.shortage_penalty_multiplier,
            "effective_shortage_penalty": candidate.shortage_penalty,
            "cvar_alpha": CVAR_ALPHA,
            "cvar_weight": candidate.cvar_weight,
        },
        "contract_checks": contract_checks,
        "contract_eligible_for_board": contract_eligible,
        "baseline_summary": baseline_summary,
        "stress_summary": stress_summary,
        "board_score_components": None,
        "board_score": None,
        "selected_as_winner": False,
    }


def run_adversarial_board_harness(
    *,
    write_report: bool = True,
    print_console_summary: bool = True,
) -> dict[str, Any]:
    data = load_problem_data()
    candidates = [
        _evaluate_candidate(candidate=policy, data=data)
        for policy in build_candidate_policies()
    ]

    eligible_candidates = [
        candidate
        for candidate in candidates
        if candidate["contract_eligible_for_board"]
    ]
    if not eligible_candidates:
        diagnostics = {
            candidate["candidate_id"]: [
                check["id"]
                for check in candidate["contract_checks"]
                if not check["passed"]
            ]
            for candidate in candidates
        }
        raise RuntimeError(
            "Zero contract-eligible candidates; board selection aborted. "
            f"Diagnostics: {diagnostics}"
        )

    board_scoring = compute_board_scores(eligible_candidates)
    score_map: dict[str, dict[str, float]] = dict(board_scoring["candidate_scores"])

    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        if candidate_id in score_map:
            score_info = score_map[candidate_id]
            candidate["board_score_components"] = {
                "normalized_baseline_objective": score_info[
                    "normalized_baseline_objective"
                ],
                "normalized_stressed_total_unmet": score_info[
                    "normalized_stressed_total_unmet"
                ],
                "normalized_stressed_critical_unmet": score_info[
                    "normalized_stressed_critical_unmet"
                ],
                "normalized_open_depot_count": score_info[
                    "normalized_open_depot_count"
                ],
            }
            candidate["board_score"] = float(score_info["board_score"])

    board_decision = select_winner(eligible_candidates, board_scoring)
    winner_id = board_decision["winner_candidate_id"]

    for candidate in candidates:
        candidate["selected_as_winner"] = candidate["candidate_id"] == winner_id

    report = {
        "harness": "adversarial_board_harness_milp",
        "problem_source": (
            "workshop/materials/"
            "part-01-explorer-paradigm/00-problem/exercise-statement.md"
        ),
        "data_inputs": [
            "depots.csv",
            "towns.csv",
            "arcs.csv",
            "scenarios.csv",
            "scenario_demands.csv",
        ],
        "constants": {
            "required_critical_towns": list(REQUIRED_CRITICAL_TOWNS),
            "critical_service_floor": CRITICAL_SERVICE_FLOOR,
            "stress_demand_multiplier": STRESS_DEMAND_MULTIPLIER,
            "base_shortage_penalty": BASE_SHORTAGE_PENALTY,
            "board_tie_tolerance": BOARD_TIE_TOLERANCE,
            "contract_check_ids": CONTRACT_CHECK_IDS,
        },
        "board_scoring": board_scoring,
        "board_decision": board_decision,
        "winner": {
            "candidate_id": winner_id,
            "board_score": float(board_decision["winner_board_score"]),
            "selection_rule": "lowest board_score with deterministic tie-break",
        },
        "candidates": candidates,
    }

    report_path = Path(__file__).resolve().parent / "adversarial_board_report.json"
    if write_report:
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
        )

    if print_console_summary:
        print("Adversarial Board Harness (MILP)")
        print(
            f"Winner: {winner_id} (board_score={board_decision['winner_board_score']:.8f})"
        )
        print("Eligible ranking:")
        for rank, row in enumerate(board_decision["eligible_ranking"], start=1):
            print(
                f"  {rank}. {row['candidate_id']} | "
                f"score={row['board_score']:.8f} | "
                f"stress_critical_unmet={row['stressed_critical_unmet']:.6f} | "
                f"stress_total_unmet={row['stressed_total_unmet']:.6f}"
            )

    return report


if __name__ == "__main__":
    run_adversarial_board_harness(write_report=True, print_console_summary=True)
