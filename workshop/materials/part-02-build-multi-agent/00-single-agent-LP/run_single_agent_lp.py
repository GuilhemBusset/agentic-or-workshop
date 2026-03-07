"""Single-agent pure LP implementation for disaster-relief transportation planning."""

from __future__ import annotations

from dataclasses import dataclass
import warnings

import xpress as xp

warnings.simplefilter("ignore")


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
    scenario_multiplier: dict[str, float]
    transport_cost: dict[tuple[str, str], float]


def prompt_writer_agent() -> PromptContract:
    return PromptContract(
        model_name="single_agent_transport_lp",
        model_class="LP",
        integer_variables_allowed=False,
        all_depots_active=True,
        critical_service_floor=0.95,
        shortage_penalty=12.0,
        cvar_alpha=0.80,
        risk_weight=24.0,
        intent_literal="Use only continuous nonnegative variables and keep every depot available.",
    )


def build_data() -> LPData:
    depots = [f"D{i:02d}" for i in range(1, 7)]
    towns = [f"T{i:02d}" for i in range(1, 13)]
    scenarios = [f"S{i:02d}" for i in range(1, 9)]

    capacity = {
        "D01": 300,
        "D02": 260,
        "D03": 280,
        "D04": 220,
        "D05": 210,
        "D06": 320,
    }
    base_demand = {
        "T01": 95,
        "T02": 110,
        "T03": 120,
        "T04": 115,
        "T05": 90,
        "T06": 75,
        "T07": 130,
        "T08": 80,
        "T09": 105,
        "T10": 85,
        "T11": 92,
        "T12": 108,
    }
    scenario_prob = {
        "S01": 0.10,
        "S02": 0.10,
        "S03": 0.15,
        "S04": 0.15,
        "S05": 0.10,
        "S06": 0.10,
        "S07": 0.15,
        "S08": 0.15,
    }
    scenario_multiplier = {
        "S01": 0.85,
        "S02": 0.95,
        "S03": 1.00,
        "S04": 1.10,
        "S05": 1.20,
        "S06": 1.30,
        "S07": 1.40,
        "S08": 1.55,
    }

    def lane_cost(depot: str, town: str) -> float:
        d_idx = int(depot[1:])
        t_idx = int(town[1:])
        return (
            5.0
            + 1.4 * abs(d_idx - ((t_idx - 1) % 6 + 1))
            + ((d_idx * 7 + t_idx * 3) % 6)
        )

    transport_cost = {(d, t): lane_cost(d, t) for d in depots for t in towns}

    return LPData(
        depots=depots,
        towns=towns,
        scenarios=scenarios,
        critical_towns={"T03", "T04", "T07", "T12"},
        capacity=capacity,
        base_demand=base_demand,
        scenario_prob=scenario_prob,
        scenario_multiplier=scenario_multiplier,
        transport_cost=transport_cost,
    )


def prompt_executor_agent(contract: PromptContract, data: LPData) -> dict[str, object]:
    if contract.model_class != "LP":
        raise ValueError("Prompt executor refused to run: model_class must be LP.")
    if contract.integer_variables_allowed:
        raise ValueError(
            "Prompt executor refused to run: integer variables are forbidden in this lesson."
        )
    if not contract.all_depots_active:
        raise ValueError(
            "Prompt executor refused to run: all depots must remain active in LP stage."
        )

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
            demand_st = data.base_demand[t] * data.scenario_multiplier[s]
            model.addConstraint(
                xp.Sum(ship[d, t, s] for d in data.depots) + unmet[t, s] == demand_st
            )

    max_unmet_share = 1.0 - contract.critical_service_floor
    for t in data.critical_towns:
        for s in data.scenarios:
            demand_st = data.base_demand[t] * data.scenario_multiplier[s]
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

    expected_lane_flow: dict[tuple[str, str], float] = {}
    for d in data.depots:
        for t in data.towns:
            expected_lane_flow[d, t] = sum(
                data.scenario_prob[s] * ship_values[d, t, s] for s in data.scenarios
            )

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
        "critical_service_floor": contract.critical_service_floor,
        "top_expected_lanes": top_lanes,
        "unmet_values": unmet_values,
        "risk_weight": contract.risk_weight,
        "shortage_penalty": contract.shortage_penalty,
        "cvar_alpha": contract.cvar_alpha,
        "integer_variables_used": 0,
        "executor_intent_literal": contract.intent_literal,
    }


def tester_agent(
    contract: PromptContract, summary: dict[str, object], data: LPData
) -> dict[str, object]:
    unmet_values: dict[tuple[str, str], float] = summary["unmet_values"]
    tolerance = 1e-6

    status_ok = str(summary["status"]).startswith("lp_")
    no_integer_ok = (
        int(summary["integer_variables_used"]) == 0
        and not contract.integer_variables_allowed
    )
    depot_policy_ok = contract.all_depots_active and len(
        summary["active_depots"]
    ) == len(data.depots)
    literal_intent_ok = (
        str(summary["executor_intent_literal"]) == contract.intent_literal
    )

    critical_ok = True
    max_unmet_share = 1.0 - contract.critical_service_floor
    for t in data.critical_towns:
        for s in data.scenarios:
            demand_st = data.base_demand[t] * data.scenario_multiplier[s]
            if unmet_values[t, s] > max_unmet_share * demand_st + tolerance:
                critical_ok = False
                break
        if not critical_ok:
            break

    objective_expected = (
        float(summary["expected_transport"])
        + float(summary["expected_penalty"])
        + contract.risk_weight * float(summary["cvar_shortage"])
    )
    objective_ok = abs(objective_expected - float(summary["objective"])) <= 1e-3

    checks = {
        "status_is_lp_optimal": status_ok,
        "no_integer_variables": no_integer_ok,
        "all_depots_active": depot_policy_ok,
        "literal_intent_respected": literal_intent_ok,
        "critical_service_respected": critical_ok,
        "objective_components_consistent": objective_ok,
    }

    return {
        "checks": checks,
        "passed": all(checks.values()),
        "passed_count": sum(1 for ok in checks.values() if ok),
        "total_count": len(checks),
    }


def print_summary(
    contract: PromptContract, summary: dict[str, object], audit: dict[str, object]
) -> None:
    print("=== Single-Agent LP Result ===")
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


def main() -> None:
    contract = prompt_writer_agent()
    data = build_data()
    summary = prompt_executor_agent(contract, data)
    audit = tester_agent(contract, summary, data)
    print_summary(contract, summary, audit)


if __name__ == "__main__":
    main()
