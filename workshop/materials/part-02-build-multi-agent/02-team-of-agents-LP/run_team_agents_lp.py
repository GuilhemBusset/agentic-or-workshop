from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import xpress as xp

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parents[3] / "data"
PENALTY = 1000.0
BOTTLENECK_THRESHOLD = 0.90
_SEP = "-" * 72
_BANNER = "=" * 72

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Depot:
    depot_id: str
    name: str
    capacity: int
    fixed_cost: int


@dataclass(frozen=True)
class Town:
    town_id: str
    name: str
    base_demand: int
    priority_flag: str
    service_min: float


@dataclass(frozen=True)
class Arc:
    arc_id: str
    depot_id: str
    town_id: str
    shipping_cost: float
    distance: int


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    description: str
    probability: float
    risk_level: str


@dataclass
class ProblemData:
    depots: list[Depot]
    towns: list[Town]
    arcs: list[Arc]
    scenarios: list[Scenario]
    scenario_demands: dict[tuple[str, str], int]
    depot_ids: list[str]
    town_ids: list[str]
    scenario_ids: list[str]
    critical_town_ids: set[str]
    capacity: dict[str, int]
    fixed_cost: dict[str, int]
    depot_name: dict[str, str]
    town_name: dict[str, str]
    service_min: dict[str, float]
    scenario_prob: dict[str, float]
    scenario_desc: dict[str, str]
    shipping_cost: dict[tuple[str, str], float]
    arc_distance: dict[tuple[str, str], int]
    total_capacity: int
    validation_warnings: list[str]


@dataclass
class ModelArtifacts:
    model: xp.problem
    ship: dict[tuple[str, str, str], xp.var]
    unmet: dict[tuple[str, str], xp.var]
    capacity_ctrs: dict[tuple[str, str], xp.constraint]
    demand_ctrs: dict[tuple[str, str], xp.constraint]
    service_ctrs: dict[tuple[str, str], xp.constraint]


@dataclass(frozen=True)
class Solution:
    status: str
    objective: float
    ship_vals: dict[tuple[str, str, str], float]
    unmet_vals: dict[tuple[str, str], float]
    capacity_duals: dict[tuple[str, str], float]
    demand_duals: dict[tuple[str, str], float]
    service_duals: dict[tuple[str, str], float]
    num_variables: int
    num_constraints: int


@dataclass(frozen=True)
class CostBreakdown:
    total_fixed_cost: int
    expected_shipping_cost: float
    expected_penalty_cost: float
    expected_total_unmet: float
    per_scenario_shipping: dict[str, float]
    per_scenario_penalty: dict[str, float]
    per_scenario_total: dict[str, float]
    per_scenario_unmet: dict[str, float]
    worst_cost_scenario: str
    worst_unmet_scenario: str


@dataclass(frozen=True)
class DepotProfile:
    depot_id: str
    name: str
    capacity: int
    avg_utilization: float
    max_utilization: float
    max_utilization_scenario: str
    per_scenario_utilization: dict[str, float]
    is_bottleneck: bool


@dataclass(frozen=True)
class TownProfile:
    town_id: str
    name: str
    is_critical: bool
    demand_min: int
    demand_max: int
    demand_mean: float
    expected_unmet: float
    worst_unmet: float
    worst_unmet_scenario: str
    service_rate_by_scenario: dict[str, float]
    dominant_depot: str
    dominant_share: float
    is_single_source: bool


