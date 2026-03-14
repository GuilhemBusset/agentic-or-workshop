"""Metamorphic testing harness for disaster-relief depot activation and routing MILP."""

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
import warnings

import xpress as xp

warnings.simplefilter("ignore")

_XPRESS_INITIALIZED = False
_CRITICAL_TOWNS = {"T03", "T04", "T07", "T12"}

SHORTAGE_PENALTY = 25.0
CVAR_ALPHA = 0.80
RISK_WEIGHT = 12.0
CRITICAL_SERVICE_FLOOR = 0.95


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
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@dataclass
class ProblemData:
    depots: list[str]
    towns: list[str]
    scenarios: list[str]
    capacity: dict[str, float]
    fixed_cost: dict[str, float]
    service_min: dict[str, float]
    scenario_prob: dict[str, float]
    shipping_cost: dict[tuple[str, str], float]
    demand: dict[tuple[str, str], float]
    critical_towns: set[str] = field(default_factory=lambda: set(_CRITICAL_TOWNS))


def load_data() -> ProblemData:
    """Load all CSV data from workshop/data/."""
    data_dir = Path(__file__).resolve().parents[3] / "data"

    depots_raw = _read_csv(data_dir / "depots.csv")
    towns_raw = _read_csv(data_dir / "towns.csv")
    arcs_raw = _read_csv(data_dir / "arcs.csv")
    scenarios_raw = _read_csv(data_dir / "scenarios.csv")
    demands_raw = _read_csv(data_dir / "scenario_demands.csv")

    return ProblemData(
        depots=sorted(r["depot_id"] for r in depots_raw),
        towns=sorted(r["town_id"] for r in towns_raw),
        scenarios=sorted(r["scenario_id"] for r in scenarios_raw),
        capacity={r["depot_id"]: float(r["capacity"]) for r in depots_raw},
        fixed_cost={r["depot_id"]: float(r["fixed_cost"]) for r in depots_raw},
        service_min={r["town_id"]: float(r["service_min"]) for r in towns_raw},
        scenario_prob={
            r["scenario_id"]: float(r["probability"]) for r in scenarios_raw
        },
        shipping_cost={
            (r["depot_id"], r["town_id"]): float(r["shipping_cost"]) for r in arcs_raw
        },
        demand={
            (r["scenario_id"], r["town_id"]): float(r["demand"]) for r in demands_raw
        },
    )


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------


@dataclass
class SolveResult:
    status: str
    objective: float
    open_depots: list[str]
    fixed_opening_cost: float
    expected_transport_cost: float
    expected_shortage_penalty: float
    cvar_risk_term: float
    expected_unmet: float
    max_scenario_unmet: float
    feasible: bool


