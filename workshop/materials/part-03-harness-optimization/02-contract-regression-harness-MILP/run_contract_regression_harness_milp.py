from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pulp

# Constants are intentionally explicit for deterministic behavior.
CRITICAL_TOWNS = ("T03", "T04", "T07", "T12")
CRITICAL_SERVICE_MIN = 0.95
SHORTAGE_PENALTY = 120.0
CVAR_ALPHA = 0.90
CVAR_RISK_WEIGHT = 10.0
EPS = 1e-6

CONTRACT_IDS = (
    "C01_model_class_milp",
    "C02_critical_towns_exact",
    "C03_critical_service_floor",
    "C04_capacity_only_if_open",
    "C05_objective_component_consistency",
    "C06_probability_contract",
    "C07_solver_status_ok",
)

REGRESSION_IDS = (
    "R01_baseline_contract_checked_solve",
    "R02_all_open_baseline_comparison",
    "R03_fixed_cost_bump_perturbation",
    "R04_stressed_demand_fixed_design_recourse",
)


@dataclass(frozen=True)
class Depot:
    depot_id: str
    capacity: float
    fixed_cost: float


@dataclass(frozen=True)
class Town:
    town_id: str
    priority_flag: str


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    probability: float


@dataclass(frozen=True)
class InstanceData:
    depots: tuple[Depot, ...]
    towns: tuple[Town, ...]
    scenarios: tuple[Scenario, ...]
    arc_cost: dict[tuple[str, str], float]
    demands: dict[tuple[str, str], float]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def data_dir() -> Path:
    return repo_root() / "workshop" / "data"


def report_path() -> Path:
    return Path(__file__).resolve().parent / "contract_regression_report.json"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_instance() -> InstanceData:
    source = data_dir()
    depots_rows = _read_csv(source / "depots.csv")
    towns_rows = _read_csv(source / "towns.csv")
    arcs_rows = _read_csv(source / "arcs.csv")
    scenarios_rows = _read_csv(source / "scenarios.csv")
    demand_rows = _read_csv(source / "scenario_demands.csv")

    depots = tuple(
        sorted(
            (
                Depot(
                    depot_id=row["depot_id"],
                    capacity=float(row["capacity"]),
                    fixed_cost=float(row["fixed_cost"]),
                )
                for row in depots_rows
            ),
            key=lambda item: item.depot_id,
        )
    )
    towns = tuple(
        sorted(
            (
                Town(town_id=row["town_id"], priority_flag=row["priority_flag"])
                for row in towns_rows
            ),
            key=lambda item: item.town_id,
        )
    )
    scenarios = tuple(
        sorted(
            (
                Scenario(
                    scenario_id=row["scenario_id"],
                    probability=float(row["probability"]),
                )
                for row in scenarios_rows
            ),
            key=lambda item: item.scenario_id,
        )
    )

    arc_cost: dict[tuple[str, str], float] = {}
    for row in arcs_rows:
        key = (row["depot_id"], row["town_id"])
        arc_cost[key] = float(row["shipping_cost"])

    demands: dict[tuple[str, str], float] = {}
    for row in demand_rows:
        key = (row["scenario_id"], row["town_id"])
        demands[key] = float(row["demand"])

    validate_instance(depots, towns, scenarios, arc_cost, demands)
    return InstanceData(
        depots=depots,
        towns=towns,
        scenarios=scenarios,
        arc_cost=arc_cost,
        demands=demands,
    )


