"""Disaster-relief transportation MILP solver.

Decides which depots to open, routes shipments to towns under 8 demand
scenarios, and minimizes:
    fixed opening cost
  + expected transport cost
  + shortage penalties
  + CVaR shortage risk term

Critical towns (T03, T04, T07, T12) must receive >= 95% of demand in every
scenario.

Outputs a JSON object with solver_status, objective, open_depots,
critical_town_service, and harness_checks_passed.
"""

import csv
import json
import math
from pathlib import Path

import xpress as xp

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
SHORTAGE_PENALTY = 50.0  # per unit of unmet demand
CVAR_ALPHA = 0.95  # confidence level for CVaR
CVAR_WEIGHT = 10.0  # weight on CVaR term in objective

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def _load_csv(filename: str) -> list[dict[str, str]]:
    with open(DATA_DIR / filename, newline="") as f:
        return list(csv.DictReader(f))


def load_data() -> dict:
    depots = _load_csv("depots.csv")
    towns = _load_csv("towns.csv")
    arcs = _load_csv("arcs.csv")
    scenarios = _load_csv("scenarios.csv")
    scenario_demands = _load_csv("scenario_demands.csv")

    # Parse into convenient structures
    depot_ids = [d["depot_id"] for d in depots]
    town_ids = [t["town_id"] for t in towns]
    scenario_ids = [s["scenario_id"] for s in scenarios]

    capacity = {d["depot_id"]: float(d["capacity"]) for d in depots}
    fixed_cost = {d["depot_id"]: float(d["fixed_cost"]) for d in depots}
    service_min = {t["town_id"]: float(t["service_min"]) for t in towns}
    priority = {t["town_id"]: t["priority_flag"] for t in towns}
    shipping_cost = {
        (a["depot_id"], a["town_id"]): float(a["shipping_cost"]) for a in arcs
    }
    probability = {s["scenario_id"]: float(s["probability"]) for s in scenarios}
    demand = {
        (sd["scenario_id"], sd["town_id"]): float(sd["demand"])
        for sd in scenario_demands
    }

    return {
        "depots": depot_ids,
        "towns": town_ids,
        "scenarios": scenario_ids,
        "capacity": capacity,
        "fixed_cost": fixed_cost,
        "service_min": service_min,
        "priority": priority,
        "shipping_cost": shipping_cost,
        "probability": probability,
        "demand": demand,
    }


# ---------------------------------------------------------------------------
# Model building
# ---------------------------------------------------------------------------
def build_model(data: dict) -> dict:
    depots = data["depots"]
    towns = data["towns"]
    scenarios = data["scenarios"]
    capacity = data["capacity"]
    fixed_cost = data["fixed_cost"]
    service_min = data["service_min"]
    shipping_cost = data["shipping_cost"]
    probability = data["probability"]
    demand = data["demand"]

    prob = xp.problem("disaster_relief_milp")
    prob.controls.outputlog = 0  # suppress solver log
    prob.controls.miprelstop = 1e-4  # relative MIP gap tolerance

    # --- Decision variables ---
    # y[d]: binary, 1 if depot d is open
    y = {}
    for d in depots:
        y[d] = xp.var(name=f"y_{d}", vartype=xp.binary)

    # x[d, t, s]: continuous, shipment from depot d to town t in scenario s
    x = {}
    for s in scenarios:
        for d in depots:
            for t in towns:
                x[d, t, s] = xp.var(name=f"x_{d}_{t}_{s}", lb=0.0)

    # u[t, s]: continuous, unmet demand at town t in scenario s
    u = {}
    for s in scenarios:
        for t in towns:
            u[t, s] = xp.var(name=f"u_{t}_{s}", lb=0.0)

    # CVaR variables
    eta = xp.var(name="eta", lb=-1e10)  # VaR threshold (free variable)
    z = {}  # excess shortage above eta per scenario
    for s in scenarios:
        z[s] = xp.var(name=f"z_{s}", lb=0.0)

    # Add all variables to model
    all_vars = list(y.values()) + list(x.values()) + list(u.values()) + [eta] + list(z.values())
    prob.addVariable(*all_vars)

    # --- Constraints ---

    # 1. Capacity: sum_t x[d,t,s] <= capacity[d] * y[d]  for all d, s
    capacity_constrs = []
    for d in depots:
        for s in scenarios:
            constr = xp.Sum(x[d, t, s] for t in towns) <= capacity[d] * y[d]
            capacity_constrs.append(constr)
    prob.addConstraint(*capacity_constrs)

    # 2. Demand balance: sum_d x[d,t,s] + u[t,s] = demand[t,s]  for all t, s
    demand_constrs = []
    for t in towns:
        for s in scenarios:
            d_ts = demand[s, t]
            constr = xp.Sum(x[d, t, s] for d in depots) + u[t, s] == d_ts
            demand_constrs.append(constr)
    prob.addConstraint(*demand_constrs)

    # 3. Critical service: u[t,s] <= (1 - service_min[t]) * demand[t,s]
    #    for critical towns in every scenario
    service_constrs = []
    for t in towns:
        if service_min[t] > 0.90:  # critical towns
            for s in scenarios:
                d_ts = demand[s, t]
                max_shortage = (1.0 - service_min[t]) * d_ts
                constr = u[t, s] <= max_shortage
                service_constrs.append(constr)
    prob.addConstraint(*service_constrs)

    # 4. CVaR: z[s] >= sum_t u[t,s] - eta  for all s
    cvar_constrs = []
    for s in scenarios:
        constr = z[s] >= xp.Sum(u[t, s] for t in towns) - eta
        cvar_constrs.append(constr)
    prob.addConstraint(*cvar_constrs)

    # --- Objective ---
    # Fixed cost
    obj_fixed = xp.Sum(fixed_cost[d] * y[d] for d in depots)

    # Expected transport cost
    obj_transport = xp.Sum(
        probability[s] * shipping_cost[d, t] * x[d, t, s]
        for s in scenarios
        for d in depots
        for t in towns
    )

    # Expected shortage penalty
    obj_shortage = xp.Sum(
        probability[s] * SHORTAGE_PENALTY * u[t, s]
        for s in scenarios
        for t in towns
    )

    # CVaR term: weight * (eta + 1/(1-alpha) * E[z])
    obj_cvar = CVAR_WEIGHT * (
        eta + (1.0 / (1.0 - CVAR_ALPHA)) * xp.Sum(probability[s] * z[s] for s in scenarios)
    )

    prob.setObjective(obj_fixed + obj_transport + obj_shortage + obj_cvar, sense=xp.minimize)

    return {
        "prob": prob,
        "y": y,
        "x": x,
        "u": u,
        "eta": eta,
        "z": z,
        "capacity_constrs": capacity_constrs,
    }


