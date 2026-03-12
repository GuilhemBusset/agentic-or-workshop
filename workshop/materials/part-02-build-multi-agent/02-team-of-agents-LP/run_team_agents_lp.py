"""Team-of-agents pure LP implementation for disaster-relief transportation planning."""

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
    candidate_name: str
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


def strategy_team() -> dict[str, object]:
    return {
        "model_name_prefix": "team_agents_transport_lp",
        "candidates": [
            {
                "name": "Pod-A (cost-focused)",
                "risk_weight": 10.0,
                "shortage_penalty": 8.0,
            },
            {"name": "Pod-B (balanced)", "risk_weight": 24.0, "shortage_penalty": 12.0},
            {
                "name": "Pod-C (risk-averse)",
                "risk_weight": 40.0,
                "shortage_penalty": 20.0,
            },
        ],
        "cvar_alpha": 0.80,
        "critical_service_floor": 0.95,
        "selection_rule": "Pick the feasible candidate with the smallest governance score.",
    }


def _read_csv(filename: str) -> list[dict[str, str]]:
    with open(DATA_DIR / filename, newline="") as fh:
        return list(csv.DictReader(fh))


def data_team() -> LPData:
    depot_rows = _read_csv("depots.csv")
    town_rows = _read_csv("towns.csv")
    arc_rows = _read_csv("arcs.csv")
    scenario_rows = _read_csv("scenarios.csv")
    sd_rows = _read_csv("scenario_demands.csv")

    depots = [r["depot_id"] for r in depot_rows]
    towns = [r["town_id"] for r in town_rows]
    scenarios = [r["scenario_id"] for r in scenario_rows]

    capacity = {r["depot_id"]: float(r["capacity"]) for r in depot_rows}
    base_demand = {r["town_id"]: float(r["base_demand"]) for r in town_rows}
    critical_towns = {
        r["town_id"] for r in town_rows if r["priority_flag"] == "critical"
    }

    scenario_prob = {r["scenario_id"]: float(r["probability"]) for r in scenario_rows}
    scenario_demand = {
        (r["scenario_id"], r["town_id"]): float(r["demand"]) for r in sd_rows
    }
    transport_cost = {
        (r["depot_id"], r["town_id"]): float(r["shipping_cost"]) for r in arc_rows
    }

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


def prompt_writer_team(
    protocol: dict[str, object], candidate: dict[str, object]
) -> PromptContract:
    return PromptContract(
        candidate_name=str(candidate["name"]),
        model_name="{}_rw{}_sp{}".format(
            protocol["model_name_prefix"],
            int(candidate["risk_weight"]),
            int(candidate["shortage_penalty"]),
        ),
        model_class="LP",
        integer_variables_allowed=False,
        all_depots_active=True,
        critical_service_floor=float(protocol["critical_service_floor"]),
        shortage_penalty=float(candidate["shortage_penalty"]),
        cvar_alpha=float(protocol["cvar_alpha"]),
        risk_weight=float(candidate["risk_weight"]),
        intent_literal="Do not use binary/integer variables and do not optimize depot opening decisions.",
    )


def prompt_executor_team(contract: PromptContract, data: LPData) -> dict[str, object]:
    if contract.model_class != "LP":
        raise ValueError("Executor blocked: non-LP contract was provided.")
    if contract.integer_variables_allowed:
        raise ValueError(
            "Executor blocked: integer variables are not allowed in this lesson."
        )
    if not contract.all_depots_active:
        raise ValueError("Executor blocked: all depots must stay active.")

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
        "risk_weight": contract.risk_weight,
        "shortage_penalty": contract.shortage_penalty,
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