@dataclass(frozen=True)
class AuditResult:
    checks: dict[str, bool]
    warnings: list[str]
    passed_count: int
    total_count: int
    all_passed: bool


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def load_data() -> ProblemData:
    """Read all CSV files from DATA_DIR and build ProblemData."""
    # Read depots
    depots: list[Depot] = []
    with open(DATA_DIR / "depots.csv", newline="") as f:
        for row in csv.DictReader(f):
            depots.append(
                Depot(
                    depot_id=row["depot_id"],
                    name=row["name"],
                    capacity=int(row["capacity"]),
                    fixed_cost=int(row["fixed_cost"]),
                )
            )

    # Read towns
    towns: list[Town] = []
    with open(DATA_DIR / "towns.csv", newline="") as f:
        for row in csv.DictReader(f):
            towns.append(
                Town(
                    town_id=row["town_id"],
                    name=row["name"],
                    base_demand=int(row["base_demand"]),
                    priority_flag=row["priority_flag"],
                    service_min=float(row["service_min"]),
                )
            )

    # Read arcs
    arcs: list[Arc] = []
    with open(DATA_DIR / "arcs.csv", newline="") as f:
        for row in csv.DictReader(f):
            arcs.append(
                Arc(
                    arc_id=row["arc_id"],
                    depot_id=row["depot_id"],
                    town_id=row["town_id"],
                    shipping_cost=float(row["shipping_cost"]),
                    distance=int(row["distance"]),
                )
            )

    # Read scenarios
    scenarios: list[Scenario] = []
    with open(DATA_DIR / "scenarios.csv", newline="") as f:
        for row in csv.DictReader(f):
            scenarios.append(
                Scenario(
                    scenario_id=row["scenario_id"],
                    description=row["description"],
                    probability=float(row["probability"]),
                    risk_level=row["risk_level"],
                )
            )

    # Read scenario demands
    scenario_demands: dict[tuple[str, str], int] = {}
    with open(DATA_DIR / "scenario_demands.csv", newline="") as f:
        for row in csv.DictReader(f):
            scenario_demands[(row["scenario_id"], row["town_id"])] = int(
                row["demand"]
            )

    # Build lookup dicts
    depot_ids = [d.depot_id for d in depots]
    town_ids = [t.town_id for t in towns]
    scenario_ids = [s.scenario_id for s in scenarios]
    critical_town_ids = {t.town_id for t in towns if t.priority_flag == "critical"}
    capacity = {d.depot_id: d.capacity for d in depots}
    fixed_cost = {d.depot_id: d.fixed_cost for d in depots}
    depot_name = {d.depot_id: d.name for d in depots}
    town_name = {t.town_id: t.name for t in towns}
    service_min = {t.town_id: t.service_min for t in towns}
    scenario_prob = {s.scenario_id: s.probability for s in scenarios}
    scenario_desc = {s.scenario_id: s.description for s in scenarios}
    shipping_cost = {(a.depot_id, a.town_id): a.shipping_cost for a in arcs}
    arc_distance = {(a.depot_id, a.town_id): a.distance for a in arcs}
    total_capacity = sum(d.capacity for d in depots)

    # Validation
    warnings: list[str] = []

    # 1. All depot x town pairs have arcs
    for d in depot_ids:
        for t in town_ids:
            if (d, t) not in shipping_cost:
                warnings.append(f"Missing arc for depot {d} -> town {t}")

    # 2. Probabilities sum to 1.0
    prob_sum = sum(scenario_prob.values())
    if abs(prob_sum - 1.0) > 1e-6:
        warnings.append(
            f"Scenario probabilities sum to {prob_sum:.6f}, expected 1.0"
        )

    # 3. All scenario x town pairs have demands
    for s in scenario_ids:
        for t in town_ids:
            if (s, t) not in scenario_demands:
                warnings.append(
                    f"Missing demand for scenario {s}, town {t}"
                )

    # 4. All capacities positive, all demands non-negative
    for d in depots:
        if d.capacity <= 0:
            warnings.append(
                f"Depot {d.depot_id} has non-positive capacity {d.capacity}"
            )
    for key, dem in scenario_demands.items():
        if dem < 0:
            warnings.append(
                f"Negative demand {dem} for scenario {key[0]}, town {key[1]}"
            )

    return ProblemData(
        depots=depots,
        towns=towns,
        arcs=arcs,
        scenarios=scenarios,
        scenario_demands=scenario_demands,
        depot_ids=depot_ids,
        town_ids=town_ids,
        scenario_ids=scenario_ids,
        critical_town_ids=critical_town_ids,
        capacity=capacity,
        fixed_cost=fixed_cost,
        depot_name=depot_name,
        town_name=town_name,
        service_min=service_min,
        scenario_prob=scenario_prob,
        scenario_desc=scenario_desc,
        shipping_cost=shipping_cost,
        arc_distance=arc_distance,
        total_capacity=total_capacity,
        validation_warnings=warnings,
    )


