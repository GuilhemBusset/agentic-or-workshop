"""Disaster-relief transportation LP solved with FICO Xpress.

All depots are active (no facility-location binary variables).
Continuous shipment variables, shortage penalties, CVaR risk term,
and hard 95 % service constraints on critical towns.
"""

import csv
from pathlib import Path

import xpress as xp

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parents[3] / "data"

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
SHORTAGE_PENALTY = 50.0  # per unit of unmet demand
CVAR_ALPHA = 0.95  # confidence level for CVaR
CVAR_LAMBDA = 0.5  # weight of the CVaR term in the objective

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _load_csv(filename: str) -> list[dict[str, str]]:
    with open(DATA_DIR / filename, newline="") as f:
        return list(csv.DictReader(f))


def load_data():
    depots_raw = _load_csv("depots.csv")
    towns_raw = _load_csv("towns.csv")
    arcs_raw = _load_csv("arcs.csv")
    scenarios_raw = _load_csv("scenarios.csv")
    demands_raw = _load_csv("scenario_demands.csv")

    depots = {r["depot_id"]: float(r["capacity"]) for r in depots_raw}
    towns = {r["town_id"]: r for r in towns_raw}
    critical_towns = {
        tid for tid, info in towns.items() if info["priority_flag"] == "critical"
    }
    arc_cost: dict[tuple[str, str], float] = {}
    for r in arcs_raw:
        arc_cost[(r["depot_id"], r["town_id"])] = float(r["shipping_cost"])

    scenarios: dict[str, float] = {}
    for r in scenarios_raw:
        scenarios[r["scenario_id"]] = float(r["probability"])

    demand: dict[tuple[str, str], float] = {}
    for r in demands_raw:
        demand[(r["scenario_id"], r["town_id"])] = float(r["demand"])

    return depots, towns, critical_towns, arc_cost, scenarios, demand


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


