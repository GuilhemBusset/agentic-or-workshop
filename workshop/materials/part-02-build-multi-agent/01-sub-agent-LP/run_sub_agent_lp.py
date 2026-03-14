"""Disaster-relief network stochastic LP -- continuous relaxation, all depots active."""

import csv
from pathlib import Path

import xpress as xp

# ── Constants ────────────────────────────────────────────────────────────────
PENALTY = 100.0  # per-unit shortage penalty (>> shipping costs)
ALPHA = 0.95  # CVaR confidence level
LAMBDA = 10.0  # weight on the CVaR term
DATA_DIR = Path(__file__).resolve().parents[3] / "data"


# ── Data loading ─────────────────────────────────────────────────────────────
def load_csv(filename: str) -> list[dict[str, str]]:
    """Read a CSV file from the data directory and return a list of row dicts."""
    filepath = DATA_DIR / filename
    with open(filepath, newline="") as fh:
        return list(csv.DictReader(fh))


def load_data() -> dict:
    """Load all five CSV files and return a structured data dictionary."""
    raw_depots = load_csv("depots.csv")
    raw_towns = load_csv("towns.csv")
    raw_arcs = load_csv("arcs.csv")
    raw_scenarios = load_csv("scenarios.csv")
    raw_demands = load_csv("scenario_demands.csv")

    depots = {
        r["depot_id"]: {
            "name": r["name"],
            "capacity": int(r["capacity"]),
            "fixed_cost": int(r["fixed_cost"]),
        }
        for r in raw_depots
    }

    towns = {
        r["town_id"]: {
            "name": r["name"],
            "base_demand": int(r["base_demand"]),
            "priority_flag": r["priority_flag"],
            "service_min": float(r["service_min"]),
        }
        for r in raw_towns
    }

    arcs = {
        (r["depot_id"], r["town_id"]): {
            "arc_id": r["arc_id"],
            "shipping_cost": float(r["shipping_cost"]),
            "distance": int(r["distance"]),
        }
        for r in raw_arcs
    }

    scenarios = {
        r["scenario_id"]: {
            "description": r["description"],
            "probability": float(r["probability"]),
            "risk_level": r["risk_level"],
        }
        for r in raw_scenarios
    }

    demand = {(r["scenario_id"], r["town_id"]): int(r["demand"]) for r in raw_demands}

    depot_ids = sorted(depots.keys())
    town_ids = sorted(towns.keys())
    scenario_ids = sorted(scenarios.keys())

    return {
        "depots": depots,
        "towns": towns,
        "arcs": arcs,
        "scenarios": scenarios,
        "demand": demand,
        "depot_ids": depot_ids,
        "town_ids": town_ids,
        "scenario_ids": scenario_ids,
    }


# ── Validation ───────────────────────────────────────────────────────────────
def validate_data(data: dict) -> None:
    """Run sanity checks on loaded data and print a summary."""
    depots = data["depots"]
    towns = data["towns"]
    arcs = data["arcs"]
    scenarios = data["scenarios"]
    demand = data["demand"]
    D = data["depot_ids"]
    T = data["town_ids"]
    S = data["scenario_ids"]

    errors: list[str] = []

    # Cardinality checks
    if len(D) != 6:
        errors.append(f"Expected 6 depots, got {len(D)}")
    if len(T) != 12:
        errors.append(f"Expected 12 towns, got {len(T)}")
    if len(arcs) != 72:
        errors.append(f"Expected 72 arcs, got {len(arcs)}")
    if len(S) != 8:
        errors.append(f"Expected 8 scenarios, got {len(S)}")
    if len(demand) != 96:
        errors.append(f"Expected 96 demand rows, got {len(demand)}")

    # Probability check
    prob_sum = sum(scenarios[s]["probability"] for s in S)
    if abs(prob_sum - 1.0) > 1e-9:
        errors.append(f"Scenario probabilities sum to {prob_sum}, expected 1.0")

    # Arc completeness
    for d in D:
        for t in T:
            if (d, t) not in arcs:
                errors.append(f"Missing arc ({d}, {t})")

    # Demand completeness
    for s in S:
        for t in T:
            if (s, t) not in demand:
                errors.append(f"Missing demand for ({s}, {t})")

    # Foreign-key integrity: arcs reference valid depots and towns
    for d, t in arcs:
        if d not in depots:
            errors.append(f"Arc references unknown depot {d}")
        if t not in towns:
            errors.append(f"Arc references unknown town {t}")

    # Foreign-key integrity: demand references valid scenarios and towns
    for s, t in demand:
        if s not in scenarios:
            errors.append(f"Demand references unknown scenario {s}")
        if t not in towns:
            errors.append(f"Demand references unknown town {t}")

    total_capacity = sum(depots[d]["capacity"] for d in D)
    max_demand = max(sum(demand[s, t] for t in T) for s in S)
    critical_towns = [t for t in T if towns[t]["priority_flag"] == "critical"]

    print("=" * 70)
    print("DATA VALIDATION SUMMARY")
    print("=" * 70)
    print(f"  Depots:          {len(D)}")
    print(f"  Towns:           {len(T)} ({len(critical_towns)} critical)")
    print(f"  Arcs:            {len(arcs)}")
    print(f"  Scenarios:       {len(S)}")
    print(f"  Demand rows:     {len(demand)}")
    print(f"  Total capacity:  {total_capacity}")
    print(
        f"  Max total demand:{max_demand:>5} (capacity ratio: {total_capacity / max_demand:.1f}x)"
    )
    print(f"  Prob. sum:       {prob_sum:.4f}")

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")
        raise ValueError("Data validation failed")
    else:
        print("  Status:          ALL CHECKS PASSED")
    print()