def build_model(data: ProblemData) -> ModelArtifacts:
    """Build the xpress LP model."""
    model = xp.problem(name="disaster_relief_lp")

    # --- Variables ---
    ship: dict[tuple[str, str, str], xp.var] = {}
    unmet: dict[tuple[str, str], xp.var] = {}

    for d in data.depot_ids:
        for t in data.town_ids:
            for s in data.scenario_ids:
                v = model.addVariable(name=f"ship_{d}_{t}_{s}", lb=0)
                ship[(d, t, s)] = v

    for t in data.town_ids:
        for s in data.scenario_ids:
            v = model.addVariable(name=f"unmet_{t}_{s}", lb=0)
            unmet[(t, s)] = v

    # --- Constraints ---
    capacity_ctrs: dict[tuple[str, str], xp.constraint] = {}
    demand_ctrs: dict[tuple[str, str], xp.constraint] = {}
    service_ctrs: dict[tuple[str, str], xp.constraint] = {}

    # Capacity constraints: sum_t ship[d,t,s] <= capacity[d]  for all d, s
    for d in data.depot_ids:
        for s in data.scenario_ids:
            expr = xp.Sum(ship[(d, t, s)] for t in data.town_ids)
            ctr = xp.constraint(
                constraint=expr <= data.capacity[d],
                name=f"cap_{d}_{s}",
            )
            model.addConstraint(ctr)
            capacity_ctrs[(d, s)] = ctr

    # Demand constraints: sum_d ship[d,t,s] + unmet[t,s] == demand[s,t]
    for t in data.town_ids:
        for s in data.scenario_ids:
            dem = data.scenario_demands[(s, t)]
            expr = (
                xp.Sum(ship[(d, t, s)] for d in data.depot_ids) + unmet[(t, s)]
            )
            ctr = xp.constraint(
                constraint=expr == dem,
                name=f"dem_{t}_{s}",
            )
            model.addConstraint(ctr)
            demand_ctrs[(t, s)] = ctr

    # Service constraints: unmet[t,s] <= (1 - service_min[t]) * demand[s,t]
    # for critical towns only
    for t in sorted(data.critical_town_ids):
        for s in data.scenario_ids:
            dem = data.scenario_demands[(s, t)]
            max_unmet = (1.0 - data.service_min[t]) * dem
            ctr = xp.constraint(
                constraint=unmet[(t, s)] <= max_unmet,
                name=f"svc_{t}_{s}",
            )
            model.addConstraint(ctr)
            service_ctrs[(t, s)] = ctr

    # --- Objective ---
    fixed_part = xp.Sum(data.fixed_cost[d] for d in data.depot_ids)
    stochastic_part = xp.Sum(
        data.scenario_prob[s]
        * (
            xp.Sum(
                data.shipping_cost[(d, t)] * ship[(d, t, s)]
                for d in data.depot_ids
                for t in data.town_ids
            )
            + xp.Sum(PENALTY * unmet[(t, s)] for t in data.town_ids)
        )
        for s in data.scenario_ids
    )
    model.setObjective(fixed_part + stochastic_part, sense=xp.minimize)

    model.controls.outputlog = 0

    return ModelArtifacts(
        model=model,
        ship=ship,
        unmet=unmet,
        capacity_ctrs=capacity_ctrs,
        demand_ctrs=demand_ctrs,
        service_ctrs=service_ctrs,
    )


