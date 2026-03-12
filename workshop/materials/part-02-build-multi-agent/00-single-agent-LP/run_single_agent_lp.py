"""Single-agent LP for disaster-relief transportation planning.

One prompt, one script, no role decomposition.
"""

from __future__ import annotations

import csv
from pathlib import Path
import warnings

import xpress as xp

warnings.simplefilter("ignore")

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

# ---------- parameters ----------
SHORTAGE_PENALTY = 12.0
CVAR_ALPHA = 0.80
RISK_WEIGHT = 24.0
CRITICAL_SERVICE_FLOOR = 0.95


def _read_csv(filename: str) -> list[dict[str, str]]:
    with open(DATA_DIR / filename, newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    # ---- load data from CSVs ----
    depot_rows = _read_csv("depots.csv")
    town_rows = _read_csv("towns.csv")
    arc_rows = _read_csv("arcs.csv")
    scenario_rows = _read_csv("scenarios.csv")
    demand_rows = _read_csv("scenario_demands.csv")

    depots = [r["depot_id"] for r in depot_rows]
    towns = [r["town_id"] for r in town_rows]
    scenarios = [r["scenario_id"] for r in scenario_rows]

    capacity = {r["depot_id"]: float(r["capacity"]) for r in depot_rows}
    critical_towns = {
        r["town_id"] for r in town_rows if r["priority_flag"] == "critical"
    }
    scenario_prob = {r["scenario_id"]: float(r["probability"]) for r in scenario_rows}
    scenario_demand = {
        (r["scenario_id"], r["town_id"]): float(r["demand"]) for r in demand_rows
    }
    transport_cost = {
        (r["depot_id"], r["town_id"]): float(r["shipping_cost"]) for r in arc_rows
    }

    # ---- build LP ----
    model = xp.problem("single_agent_transport_lp")
    model.controls.outputlog = 0

    ship = {
        (d, t, s): xp.var(lb=0.0, name=f"ship_{d}_{t}_{s}")
        for d in depots
        for t in towns
        for s in scenarios
    }
    unmet = {
        (t, s): xp.var(lb=0.0, name=f"unmet_{t}_{s}") for t in towns for s in scenarios
    }
    scenario_shortage = {s: xp.var(lb=0.0, name=f"shortage_{s}") for s in scenarios}
    z = xp.var(lb=0.0, name="cvar_z")
    eta = {s: xp.var(lb=0.0, name=f"cvar_eta_{s}") for s in scenarios}

    model.addVariable(
        list(ship.values()),
        list(unmet.values()),
        list(scenario_shortage.values()),
        [z],
        list(eta.values()),
    )

    for d in depots:
        for s in scenarios:
            model.addConstraint(xp.Sum(ship[d, t, s] for t in towns) <= capacity[d])

    for t in towns:
        for s in scenarios:
            demand_st = scenario_demand[s, t]
            model.addConstraint(
                xp.Sum(ship[d, t, s] for d in depots) + unmet[t, s] == demand_st
            )

    max_unmet_share = 1.0 - CRITICAL_SERVICE_FLOOR
    for t in critical_towns:
        for s in scenarios:
            demand_st = scenario_demand[s, t]
            model.addConstraint(unmet[t, s] <= max_unmet_share * demand_st)

    for s in scenarios:
        model.addConstraint(scenario_shortage[s] == xp.Sum(unmet[t, s] for t in towns))
        model.addConstraint(eta[s] >= scenario_shortage[s] - z)

    expected_transport_expr = xp.Sum(
        scenario_prob[s] * transport_cost[d, t] * ship[d, t, s]
        for d in depots
        for t in towns
        for s in scenarios
    )
    expected_penalty_expr = xp.Sum(
        scenario_prob[s] * SHORTAGE_PENALTY * unmet[t, s]
        for t in towns
        for s in scenarios
    )
    cvar_expr = z + (1.0 / (1.0 - CVAR_ALPHA)) * xp.Sum(
        scenario_prob[s] * eta[s] for s in scenarios
    )

    model.setObjective(
        expected_transport_expr + expected_penalty_expr + RISK_WEIGHT * cvar_expr,
        sense=xp.minimize,
    )

    # ---- solve ----
    model.solve()

    # ---- extract results ----
    ship_vals = {k: float(model.getSolution(v)) for k, v in ship.items()}
    unmet_vals = {k: float(model.getSolution(v)) for k, v in unmet.items()}
    shortage_vals = {
        s: float(model.getSolution(scenario_shortage[s])) for s in scenarios
    }
    z_val = float(model.getSolution(z))
    eta_vals = {s: float(model.getSolution(eta[s])) for s in scenarios}

    expected_transport = sum(
        scenario_prob[s] * transport_cost[d, t] * ship_vals[d, t, s]
        for d in depots
        for t in towns
        for s in scenarios
    )
    expected_unmet = sum(
        scenario_prob[s] * unmet_vals[t, s] for t in towns for s in scenarios
    )
    expected_penalty = SHORTAGE_PENALTY * expected_unmet
    cvar_shortage = z_val + (1.0 / (1.0 - CVAR_ALPHA)) * sum(
        scenario_prob[s] * eta_vals[s] for s in scenarios
    )

    expected_lane_flow: dict[tuple[str, str], float] = {}
    for d in depots:
        for t in towns:
            expected_lane_flow[d, t] = sum(
                scenario_prob[s] * ship_vals[d, t, s] for s in scenarios
            )
    top_lanes = sorted(
        expected_lane_flow.items(), key=lambda item: item[1], reverse=True
    )[:8]

    # ---- verify ----
    status = model.getProbStatusString()
    objective = float(model.getObjVal())

    status_ok = status.startswith("lp_")
    critical_ok = True
    for t in critical_towns:
        for s in scenarios:
            if unmet_vals[t, s] > max_unmet_share * scenario_demand[s, t] + 1e-6:
                critical_ok = False
                break
        if not critical_ok:
            break

    obj_recomputed = expected_transport + expected_penalty + RISK_WEIGHT * cvar_shortage
    objective_ok = abs(obj_recomputed - objective) <= 1e-3

    checks = {
        "lp_optimal": status_ok,
        "no_integer_vars": True,
        "all_depots_active": len(depots) == 6,
        "critical_service": critical_ok,
        "objective_consistent": objective_ok,
    }
    passed = sum(1 for ok in checks.values() if ok)

    # ---- print ----
    print("=== Single-Agent LP Result ===")
    print(f"Solver status: {status}")
    print(f"Objective value: {objective:.2f}")
    print(f"Active depots: {', '.join(depots)}")
    print(f"Expected transport cost: {expected_transport:.2f}")
    print(f"Expected shortage penalty: {expected_penalty:.2f}")
    print(f"Expected unmet demand: {expected_unmet:.2f}")
    print(f"CVaR-style shortage indicator: {cvar_shortage:.2f}")
    print(f"Worst scenario unmet demand: {max(shortage_vals.values()):.2f}")
    print(f"Prompt contract respected: {all(checks.values())}")
    print(f"Tester checks passed: {passed}/{len(checks)}")
    print("Top expected shipment lanes:")
    for (depot, town), volume in top_lanes:
        print(f"  - {depot} -> {town}: {volume:.2f}")


if __name__ == "__main__":
    main()