def validate_instance(
    depots: tuple[Depot, ...],
    towns: tuple[Town, ...],
    scenarios: tuple[Scenario, ...],
    arc_cost: dict[tuple[str, str], float],
    demands: dict[tuple[str, str], float],
) -> None:
    depot_ids = tuple(d.depot_id for d in depots)
    town_ids = tuple(t.town_id for t in towns)
    scenario_ids = tuple(s.scenario_id for s in scenarios)

    if not depots or not towns or not scenarios:
        raise ValueError("Input CSVs produced an empty index set.")

    for depot in depots:
        if depot.capacity < 0 or depot.fixed_cost < 0:
            raise ValueError(f"Invalid depot data for {depot.depot_id}.")

    for scenario in scenarios:
        if scenario.probability <= 0:
            raise ValueError(
                f"Non-positive probability in scenario {scenario.scenario_id}."
            )

    for depot_id in depot_ids:
        for town_id in town_ids:
            if (depot_id, town_id) not in arc_cost:
                raise ValueError(f"Missing arc cost for {depot_id}->{town_id}.")

    for scenario_id in scenario_ids:
        for town_id in town_ids:
            key = (scenario_id, town_id)
            if key not in demands:
                raise ValueError(
                    f"Missing scenario demand for {scenario_id}, {town_id}."
                )
            if demands[key] < 0:
                raise ValueError(f"Negative demand for {scenario_id}, {town_id}.")


@dataclass
class SolveResult:
    status: str
    objective_value: float
    reported_total_objective: float
    components: dict[str, float]
    open_depots: dict[str, int]
    shipments: dict[tuple[str, str, str], float]
    unmet: dict[tuple[str, str], float]
    shortage_by_scenario: dict[str, float]
    eta: float
    excess: dict[str, float]
    model_class_is_milp: bool


