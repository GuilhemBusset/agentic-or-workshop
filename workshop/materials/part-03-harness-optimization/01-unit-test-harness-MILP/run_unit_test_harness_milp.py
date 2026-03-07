"""Unit-test harness first MILP for disaster-relief depot activation and routing."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import warnings

import xpress as xp

warnings.simplefilter("ignore")

_XPRESS_INITIALIZED = False
_REQUIRED_CRITICAL_TOWNS = {"T03", "T04", "T07", "T12"}


def _initialize_xpress() -> None:
    global _XPRESS_INITIALIZED
    if _XPRESS_INITIALIZED:
        return

    package_dir = Path(xp.__file__).resolve().parent
    community_license = package_dir / "license" / "community-xpauth.xpr"
    if community_license.exists():
        xp.init(str(community_license))

    _XPRESS_INITIALIZED = True


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def prompt_writer_agent() -> dict[str, object]:
    """Return deterministic MILP contract/spec for the prompt executor."""
    return {
        "model_name": "unit_test_harness_milp",
        "model_class": "MILP",
        "decision_variables": {
            "open_depot_binary": True,
            "shipment_continuous": True,
            "unmet_continuous": True,
        },
        "critical_towns": sorted(_REQUIRED_CRITICAL_TOWNS),
        "critical_service_floor": 0.95,
        "shortage_penalty": 25.0,
        "cvar_alpha": 0.80,
        "risk_weight": 12.0,
        "intent": "Open depots with binary variables and optimize expected cost plus CVaR shortage risk under scenario uncertainty.",
    }


def build_data() -> dict[str, object]:
    """Load and validate all MILP data inputs from workshop/data/."""
    data_dir = Path(__file__).resolve().parents[3] / "data"

    depots_raw = _read_csv(data_dir / "depots.csv")
    towns_raw = _read_csv(data_dir / "towns.csv")
    arcs_raw = _read_csv(data_dir / "arcs.csv")
    scenarios_raw = _read_csv(data_dir / "scenarios.csv")
    scenario_demands_raw = _read_csv(data_dir / "scenario_demands.csv")

    depots = sorted(row["depot_id"] for row in depots_raw)
    towns = sorted(row["town_id"] for row in towns_raw)
    scenarios = sorted(row["scenario_id"] for row in scenarios_raw)

    capacity = {row["depot_id"]: float(row["capacity"]) for row in depots_raw}
    fixed_cost = {row["depot_id"]: float(row["fixed_cost"]) for row in depots_raw}
    service_min = {row["town_id"]: float(row["service_min"]) for row in towns_raw}
    scenario_prob = {
        row["scenario_id"]: float(row["probability"]) for row in scenarios_raw
    }
    shipping_cost = {
        (row["depot_id"], row["town_id"]): float(row["shipping_cost"])
        for row in arcs_raw
    }

    scenario_demands = sorted(
        [
            {
                "scenario_id": row["scenario_id"],
                "town_id": row["town_id"],
                "demand": float(row["demand"]),
            }
            for row in scenario_demands_raw
        ],
        key=lambda row: (row["scenario_id"], row["town_id"]),
    )
    demand = {
        (row["scenario_id"], row["town_id"]): float(row["demand"])
        for row in scenario_demands_raw
    }

    critical_towns = {
        row["town_id"]
        for row in towns_raw
        if row["priority_flag"].lower() == "critical"
    }

    if len(depots) != 6:
        raise ValueError(f"Expected 6 depots, found {len(depots)}")
    if len(towns) != 12:
        raise ValueError(f"Expected 12 towns, found {len(towns)}")
    if len(scenarios) != 8:
        raise ValueError(f"Expected 8 scenarios, found {len(scenarios)}")

    probability_sum = sum(scenario_prob[scenario] for scenario in scenarios)
    if abs(probability_sum - 1.0) > 1e-9:
        raise ValueError(
            f"Scenario probabilities must sum to 1.0, got {probability_sum:.12f}"
        )

    if critical_towns != _REQUIRED_CRITICAL_TOWNS:
        raise ValueError(
            f"Critical towns mismatch. Expected {_REQUIRED_CRITICAL_TOWNS}, got {critical_towns}"
        )

    for scenario in scenarios:
        for town in towns:
            if (scenario, town) not in demand:
                raise ValueError(f"Missing demand for scenario={scenario}, town={town}")

    for depot in depots:
        for town in towns:
            if (depot, town) not in shipping_cost:
                raise ValueError(f"Missing arc cost for depot={depot}, town={town}")

    return {
        "depots": depots,
        "towns": towns,
        "scenarios": scenarios,
        "critical_towns": sorted(critical_towns),
        "probability_sum": float(probability_sum),
        "capacity": capacity,
        "fixed_cost": fixed_cost,
        "service_min": service_min,
        "scenario_prob": scenario_prob,
        "shipping_cost": shipping_cost,
        "scenario_demands": scenario_demands,
        "demand": demand,
    }


def prompt_executor_agent(
    contract: dict[str, object], data: dict[str, object]
) -> dict[str, object]:
    """Build and solve the contract-compliant MILP and return a parseable summary."""
    if contract.get("model_class") != "MILP":
        raise ValueError("Executor rejects contract: model_class must be MILP.")

    decision_variables = contract.get("decision_variables", {})
    if not isinstance(decision_variables, dict) or not decision_variables.get(
        "open_depot_binary", False
    ):
        raise ValueError(
            "Executor rejects contract: binary depot-open variables are required."
        )

    contract_critical = set(contract.get("critical_towns", []))
    if contract_critical != _REQUIRED_CRITICAL_TOWNS:
        raise ValueError("Executor rejects contract: critical town set is invalid.")

    _initialize_xpress()

    depots = list(data["depots"])
    towns = list(data["towns"])
    scenarios = list(data["scenarios"])
    capacity = dict(data["capacity"])
    fixed_cost = dict(data["fixed_cost"])
    shipping_cost = dict(data["shipping_cost"])
    scenario_prob = dict(data["scenario_prob"])
    demand = dict(data["demand"])

    shortage_penalty = float(contract["shortage_penalty"])
    cvar_alpha = float(contract["cvar_alpha"])
    risk_weight = float(contract["risk_weight"])
    critical_service_floor = float(contract["critical_service_floor"])

    model = xp.problem(str(contract["model_name"]))
    model.controls.outputlog = 0

    open_depot = {
        depot: xp.var(vartype=xp.binary, name=f"open_{depot}") for depot in depots
    }
    ship = {
        (depot, town, scenario): xp.var(lb=0.0, name=f"ship_{depot}_{town}_{scenario}")
        for depot in depots
        for town in towns
        for scenario in scenarios
    }
    unmet = {
        (town, scenario): xp.var(lb=0.0, name=f"unmet_{town}_{scenario}")
        for town in towns
        for scenario in scenarios
    }
    scenario_shortage = {
        scenario: xp.var(lb=0.0, name=f"shortage_{scenario}") for scenario in scenarios
    }
    eta = xp.var(lb=0.0, name="cvar_eta")
    xi = {
        scenario: xp.var(lb=0.0, name=f"cvar_xi_{scenario}") for scenario in scenarios
    }

    model.addVariable(
        list(open_depot.values()),
        list(ship.values()),
        list(unmet.values()),
        list(scenario_shortage.values()),
        [eta],
        list(xi.values()),
    )

    for depot in depots:
        for scenario in scenarios:
            model.addConstraint(
                xp.Sum(ship[depot, town, scenario] for town in towns)
                <= capacity[depot] * open_depot[depot]
            )

    for town in towns:
        for scenario in scenarios:
            model.addConstraint(
                xp.Sum(ship[depot, town, scenario] for depot in depots)
                + unmet[town, scenario]
                == demand[scenario, town]
            )

    for town in _REQUIRED_CRITICAL_TOWNS:
        for scenario in scenarios:
            model.addConstraint(
                xp.Sum(ship[depot, town, scenario] for depot in depots)
                >= critical_service_floor * demand[scenario, town]
            )

    for scenario in scenarios:
        model.addConstraint(
            scenario_shortage[scenario]
            == xp.Sum(unmet[town, scenario] for town in towns)
        )
        model.addConstraint(xi[scenario] >= scenario_shortage[scenario] - eta)

    fixed_cost_expr = xp.Sum(fixed_cost[depot] * open_depot[depot] for depot in depots)
    expected_transport_expr = xp.Sum(
        scenario_prob[scenario]
        * shipping_cost[depot, town]
        * ship[depot, town, scenario]
        for depot in depots
        for town in towns
        for scenario in scenarios
    )
    expected_shortage_penalty_expr = xp.Sum(
        scenario_prob[scenario] * shortage_penalty * unmet[town, scenario]
        for town in towns
        for scenario in scenarios
    )
    cvar_shortage_expr = eta + (1.0 / (1.0 - cvar_alpha)) * xp.Sum(
        scenario_prob[scenario] * xi[scenario] for scenario in scenarios
    )

    model.setObjective(
        fixed_cost_expr
        + expected_transport_expr
        + expected_shortage_penalty_expr
        + risk_weight * cvar_shortage_expr,
        sense=xp.minimize,
    )
    model.solve()

    solver_status = str(model.getProbStatusString())

    open_values = {
        depot: float(model.getSolution(open_depot[depot])) for depot in sorted(depots)
    }
    ship_values = {
        (depot, town, scenario): float(model.getSolution(ship[depot, town, scenario]))
        for depot in depots
        for town in towns
        for scenario in scenarios
    }
    unmet_values = {
        (town, scenario): float(model.getSolution(unmet[town, scenario]))
        for town in towns
        for scenario in scenarios
    }
    scenario_shortage_values = {
        scenario: float(model.getSolution(scenario_shortage[scenario]))
        for scenario in scenarios
    }
    eta_value = float(model.getSolution(eta))
    xi_values = {
        scenario: float(model.getSolution(xi[scenario])) for scenario in scenarios
    }

    open_depots = sorted(
        [depot for depot, value in open_values.items() if value >= 0.5]
    )

    fixed_opening_cost = float(
        sum(fixed_cost[depot] * open_values[depot] for depot in depots)
    )
    expected_transport_cost = float(
        sum(
            scenario_prob[scenario]
            * shipping_cost[depot, town]
            * ship_values[depot, town, scenario]
            for depot in depots
            for town in towns
            for scenario in scenarios
        )
    )
    expected_unmet = float(
        sum(
            scenario_prob[scenario] * unmet_values[town, scenario]
            for town in towns
            for scenario in scenarios
        )
    )
    expected_shortage_penalty = float(shortage_penalty * expected_unmet)
    cvar_shortage = float(
        eta_value
        + (1.0 / (1.0 - cvar_alpha))
        * sum(scenario_prob[scenario] * xi_values[scenario] for scenario in scenarios)
    )
    cvar_risk_term = float(risk_weight * cvar_shortage)
    total_recomputed = float(
        fixed_opening_cost
        + expected_transport_cost
        + expected_shortage_penalty
        + cvar_risk_term
    )

    total_unmet_by_scenario = {
        scenario: float(scenario_shortage_values[scenario])
        for scenario in sorted(scenarios)
    }
    depot_shipments = {
        scenario: {
            depot: float(sum(ship_values[depot, town, scenario] for town in towns))
            for depot in sorted(depots)
        }
        for scenario in sorted(scenarios)
    }
    service_ratio = {
        scenario: {
            town: float(
                (demand[scenario, town] - unmet_values[town, scenario])
                / demand[scenario, town]
            )
            for town in sorted(towns)
        }
        for scenario in sorted(scenarios)
    }

    return {
        "solver_status": solver_status,
        "objective": float(model.getObjVal()),
        "open_depots": open_depots,
        "open_depot_count": len(open_depots),
        "cost_breakdown": {
            "fixed_opening_cost": fixed_opening_cost,
            "expected_transport_cost": expected_transport_cost,
            "expected_shortage_penalty": expected_shortage_penalty,
            "cvar_risk_term": cvar_risk_term,
            "total_recomputed": total_recomputed,
        },
        "unmet_metrics": {
            "expected_unmet": expected_unmet,
            "max_scenario_unmet": float(max(total_unmet_by_scenario.values())),
            "total_unmet_by_scenario": total_unmet_by_scenario,
        },
        "risk_metrics": {
            "alpha": cvar_alpha,
            "eta": eta_value,
            "cvar_shortage": cvar_shortage,
        },
        "contract_respected": True,
        "open_values": open_values,
        "depot_shipments": depot_shipments,
        "service_ratio": service_ratio,
        "critical_service_floor": critical_service_floor,
    }


def unit_test_agent(
    contract: dict[str, object],
    summary: dict[str, object],
    data: dict[str, object],
) -> dict[str, object]:
    """Validate core MILP invariants and return explicit pass/fail details."""
    checks: dict[str, bool] = {}
    failures: list[str] = []
    tolerance = 1e-4

    checks["contract_milp"] = contract.get("model_class") == "MILP"
    if not checks["contract_milp"]:
        failures.append("Contract mismatch: model_class must be MILP.")

    decision_variables = contract.get("decision_variables", {})
    checks["binary_open_variable_required"] = bool(
        isinstance(decision_variables, dict)
        and decision_variables.get("open_depot_binary", False)
    )
    if not checks["binary_open_variable_required"]:
        failures.append("Contract mismatch: binary depot-open variable is required.")

    status = str(summary.get("solver_status", ""))
    checks["solver_status_optimal"] = (
        "optimal" in status.lower()
        or status.lower().startswith("mip_")
        or status.lower().startswith("lp_")
    )
    if not checks["solver_status_optimal"]:
        failures.append(f"Solver did not return an optimal status: {status}")

    open_depots = list(summary.get("open_depots", []))
    open_depot_count = int(summary.get("open_depot_count", -1))
    checks["open_depot_count_consistent"] = open_depot_count == len(open_depots)
    if not checks["open_depot_count_consistent"]:
        failures.append("Open depot count does not match open depot list length.")

    objective = float(summary.get("objective", 0.0))
    cost_breakdown = summary.get("cost_breakdown", {})
    recomputed_total = float(cost_breakdown.get("total_recomputed", 0.0))
    checks["objective_consistency"] = abs(objective - recomputed_total) <= 1e-3
    if not checks["objective_consistency"]:
        failures.append(
            "Objective inconsistency: summary objective does not match recomputed cost total."
        )

    checks["probability_sum_one"] = (
        abs(float(data.get("probability_sum", 0.0)) - 1.0) <= 1e-9
    )
    if not checks["probability_sum_one"]:
        failures.append("Scenario probabilities do not sum to 1.")

    service_ratio = summary.get("service_ratio", {})
    service_floor = float(contract.get("critical_service_floor", 0.95))
    critical_service_ok = True
    for scenario in data["scenarios"]:
        for town in _REQUIRED_CRITICAL_TOWNS:
            ratio = float(service_ratio.get(scenario, {}).get(town, -1.0))
            if ratio + tolerance < service_floor:
                critical_service_ok = False
                failures.append(
                    f"Critical service floor violated for {town} in {scenario}: ratio={ratio:.6f}."
                )
                break
        if not critical_service_ok:
            break
    checks["critical_service_floor"] = critical_service_ok

    open_values = summary.get("open_values", {})
    depot_shipments = summary.get("depot_shipments", {})
    capacity = data.get("capacity", {})
    capacity_open_ok = True
    for scenario in data["scenarios"]:
        for depot in data["depots"]:
            shipped = float(depot_shipments.get(scenario, {}).get(depot, 0.0))
            is_open = float(open_values.get(depot, 0.0)) >= 0.5
            allowed = float(capacity[depot]) if is_open else 0.0
            if shipped > allowed + tolerance:
                capacity_open_ok = False
                failures.append(
                    f"Capacity-open violation for depot={depot}, scenario={scenario}: shipped={shipped:.6f}, allowed={allowed:.6f}."
                )
                break
        if not capacity_open_ok:
            break
    checks["capacity_only_if_open"] = capacity_open_ok

    return {
        "passed": len(failures) == 0,
        "checks": checks,
        "failures": failures,
        "passed_count": sum(1 for value in checks.values() if value),
        "total_count": len(checks),
    }


def main() -> None:
    contract = prompt_writer_agent()
    data = build_data()
    summary = prompt_executor_agent(contract, data)
    harness_result = unit_test_agent(contract, summary, data)

    output = {
        "solver_status": summary["solver_status"],
        "objective": summary["objective"],
        "open_depots": summary["open_depots"],
        "open_depot_count": summary["open_depot_count"],
        "cost_breakdown": summary["cost_breakdown"],
        "unmet_metrics": summary["unmet_metrics"],
        "risk_metrics": summary["risk_metrics"],
        "contract_respected": summary["contract_respected"],
        "harness_checks_passed": harness_result["passed"],
        "harness_passed_count": harness_result["passed_count"],
        "harness_total_count": harness_result["total_count"],
        "harness_failures": harness_result["failures"],
    }
    print(json.dumps(output, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
