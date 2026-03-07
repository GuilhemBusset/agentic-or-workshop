# P05 - Disruption Recovery Routing with Contra-Flow and Overflow Nodes

After severe weather, a large e-commerce network must clear outbound parcel backlog from 80 demand zones to 50 temporary overflow processing nodes over 6 recovery phases.
The operator can use contracted shuttle capacity and road corridors, and may activate contra-flow on selected roads.

The planner must decide:
1. Overflow-node assignment and phased backlog flow from each zone.
2. Shuttle allocation by phase and zone.
3. Contra-flow activation on reversible corridors.

## Constraints
- Overflow-node capacities are finite.
- Road capacities are phase-dependent and scenario-dependent.
- Contra-flow can increase outbound capacity but has setup cost and limits.
- A share of backlog must be shuttle-served due local driver/vehicle shortages.
- Priority zones must clear earlier with stricter completion targets.

## Objective
Minimize expected service-loss proxy:
- weighted backlog delay,
- unmet backlog penalty by phase end,
- contra-flow activation cost,
- excessive shuttle repositioning cost.

## Data description
- `zones.csv`: Initial backlog and service-priority settings by demand zone (backlog units, priority weight, shuttle-only share, minimum clearance target).
- `overflow_nodes.csv`: Candidate temporary processing nodes with capacity and setup cost.
- `phases.csv`: Recovery-phase structure (phase duration and share of demand/backlog released each phase).
- `road_arcs.csv`: Directed road network with base per-phase capacities, travel times, and optional reversible-group membership.
- `contraflow_groups.csv`: Contra-flow control parameters for reversible corridors (max active phases, capacity multiplier, activation cost).
- `scenarios.csv`: Scenario-dependent capacity multipliers by phase and arc, with scenario probabilities.
- `shuttle_fleet.csv`: Shuttle resources by depot (fleet size, carrying capacity, max roundtrips, reposition cost).
- `shuttle_access.csv`: Zone-to-shuttle-depot access map and shuttle trip times.
- `parameters.csv`: Global penalty and weighting coefficients for unmet backlog and delay.

## Deliverables
Provide:
- phase-by-phase cleared backlog by zone and overflow node,
- selected contra-flow actions,
- shuttle deployment plan,
- expected uncleared backlog and weighted completion-time metrics.