def solve_and_extract(data: ProblemData, artifacts: ModelArtifacts) -> Solution:
    """Solve the LP and extract solution values and duals."""
    model = artifacts.model
    model.solve()

    status = model.getProbStatusString()
    objective = model.getObjVal()
    num_variables = model.attributes.cols
    num_constraints = model.attributes.rows

    # Extract primal values
    ship_vals: dict[tuple[str, str, str], float] = {}
    for key, var in artifacts.ship.items():
        ship_vals[key] = model.getSolution(var)

    unmet_vals: dict[tuple[str, str], float] = {}
    for key, var in artifacts.unmet.items():
        unmet_vals[key] = model.getSolution(var)

    # Extract dual values
    capacity_duals: dict[tuple[str, str], float] = {}
    for key, ctr in artifacts.capacity_ctrs.items():
        capacity_duals[key] = model.getDuals(ctr)

    demand_duals: dict[tuple[str, str], float] = {}
    for key, ctr in artifacts.demand_ctrs.items():
        demand_duals[key] = model.getDuals(ctr)

    service_duals: dict[tuple[str, str], float] = {}
    for key, ctr in artifacts.service_ctrs.items():
        service_duals[key] = model.getDuals(ctr)

    return Solution(
        status=status,
        objective=objective,
        ship_vals=ship_vals,
        unmet_vals=unmet_vals,
        capacity_duals=capacity_duals,
        demand_duals=demand_duals,
        service_duals=service_duals,
        num_variables=num_variables,
        num_constraints=num_constraints,
    )


def compute_cost_breakdown(data: ProblemData, sol: Solution) -> CostBreakdown:
    """Decompose objective into fixed, shipping, penalty components."""
    total_fixed_cost = sum(data.fixed_cost[d] for d in data.depot_ids)

    per_scenario_shipping: dict[str, float] = {}
    per_scenario_penalty: dict[str, float] = {}
    per_scenario_total: dict[str, float] = {}
    per_scenario_unmet: dict[str, float] = {}

    for s in data.scenario_ids:
        ship_cost = sum(
            data.shipping_cost[(d, t)] * sol.ship_vals[(d, t, s)]
            for d in data.depot_ids
            for t in data.town_ids
        )
        pen_cost = sum(
            PENALTY * sol.unmet_vals[(t, s)] for t in data.town_ids
        )
        total_unmet = sum(sol.unmet_vals[(t, s)] for t in data.town_ids)

        per_scenario_shipping[s] = ship_cost
        per_scenario_penalty[s] = pen_cost
        per_scenario_total[s] = ship_cost + pen_cost
        per_scenario_unmet[s] = total_unmet

    expected_shipping_cost = sum(
        data.scenario_prob[s] * per_scenario_shipping[s] for s in data.scenario_ids
    )
    expected_penalty_cost = sum(
        data.scenario_prob[s] * per_scenario_penalty[s] for s in data.scenario_ids
    )
    expected_total_unmet = sum(
        data.scenario_prob[s] * per_scenario_unmet[s] for s in data.scenario_ids
    )

    worst_cost_scenario = max(data.scenario_ids, key=lambda s: per_scenario_total[s])
    worst_unmet_scenario = max(
        data.scenario_ids, key=lambda s: per_scenario_unmet[s]
    )

    return CostBreakdown(
        total_fixed_cost=total_fixed_cost,
        expected_shipping_cost=expected_shipping_cost,
        expected_penalty_cost=expected_penalty_cost,
        expected_total_unmet=expected_total_unmet,
        per_scenario_shipping=per_scenario_shipping,
        per_scenario_penalty=per_scenario_penalty,
        per_scenario_total=per_scenario_total,
        per_scenario_unmet=per_scenario_unmet,
        worst_cost_scenario=worst_cost_scenario,
        worst_unmet_scenario=worst_unmet_scenario,
    )