def solve_model(
    data: InstanceData,
    *,
    fixed_open: dict[str, int] | None = None,
    forced_all_open: bool = False,
    fixed_cost_multiplier: float = 1.0,
    demand_multiplier: float = 1.0,
    objective_corruption: float = 0.0,
) -> SolveResult:
    depots = tuple(d.depot_id for d in data.depots)
    towns = tuple(t.town_id for t in data.towns)
    scenarios = tuple(s.scenario_id for s in data.scenarios)
    probabilities = {s.scenario_id: s.probability for s in data.scenarios}
    capacities = {d.depot_id: d.capacity for d in data.depots}
    fixed_costs = {
        d.depot_id: d.fixed_cost * fixed_cost_multiplier for d in data.depots
    }

    effective_demands = {
        (scenario_id, town_id): data.demands[(scenario_id, town_id)] * demand_multiplier
        for scenario_id in scenarios
        for town_id in towns
    }

    model = pulp.LpProblem("ContractRegressionMILP", pulp.LpMinimize)

    if fixed_open is not None:
        open_vars = {depot_id: int(fixed_open[depot_id]) for depot_id in depots}
        model_class_is_milp = False
    else:
        open_vars = {
            depot_id: pulp.LpVariable(
                f"open_{depot_id}", lowBound=0, upBound=1, cat=pulp.LpBinary
            )
            for depot_id in depots
        }
        model_class_is_milp = True

    ship = {
        (scenario_id, depot_id, town_id): pulp.LpVariable(
            f"ship_{scenario_id}_{depot_id}_{town_id}",
            lowBound=0,
            cat=pulp.LpContinuous,
        )
        for scenario_id in scenarios
        for depot_id in depots
        for town_id in towns
    }

    unmet = {
        (scenario_id, town_id): pulp.LpVariable(
            f"unmet_{scenario_id}_{town_id}",
            lowBound=0,
            cat=pulp.LpContinuous,
        )
        for scenario_id in scenarios
        for town_id in towns
    }

    shortage = {
        scenario_id: pulp.LpVariable(
            f"shortage_{scenario_id}", lowBound=0, cat=pulp.LpContinuous
        )
        for scenario_id in scenarios
    }

    eta = pulp.LpVariable("eta", lowBound=0, cat=pulp.LpContinuous)
    excess = {
        scenario_id: pulp.LpVariable(
            f"excess_{scenario_id}", lowBound=0, cat=pulp.LpContinuous
        )
        for scenario_id in scenarios
    }

    for scenario_id in scenarios:
        for town_id in towns:
            model += (
                pulp.lpSum(
                    ship[(scenario_id, depot_id, town_id)] for depot_id in depots
                )
                + unmet[(scenario_id, town_id)]
                == effective_demands[(scenario_id, town_id)],
                f"demand_balance_{scenario_id}_{town_id}",
            )

            if town_id in CRITICAL_TOWNS:
                model += (
                    pulp.lpSum(
                        ship[(scenario_id, depot_id, town_id)] for depot_id in depots
                    )
                    >= CRITICAL_SERVICE_MIN * effective_demands[(scenario_id, town_id)],
                    f"critical_service_{scenario_id}_{town_id}",
                )

    for scenario_id in scenarios:
        for depot_id in depots:
            if forced_all_open:
                open_factor: float | pulp.LpVariable = 1.0
            elif fixed_open is not None:
                open_factor = float(open_vars[depot_id])
            else:
                open_factor = open_vars[depot_id]

            model += (
                pulp.lpSum(ship[(scenario_id, depot_id, town_id)] for town_id in towns)
                <= capacities[depot_id] * open_factor,
                f"capacity_if_open_{scenario_id}_{depot_id}",
            )

    for scenario_id in scenarios:
        model += (
            shortage[scenario_id]
            == pulp.lpSum(unmet[(scenario_id, town_id)] for town_id in towns),
            f"shortage_def_{scenario_id}",
        )
        model += (
            excess[scenario_id] >= shortage[scenario_id] - eta,
            f"cvar_excess_{scenario_id}",
        )

    fixed_opening_expr = (
        pulp.lpSum(fixed_costs[depot_id] * open_vars[depot_id] for depot_id in depots)
        if fixed_open is None and not forced_all_open
        else pulp.lpSum(
            fixed_costs[depot_id]
            * (1.0 if forced_all_open else float(open_vars[depot_id]))
            for depot_id in depots
        )
    )

    expected_transport_expr = pulp.lpSum(
        probabilities[scenario_id]
        * data.arc_cost[(depot_id, town_id)]
        * ship[(scenario_id, depot_id, town_id)]
        for scenario_id in scenarios
        for depot_id in depots
        for town_id in towns
    )

    expected_shortage_expr = SHORTAGE_PENALTY * pulp.lpSum(
        probabilities[scenario_id] * unmet[(scenario_id, town_id)]
        for scenario_id in scenarios
        for town_id in towns
    )

    cvar_expr = CVAR_RISK_WEIGHT * (
        eta
        + (1.0 / (1.0 - CVAR_ALPHA))
        * pulp.lpSum(
            probabilities[scenario_id] * excess[scenario_id]
            for scenario_id in scenarios
        )
    )

    model += (
        fixed_opening_expr
        + expected_transport_expr
        + expected_shortage_expr
        + cvar_expr
    )

    solver = pulp.PULP_CBC_CMD(msg=False, threads=1)
    model.solve(solver)

    status = pulp.LpStatus[model.status]

    open_values: dict[str, int] = {}
    for depot_id in depots:
        if forced_all_open:
            open_values[depot_id] = 1
        elif fixed_open is not None:
            open_values[depot_id] = int(open_vars[depot_id])
        else:
            open_values[depot_id] = int(round(float(pulp.value(open_vars[depot_id]))))

    shipment_values = {
        key: float(pulp.value(var) or 0.0)
        for key, var in sorted(ship.items(), key=lambda item: item[0])
    }
    unmet_values = {
        key: float(pulp.value(var) or 0.0)
        for key, var in sorted(unmet.items(), key=lambda item: item[0])
    }
    shortage_values = {
        scenario_id: float(pulp.value(shortage[scenario_id]) or 0.0)
        for scenario_id in scenarios
    }
    excess_values = {
        scenario_id: float(pulp.value(excess[scenario_id]) or 0.0)
        for scenario_id in scenarios
    }
    eta_value = float(pulp.value(eta) or 0.0)

    fixed_opening_value = sum(fixed_costs[d] * open_values[d] for d in depots)
    expected_transport_value = sum(
        probabilities[s] * data.arc_cost[(d, t)] * shipment_values[(s, d, t)]
        for s in scenarios
        for d in depots
        for t in towns
    )
    expected_shortage_value = SHORTAGE_PENALTY * sum(
        probabilities[s] * unmet_values[(s, t)] for s in scenarios for t in towns
    )
    cvar_value = CVAR_RISK_WEIGHT * (
        eta_value
        + (1.0 / (1.0 - CVAR_ALPHA))
        * sum(probabilities[s] * excess_values[s] for s in scenarios)
    )

    objective_value = float(pulp.value(model.objective) or 0.0)
    reported_total_objective = objective_value + objective_corruption

    components = {
        "fixed_opening_cost": fixed_opening_value,
        "expected_transport_cost": expected_transport_value,
        "expected_shortage_penalty": expected_shortage_value,
        "cvar_shortage_risk": cvar_value,
        "component_total": fixed_opening_value
        + expected_transport_value
        + expected_shortage_value
        + cvar_value,
    }

    return SolveResult(
        status=status,
        objective_value=objective_value,
        reported_total_objective=reported_total_objective,
        components=components,
        open_depots=open_values,
        shipments=shipment_values,
        unmet=unmet_values,
        shortage_by_scenario=shortage_values,
        eta=eta_value,
        excess=excess_values,
        model_class_is_milp=model_class_is_milp,
    )