# ── Model building ───────────────────────────────────────────────────────────
def build_model(data: dict) -> tuple:
    """
    Build the two-stage stochastic LP and return (problem, variables_dict).

    Decision variables (all continuous):
        x[d,t,s] >= 0  : shipment from depot d to town t in scenario s
        u[t,s]   >= 0  : unmet demand at town t in scenario s
        eta      free  : VaR auxiliary for CVaR
        z[s]     >= 0  : CVaR excess-loss auxiliary per scenario
    """
    D = data["depot_ids"]
    T = data["town_ids"]
    S = data["scenario_ids"]
    depots = data["depots"]
    arcs = data["arcs"]
    scenarios = data["scenarios"]
    demand = data["demand"]
    towns = data["towns"]

    prob = xp.problem("disaster_relief")

    # ── Variables ─────────────────────────────────────────────────────────
    x = {}
    for d in D:
        for t in T:
            for s in S:
                x[d, t, s] = prob.addVariable(name=f"x_{d}_{t}_{s}", lb=0)

    u = {}
    for t in T:
        for s in S:
            u[t, s] = prob.addVariable(name=f"u_{t}_{s}", lb=0)

    eta = prob.addVariable(name="eta", lb=-xp.infinity)

    z = {}
    for s in S:
        z[s] = prob.addVariable(name=f"z_{s}", lb=0)

    n_vars = len(x) + len(u) + 1 + len(z)

    # ── Objective ─────────────────────────────────────────────────────────
    # Fixed cost (constant -- all depots open)
    fixed_cost_total = sum(depots[d]["fixed_cost"] for d in D)

    # Expected transport cost
    transport_expr = xp.Sum(
        scenarios[s]["probability"] * arcs[d, t]["shipping_cost"] * x[d, t, s]
        for d in D
        for t in T
        for s in S
    )

    # Expected shortage penalty
    penalty_expr = xp.Sum(
        scenarios[s]["probability"] * PENALTY * u[t, s] for t in T for s in S
    )

    # CVaR term: LAMBDA * [eta + 1/(1-ALPHA) * sum_s p_s * z_s]
    cvar_expr = LAMBDA * (
        eta
        + (1.0 / (1.0 - ALPHA)) * xp.Sum(scenarios[s]["probability"] * z[s] for s in S)
    )

    prob.setObjective(
        fixed_cost_total + transport_expr + penalty_expr + cvar_expr,
        sense=xp.minimize,
    )

    # ── Constraints ───────────────────────────────────────────────────────

    # 1. Demand satisfaction: sum_d x[d,t,s] + u[t,s] = demand[t,s]
    for t in T:
        for s in S:
            prob.addConstraint(xp.Sum(x[d, t, s] for d in D) + u[t, s] == demand[s, t])

    # 2. Depot capacity: sum_t x[d,t,s] <= capacity[d]
    for d in D:
        for s in S:
            prob.addConstraint(xp.Sum(x[d, t, s] for t in T) <= depots[d]["capacity"])

    # 3. Service level: E[u[t]] <= (1 - service_min) * E[demand[t]]
    #    sum_s p_s * u[t,s] <= (1 - service_min[t]) * sum_s p_s * demand[t,s]
    for t in T:
        smin = towns[t]["service_min"]
        expected_demand = sum(scenarios[s]["probability"] * demand[s, t] for s in S)
        prob.addConstraint(
            xp.Sum(scenarios[s]["probability"] * u[t, s] for s in S)
            <= (1.0 - smin) * expected_demand
        )

    # 4. CVaR linearization: z[s] >= L_s - eta, where L_s = PENALTY * sum_t u[t,s]
    for s in S:
        loss_s = xp.Sum(PENALTY * u[t, s] for t in T)
        prob.addConstraint(z[s] >= loss_s - eta)

    # ── Model statistics ──────────────────────────────────────────────────
    # constraints: 96 demand + 48 capacity + 12 service + 8 CVaR = 164
    n_cons = len(T) * len(S) + len(D) * len(S) + len(T) + len(S)
    print("=" * 70)
    print("MODEL STATISTICS")
    print("=" * 70)
    print(f"  Variables:       {n_vars}")
    print(f"    x[d,t,s]:      {len(x)}")
    print(f"    u[t,s]:        {len(u)}")
    print("    eta:           1")
    print(f"    z[s]:          {len(z)}")
    print(f"  Constraints:     {n_cons}")
    print(f"    Demand sat.:   {len(T) * len(S)}")
    print(f"    Capacity:      {len(D) * len(S)}")
    print(f"    Service level: {len(T)}")
    print(f"    CVaR:          {len(S)}")
    print()

    variables = {"x": x, "u": u, "eta": eta, "z": z}
    return prob, variables