def tester_team(
    contract: PromptContract, result: dict[str, object], data: LPData
) -> dict[str, object]:
    unmet_values: dict[tuple[str, str], float] = result["unmet_values"]
    tolerance = 1e-6

    max_unmet_share = 1.0 - contract.critical_service_floor
    violations = []
    for t in data.critical_towns:
        for s in data.scenarios:
            demand_st = data.scenario_demand[s, t]
            threshold = max_unmet_share * demand_st
            if unmet_values[t, s] > threshold + tolerance:
                violations.append((t, s, unmet_values[t, s], threshold))

    checks = {
        "status_is_lp_optimal": str(result["status"]).startswith("lp_"),
        "no_integer_variables": int(result["integer_variables_used"]) == 0
        and not contract.integer_variables_allowed,
        "all_depots_active": contract.all_depots_active
        and len(result["active_depots"]) == len(data.depots),
        "literal_intent_respected": str(result["executor_intent_literal"])
        == contract.intent_literal,
        "critical_service_respected": len(violations) == 0,
    }

    objective_expected = (
        float(result["expected_transport"])
        + float(result["expected_penalty"])
        + contract.risk_weight * float(result["cvar_shortage"])
    )
    checks["objective_components_consistent"] = (
        abs(objective_expected - float(result["objective"])) <= 1e-3
    )

    governance_score = (
        float(result["expected_transport"])
        + float(result["expected_penalty"])
        + 15.0 * float(result["worst_scenario_unmet"])
    )

    return {
        "checks": checks,
        "violations": violations,
        "contract_respected": all(checks.values()),
        "governance_score": governance_score,
        "passed_count": sum(1 for ok in checks.values() if ok),
        "total_count": len(checks),
    }


def board_team(results: list[dict[str, object]]) -> dict[str, object]:
    feasible = [item for item in results if item["audit"]["contract_respected"]]
    if not feasible:
        return min(results, key=lambda item: item["audit"]["governance_score"])
    return min(feasible, key=lambda item: item["audit"]["governance_score"])


def reporter_team(
    all_results: list[dict[str, object]], selected: dict[str, object]
) -> None:
    print("=== Team-of-Agents LP Result ===")
    print("Candidate comparison:")
    for item in all_results:
        contract: PromptContract = item["contract"]
        result = item["result"]
        audit = item["audit"]
        print(
            "  - {} | risk_w={:.1f} short_p={:.1f} | obj={:.2f} | "
            "exp_unmet={:.2f} | worst_unmet={:.2f} | "
            "contract_ok={} | checks={}/{} | gov_score={:.2f}".format(
                contract.candidate_name,
                contract.risk_weight,
                contract.shortage_penalty,
                result["objective"],
                result["expected_unmet"],
                result["worst_scenario_unmet"],
                audit["contract_respected"],
                audit["passed_count"],
                audit["total_count"],
                audit["governance_score"],
            )
        )

    result = selected["result"]
    contract: PromptContract = selected["contract"]
    audit = selected["audit"]
    print("\nBoard-selected plan:")
    print(f"Prompt writer intent: {contract.intent_literal}")
    print(f"Solver status: {result['status']}")
    print(f"Selected candidate: {contract.candidate_name}")
    print(f"Selected risk weight: {result['risk_weight']:.1f}")
    print(f"Selected shortage penalty: {result['shortage_penalty']:.1f}")
    print(f"Objective value: {result['objective']:.2f}")
    print(f"Active depots: {', '.join(result['active_depots'])}")
    print(f"Expected transport cost: {result['expected_transport']:.2f}")
    print(f"Expected shortage penalty: {result['expected_penalty']:.2f}")
    print(f"Expected unmet demand: {result['expected_unmet']:.2f}")
    print(f"CVaR-style shortage indicator: {result['cvar_shortage']:.2f}")
    print(f"Worst scenario unmet demand: {result['worst_scenario_unmet']:.2f}")
    print(f"Prompt contract respected: {audit['contract_respected']}")
    print(f"Tester checks passed: {audit['passed_count']}/{audit['total_count']}")
    print(f"Governance score: {audit['governance_score']:.2f}")
    print("Top expected shipment lanes:")
    for (depot, town), volume in result["top_expected_lanes"]:
        print(f"  - {depot} -> {town}: {volume:.2f}")


def run_team_process() -> None:
    protocol = strategy_team()
    data = data_team()

    collected = []
    for candidate in protocol["candidates"]:
        contract = prompt_writer_team(protocol, candidate)
        result = prompt_executor_team(contract, data)
        audit = tester_team(contract, result, data)
        collected.append({"contract": contract, "result": result, "audit": audit})

    selected = board_team(collected)
    reporter_team(collected, selected)


if __name__ == "__main__":
    run_team_process()