def solve_milp(
    data: ProblemData,
    *,
    fixed_open: dict[str, int] | None = None,
    shortage_penalty: float = SHORTAGE_PENALTY,
    cvar_alpha: float = CVAR_ALPHA,
    risk_weight: float = RISK_WEIGHT,
    critical_service_floor: float = CRITICAL_SERVICE_FLOOR,
    model_name: str = "metamorphic",
) -> SolveResult:
    """Build and solve the disaster-relief MILP.

    If *fixed_open* is provided, depot-open variables are fixed to those values
    (turning the MILP into an LP over the recourse variables).
    """
    _initialize_xpress()

    depots = data.depots
    towns = data.towns
    scenarios = data.scenarios

    model = xp.problem(model_name)
    model.controls.outputlog = 0
    model.controls.miprelstop = 1e-6

    # Variables
    open_depot = {d: xp.var(vartype=xp.binary, name=f"open_{d}") for d in depots}
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
    eta = xp.var(lb=0.0, name="cvar_eta")
    xi = {s: xp.var(lb=0.0, name=f"cvar_xi_{s}") for s in scenarios}

    model.addVariable(
        list(open_depot.values()),
        list(ship.values()),
        list(unmet.values()),
        list(scenario_shortage.values()),
        [eta],
        list(xi.values()),
    )

    # Fix depot-open decisions if requested
    if fixed_open is not None:
        for d in depots:
            val = float(fixed_open[d])
            model.chgbounds([open_depot[d]], ["B"], [val])

    # Constraints: capacity linking
    for d in depots:
        for s in scenarios:
            model.addConstraint(
                xp.Sum(ship[d, t, s] for t in towns) <= data.capacity[d] * open_depot[d]
            )

    # Constraints: demand balance
    for t in towns:
        for s in scenarios:
            model.addConstraint(
                xp.Sum(ship[d, t, s] for d in depots) + unmet[t, s] == data.demand[s, t]
            )

    # Constraints: critical service floor
    for t in data.critical_towns:
        for s in scenarios:
            model.addConstraint(
                xp.Sum(ship[d, t, s] for d in depots)
                >= critical_service_floor * data.demand[s, t]
            )

    # Constraints: CVaR auxiliary
    for s in scenarios:
        model.addConstraint(scenario_shortage[s] == xp.Sum(unmet[t, s] for t in towns))
        model.addConstraint(xi[s] >= scenario_shortage[s] - eta)

    # Objective
    fixed_cost_expr = xp.Sum(data.fixed_cost[d] * open_depot[d] for d in depots)
    expected_transport_expr = xp.Sum(
        data.scenario_prob[s] * data.shipping_cost[d, t] * ship[d, t, s]
        for d in depots
        for t in towns
        for s in scenarios
    )
    expected_shortage_expr = xp.Sum(
        data.scenario_prob[s] * shortage_penalty * unmet[t, s]
        for t in towns
        for s in scenarios
    )
    cvar_expr = eta + (1.0 / (1.0 - cvar_alpha)) * xp.Sum(
        data.scenario_prob[s] * xi[s] for s in scenarios
    )

    model.setObjective(
        fixed_cost_expr
        + expected_transport_expr
        + expected_shortage_expr
        + risk_weight * cvar_expr,
        sense=xp.minimize,
    )
    model.solve()

    status_str = str(model.getProbStatusString())
    feasible = "infeas" not in status_str.lower()

    if not feasible:
        return SolveResult(
            status=status_str,
            objective=float("inf"),
            open_depots=[],
            fixed_opening_cost=0.0,
            expected_transport_cost=0.0,
            expected_shortage_penalty=0.0,
            cvar_risk_term=0.0,
            expected_unmet=0.0,
            max_scenario_unmet=0.0,
            feasible=False,
        )

    # Extract solution
    open_vals = {d: float(model.getSolution(open_depot[d])) for d in depots}
    ship_vals = {
        (d, t, s): float(model.getSolution(ship[d, t, s]))
        for d in depots
        for t in towns
        for s in scenarios
    }
    unmet_vals = {
        (t, s): float(model.getSolution(unmet[t, s])) for t in towns for s in scenarios
    }
    shortage_vals = {
        s: float(model.getSolution(scenario_shortage[s])) for s in scenarios
    }
    eta_val = float(model.getSolution(eta))
    xi_vals = {s: float(model.getSolution(xi[s])) for s in scenarios}

    opened = sorted(d for d, v in open_vals.items() if v >= 0.5)

    fc = sum(data.fixed_cost[d] * open_vals[d] for d in depots)
    tc = sum(
        data.scenario_prob[s] * data.shipping_cost[d, t] * ship_vals[d, t, s]
        for d in depots
        for t in towns
        for s in scenarios
    )
    eu = sum(data.scenario_prob[s] * unmet_vals[t, s] for t in towns for s in scenarios)
    esp = shortage_penalty * eu
    cvar_val = eta_val + (1.0 / (1.0 - cvar_alpha)) * sum(
        data.scenario_prob[s] * xi_vals[s] for s in scenarios
    )

    return SolveResult(
        status=status_str,
        objective=float(model.getObjVal()),
        open_depots=opened,
        fixed_opening_cost=fc,
        expected_transport_cost=tc,
        expected_shortage_penalty=esp,
        cvar_risk_term=risk_weight * cvar_val,
        expected_unmet=eu,
        max_scenario_unmet=max(shortage_vals.values()),
        feasible=True,
    )


# ---------------------------------------------------------------------------
# Metamorphic relations
# ---------------------------------------------------------------------------


@dataclass
class RelationResult:
    name: str
    passed: bool
    baseline_value: float
    perturbed_value: float
    direction: str
    description: str
    error: str | None = None


def _baseline_open_map(result: SolveResult, depots: list[str]) -> dict[str, int]:
    return {d: (1 if d in result.open_depots else 0) for d in depots}


def relation_capacity_halving(
    data: ProblemData, baseline: SolveResult
) -> RelationResult:
    """Halve depot capacities with fixed depot decisions.

    Expected: unmet(perturbed) >= unmet(baseline).
    """
    perturbed_data = ProblemData(
        depots=data.depots,
        towns=data.towns,
        scenarios=data.scenarios,
        capacity={d: c * 0.5 for d, c in data.capacity.items()},
        fixed_cost=data.fixed_cost,
        service_min=data.service_min,
        scenario_prob=data.scenario_prob,
        shipping_cost=data.shipping_cost,
        demand=data.demand,
        critical_towns=data.critical_towns,
    )
    fixed = _baseline_open_map(baseline, data.depots)
    perturbed = solve_milp(perturbed_data, fixed_open=fixed, model_name="cap_halving")

    if not perturbed.feasible:
        return RelationResult(
            name="capacity_halving",
            passed=True,
            baseline_value=baseline.expected_unmet,
            perturbed_value=float("inf"),
            direction=">=",
            description="Halve capacities (fixed depots): unmet must not decrease",
            error="Perturbed problem infeasible (scarcity exceeds critical floor)",
        )

    ok = perturbed.expected_unmet >= baseline.expected_unmet - 1e-6
    return RelationResult(
        name="capacity_halving",
        passed=ok,
        baseline_value=baseline.expected_unmet,
        perturbed_value=perturbed.expected_unmet,
        direction=">=",
        description="Halve capacities (fixed depots): unmet must not decrease",
    )