def profile_depots(data: ProblemData, sol: Solution) -> list[DepotProfile]:
    """Compute utilization for each depot. Sort by avg_utilization descending."""
    profiles: list[DepotProfile] = []

    for d in data.depot_ids:
        cap = data.capacity[d]
        per_scenario_util: dict[str, float] = {}

        for s in data.scenario_ids:
            total_shipped = sum(
                sol.ship_vals[(d, t, s)] for t in data.town_ids
            )
            per_scenario_util[s] = total_shipped / cap if cap > 0 else 0.0

        avg_util = sum(per_scenario_util.values()) / len(data.scenario_ids)
        max_util_scenario = max(
            data.scenario_ids, key=lambda s: per_scenario_util[s]
        )
        max_util = per_scenario_util[max_util_scenario]

        profiles.append(
            DepotProfile(
                depot_id=d,
                name=data.depot_name[d],
                capacity=cap,
                avg_utilization=avg_util,
                max_utilization=max_util,
                max_utilization_scenario=max_util_scenario,
                per_scenario_utilization=per_scenario_util,
                is_bottleneck=max_util >= BOTTLENECK_THRESHOLD,
            )
        )

    profiles.sort(key=lambda p: p.avg_utilization, reverse=True)
    return profiles


def profile_towns(data: ProblemData, sol: Solution) -> list[TownProfile]:
    """Compute service and sourcing profile. Return in original town_ids order."""
    profiles: list[TownProfile] = []

    for t in data.town_ids:
        is_critical = t in data.critical_town_ids
        demands = [data.scenario_demands[(s, t)] for s in data.scenario_ids]
        demand_min = min(demands)
        demand_max = max(demands)
        demand_mean = sum(demands) / len(demands)

        # Unmet per scenario
        unmet_by_scenario = {
            s: sol.unmet_vals[(t, s)] for s in data.scenario_ids
        }
        expected_unmet = sum(
            data.scenario_prob[s] * unmet_by_scenario[s]
            for s in data.scenario_ids
        )
        worst_unmet_scenario = max(
            data.scenario_ids, key=lambda s: unmet_by_scenario[s]
        )
        worst_unmet = unmet_by_scenario[worst_unmet_scenario]

        # Service rate by scenario
        service_rate_by_scenario: dict[str, float] = {}
        for s in data.scenario_ids:
            dem = data.scenario_demands[(s, t)]
            if dem > 0:
                service_rate_by_scenario[s] = (
                    1.0 - unmet_by_scenario[s] / dem
                )
            else:
                service_rate_by_scenario[s] = 1.0

        # Dominant depot: expected flow share
        depot_expected_flow: dict[str, float] = {}
        total_expected_flow = 0.0
        for d in data.depot_ids:
            exp_flow = sum(
                data.scenario_prob[s] * sol.ship_vals[(d, t, s)]
                for s in data.scenario_ids
            )
            depot_expected_flow[d] = exp_flow
            total_expected_flow += exp_flow

        dominant_depot = max(
            data.depot_ids, key=lambda d: depot_expected_flow[d]
        )
        dominant_share = (
            depot_expected_flow[dominant_depot] / total_expected_flow
            if total_expected_flow > 0
            else 0.0
        )

        is_single_source = dominant_share >= BOTTLENECK_THRESHOLD

        profiles.append(
            TownProfile(
                town_id=t,
                name=data.town_name[t],
                is_critical=is_critical,
                demand_min=demand_min,
                demand_max=demand_max,
                demand_mean=demand_mean,
                expected_unmet=expected_unmet,
                worst_unmet=worst_unmet,
                worst_unmet_scenario=worst_unmet_scenario,
                service_rate_by_scenario=service_rate_by_scenario,
                dominant_depot=dominant_depot,
                dominant_share=dominant_share,
                is_single_source=is_single_source,
            )
        )

    return profiles