def build_and_solve():
    depots, towns, critical_towns, arc_cost, scenarios, demand = load_data()

    depot_ids = sorted(depots)
    town_ids = sorted(towns)
    scenario_ids = sorted(scenarios)

    prob = xp.problem("disaster_relief_lp")
    prob.controls.outputlog = 0  # quiet solver output

    # -- Decision variables ------------------------------------------------

    # x[d,t,s]: shipment from depot d to town t in scenario s
    x: dict[tuple[str, str, str], xp.var] = {}
    for d in depot_ids:
        for t in town_ids:
            for s in scenario_ids:
                x[d, t, s] = prob.addVariable(name=f"x_{d}_{t}_{s}", lb=0)

    # u[t,s]: unmet demand for town t in scenario s
    u: dict[tuple[str, str], xp.var] = {}
    for t in town_ids:
        for s in scenario_ids:
            u[t, s] = prob.addVariable(name=f"u_{t}_{s}", lb=0)

    # CVaR auxiliary variables
    eta = prob.addVariable(name="eta", lb=-xp.infinity)
    z: dict[str, xp.var] = {}
    for s in scenario_ids:
        z[s] = prob.addVariable(name=f"z_{s}", lb=0)

    # -- Constraints -------------------------------------------------------

    # 1. Demand satisfaction: sum_d x[d,t,s] + u[t,s] == demand[s,t]
    for t in town_ids:
        for s in scenario_ids:
            prob.addConstraint(
                xp.Sum(x[d, t, s] for d in depot_ids) + u[t, s] == demand[(s, t)]
            )

    # 2. Depot capacity: sum_t x[d,t,s] <= capacity[d]  for each d, s
    for d in depot_ids:
        for s in scenario_ids:
            prob.addConstraint(
                xp.Sum(x[d, t, s] for t in town_ids) <= depots[d]
            )

    # 3. Critical-town 95 % service: u[t,s] <= 0.05 * demand[s,t]
    for t in critical_towns:
        for s in scenario_ids:
            prob.addConstraint(u[t, s] <= 0.05 * demand[(s, t)])

    # 4. CVaR linearisation: z[s] >= shortage_cost[s] - eta
    for s in scenario_ids:
        shortage_cost_s = xp.Sum(SHORTAGE_PENALTY * u[t, s] for t in town_ids)
        prob.addConstraint(z[s] >= shortage_cost_s - eta)

    # -- Objective ---------------------------------------------------------
    # Expected shipping cost
    expected_shipping = xp.Sum(
        scenarios[s] * arc_cost[(d, t)] * x[d, t, s]
        for d in depot_ids
        for t in town_ids
        for s in scenario_ids
    )

    # Expected shortage penalty
    expected_penalty = xp.Sum(
        scenarios[s] * SHORTAGE_PENALTY * u[t, s]
        for t in town_ids
        for s in scenario_ids
    )

    # CVaR term: eta + 1/(1-alpha) * E[z]
    cvar_term = eta + (1.0 / (1.0 - CVAR_ALPHA)) * xp.Sum(
        scenarios[s] * z[s] for s in scenario_ids
    )

    total_obj = expected_shipping + expected_penalty + CVAR_LAMBDA * cvar_term
    prob.setObjective(total_obj, sense=xp.minimize)

    # -- Solve -------------------------------------------------------------
    prob.lpOptimize()

    solve_status = prob.attributes.solvestatus
    sol_status = prob.attributes.solstatus
    obj_val = prob.attributes.objval

    print("=" * 60)
    print("DISASTER RELIEF TRANSPORTATION LP")
    print("=" * 60)
    print(f"Solver status : solve={solve_status}, solution={sol_status}")
    print(f"Objective     : {obj_val:,.2f}")

    # -- Cost breakdown ----------------------------------------------------
    shipping_val = sum(
        scenarios[s] * arc_cost[(d, t)] * prob.getSolution(x[d, t, s])
        for d in depot_ids
        for t in town_ids
        for s in scenario_ids
    )
    penalty_val = sum(
        scenarios[s] * SHORTAGE_PENALTY * prob.getSolution(u[t, s])
        for t in town_ids
        for s in scenario_ids
    )
    eta_val = prob.getSolution(eta)
    ez_val = sum(scenarios[s] * prob.getSolution(z[s]) for s in scenario_ids)
    cvar_val = eta_val + ez_val / (1.0 - CVAR_ALPHA)

    print()
    print("Cost breakdown")
    print("-" * 40)
    print(f"  Expected shipping cost : {shipping_val:>10,.2f}")
    print(f"  Expected shortage pen. : {penalty_val:>10,.2f}")
    print(f"  CVaR term (weighted)   : {CVAR_LAMBDA * cvar_val:>10,.2f}")
    print(f"  VaR (eta)              : {eta_val:>10,.2f}")
    print(f"  CVaR (unweighted)      : {cvar_val:>10,.2f}")

    # -- Unmet demand summary per scenario ---------------------------------
    print()
    print("Unmet demand by scenario")
    print("-" * 40)
    for s in scenario_ids:
        total_unmet = sum(prob.getSolution(u[t, s]) for t in town_ids)
        print(f"  {s}: {total_unmet:>8.2f}")

    # -- Critical town service check ---------------------------------------
    print()
    print("Critical-town service levels (min across scenarios)")
    print("-" * 40)
    for t in sorted(critical_towns):
        min_service = 1.0
        for s in scenario_ids:
            dem = demand[(s, t)]
            delivered = dem - prob.getSolution(u[t, s])
            service = delivered / dem if dem > 0 else 1.0
            min_service = min(min_service, service)
        print(f"  {t} ({towns[t]['name']:>8s}): {min_service:>6.1%}")

    # -- Top shipment lanes (expected flow) --------------------------------
    lane_flow: dict[tuple[str, str], float] = {}
    for d in depot_ids:
        for t in town_ids:
            total = sum(
                scenarios[s] * prob.getSolution(x[d, t, s]) for s in scenario_ids
            )
            if total > 1e-6:
                lane_flow[(d, t)] = total

    top_lanes = sorted(lane_flow.items(), key=lambda kv: kv[1], reverse=True)[:15]
    print()
    print("Top shipment lanes (expected flow)")
    print("-" * 50)
    print(f"  {'Depot':>6s}  {'Town':>6s}  {'Exp. Flow':>10s}  {'Unit Cost':>10s}")
    for (d, t), flow in top_lanes:
        print(f"  {d:>6s}  {t:>6s}  {flow:>10.2f}  {arc_cost[(d, t)]:>10.2f}")

    # -- Depot utilisation -------------------------------------------------
    print()
    print("Average depot utilisation")
    print("-" * 40)
    for d in depot_ids:
        avg_used = sum(
            scenarios[s] * sum(prob.getSolution(x[d, t, s]) for t in town_ids)
            for s in scenario_ids
        )
        cap = depots[d]
        print(f"  {d}: {avg_used:>7.1f} / {cap:.0f}  ({avg_used / cap:>5.1%})")

    print()
    print("=" * 60)


if __name__ == "__main__":
    build_and_solve()