def relation_fixed_cost_halving(
    data: ProblemData, baseline: SolveResult
) -> RelationResult:
    """Halve all depot fixed costs, re-optimise fully.

    Expected: objective(perturbed) <= objective(baseline).
    """
    perturbed_data = ProblemData(
        depots=data.depots,
        towns=data.towns,
        scenarios=data.scenarios,
        capacity=data.capacity,
        fixed_cost={d: c * 0.5 for d, c in data.fixed_cost.items()},
        service_min=data.service_min,
        scenario_prob=data.scenario_prob,
        shipping_cost=data.shipping_cost,
        demand=data.demand,
        critical_towns=data.critical_towns,
    )
    perturbed = solve_milp(perturbed_data, model_name="fc_halving")

    if not perturbed.feasible:
        return RelationResult(
            name="fixed_cost_halving",
            passed=False,
            baseline_value=baseline.objective,
            perturbed_value=float("inf"),
            direction="<=",
            description="Halve fixed costs (full MILP): objective must not increase",
            error="Perturbed problem unexpectedly infeasible",
        )

    ok = perturbed.objective <= baseline.objective + 1e-4
    return RelationResult(
        name="fixed_cost_halving",
        passed=ok,
        baseline_value=baseline.objective,
        perturbed_value=perturbed.objective,
        direction="<=",
        description="Halve fixed costs (full MILP): objective must not increase",
    )


def relation_demand_scaling(data: ProblemData, baseline: SolveResult) -> RelationResult:
    """Scale demands by 2x and 3x with fixed depot decisions.

    Expected: unmet(3x) >= unmet(2x) >= unmet(baseline).
    """
    fixed = _baseline_open_map(baseline, data.depots)
    results: list[tuple[float, SolveResult | None]] = []

    for factor in (2.0, 3.0):
        perturbed_data = ProblemData(
            depots=data.depots,
            towns=data.towns,
            scenarios=data.scenarios,
            capacity=data.capacity,
            fixed_cost=data.fixed_cost,
            service_min=data.service_min,
            scenario_prob=data.scenario_prob,
            shipping_cost=data.shipping_cost,
            demand={k: v * factor for k, v in data.demand.items()},
            critical_towns=data.critical_towns,
        )
        r = solve_milp(perturbed_data, fixed_open=fixed, model_name=f"demand_{factor}x")
        results.append((factor, r))

    r_2x = results[0][1]
    r_3x = results[1][1]

    if r_2x is None or not r_2x.feasible:
        return RelationResult(
            name="demand_scaling",
            passed=True,
            baseline_value=baseline.expected_unmet,
            perturbed_value=float("inf"),
            direction=">=",
            description="Scale demands 2x/3x (fixed depots): unmet chain monotonic",
            error="2x demand problem infeasible",
        )
    if r_3x is None or not r_3x.feasible:
        return RelationResult(
            name="demand_scaling",
            passed=r_2x.expected_unmet >= baseline.expected_unmet - 1e-6,
            baseline_value=baseline.expected_unmet,
            perturbed_value=r_2x.expected_unmet,
            direction=">=",
            description="Scale demands 2x/3x (fixed depots): unmet chain monotonic",
            error="3x demand problem infeasible; only 2x vs baseline checked",
        )

    chain_ok = (
        r_3x.expected_unmet >= r_2x.expected_unmet - 1e-6
        and r_2x.expected_unmet >= baseline.expected_unmet - 1e-6
    )
    return RelationResult(
        name="demand_scaling",
        passed=chain_ok,
        baseline_value=baseline.expected_unmet,
        perturbed_value=r_3x.expected_unmet,
        direction=">=",
        description=(
            f"Scale demands 2x/3x (fixed depots): "
            f"unmet(3x)={r_3x.expected_unmet:.4f} >= "
            f"unmet(2x)={r_2x.expected_unmet:.4f} >= "
            f"unmet(baseline)={baseline.expected_unmet:.4f}"
        ),
    )