def audit_solution(
    data: ProblemData, sol: Solution, costs: CostBreakdown
) -> AuditResult:
    """Verify solution correctness."""
    checks: dict[str, bool] = {}
    warnings: list[str] = []

    # 1. LP optimal status
    is_optimal = "optimal" in sol.status.lower()
    checks["lp_optimal_status"] = is_optimal
    if not is_optimal:
        warnings.append(f"LP status is '{sol.status}', expected optimal")

    # 2. All depots active
    all_active = True
    for d in data.depot_ids:
        total = sum(
            sol.ship_vals[(d, t, s)]
            for t in data.town_ids
            for s in data.scenario_ids
        )
        if total < 1e-6:
            all_active = False
            warnings.append(f"Depot {d} has zero total shipments")
    checks["all_depots_active"] = all_active

    # 3. Critical service met
    critical_ok = True
    for t in sorted(data.critical_town_ids):
        for s in data.scenario_ids:
            dem = data.scenario_demands[(s, t)]
            max_unmet = (1.0 - data.service_min[t]) * dem
            if sol.unmet_vals[(t, s)] > max_unmet + 1e-6:
                critical_ok = False
                warnings.append(
                    f"Service violation: town {t}, scenario {s}: "
                    f"unmet={sol.unmet_vals[(t, s)]:.4f} > max={max_unmet:.4f}"
                )
    checks["critical_service_met"] = critical_ok

    # 4. Demand balance
    demand_ok = True
    for t in data.town_ids:
        for s in data.scenario_ids:
            dem = data.scenario_demands[(s, t)]
            supplied = sum(
                sol.ship_vals[(d, t, s)] for d in data.depot_ids
            )
            balance = supplied + sol.unmet_vals[(t, s)]
            if abs(balance - dem) > 1e-4:
                demand_ok = False
                warnings.append(
                    f"Demand imbalance: town {t}, scenario {s}: "
                    f"supply+unmet={balance:.4f} != demand={dem}"
                )
    checks["demand_balance_verified"] = demand_ok

    # 5. Capacity respected
    capacity_ok = True
    for d in data.depot_ids:
        for s in data.scenario_ids:
            total = sum(
                sol.ship_vals[(d, t, s)] for t in data.town_ids
            )
            if total > data.capacity[d] + 1e-4:
                capacity_ok = False
                warnings.append(
                    f"Capacity exceeded: depot {d}, scenario {s}: "
                    f"shipped={total:.4f} > cap={data.capacity[d]}"
                )
    checks["capacity_respected"] = capacity_ok

    # 6. Objective decomposition consistent
    recomputed = (
        costs.total_fixed_cost
        + costs.expected_shipping_cost
        + costs.expected_penalty_cost
    )
    obj_ok = abs(recomputed - sol.objective) < 1e-2
    checks["objective_decomposition_consistent"] = obj_ok
    if not obj_ok:
        warnings.append(
            f"Objective mismatch: recomputed={recomputed:.4f} "
            f"vs solver={sol.objective:.4f}"
        )

    passed_count = sum(1 for v in checks.values() if v)
    total_count = len(checks)

    return AuditResult(
        checks=checks,
        warnings=warnings,
        passed_count=passed_count,
        total_count=total_count,
        all_passed=passed_count == total_count,
    )