def _check_entry(
    check_id: str, passed: bool, details: dict[str, Any]
) -> dict[str, Any]:
    return {
        "id": check_id,
        "passed": bool(passed),
        "details": details,
    }


def contract_check_model_class_milp(result: SolveResult) -> dict[str, Any]:
    return _check_entry(
        "C01_model_class_milp",
        result.model_class_is_milp,
        {"model_class_is_milp": result.model_class_is_milp},
    )


def contract_check_critical_towns_exact(data: InstanceData) -> dict[str, Any]:
    critical_from_data = tuple(
        sorted(
            t.town_id
            for t in data.towns
            if t.priority_flag.strip().lower() == "critical"
        )
    )
    expected = tuple(sorted(CRITICAL_TOWNS))
    passed = critical_from_data == expected
    return _check_entry(
        "C02_critical_towns_exact",
        passed,
        {
            "critical_from_data": list(critical_from_data),
            "expected_critical_towns": list(expected),
        },
    )


def contract_check_critical_service_floor(
    data: InstanceData, result: SolveResult, demand_multiplier: float = 1.0
) -> dict[str, Any]:
    depots = tuple(d.depot_id for d in data.depots)
    scenarios = tuple(s.scenario_id for s in data.scenarios)
    worst_margin = float("inf")
    violations: list[dict[str, Any]] = []

    for scenario_id in scenarios:
        for town_id in sorted(CRITICAL_TOWNS):
            demand = data.demands[(scenario_id, town_id)] * demand_multiplier
            served = sum(
                result.shipments[(scenario_id, depot_id, town_id)]
                for depot_id in depots
            )
            ratio = 1.0 if demand <= EPS else served / demand
            margin = ratio - CRITICAL_SERVICE_MIN
            worst_margin = min(worst_margin, margin)
            if margin < -1e-5:
                violations.append(
                    {
                        "scenario_id": scenario_id,
                        "town_id": town_id,
                        "served_ratio": ratio,
                    }
                )

    return _check_entry(
        "C03_critical_service_floor",
        not violations,
        {
            "worst_margin": 0.0 if worst_margin == float("inf") else worst_margin,
            "violation_count": len(violations),
        },
    )


def contract_check_capacity_only_if_open(
    data: InstanceData, result: SolveResult
) -> dict[str, Any]:
    depots = tuple(d.depot_id for d in data.depots)
    towns = tuple(t.town_id for t in data.towns)
    scenarios = tuple(s.scenario_id for s in data.scenarios)
    capacities = {d.depot_id: d.capacity for d in data.depots}

    max_violation = 0.0
    violations = 0
    for scenario_id in scenarios:
        for depot_id in depots:
            shipped = sum(
                result.shipments[(scenario_id, depot_id, town_id)] for town_id in towns
            )
            rhs = capacities[depot_id] * result.open_depots[depot_id]
            violation = shipped - rhs
            if violation > max_violation:
                max_violation = violation
            if violation > 1e-5:
                violations += 1

    return _check_entry(
        "C04_capacity_only_if_open",
        violations == 0,
        {
            "max_violation": max_violation,
            "violation_count": violations,
        },
    )