# ---------------------------------------------------------------------------
# Solve and extract results
# ---------------------------------------------------------------------------
def solve(artifacts: dict, data: dict) -> dict:
    prob = artifacts["prob"]
    y = artifacts["y"]
    x = artifacts["x"]
    u = artifacts["u"]

    prob.solve()

    # Map xpress solve status
    mip_status = prob.attributes.mipstatus
    status_map = {
        0: "not_started",
        1: "lp_optimal",
        2: "lp_infeasible",
        3: "no_integer_found",
        4: "mip_infeasible",
        5: "mip_optimal",
        6: "mip_solution",
    }
    solver_status = status_map.get(mip_status, f"unknown_{mip_status}")

    objective = prob.attributes.mipobjval

    # Open depots
    open_depots = [d for d in data["depots"] if prob.getSolution(y[d]) > 0.5]

    # Critical town service levels
    critical_town_service = {}
    critical_towns = {t for t in data["towns"] if data["service_min"][t] > 0.90}
    for t in critical_towns:
        ratios = []
        for s in data["scenarios"]:
            d_ts = data["demand"][s, t]
            shortage = prob.getSolution(u[t, s])
            served = d_ts - shortage
            ratio = served / d_ts if d_ts > 0 else 1.0
            ratios.append(ratio)
        critical_town_service[t] = {
            "min_ratio": min(ratios),
            "avg_ratio": sum(ratios) / len(ratios),
        }

    return {
        "solver_status": solver_status,
        "objective": round(objective, 2),
        "open_depots": sorted(open_depots),
        "critical_town_service": critical_town_service,
    }


# ---------------------------------------------------------------------------
# Harness checks
# ---------------------------------------------------------------------------
def run_harness_checks(result: dict, data: dict) -> bool:
    checks = []

    # 1. Solver found optimal solution
    checks.append(result["solver_status"] in ("mip_optimal", "lp_optimal", "optimal", "mip_solution"))

    # 2. Objective is finite and positive
    obj = result["objective"]
    checks.append(isinstance(obj, (int, float)) and math.isfinite(obj) and obj > 0)

    # 3. At least one depot is open
    checks.append(len(result["open_depots"]) > 0)

    # 4. Open depots are valid IDs
    valid_ids = set(data["depots"])
    checks.append(all(d in valid_ids for d in result["open_depots"]))

    # 5. Critical towns meet 95% service level
    critical_towns = {t for t in data["towns"] if data["service_min"][t] > 0.90}
    for t in critical_towns:
        svc = result["critical_town_service"].get(t)
        if svc is None:
            checks.append(False)
        else:
            checks.append(svc["min_ratio"] >= 0.95 - 1e-6)

    return all(checks)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    data = load_data()
    artifacts = build_model(data)
    result = solve(artifacts, data)
    passed = run_harness_checks(result, data)
    result["harness_checks_passed"] = passed
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