def print_report(
    data: ProblemData,
    sol: Solution,
    costs: CostBreakdown,
    depot_profiles: list[DepotProfile],
    town_profiles: list[TownProfile],
    audit: AuditResult,
) -> None:
    """Print the full LP solution report."""

    print(_BANNER)
    print("  DISASTER RELIEF NETWORK -- LP SOLUTION REPORT")
    print(_BANNER)

    # --- DATA VALIDATION ---
    print()
    print(_SEP)
    print("  DATA VALIDATION")
    print(_SEP)
    if data.validation_warnings:
        for w in data.validation_warnings:
            print(f"  WARNING: {w}")
    else:
        print("  All checks passed.")

    # --- SOLVER SUMMARY ---
    print()
    print(_SEP)
    print("  SOLVER SUMMARY")
    print(_SEP)
    print(f"  Status              : {sol.status}")
    print(f"  Objective value     : {sol.objective:,.2f}")
    print(f"  Variables           : {sol.num_variables}")
    print(f"  Constraints         : {sol.num_constraints}")
    print(f"  Penalty per unit    : {PENALTY:.1f}")

    # --- COST BREAKDOWN ---
    print()
    print(_SEP)
    print("  COST BREAKDOWN")
    print(_SEP)
    total_recomputed = (
        costs.total_fixed_cost
        + costs.expected_shipping_cost
        + costs.expected_penalty_cost
    )
    print(f"  Fixed cost (all depots) : {costs.total_fixed_cost:>14,}")
    print(
        f"  Expected shipping cost  : {costs.expected_shipping_cost:>14,.2f}"
    )
    print(
        f"  Expected penalty cost   : {costs.expected_penalty_cost:>14,.2f}"
    )
    print(
        f"  Expected total unmet    : {costs.expected_total_unmet:>14,.2f}"
    )
    print(f"                            {'-' * 14}")
    print(f"  Total (recomputed)      : {total_recomputed:>14,.2f}")

    # --- PER-SCENARIO BREAKDOWN ---
    print()
    print(_SEP)
    print("  PER-SCENARIO BREAKDOWN")
    print(_SEP)
    print(
        f"  {'Scenario':<10}{'Description':<18}{'Shipping':>10}"
        f"{'Penalty':>12}{'Total':>12}{'Unmet':>9}"
    )
    for s in data.scenario_ids:
        print(
            f"  {s:<10}{data.scenario_desc[s]:<18}"
            f"{costs.per_scenario_shipping[s]:>10,.2f}"
            f"{costs.per_scenario_penalty[s]:>12,.2f}"
            f"{costs.per_scenario_total[s]:>12,.2f}"
            f"{costs.per_scenario_unmet[s]:>9,.2f}"
        )
    print()
    wc = costs.worst_cost_scenario
    wu = costs.worst_unmet_scenario
    print(f"  Worst cost scenario : {wc} ({data.scenario_desc[wc]})")
    print(f"  Worst unmet scenario: {wu} ({data.scenario_desc[wu]})")

    # --- DEPOT UTILIZATION ---
    print()
    print(_SEP)
    print("  DEPOT UTILIZATION")
    print(_SEP)
    print(
        f"  {'Depot':<7}{'Name':<17}{'Cap':>4}{'AvgUtil':>9}"
        f"{'MaxUtil':>9}{'MaxScen':>9}  {'Status'}"
    )
    for dp in depot_profiles:
        status_str = "BOTTLENECK" if dp.is_bottleneck else "ok"
        print(
            f"  {dp.depot_id:<7}{dp.name:<17}{dp.capacity:>4}"
            f"{dp.avg_utilization:>8.1%}{dp.max_utilization:>9.1%}"
            f"{dp.max_utilization_scenario:>9}  {status_str}"
        )
    bottleneck_count = sum(1 for dp in depot_profiles if dp.is_bottleneck)
    print(f"  Bottleneck alerts: {bottleneck_count} depot(s)")

    # --- TOWN SERVICE PROFILES ---
    print()
    print(_SEP)
    print("  TOWN SERVICE PROFILES")
    print(_SEP)
    print(
        f"  {'Town':<6}{'Name':<11}{'Crit':<6}{'DemMin':>6}{'DemMax':>7}"
        f"{'DemMean':>8}{'E[Unmet]':>9}{'WorstUnmet':>11}"
        f"{'Dominant':>9}{'Share':>7}{'SPOF':>6}"
    )
    for tp in town_profiles:
        crit_str = "Y" if tp.is_critical else "N"
        spof_str = "Y" if tp.is_single_source else "N"
        print(
            f"  {tp.town_id:<6}{tp.name:<11}{crit_str:<6}"
            f"{tp.demand_min:>6}{tp.demand_max:>7}{tp.demand_mean:>8.1f}"
            f"{tp.expected_unmet:>9.2f}{tp.worst_unmet:>11.2f}"
            f"{tp.dominant_depot:>9}{tp.dominant_share:>6.1%}{spof_str:>6}"
        )
    spof_count = sum(1 for tp in town_profiles if tp.is_single_source)
    print(f"  Single-point-of-failure towns: {spof_count}")

    # --- CAPACITY SHADOW PRICES ---
    print()
    print(_SEP)
    print("  CAPACITY SHADOW PRICES (non-zero)")
    print(_SEP)
    nonzero_cap = {
        k: v for k, v in sol.capacity_duals.items() if abs(v) > 1e-8
    }
    if nonzero_cap:
        for (d, s), dual in sorted(nonzero_cap.items()):
            print(f"  cap_{d}_{s} : {dual:>10.4f}")
    else:
        print("  All capacity constraints non-binding.")

    # --- DEMAND SHADOW PRICES (S01) ---
    print()
    print(_SEP)
    print("  DEMAND SHADOW PRICES (scenario S01)")
    print(_SEP)
    for t in data.town_ids:
        dual = sol.demand_duals.get((t, "S01"), 0.0)
        print(f"  dem_{t}_S01 : {dual:>10.4f}")

    # --- SERVICE CONSTRAINT DUALS ---
    print()
    print(_SEP)
    print("  SERVICE CONSTRAINT DUALS (non-zero)")
    print(_SEP)
    nonzero_svc = {
        k: v for k, v in sol.service_duals.items() if abs(v) > 1e-8
    }
    if nonzero_svc:
        for (t, s), dual in sorted(nonzero_svc.items()):
            print(f"  svc_{t}_{s} : {dual:>10.4f}")
    else:
        print("  All service constraints non-binding.")

    # --- TOP EXPECTED SHIPMENT LANES ---
    print()
    print(_SEP)
    print("  TOP EXPECTED SHIPMENT LANES")
    print(_SEP)
    lanes: list[tuple[str, str, float]] = []
    for d in data.depot_ids:
        for t in data.town_ids:
            exp_flow = sum(
                data.scenario_prob[s] * sol.ship_vals[(d, t, s)]
                for s in data.scenario_ids
            )
            if exp_flow > 0.01:
                lanes.append((d, t, exp_flow))
    lanes.sort(key=lambda x: x[2], reverse=True)

    print(
        f"  {'Depot':<7}{'Town':<10}{'ExpFlow':>10}{'Cost':>8}{'Dist':>6}"
    )
    for d, t, flow in lanes:
        print(
            f"  {d:<7}{t:<10}{flow:>10.2f}"
            f"{data.shipping_cost[(d, t)]:>8.2f}"
            f"{data.arc_distance[(d, t)]:>6}"
        )

    # --- AUDIT RESULTS ---
    print()
    print(_SEP)
    print("  AUDIT RESULTS")
    print(_SEP)
    for check_name, passed in audit.checks.items():
        tag = "PASS" if passed else "FAIL"
        print(f"  [{tag}] {check_name}")
    if audit.warnings:
        for w in audit.warnings:
            print(f"    WARNING: {w}")
    print(f"  Checks passed: {audit.passed_count}/{audit.total_count}")
    overall = "ALL CLEAR" if audit.all_passed else "ISSUES DETECTED"
    print(f"  Overall       : {overall}")

    print()
    print(_BANNER)
    print("  END OF REPORT")
    print(_BANNER)


def main() -> None:
    """Load, build, solve, analyze, and report."""
    data = load_data()
    artifacts = build_model(data)
    sol = solve_and_extract(data, artifacts)
    costs = compute_cost_breakdown(data, sol)
    depot_profiles = profile_depots(data, sol)
    town_profiles = profile_towns(data, sol)
    audit = audit_solution(data, sol, costs)
    print_report(data, sol, costs, depot_profiles, town_profiles, audit)


if __name__ == "__main__":
    main()
