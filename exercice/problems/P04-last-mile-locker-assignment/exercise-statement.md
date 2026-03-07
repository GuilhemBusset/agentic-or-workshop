# P04 - Last-Mile Locker Activation and Courier Assignment

An e-commerce operator serves 120 urban demand zones for next-day parcels.
It can deliver either:
1. to parcel lockers (customer pickup), or
2. to doorstep (courier final delivery).

The operator must decide:
- which locker sites to activate,
- how many parcels from each zone go to each active locker,
- how many parcels remain doorstep deliveries,
- courier shift allocation by zone.

## Key constraints
- Locker sites have fixed opening cost and finite daily capacity.
- Couriers have shift-hour limits and per-shift parcel productivity.
- Each zone has a promised service window requiring enough same-day handling.
- Fairness rule: every zone must receive at least a minimum share of on-time service.
- Priority zones (high-volume premium SLA districts) have higher service floor.

## Objective
Minimize total cost:
- locker activation,
- transport and handling cost,
- courier labor,
- late-service penalties,
- fairness shortfall penalties.

## Data description
- `zones.csv`: Demand-zone workload and service targets (parcel volume, priority/critical flag, minimum on-time rate, same-day target).
- `lockers.csv`: Candidate locker sites with opening cost, daily capacity, and per-parcel handling cost.
- `locker_to_zone_cost.csv`: Cost and travel-time matrix for serving each zone from each locker.
- `direct_doorstep_cost.csv`: Per-zone doorstep delivery cost and baseline on-time performance.
- `courier_shifts.csv`: Shift templates and labor productivity/cost parameters (max couriers, hours, parcels/hour, cost per courier).
- `parameters.csv`: Global penalty coefficients and policy constants (for lateness, fairness shortfall, and related objectives).

## Deliverables
Return:
- active locker list,
- parcel allocation plan (zone -> locker/doorstep),
- courier shift usage,
- per-zone on-time rate and fairness compliance.
