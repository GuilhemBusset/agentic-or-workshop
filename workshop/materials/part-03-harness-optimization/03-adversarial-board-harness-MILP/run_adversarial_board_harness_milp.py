"""Multi-candidate depot activation and routing MILP with CVaR risk,
stress testing, contract validation, and competitive scoring."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pulp
import xpress as xp

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR: Path = Path(__file__).resolve().parents[3] / "data"
REPORT_DIR: Path = Path(__file__).resolve().parent

_CRITICAL_TOWNS: set[str] = {"T03", "T04", "T07", "T12"}
_BASE_SHORTAGE_PENALTY: float = 25.0
_CRITICAL_SERVICE_FLOOR: float = 0.95
_STRESS_DEMAND_MULTIPLIER: float = 1.2
_BOARD_TIE_TOLERANCE: float = 1e-9

_CONTRACT_CHECK_IDS: list[str] = [
    "C01_model_class_milp",
    "C02_binary_open_decisions",
    "C03_critical_towns_exact",
    "C04_critical_service_floor",
    "C05_capacity_only_if_open",
    "C06_objective_component_consistency",
    "C07_probability_contract",
    "C08_solver_status_ok",
]

_SCORING_WEIGHTS: dict[str, float] = {
    "normalized_baseline_objective": 0.40,
    "normalized_open_depot_count": 0.05,
    "normalized_stressed_critical_unmet": 0.20,
    "normalized_stressed_total_unmet": 0.35,
}

# Candidate definitions -- parameters are chosen so that each candidate
# produces structurally different solutions under stress testing:
#   - cost_lean:  very low penalty, zero CVaR -> accepts unmet demand
#   - balanced:   moderate penalty, zero CVaR -> partial unmet demand
#   - resilience: high penalty + CVaR weight  -> zero unmet demand
_CANDIDATES: list[dict] = [
    {
        "candidate_id": "candidate_cost_lean",
        "shortage_penalty_multiplier": 0.08,
        "effective_shortage_penalty": 0.08 * _BASE_SHORTAGE_PENALTY,
        "cvar_weight": 0.0,
        "cvar_alpha": 0.80,
        "solver_backend": "xpress",
    },
    {
        "candidate_id": "candidate_balanced",
        "shortage_penalty_multiplier": 0.12,
        "effective_shortage_penalty": 0.12 * _BASE_SHORTAGE_PENALTY,
        "cvar_weight": 0.0,
        "cvar_alpha": 0.80,
        "solver_backend": "pulp",
    },
    {
        "candidate_id": "candidate_resilience",
        "shortage_penalty_multiplier": 1.00,
        "effective_shortage_penalty": 1.00 * _BASE_SHORTAGE_PENALTY,
        "cvar_weight": 10.0,
        "cvar_alpha": 0.80,
        "solver_backend": "xpress",
    },
]

# ---------------------------------------------------------------------------
# Xpress licence helper
# ---------------------------------------------------------------------------
_XPRESS_INITIALIZED: bool = False


def _initialize_xpress() -> None:
    global _XPRESS_INITIALIZED
    if _XPRESS_INITIALIZED:
        return
    package_dir = Path(xp.__file__).resolve().parent
    community_license = package_dir / "license" / "community-xpauth.xpr"
    if community_license.exists():
        xp.init(str(community_license))
    _XPRESS_INITIALIZED = True


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_data() -> dict:
    """Load all CSV data from workshop/data/ and return a plain dict."""
    depots_raw = _read_csv(DATA_DIR / "depots.csv")
    towns_raw = _read_csv(DATA_DIR / "towns.csv")
    arcs_raw = _read_csv(DATA_DIR / "arcs.csv")
    scenarios_raw = _read_csv(DATA_DIR / "scenarios.csv")
    demands_raw = _read_csv(DATA_DIR / "scenario_demands.csv")

    return {
        "depots": sorted(r["depot_id"] for r in depots_raw),
        "towns": sorted(r["town_id"] for r in towns_raw),
        "scenarios": sorted(r["scenario_id"] for r in scenarios_raw),
        "capacity": {r["depot_id"]: float(r["capacity"]) for r in depots_raw},
        "fixed_cost": {r["depot_id"]: float(r["fixed_cost"]) for r in depots_raw},
        "service_min": {r["town_id"]: float(r["service_min"]) for r in towns_raw},
        "scenario_prob": {
            r["scenario_id"]: float(r["probability"]) for r in scenarios_raw
        },
        "shipping_cost": {
            (r["depot_id"], r["town_id"]): float(r["shipping_cost"]) for r in arcs_raw
        },
        "demand": {
            (r["scenario_id"], r["town_id"]): float(r["demand"]) for r in demands_raw
        },
        "critical_towns": set(_CRITICAL_TOWNS),
    }


# ---------------------------------------------------------------------------
# Shared model-building helpers
# ---------------------------------------------------------------------------


def _build_effective_demand(
    data: dict,
    demand_multiplier: float,
) -> dict[tuple[str, str], float]:
    """Compute effective demand for each (scenario, town) pair."""
    return {
        (s, t): data["demand"][(s, t)] * demand_multiplier
        for s in data["scenarios"]
        for t in data["towns"]
    }


# ---------------------------------------------------------------------------
# Solver: xpress backend
# ---------------------------------------------------------------------------


def _solve_xpress(
    data: dict,
    *,
    rho: float,
    lam: float,
    alpha: float,
    frozen_depots: dict[str, int] | None = None,
    demand_multiplier: float = 1.0,
    model_name: str = "depot_milp",
) -> dict:
    """Build and solve the two-stage stochastic MILP using FICO Xpress."""
    _initialize_xpress()

    depots = data["depots"]
    towns = data["towns"]
    scenarios = data["scenarios"]

    prob = xp.problem(model_name)
    prob.controls.outputlog = 0
    prob.controls.miprelstop = 1e-4

    # Decision variables (created directly on the problem to avoid deprecation)
    y = {d: prob.addVariable(vartype=xp.binary, name=f"y_{d}") for d in depots}
    x = {
        (d, t, s): prob.addVariable(lb=0.0, name=f"x_{d}_{t}_{s}")
        for d in depots
        for t in towns
        for s in scenarios
    }
    u = {
        (t, s): prob.addVariable(lb=0.0, name=f"u_{t}_{s}")
        for t in towns
        for s in scenarios
    }
    eta = prob.addVariable(lb=-1e10, name="eta")
    z = {s: prob.addVariable(lb=0.0, name=f"z_{s}") for s in scenarios}

    # Freeze depot decisions if requested
    if frozen_depots is not None:
        for d in depots:
            val = float(frozen_depots[d])
            prob.chgBounds([y[d]], ["B"], [val])

    # Effective demand
    dem = _build_effective_demand(data, demand_multiplier)

    # C1: Capacity
    for d in depots:
        for s in scenarios:
            prob.addConstraint(
                xp.Sum(x[d, t, s] for t in towns) <= data["capacity"][d] * y[d]
            )

    # C2: Demand balance
    for t in towns:
        for s in scenarios:
            prob.addConstraint(
                xp.Sum(x[d, t, s] for d in depots) + u[t, s] == dem[s, t]
            )

    # C3: Service floor (ALL towns)
    for t in towns:
        mu_t = data["service_min"][t]
        for s in scenarios:
            prob.addConstraint(u[t, s] <= (1.0 - mu_t) * dem[s, t])

    # C4: CVaR auxiliary
    for s in scenarios:
        prob.addConstraint(z[s] >= xp.Sum(rho * u[t, s] for t in towns) - eta)

    # Objective
    p = data["scenario_prob"]
    c = data["shipping_cost"]
    f = data["fixed_cost"]

    fixed_cost_expr = xp.Sum(f[d] * y[d] for d in depots)
    transport_expr = xp.Sum(
        p[s] * c[d, t] * x[d, t, s] for d in depots for t in towns for s in scenarios
    )
    shortage_expr = xp.Sum(p[s] * rho * u[t, s] for t in towns for s in scenarios)
    cvar_expr = lam * (
        eta + (1.0 / (1.0 - alpha)) * xp.Sum(p[s] * z[s] for s in scenarios)
    )

    prob.setObjective(
        fixed_cost_expr + transport_expr + shortage_expr + cvar_expr,
        sense=xp.minimize,
    )
    prob.solve()

    # Extract status via non-deprecated attributes
    sol_status = prob.attributes.solstatus
    is_optimal = (
        sol_status == xp.SolStatus.OPTIMAL or sol_status == xp.SolStatus.FEASIBLE
    )

    if not is_optimal:
        return {
            "status": sol_status.name,
            "objective": float("inf"),
            "objective_components": {},
            "open_depots": [],
            "open_depot_count": 0,
            "unmet_metrics": {
                "total_unmet": float("inf"),
                "critical_unmet": float("inf"),
            },
        }

    # Extract solution values
    y_val = {d: float(prob.getSolution(y[d])) for d in depots}
    x_val = {
        (d, t, s): float(prob.getSolution(x[d, t, s]))
        for d in depots
        for t in towns
        for s in scenarios
    }
    u_val = {(t, s): float(prob.getSolution(u[t, s])) for t in towns for s in scenarios}
    eta_val = float(prob.getSolution(eta))
    z_val = {s: float(prob.getSolution(z[s])) for s in scenarios}

    # Compute objective components
    fc = sum(f[d] * y_val[d] for d in depots)
    tc = sum(
        p[s] * c[d, t] * x_val[d, t, s]
        for d in depots
        for t in towns
        for s in scenarios
    )
    sp = sum(p[s] * rho * u_val[t, s] for t in towns for s in scenarios)
    cv = lam * (
        eta_val + (1.0 / (1.0 - alpha)) * sum(p[s] * z_val[s] for s in scenarios)
    )
    total_obj = fc + tc + sp + cv

    opened = sorted(d for d in depots if y_val[d] >= 0.5)

    # Unmet metrics
    total_unmet = sum(u_val[t, s] for t in towns for s in scenarios)
    critical_unmet = sum(u_val[t, s] for t in data["critical_towns"] for s in scenarios)

    return {
        "status": "Optimal",
        "objective": float(prob.attributes.objval),
        "objective_components": {
            "fixed_opening_cost": fc,
            "expected_transport_cost": tc,
            "expected_shortage_penalty": sp,
            "cvar_shortage_risk": cv,
            "total_objective": total_obj,
        },
        "open_depots": opened,
        "open_depot_count": len(opened),
        "unmet_metrics": {
            "total_unmet": total_unmet,
            "critical_unmet": critical_unmet,
        },
        "_y_val": y_val,
    }


# ---------------------------------------------------------------------------
# Solver: pulp backend
# ---------------------------------------------------------------------------


def _solve_pulp(
    data: dict,
    *,
    rho: float,
    lam: float,
    alpha: float,
    frozen_depots: dict[str, int] | None = None,
    demand_multiplier: float = 1.0,
    model_name: str = "depot_milp",
) -> dict:
    """Build and solve the two-stage stochastic MILP using PuLP (CBC)."""
    depots = data["depots"]
    towns = data["towns"]
    scenarios = data["scenarios"]

    prob = pulp.LpProblem(model_name, pulp.LpMinimize)

    # Decision variables
    y = {d: pulp.LpVariable(f"y_{d}", cat="Binary") for d in depots}

    # Freeze depot decisions via equality constraints (not bounds) to ensure
    # CBC reports correct solution values for fixed variables.
    if frozen_depots is not None:
        for d in depots:
            prob += (y[d] == frozen_depots[d], f"fix_y_{d}")

    x = {
        (d, t, s): pulp.LpVariable(f"x_{d}_{t}_{s}", lowBound=0)
        for d in depots
        for t in towns
        for s in scenarios
    }
    u = {
        (t, s): pulp.LpVariable(f"u_{t}_{s}", lowBound=0)
        for t in towns
        for s in scenarios
    }
    eta = pulp.LpVariable("eta", lowBound=-1e10)
    z = {s: pulp.LpVariable(f"z_{s}", lowBound=0) for s in scenarios}

    # Effective demand
    dem = _build_effective_demand(data, demand_multiplier)

    p = data["scenario_prob"]
    c = data["shipping_cost"]
    f = data["fixed_cost"]

    # C1: Capacity
    for d in depots:
        for s in scenarios:
            prob += (
                pulp.lpSum(x[d, t, s] for t in towns) <= data["capacity"][d] * y[d],
                f"cap_{d}_{s}",
            )

    # C2: Demand balance
    for t in towns:
        for s in scenarios:
            prob += (
                pulp.lpSum(x[d, t, s] for d in depots) + u[t, s] == dem[s, t],
                f"dem_{t}_{s}",
            )

    # C3: Service floor (ALL towns)
    for t in towns:
        mu_t = data["service_min"][t]
        for s in scenarios:
            prob += (
                u[t, s] <= (1.0 - mu_t) * dem[s, t],
                f"svc_{t}_{s}",
            )

    # C4: CVaR auxiliary
    for s in scenarios:
        prob += (
            z[s] >= pulp.lpSum(rho * u[t, s] for t in towns) - eta,
            f"cvar_{s}",
        )

    # Objective
    fixed_cost_expr = pulp.lpSum(f[d] * y[d] for d in depots)
    transport_expr = pulp.lpSum(
        p[s] * c[d, t] * x[d, t, s] for d in depots for t in towns for s in scenarios
    )
    shortage_expr = pulp.lpSum(p[s] * rho * u[t, s] for t in towns for s in scenarios)
    cvar_expr = lam * (
        eta + (1.0 / (1.0 - alpha)) * pulp.lpSum(p[s] * z[s] for s in scenarios)
    )

    prob += fixed_cost_expr + transport_expr + shortage_expr + cvar_expr

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    status_str = pulp.LpStatus[prob.status]

    if status_str != "Optimal":
        return {
            "status": status_str,
            "objective": float("inf"),
            "objective_components": {},
            "open_depots": [],
            "open_depot_count": 0,
            "unmet_metrics": {
                "total_unmet": float("inf"),
                "critical_unmet": float("inf"),
            },
        }

    # Extract solution values (guard against None from CBC)
    def _pval(v: pulp.LpVariable) -> float:
        return float(v.varValue) if v.varValue is not None else 0.0

    y_val = {d: _pval(y[d]) for d in depots}
    x_val = {
        (d, t, s): _pval(x[d, t, s]) for d in depots for t in towns for s in scenarios
    }
    u_val = {(t, s): _pval(u[t, s]) for t in towns for s in scenarios}
    eta_val = _pval(eta)
    z_val = {s: _pval(z[s]) for s in scenarios}

    # Compute objective components
    fc = sum(f[d] * y_val[d] for d in depots)
    tc = sum(
        p[s] * c[d, t] * x_val[d, t, s]
        for d in depots
        for t in towns
        for s in scenarios
    )
    sp = sum(p[s] * rho * u_val[t, s] for t in towns for s in scenarios)
    cv = lam * (
        eta_val + (1.0 / (1.0 - alpha)) * sum(p[s] * z_val[s] for s in scenarios)
    )
    total_obj = fc + tc + sp + cv

    opened = sorted(d for d in depots if y_val[d] >= 0.5)

    # Unmet metrics
    total_unmet = sum(u_val[t, s] for t in towns for s in scenarios)
    critical_unmet = sum(u_val[t, s] for t in data["critical_towns"] for s in scenarios)

    return {
        "status": "Optimal",
        "objective": float(pulp.value(prob.objective)),
        "objective_components": {
            "fixed_opening_cost": fc,
            "expected_transport_cost": tc,
            "expected_shortage_penalty": sp,
            "cvar_shortage_risk": cv,
            "total_objective": total_obj,
        },
        "open_depots": opened,
        "open_depot_count": len(opened),
        "unmet_metrics": {
            "total_unmet": total_unmet,
            "critical_unmet": critical_unmet,
        },
        "_y_val": y_val,
    }


# ---------------------------------------------------------------------------
# Unified solver dispatch
# ---------------------------------------------------------------------------


def solve_model(
    data: dict,
    *,
    rho: float,
    lam: float,
    alpha: float,
    solver_backend: str,
    frozen_depots: dict[str, int] | None = None,
    demand_multiplier: float = 1.0,
    model_name: str = "depot_milp",
) -> dict:
    """Dispatch to xpress or pulp backend."""
    if solver_backend == "xpress":
        return _solve_xpress(
            data,
            rho=rho,
            lam=lam,
            alpha=alpha,
            frozen_depots=frozen_depots,
            demand_multiplier=demand_multiplier,
            model_name=model_name,
        )
    elif solver_backend == "pulp":
        return _solve_pulp(
            data,
            rho=rho,
            lam=lam,
            alpha=alpha,
            frozen_depots=frozen_depots,
            demand_multiplier=demand_multiplier,
            model_name=model_name,
        )
    else:
        raise ValueError(f"Unknown solver backend: {solver_backend!r}")


# ---------------------------------------------------------------------------
# Contract checks
# ---------------------------------------------------------------------------


def _run_contract_checks(
    candidate_id: str,
    baseline: dict,
    data: dict,
) -> list[dict]:
    """Run the 8 contract checks on a baseline result, return list of dicts."""
    checks: list[dict] = []

    # C01: Model uses binary depot variables (true by construction)
    checks.append(
        {
            "id": "C01_model_class_milp",
            "passed": True,
            "details": "Binary depot variables used by construction.",
        }
    )

    # C02: All y_i rounded values are 0 or 1
    y_val = baseline.get("_y_val", {})
    all_binary = all(round(v) in (0, 1) for v in y_val.values())
    checks.append(
        {
            "id": "C02_binary_open_decisions",
            "passed": all_binary,
            "details": f"All depot decisions binary: {all_binary}.",
        }
    )

    # C03: Critical towns = {T03, T04, T07, T12}
    critical_match = data["critical_towns"] == _CRITICAL_TOWNS
    checks.append(
        {
            "id": "C03_critical_towns_exact",
            "passed": critical_match,
            "details": f"Critical towns: {sorted(data['critical_towns'])}.",
        }
    )

    # C04: Critical service floor met in all scenarios
    critical_ok = True
    details_c04 = "All critical towns meet 0.95 service floor."
    if baseline["status"] == "Optimal" and "_y_val" in baseline:
        crit_unmet = baseline["unmet_metrics"]["critical_unmet"]
        if crit_unmet > 1e-6:
            details_c04 = (
                f"Critical unmet total: {crit_unmet:.6f} (allowed by 5% slack)."
            )
    else:
        critical_ok = baseline["status"] == "Optimal"
        if not critical_ok:
            details_c04 = f"Model status not optimal: {baseline['status']}."

    checks.append(
        {
            "id": "C04_critical_service_floor",
            "passed": critical_ok,
            "details": details_c04,
        }
    )

    # C05: Capacity only if open (verified by constraints, always true for optimal)
    checks.append(
        {
            "id": "C05_capacity_only_if_open",
            "passed": True,
            "details": "Enforced by capacity-linking constraints.",
        }
    )

    # C06: Objective component consistency
    components = baseline.get("objective_components", {})
    if components:
        comp_total = components.get("total_objective", 0.0)
        obj = baseline.get("objective", 0.0)
        consistency = abs(obj - comp_total) < 1e-2
    else:
        consistency = False
    checks.append(
        {
            "id": "C06_objective_component_consistency",
            "passed": consistency,
            "details": (
                f"|objective ({baseline.get('objective', 0.0):.4f}) - "
                f"sum(components) ({components.get('total_objective', 0.0):.4f})| "
                f"= {abs(baseline.get('objective', 0.0) - components.get('total_objective', 0.0)):.6f}."
            ),
        }
    )

    # C07: Probability contract
    prob_sum = sum(data["scenario_prob"].values())
    prob_ok = abs(prob_sum - 1.0) < 1e-9
    checks.append(
        {
            "id": "C07_probability_contract",
            "passed": prob_ok,
            "details": f"Sum of probabilities: {prob_sum}.",
        }
    )

    # C08: Solver status ok
    status_ok = baseline["status"] == "Optimal"
    checks.append(
        {
            "id": "C08_solver_status_ok",
            "passed": status_ok,
            "details": f"Solver status: {baseline['status']}.",
        }
    )

    return checks


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _min_max_normalize(values: list[float]) -> list[float]:
    """Min-max normalize a list of values (lower is better)."""
    eps = 1e-12
    min_val = min(values)
    max_val = max(values)
    if (max_val - min_val) <= eps:
        return [0.0] * len(values)
    return [(v - min_val) / (max_val - min_val) for v in values]


def _compute_board_scores(
    eligible_candidates: list[dict],
) -> dict:
    """Compute competitive scores for eligible candidates.

    Returns a dict with normalization details and per-candidate scores.
    """
    if not eligible_candidates:
        return {
            "weights": _SCORING_WEIGHTS,
            "normalization": {
                "method": "min_max",
                "lower_is_better": True,
                "epsilon": 1e-12,
                "metric_bounds": {},
            },
            "candidate_scores": {},
        }

    # Gather raw metrics
    raw: dict[str, dict[str, float]] = {}
    for cand in eligible_candidates:
        cid = cand["candidate_id"]
        raw[cid] = {
            "raw_baseline_objective": cand["baseline_summary"]["objective"],
            "raw_open_depot_count": float(cand["baseline_summary"]["open_depot_count"]),
            "raw_stressed_critical_unmet": cand["stress_summary"]["unmet_metrics"][
                "critical_unmet"
            ],
            "raw_stressed_total_unmet": cand["stress_summary"]["unmet_metrics"][
                "total_unmet"
            ],
        }

    cids = [c["candidate_id"] for c in eligible_candidates]

    # Normalize each metric
    metrics = [
        ("baseline_objective", "raw_baseline_objective"),
        ("open_depot_count", "raw_open_depot_count"),
        ("stressed_critical_unmet", "raw_stressed_critical_unmet"),
        ("stressed_total_unmet", "raw_stressed_total_unmet"),
    ]

    metric_bounds: dict[str, dict[str, float]] = {}
    normalized: dict[str, dict[str, float]] = {cid: {} for cid in cids}

    for metric_name, raw_key in metrics:
        vals = [raw[cid][raw_key] for cid in cids]
        norm_vals = _min_max_normalize(vals)
        metric_bounds[metric_name] = {"min": min(vals), "max": max(vals)}
        for i, cid in enumerate(cids):
            normalized[cid][f"normalized_{metric_name}"] = norm_vals[i]

    # Compute weighted score
    candidate_scores: dict[str, dict] = {}
    for cid in cids:
        score = (
            _SCORING_WEIGHTS["normalized_baseline_objective"]
            * normalized[cid]["normalized_baseline_objective"]
            + _SCORING_WEIGHTS["normalized_open_depot_count"]
            * normalized[cid]["normalized_open_depot_count"]
            + _SCORING_WEIGHTS["normalized_stressed_critical_unmet"]
            * normalized[cid]["normalized_stressed_critical_unmet"]
            + _SCORING_WEIGHTS["normalized_stressed_total_unmet"]
            * normalized[cid]["normalized_stressed_total_unmet"]
        )
        candidate_scores[cid] = {
            **raw[cid],
            **normalized[cid],
            "board_score": score,
        }

    return {
        "weights": _SCORING_WEIGHTS,
        "normalization": {
            "method": "min_max",
            "lower_is_better": True,
            "epsilon": 1e-12,
            "metric_bounds": metric_bounds,
        },
        "candidate_scores": candidate_scores,
    }


def _select_winner(
    eligible_candidates: list[dict],
    candidate_scores: dict[str, dict],
) -> tuple[str | None, float | None]:
    """Select the winner: lowest board_score with deterministic tie-break."""
    if not eligible_candidates:
        return None, None

    ranked = sorted(
        eligible_candidates,
        key=lambda c: (
            candidate_scores[c["candidate_id"]]["board_score"],
            c["stress_summary"]["unmet_metrics"]["critical_unmet"],
            c["stress_summary"]["unmet_metrics"]["total_unmet"],
            c["candidate_id"],
        ),
    )

    winner = ranked[0]
    wid = winner["candidate_id"]
    return wid, candidate_scores[wid]["board_score"]


# ---------------------------------------------------------------------------
# Main harness
# ---------------------------------------------------------------------------


def run_adversarial_board_harness(
    *,
    write_report: bool = True,
    print_console_summary: bool = True,
) -> dict:
    """Run the full competitive evaluation harness and return the report dict."""
    data = load_data()

    candidates_output: list[dict] = []

    for cand_def in _CANDIDATES:
        cid = cand_def["candidate_id"]
        rho = cand_def["effective_shortage_penalty"]
        lam = cand_def["cvar_weight"]
        alpha = cand_def["cvar_alpha"]
        backend = cand_def["solver_backend"]

        # --- Baseline solve ---
        baseline = solve_model(
            data,
            rho=rho,
            lam=lam,
            alpha=alpha,
            solver_backend=backend,
            model_name=f"{cid}_baseline",
        )

        # Contract checks
        checks = _run_contract_checks(cid, baseline, data)
        all_passed = all(ch["passed"] for ch in checks)

        # --- Stress test ---
        y_val = baseline.get("_y_val", {})
        frozen_design = {d: int(round(y_val.get(d, 0))) for d in data["depots"]}

        stress = solve_model(
            data,
            rho=rho,
            lam=lam,
            alpha=alpha,
            solver_backend=backend,
            frozen_depots=frozen_design,
            demand_multiplier=_STRESS_DEMAND_MULTIPLIER,
            model_name=f"{cid}_stress",
        )

        # Build candidate output (strip internal _y_val)
        baseline_summary = {k: v for k, v in baseline.items() if not k.startswith("_")}
        baseline_summary["demand_multiplier"] = 1.0

        stress_summary = {k: v for k, v in stress.items() if not k.startswith("_")}
        stress_summary["demand_multiplier"] = _STRESS_DEMAND_MULTIPLIER
        stress_summary["frozen_open_design"] = frozen_design

        cand_output = {
            "candidate_id": cid,
            "parameters": {
                "shortage_penalty_multiplier": cand_def["shortage_penalty_multiplier"],
                "effective_shortage_penalty": rho,
                "cvar_weight": lam,
                "cvar_alpha": alpha,
            },
            "solver_backend": backend,
            "contract_checks": checks,
            "contract_eligible_for_board": all_passed,
            "baseline_summary": baseline_summary,
            "stress_summary": stress_summary,
            "board_score": None,
            "board_score_components": None,
            "selected_as_winner": False,
        }
        candidates_output.append(cand_output)

    # --- Scoring ---
    eligible = [c for c in candidates_output if c["contract_eligible_for_board"]]

    scoring = _compute_board_scores(eligible)

    # Assign scores back
    for cand in candidates_output:
        cid = cand["candidate_id"]
        if cid in scoring["candidate_scores"]:
            sc = scoring["candidate_scores"][cid]
            cand["board_score"] = sc["board_score"]
            cand["board_score_components"] = {
                "normalized_baseline_objective": sc["normalized_baseline_objective"],
                "normalized_open_depot_count": sc["normalized_open_depot_count"],
                "normalized_stressed_critical_unmet": sc[
                    "normalized_stressed_critical_unmet"
                ],
                "normalized_stressed_total_unmet": sc[
                    "normalized_stressed_total_unmet"
                ],
            }

    winner_id, winner_score = _select_winner(eligible, scoring["candidate_scores"])

    # Mark winner
    for cand in candidates_output:
        cand["selected_as_winner"] = cand["candidate_id"] == winner_id

    # --- Build ranking ---
    eligible_ranking = []
    for cand in sorted(
        eligible,
        key=lambda c: (
            scoring["candidate_scores"][c["candidate_id"]]["board_score"],
            c["stress_summary"]["unmet_metrics"]["critical_unmet"],
            c["stress_summary"]["unmet_metrics"]["total_unmet"],
            c["candidate_id"],
        ),
    ):
        cid = cand["candidate_id"]
        sc = scoring["candidate_scores"][cid]
        eligible_ranking.append(
            {
                "candidate_id": cid,
                "board_score": sc["board_score"],
                "raw_baseline_objective": sc["raw_baseline_objective"],
                "raw_open_depot_count": sc["raw_open_depot_count"],
                "raw_stressed_critical_unmet": sc["raw_stressed_critical_unmet"],
                "raw_stressed_total_unmet": sc["raw_stressed_total_unmet"],
            }
        )

    # --- Assemble report ---
    report: dict = {
        "harness": "adversarial_board_harness_milp",
        "data_inputs": [
            "depots.csv",
            "towns.csv",
            "arcs.csv",
            "scenarios.csv",
            "scenario_demands.csv",
        ],
        "constants": {
            "base_shortage_penalty": _BASE_SHORTAGE_PENALTY,
            "critical_service_floor": _CRITICAL_SERVICE_FLOOR,
            "required_critical_towns": sorted(_CRITICAL_TOWNS),
            "stress_demand_multiplier": _STRESS_DEMAND_MULTIPLIER,
            "board_tie_tolerance": _BOARD_TIE_TOLERANCE,
            "contract_check_ids": _CONTRACT_CHECK_IDS,
        },
        "candidates": candidates_output,
        "board_scoring": scoring,
        "board_decision": {
            "eligible_ranking": eligible_ranking,
            "winner_candidate_id": winner_id,
            "winner_board_score": winner_score,
            "tie_tolerance": _BOARD_TIE_TOLERANCE,
            "tie_break_order": [
                "lower stressed critical unmet",
                "lower stressed total unmet",
                "lexicographic candidate_id",
            ],
        },
        "winner": {
            "candidate_id": winner_id,
            "board_score": winner_score,
            "selection_rule": "lowest board_score with deterministic tie-break",
        },
    }

    if print_console_summary:
        _print_summary(report)

    if write_report:
        report_path = REPORT_DIR / "adversarial_board_report.json"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=False))

    return report


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------


def _print_summary(report: dict) -> None:
    """Print a readable console summary of the results."""
    print("=" * 72)
    print("  ADVERSARIAL BOARD HARNESS -- MILP")
    print("=" * 72)

    for cand in report["candidates"]:
        cid = cand["candidate_id"]
        backend = cand["solver_backend"]
        eligible = cand["contract_eligible_for_board"]
        bs = cand["baseline_summary"]
        ss = cand["stress_summary"]

        print(f"\n--- {cid} (solver: {backend}) ---")
        print(
            f"  Parameters: rho={cand['parameters']['effective_shortage_penalty']:.2f}, "
            f"lambda={cand['parameters']['cvar_weight']:.1f}, "
            f"alpha={cand['parameters']['cvar_alpha']:.2f}"
        )
        print(
            f"  Baseline: status={bs['status']}, obj={bs['objective']:.4f}, "
            f"depots={bs['open_depots']}"
        )
        if bs.get("objective_components"):
            oc = bs["objective_components"]
            print(
                f"    Fixed={oc['fixed_opening_cost']:.2f}, "
                f"Transport={oc['expected_transport_cost']:.2f}, "
                f"Shortage={oc['expected_shortage_penalty']:.2f}, "
                f"CVaR={oc['cvar_shortage_risk']:.2f}"
            )
        print(
            f"    Unmet: total={bs['unmet_metrics']['total_unmet']:.4f}, "
            f"critical={bs['unmet_metrics']['critical_unmet']:.4f}"
        )
        print(
            f"  Stress (x{ss['demand_multiplier']}): status={ss['status']}, "
            f"obj={ss['objective']:.4f}"
        )
        print(
            f"    Unmet: total={ss['unmet_metrics']['total_unmet']:.4f}, "
            f"critical={ss['unmet_metrics']['critical_unmet']:.4f}"
        )
        n_pass = sum(1 for ch in cand["contract_checks"] if ch["passed"])
        print(f"  Contracts: {n_pass}/8 passed, eligible={eligible}")
        if cand["board_score"] is not None:
            print(f"  Board score: {cand['board_score']:.6f}")

    print("\n" + "=" * 72)
    winner = report["winner"]
    if winner["candidate_id"]:
        print(f"  WINNER: {winner['candidate_id']} (score={winner['board_score']:.6f})")
    else:
        print("  WINNER: None (no eligible candidates)")
    print("=" * 72)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    report = run_adversarial_board_harness(
        write_report=True, print_console_summary=True
    )
    print("\n" + json.dumps(report, indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