# ── Solution reporting ───────────────────────────────────────────────────────
def report_solution(prob: xp.problem, data: dict, variables: dict) -> None:
    """Extract and display the optimal solution."""
    D = data["depot_ids"]
    T = data["town_ids"]
    S = data["scenario_ids"]
    depots = data["depots"]
    towns = data["towns"]
    scenarios = data["scenarios"]
    demand = data["demand"]
    arcs = data["arcs"]

    x = variables["x"]
    u = variables["u"]
    eta = variables["eta"]
    z = variables["z"]

    sol_status = prob.attributes.solstatus
    lp_status = prob.attributes.lpstatus
    print("=" * 70)
    print("SOLUTION REPORT")
    print("=" * 70)
    print(f"  LP status:       {lp_status}")
    print(f"  Solution status: {sol_status}")

    if sol_status != 1:
        print("  No optimal solution found.")
        return

    obj = prob.attributes.objval

    # Retrieve variable values
    x_val = {k: prob.getSolution(v) for k, v in x.items()}
    u_val = {k: prob.getSolution(v) for k, v in u.items()}
    eta_val = prob.getSolution(eta)
    z_val = {k: prob.getSolution(v) for k, v in z.items()}

    # ── Objective breakdown ───────────────────────────────────────────────
    fixed_cost_total = sum(depots[d]["fixed_cost"] for d in D)

    expected_transport = sum(
        scenarios[s]["probability"] * arcs[d, t]["shipping_cost"] * x_val[d, t, s]
        for d in D
        for t in T
        for s in S
    )

    expected_penalty = sum(
        scenarios[s]["probability"] * PENALTY * u_val[t, s] for t in T for s in S
    )

    cvar_value = LAMBDA * (
        eta_val
        + (1.0 / (1.0 - ALPHA)) * sum(scenarios[s]["probability"] * z_val[s] for s in S)
    )

    print()
    print("  OBJECTIVE BREAKDOWN")
    print("  " + "-" * 50)
    print(f"    Fixed costs (constant):     {fixed_cost_total:>12.2f}")
    print(f"    Expected transport cost:    {expected_transport:>12.2f}")
    print(f"    Expected shortage penalty:  {expected_penalty:>12.2f}")
    print(f"    CVaR term (lambda={LAMBDA}):     {cvar_value:>12.2f}")
    print("    -----------------------------------------------")
    print(f"    Total objective:            {obj:>12.2f}")
    print()

    # ── CVaR / VaR ────────────────────────────────────────────────────────
    print("  RISK MEASURES")
    print("  " + "-" * 50)
    print(f"    VaR (eta) at alpha={ALPHA}:     {eta_val:>12.2f}")
    # CVaR = eta + 1/(1-alpha) * E[z]
    cvar_raw = eta_val + (1.0 / (1.0 - ALPHA)) * sum(
        scenarios[s]["probability"] * z_val[s] for s in S
    )
    print(f"    CVaR at alpha={ALPHA}:          {cvar_raw:>12.2f}")
    print()

    # ── Per-scenario shortage cost ────────────────────────────────────────
    print("  PER-SCENARIO SHORTAGE COST")
    print("  " + "-" * 50)
    for s in S:
        loss_s = sum(PENALTY * u_val[t, s] for t in T)
        print(
            f"    {s} ({scenarios[s]['description']:>14s}):  "
            f"shortage cost = {loss_s:>10.2f}   z = {z_val[s]:>10.2f}"
        )
    print()

    # ── Depot utilization ─────────────────────────────────────────────────
    print("  DEPOT UTILIZATION")
    print("  " + "-" * 50)
    print(
        f"    {'Depot':<6} {'Name':<15} {'Cap':>5}  {'Min%':>6}  {'Avg%':>6}  {'Max%':>6}"
    )
    print("    " + "-" * 48)
    for d in D:
        cap = depots[d]["capacity"]
        usage_by_s = []
        for s in S:
            total_ship = sum(x_val[d, t, s] for t in T)
            usage_by_s.append(total_ship)
        min_u = min(usage_by_s)
        max_u = max(usage_by_s)
        avg_u = sum(usage_by_s) / len(usage_by_s)
        print(
            f"    {d:<6} {depots[d]['name']:<15} {cap:>5}  "
            f"{100.0 * min_u / cap:>5.1f}%  "
            f"{100.0 * avg_u / cap:>5.1f}%  "
            f"{100.0 * max_u / cap:>5.1f}%"
        )
    print()

    # ── Service levels per town ───────────────────────────────────────────
    print("  SERVICE LEVELS (expected fraction of demand met)")
    print("  " + "-" * 50)
    print(
        f"    {'Town':<6} {'Name':<10} {'Type':<10} {'Req':>5}  "
        f"{'Achieved':>8}  {'Status':<6}"
    )
    print("    " + "-" * 52)

    all_compliant = True
    for t in T:
        exp_demand = sum(scenarios[s]["probability"] * demand[s, t] for s in S)
        exp_unmet = sum(scenarios[s]["probability"] * u_val[t, s] for s in S)
        if exp_demand > 1e-12:
            service_achieved = 1.0 - exp_unmet / exp_demand
        else:
            service_achieved = 1.0
        service_req = towns[t]["service_min"]
        ok = service_achieved >= service_req - 1e-6
        if not ok:
            all_compliant = False
        flag = towns[t]["priority_flag"]
        status_str = "OK" if ok else "FAIL"
        print(
            f"    {t:<6} {towns[t]['name']:<10} {flag:<10} "
            f"{100.0 * service_req:>4.0f}%  "
            f"{100.0 * service_achieved:>7.2f}%  {status_str}"
        )
    print()
    if all_compliant:
        print("    All service level constraints satisfied.")
    else:
        print("    WARNING: Some service level constraints are violated!")
    print()

    # ── Unmet demand summary ──────────────────────────────────────────────
    print("  UNMET DEMAND SUMMARY (units)")
    print("  " + "-" * 50)
    header = f"    {'Town':<6}"
    for s in S:
        header += f" {s:>7}"
    header += f" {'E[unmet]':>9}"
    print(header)
    print("    " + "-" * (6 + 8 * len(S) + 10))

    total_exp_unmet = 0.0
    for t in T:
        row = f"    {t:<6}"
        exp_u = 0.0
        for s in S:
            val = u_val[t, s]
            exp_u += scenarios[s]["probability"] * val
            row += f" {val:>7.2f}"
        row += f" {exp_u:>9.4f}"
        total_exp_unmet += exp_u
        print(row)
    print()
    print(f"    Total expected unmet demand: {total_exp_unmet:.4f}")
    print()

    # ── Total expected cost (excl. fixed) per scenario ────────────────────
    print("  PER-SCENARIO TOTAL COST (transport + shortage)")
    print("  " + "-" * 50)
    for s in S:
        transport_s = sum(
            arcs[d, t]["shipping_cost"] * x_val[d, t, s] for d in D for t in T
        )
        shortage_s = sum(PENALTY * u_val[t, s] for t in T)
        total_s = transport_s + shortage_s
        print(
            f"    {s} ({scenarios[s]['description']:>14s}):  "
            f"transport={transport_s:>9.2f}  "
            f"shortage={shortage_s:>9.2f}  "
            f"total={total_s:>10.2f}"
        )
    print()
    print("=" * 70)


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    data = load_data()
    validate_data(data)
    prob, variables = build_model(data)
    prob.solve()
    report_solution(prob, data, variables)


if __name__ == "__main__":
    main()