def contract_check_objective_component_consistency(
    result: SolveResult,
) -> dict[str, Any]:
    component_total = result.components["component_total"]
    raw_delta = abs(result.objective_value - component_total)
    reported_delta = abs(result.reported_total_objective - component_total)
    passed = raw_delta <= 1e-5 and reported_delta <= 1e-5
    return _check_entry(
        "C05_objective_component_consistency",
        passed,
        {
            "objective_value": result.objective_value,
            "reported_total_objective": result.reported_total_objective,
            "component_total": component_total,
            "abs_delta_objective_vs_components": raw_delta,
            "abs_delta_reported_vs_components": reported_delta,
        },
    )


def contract_check_probability_contract(data: InstanceData) -> dict[str, Any]:
    probabilities = [s.probability for s in data.scenarios]
    total_probability = sum(probabilities)
    min_probability = min(probabilities)
    passed = abs(total_probability - 1.0) <= 1e-9 and min_probability > 0.0
    return _check_entry(
        "C06_probability_contract",
        passed,
        {
            "total_probability": total_probability,
            "min_probability": min_probability,
            "scenario_count": len(data.scenarios),
        },
    )


def contract_check_solver_status_ok(result: SolveResult) -> dict[str, Any]:
    passed = result.status == "Optimal"
    return _check_entry(
        "C07_solver_status_ok",
        passed,
        {"solver_status": result.status},
    )


def evaluate_contracts(
    data: InstanceData,
    result: SolveResult,
    *,
    demand_multiplier: float = 1.0,
) -> list[dict[str, Any]]:
    checks = [
        contract_check_model_class_milp(result),
        contract_check_critical_towns_exact(data),
        contract_check_critical_service_floor(
            data, result, demand_multiplier=demand_multiplier
        ),
        contract_check_capacity_only_if_open(data, result),
        contract_check_objective_component_consistency(result),
        contract_check_probability_contract(data),
        contract_check_solver_status_ok(result),
    ]
    return checks


def _all_passed(checks: list[dict[str, Any]]) -> bool:
    return all(bool(item["passed"]) for item in checks)


def _metrics_summary(data: InstanceData, result: SolveResult) -> dict[str, Any]:
    scenarios = tuple(s.scenario_id for s in data.scenarios)
    towns = tuple(t.town_id for t in data.towns)
    probabilities = {s.scenario_id: s.probability for s in data.scenarios}

    expected_unmet = sum(
        probabilities[scenario_id] * result.unmet[(scenario_id, town_id)]
        for scenario_id in scenarios
        for town_id in towns
    )
    total_unmet = sum(result.unmet.values())

    return {
        "solver_status": result.status,
        "objective": result.reported_total_objective,
        "open_depots": {k: result.open_depots[k] for k in sorted(result.open_depots)},
        "components": {
            "fixed_opening_cost": result.components["fixed_opening_cost"],
            "expected_transport_cost": result.components["expected_transport_cost"],
            "expected_shortage_penalty": result.components["expected_shortage_penalty"],
            "cvar_shortage_risk": result.components["cvar_shortage_risk"],
            "component_total": result.components["component_total"],
        },
        "expected_unmet_demand": expected_unmet,
        "total_unmet_demand": total_unmet,
        "eta": result.eta,
        "shortage_by_scenario": {
            scenario_id: result.shortage_by_scenario[scenario_id]
            for scenario_id in sorted(scenarios)
        },
    }