def relation_penalty_under_scarcity(
    data: ProblemData, baseline: SolveResult
) -> RelationResult:
    """Under 40% capacity, tripling the penalty must not increase unmet demand.

    Expected: unmet(penalty=75) <= unmet(penalty=25).
    """
    scarce_data = ProblemData(
        depots=data.depots,
        towns=data.towns,
        scenarios=data.scenarios,
        capacity={d: c * 0.4 for d, c in data.capacity.items()},
        fixed_cost=data.fixed_cost,
        service_min=data.service_min,
        scenario_prob=data.scenario_prob,
        shipping_cost=data.shipping_cost,
        demand=data.demand,
        critical_towns=data.critical_towns,
    )
    fixed = _baseline_open_map(baseline, data.depots)

    r_low = solve_milp(
        scarce_data,
        fixed_open=fixed,
        shortage_penalty=25.0,
        model_name="penalty_low",
    )
    r_high = solve_milp(
        scarce_data,
        fixed_open=fixed,
        shortage_penalty=75.0,
        model_name="penalty_high",
    )

    if not r_low.feasible or not r_high.feasible:
        return RelationResult(
            name="penalty_under_scarcity",
            passed=True,
            baseline_value=0.0,
            perturbed_value=0.0,
            direction="<=",
            description="Penalty under scarcity: unmet(penalty=75) <= unmet(penalty=25)",
            error="One or both scarce-capacity variants infeasible",
        )

    ok = r_high.expected_unmet <= r_low.expected_unmet + 1e-6
    return RelationResult(
        name="penalty_under_scarcity",
        passed=ok,
        baseline_value=r_low.expected_unmet,
        perturbed_value=r_high.expected_unmet,
        direction="<=",
        description="Penalty under scarcity: unmet(penalty=75) <= unmet(penalty=25)",
    )


def relation_tightened_critical_floor(
    data: ProblemData, baseline: SolveResult
) -> RelationResult:
    """Tighten critical service floor from 0.95 to 0.99 (full MILP).

    Expected: objective(perturbed) >= objective(baseline).
    """
    perturbed = solve_milp(data, critical_service_floor=0.99, model_name="tight_floor")

    if not perturbed.feasible:
        return RelationResult(
            name="tightened_critical_floor",
            passed=True,
            baseline_value=baseline.objective,
            perturbed_value=float("inf"),
            direction=">=",
            description="Tighten critical floor to 0.99 (full MILP): objective must not decrease",
            error="Perturbed problem infeasible under tighter floor",
        )

    ok = perturbed.objective >= baseline.objective - 1e-4
    return RelationResult(
        name="tightened_critical_floor",
        passed=ok,
        baseline_value=baseline.objective,
        perturbed_value=perturbed.objective,
        direction=">=",
        description="Tighten critical floor to 0.99 (full MILP): objective must not decrease",
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

ALL_RELATIONS = [
    relation_capacity_halving,
    relation_fixed_cost_halving,
    relation_demand_scaling,
    relation_penalty_under_scarcity,
    relation_tightened_critical_floor,
]


def run_harness() -> dict:
    """Solve the baseline, apply all metamorphic relations, and return a report."""
    data = load_data()
    baseline = solve_milp(data, model_name="baseline")

    if not baseline.feasible:
        return {
            "baseline": {"status": baseline.status, "feasible": False},
            "relations": [],
            "all_passed": False,
        }

    relation_results = [rel(data, baseline) for rel in ALL_RELATIONS]

    def _safe(v: float) -> float | None:
        """Replace inf/nan with None for JSON serialization."""
        if v != v or v == float("inf") or v == float("-inf"):
            return None
        return v

    report = {
        "baseline": {
            "status": baseline.status,
            "feasible": baseline.feasible,
            "objective": baseline.objective,
            "open_depots": baseline.open_depots,
            "cost_breakdown": {
                "fixed_opening_cost": baseline.fixed_opening_cost,
                "expected_transport_cost": baseline.expected_transport_cost,
                "expected_shortage_penalty": baseline.expected_shortage_penalty,
                "cvar_risk_term": baseline.cvar_risk_term,
            },
            "expected_unmet": baseline.expected_unmet,
            "max_scenario_unmet": baseline.max_scenario_unmet,
        },
        "relations": [
            {
                "name": r.name,
                "passed": r.passed,
                "baseline_value": _safe(r.baseline_value),
                "perturbed_value": _safe(r.perturbed_value),
                "direction": r.direction,
                "description": r.description,
                **({"error": r.error} if r.error else {}),
            }
            for r in relation_results
        ],
        "all_passed": all(r.passed for r in relation_results),
    }
    return report


def main() -> None:
    report = run_harness()
    report_path = Path(__file__).resolve().parent / "metamorphic_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=False))
    print(json.dumps(report, indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
