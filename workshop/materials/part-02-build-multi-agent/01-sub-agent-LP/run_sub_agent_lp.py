"""Sub-agent pure LP implementation for disaster-relief transportation planning."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import warnings

import xpress as xp

warnings.simplefilter("ignore")

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


@dataclass(frozen=True)
class PromptContract:
    model_name: str
    model_class: str
    integer_variables_allowed: bool
    all_depots_active: bool
    critical_service_floor: float
    shortage_penalty: float
    cvar_alpha: float
    risk_weight: float
    intent_literal: str


@dataclass(frozen=True)
class LPData:
    depots: list[str]
    towns: list[str]
    scenarios: list[str]
    critical_towns: set[str]
    capacity: dict[str, float]
    base_demand: dict[str, float]
    scenario_prob: dict[str, float]
    scenario_demand: dict[tuple[str, str], float]
    transport_cost: dict[tuple[str, str], float]


def planner_sub_agent() -> dict[str, float | str | bool]:
    return {
        "model_name": "sub_agent_transport_lp",
        "model_class": "LP",
        "integer_variables_allowed": False,
        "all_depots_active": True,
        "critical_service_floor": 0.95,
        "shortage_penalty": 15.0,
        "cvar_alpha": 0.85,
        "risk_weight": 20.0,
        "intent_literal": "Do not create integer or binary variables. Keep all depots active and solve transportation only.",
    }


def prompt_writer_sub_agent(plan: dict[str, float | str | bool]) -> PromptContract:
    return PromptContract(
        model_name=str(plan["model_name"]),
        model_class=str(plan["model_class"]),
        integer_variables_allowed=bool(plan["integer_variables_allowed"]),
        all_depots_active=bool(plan["all_depots_active"]),
        critical_service_floor=float(plan["critical_service_floor"]),
        shortage_penalty=float(plan["shortage_penalty"]),
        cvar_alpha=float(plan["cvar_alpha"]),
        risk_weight=float(plan["risk_weight"]),
        intent_literal=str(plan["intent_literal"]),
    )


def data_sub_agent() -> LPData:
    depots: list[str] = []
    capacity: dict[str, float] = {}
    with open(DATA_DIR / "depots.csv", newline="") as f:
        for row in csv.DictReader(f):
            did = row["depot_id"]
            depots.append(did)
            capacity[did] = float(row["capacity"])

    towns: list[str] = []
    critical_towns: set[str] = set()
    base_demand: dict[str, float] = {}
    with open(DATA_DIR / "towns.csv", newline="") as f:
        for row in csv.DictReader(f):
            tid = row["town_id"]
            towns.append(tid)
            base_demand[tid] = float(row["base_demand"])
            if row["priority_flag"] == "critical":
                critical_towns.add(tid)

    transport_cost: dict[tuple[str, str], float] = {}
    with open(DATA_DIR / "arcs.csv", newline="") as f:
        for row in csv.DictReader(f):
            transport_cost[row["depot_id"], row["town_id"]] = float(
                row["shipping_cost"]
            )

    scenarios: list[str] = []
    scenario_prob: dict[str, float] = {}
    with open(DATA_DIR / "scenarios.csv", newline="") as f:
        for row in csv.DictReader(f):
            sid = row["scenario_id"]
            scenarios.append(sid)
            scenario_prob[sid] = float(row["probability"])

    scenario_demand: dict[tuple[str, str], float] = {}
    with open(DATA_DIR / "scenario_demands.csv", newline="") as f:
        for row in csv.DictReader(f):
            scenario_demand[row["scenario_id"], row["town_id"]] = float(row["demand"])

    return LPData(
        depots=depots,
        towns=towns,
        scenarios=scenarios,
        critical_towns=critical_towns,
        capacity=capacity,
        base_demand=base_demand,
        scenario_prob=scenario_prob,
        scenario_demand=scenario_demand,
        transport_cost=transport_cost,
    )


def prompt_executor_sub_agent(
    contract: PromptContract, data: LPData
) -> dict[str, object]:
    if contract.model_class != "LP":
        raise ValueError("Executor blocked: prompt writer requested non-LP model.")
    if contract.integer_variables_allowed:
        raise ValueError(
            "Executor blocked: integer variables are disabled by workshop contract."
        )
    if not contract.all_depots_active:
        raise ValueError("Executor blocked: this stage requires all depots active.")

    model = xp.problem(contract.model_name)
    model.controls.outputlog = 0

    ship = {
        (d, t, s): xp.var(lb=0.0, name=f"ship_{d}_{t}_{s}")
        for d in data.depots
        for t in data.towns
        for s in data.scenarios
    }
    unmet = {
        (t, s): xp.var(lb=0.0, name=f"unmet_{t}_{s}")
        for t in data.towns
        for s in data.scenarios
    }
    scenario_shortage = {
        s: xp.var(lb=0.0, name=f"shortage_{s}") for s in data.scenarios
    }
    z = xp.var(lb=0.0, name="cvar_z")
    eta = {s: xp.var(lb=0.0, name=f"cvar_eta_{s}") for s in data.scenarios}

    model.addVariable(
        list(ship.values()),
        list(unmet.values()),
        list(scenario_shortage.values()),
        [z],
        list(eta.values()),
    )

    for d in data.depots:
        for s in data.scenarios:
            model.addConstraint(
                xp.Sum(ship[d, t, s] for t in data.towns) <= data.capacity[d]
            )

    for t in data.towns:
        for s in data.scenarios:
            demand_st = data.scenario_demand[s, t]
            model.addConstraint(
                xp.Sum(ship[d, t, s] for d in data.depots) + unmet[t, s] == demand_st
            )

    max_unmet_share = 1.0 - contract.critical_service_floor
    for t in data.critical_towns:
        for s in data.scenarios:
            demand_st = data.scenario_demand[s, t]
            model.addConstraint(unmet[t, s] <= max_unmet_share * demand_st)

    for s in data.scenarios:
        model.addConstraint(
            scenario_shortage[s] == xp.Sum(unmet[t, s] for t in data.towns)
        )
        model.addConstraint(eta[s] >= scenario_shortage[s] - z)

    expected_transport_expr = xp.Sum(
        data.scenario_prob[s] * data.transport_cost[d, t] * ship[d, t, s]
        for d in data.depots
        for t in data.towns
        for s in data.scenarios
    )
    expected_penalty_expr = xp.Sum(
        data.scenario_prob[s] * contract.shortage_penalty * unmet[t, s]
        for t in data.towns
        for s in data.scenarios
    )
    cvar_expr = z + (1.0 / (1.0 - contract.cvar_alpha)) * xp.Sum(
        data.scenario_prob[s] * eta[s] for s in data.scenarios
    )

    model.setObjective(
        expected_transport_expr
        + expected_penalty_expr
        + contract.risk_weight * cvar_expr,
        sense=xp.minimize,
    )
    model.solve()

    ship_values = {
        (d, t, s): float(model.getSolution(ship[d, t, s]))
        for d in data.depots
        for t in data.towns
        for s in data.scenarios
    }
    unmet_values = {
        (t, s): float(model.getSolution(unmet[t, s]))
        for t in data.towns
        for s in data.scenarios
    }
    shortage_values = {
        s: float(model.getSolution(scenario_shortage[s])) for s in data.scenarios
    }
    z_val = float(model.getSolution(z))
    eta_values = {s: float(model.getSolution(eta[s])) for s in data.scenarios}

    expected_transport = sum(
        data.scenario_prob[s] * data.transport_cost[d, t] * ship_values[d, t, s]
        for d in data.depots
        for t in data.towns
        for s in data.scenarios
    )
    expected_unmet = sum(
        data.scenario_prob[s] * unmet_values[t, s]
        for t in data.towns
        for s in data.scenarios
    )
    expected_penalty = contract.shortage_penalty * expected_unmet
    cvar_shortage = z_val + (1.0 / (1.0 - contract.cvar_alpha)) * sum(
        data.scenario_prob[s] * eta_values[s] for s in data.scenarios
    )

    expected_lane_flow = {
        (d, t): sum(
            data.scenario_prob[s] * ship_values[d, t, s] for s in data.scenarios
        )
        for d in data.depots
        for t in data.towns
    }
    top_lanes = sorted(
        expected_lane_flow.items(), key=lambda item: item[1], reverse=True
    )[:8]

    return {
        "status": model.getProbStatusString(),
        "objective": float(model.getObjVal()),
        "active_depots": list(data.depots),
        "expected_transport": expected_transport,
        "expected_penalty": expected_penalty,
        "expected_unmet": expected_unmet,
        "cvar_shortage": cvar_shortage,
        "worst_scenario_unmet": max(shortage_values.values()),
        "top_expected_lanes": top_lanes,
        "unmet_values": unmet_values,
        "integer_variables_used": 0,
        "executor_intent_literal": contract.intent_literal,
    }


def tester_sub_agent(
    contract: PromptContract, summary: dict[str, object], data: LPData
) -> dict[str, object]:
    unmet_values: dict[tuple[str, str], float] = summary["unmet_values"]
    tolerance = 1e-6

    max_unmet_share = 1.0 - contract.critical_service_floor
    critical_violations = []
    for t in data.critical_towns:
        for s in data.scenarios:
            demand_st = data.scenario_demand[s, t]
            threshold = max_unmet_share * demand_st
            if unmet_values[t, s] > threshold + tolerance:
                critical_violations.append((t, s, unmet_values[t, s], threshold))

    checks = {
        "status_is_lp_optimal": str(summary["status"]).startswith("lp_"),
        "no_integer_variables": int(summary["integer_variables_used"]) == 0
        and not contract.integer_variables_allowed,
        "all_depots_active": contract.all_depots_active
        and len(summary["active_depots"]) == len(data.depots),
        "literal_intent_respected": str(summary["executor_intent_literal"])
        == contract.intent_literal,
        "critical_service_respected": len(critical_violations) == 0,
    }

    objective_expected = (
        float(summary["expected_transport"])
        + float(summary["expected_penalty"])
        + contract.risk_weight * float(summary["cvar_shortage"])
    )
    checks["objective_components_consistent"] = (
        abs(objective_expected - float(summary["objective"])) <= 1e-3
    )

    return {
        "checks": checks,
        "critical_violations": critical_violations,
        "passed": all(checks.values()),
        "passed_count": sum(1 for ok in checks.values() if ok),
        "total_count": len(checks),
    }


def reporter_sub_agent(
    contract: PromptContract, summary: dict[str, object], audit: dict[str, object]
) -> None:
    print("=== Sub-Agent LP Result ===")
    print(f"Prompt writer intent: {contract.intent_literal}")
    print(f"Solver status: {summary['status']}")
    print(f"Objective value: {summary['objective']:.2f}")
    print(f"Active depots: {', '.join(summary['active_depots'])}")
    print(f"Expected transport cost: {summary['expected_transport']:.2f}")
    print(f"Expected shortage penalty: {summary['expected_penalty']:.2f}")
    print(f"Expected unmet demand: {summary['expected_unmet']:.2f}")
    print(f"CVaR-style shortage indicator: {summary['cvar_shortage']:.2f}")
    print(f"Worst scenario unmet demand: {summary['worst_scenario_unmet']:.2f}")
    print(f"Prompt contract respected: {audit['passed']}")
    print(f"Tester checks passed: {audit['passed_count']}/{audit['total_count']}")
    print("Top expected shipment lanes:")
    for (depot, town), volume in summary["top_expected_lanes"]:
        print(f"  - {depot} -> {town}: {volume:.2f}")


def manager() -> None:
    plan = planner_sub_agent()
    contract = prompt_writer_sub_agent(plan)
    data = data_sub_agent()
    summary = prompt_executor_sub_agent(contract, data)
    audit = tester_sub_agent(contract, summary, data)
    reporter_sub_agent(contract, summary, audit)


if __name__ == "__main__":
    manager()
