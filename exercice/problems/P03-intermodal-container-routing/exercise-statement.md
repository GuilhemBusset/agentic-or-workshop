# P03 - Intermodal Container Routing with Contract Tiers

A large e-commerce logistics operator must move import containers from 3 ports to 20 inland fulfillment and sort destinations over a 5-day planning window.
Available modes: truck, rail, and barge.

The operator must decide:
1. Route and mode for each shipment.
2. Whether to activate carrier contract tiers (fixed fee + discounted variable rate).
3. How to balance transport cost, late delivery penalties, and emissions.

## Complexity drivers
- Arc capacities by mode and day are limited.
- Some destinations have tight due days; late arrivals incur penalties.
- Rail and barge have lower emissions but longer transit times.
- Contract tiers are stepwise: activating a tier changes marginal cost only after volume thresholds.
- Total emissions must stay under a global cap.

## Objective
Minimize total cost:
- transport variable cost,
- contract activation fees,
- late delivery penalties,
- optional overflow penalties if demand is not moved on time.

## Data description
- `shipments.csv`: Container demand to route (origin port, inland destination, due day, volume in TEU, where TEU means twenty-foot equivalent unit, and lateness penalty).
- `arcs.csv`: Intermodal network arcs (from/to nodes, mode, transit time, unit cost, emissions intensity, and daily capacity).
- `contract_tiers.csv`: Optional carrier contract tiers by mode (activation threshold, fixed fee, and per-TEU discount).
- `parameters.csv`: Global planning constants (for example horizon length and total emissions cap).

## Deliverables
Return:
- shipment routing plan,
- activated contract tiers,
- arrival-day and lateness report,
- cost breakdown and total emissions.