def run_harness(
    *,
    output_path: Path | None = None,
    write_report: bool = True,
    objective_corruption: float = 0.0,
) -> dict[str, Any]:
    data = load_instance()

    baseline = solve_model(data, objective_corruption=objective_corruption)
    baseline_contracts = evaluate_contracts(data, baseline)

    all_open = solve_model(data, forced_all_open=True)

    baseline_obj = baseline.reported_total_objective
    all_open_obj = all_open.reported_total_objective
    r02_passed = baseline_obj <= all_open_obj + 1e-5

    fixed_cost_multiplier = 1.25
    bumped_optimum = solve_model(data, fixed_cost_multiplier=fixed_cost_multiplier)
    baseline_design_under_bumped = solve_model(
        data,
        fixed_open=baseline.open_depots,
        fixed_cost_multiplier=fixed_cost_multiplier,
    )
    r03_passed = (
        bumped_optimum.reported_total_objective
        <= baseline_design_under_bumped.reported_total_objective + 1e-5
    )

    stressed_recourse = solve_model(
        data,
        fixed_open=baseline.open_depots,
        demand_multiplier=1.15,
    )
    stressed_contract_status = contract_check_solver_status_ok(stressed_recourse)
    stressed_expected_unmet = sum(
        s.probability * stressed_recourse.unmet[(s.scenario_id, t.town_id)]
        for s in data.scenarios
        for t in data.towns
    )
    stressed_total_unmet = sum(stressed_recourse.unmet.values())

    regression_checks = [
        _check_entry(
            "R01_baseline_contract_checked_solve",
            _all_passed(baseline_contracts),
            {
                "required_contract_ids": list(CONTRACT_IDS),
                "all_contracts_passed": _all_passed(baseline_contracts),
            },
        ),
        _check_entry(
            "R02_all_open_baseline_comparison",
            r02_passed,
            {
                "baseline_objective": baseline_obj,
                "all_open_objective": all_open_obj,
                "lhs_le_rhs_plus_tol": r02_passed,
            },
        ),
        _check_entry(
            "R03_fixed_cost_bump_perturbation",
            r03_passed,
            {
                "fixed_cost_multiplier": fixed_cost_multiplier,
                "bumped_optimum_objective": bumped_optimum.reported_total_objective,
                "baseline_design_under_bumped_objective": baseline_design_under_bumped.reported_total_objective,
                "lhs_le_rhs_plus_tol": r03_passed,
            },
        ),
        _check_entry(
            "R04_stressed_demand_fixed_design_recourse",
            stressed_contract_status["passed"],
            {
                "demand_multiplier": 1.15,
                "solver_status": stressed_recourse.status,
                "expected_unmet_demand": stressed_expected_unmet,
                "total_unmet_demand": stressed_total_unmet,
            },
        ),
    ]

    overall_passed = _all_passed(baseline_contracts) and _all_passed(regression_checks)

    report = {
        "harness_id": "contract_regression_harness_milp",
        "schema_version": 1,
        "checks": {
            "contract": baseline_contracts,
            "regression": regression_checks,
        },
        "baseline": _metrics_summary(data, baseline),
        "all_open_comparison": {
            "all_open": _metrics_summary(data, all_open),
            "baseline_objective": baseline_obj,
            "all_open_objective": all_open_obj,
        },
        "fixed_cost_bump": {
            "fixed_cost_multiplier": fixed_cost_multiplier,
            "bumped_optimum": _metrics_summary(data, bumped_optimum),
            "baseline_design_evaluation_under_bumped": _metrics_summary(
                data, baseline_design_under_bumped
            ),
        },
        "stressed_demand_fixed_design_recourse": {
            "demand_multiplier": 1.15,
            "stressed_recourse": _metrics_summary(data, stressed_recourse),
        },
        "overall_passed": overall_passed,
    }

    if write_report:
        destination = report_path() if output_path is None else output_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")

    return report


def _print_summary(report: dict[str, Any]) -> None:
    print("=== Contract Checks ===")
    for check in report["checks"]["contract"]:
        status = "PASS" if check["passed"] else "FAIL"
        print(f"{check['id']}: {status}")

    print("=== Regression Checks ===")
    for check in report["checks"]["regression"]:
        status = "PASS" if check["passed"] else "FAIL"
        print(f"{check['id']}: {status}")

    print("=== Deterministic Metrics ===")
    print(f"baseline_objective={report['baseline']['objective']:.6f}")
    print(
        f"all_open_objective={report['all_open_comparison']['all_open_objective']:.6f}"
    )
    print(
        "stressed_expected_unmet="
        f"{report['stressed_demand_fixed_design_recourse']['stressed_recourse']['expected_unmet_demand']:.6f}"
    )
    verdict = "PASS" if report["overall_passed"] else "FAIL"
    print(f"overall_harness_verdict={verdict}")


def main() -> int:
    report = run_harness(write_report=True)
    _print_summary(report)
    return 0 if report["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
