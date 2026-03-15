# P02 - Multi-Echelon Temperature-Controlled Distribution

A large e-commerce grocery operator distributes temperature-sensitive products from 6 upstream fulfillment plants to 10 candidate regional cross-docks and then to 140 delivery stations.
Planning horizon: 3 weekly periods and 5 demand scenarios.

The operator must decide:
1. Which candidate cross-docks to activate (fixed cost).
2. Weekly shipment volumes on plant->hub and hub->station arcs.
3. How much demand can remain unmet (penalized, especially for premium-service stations).

## Operational complexity
- Product is perishable; inventory carried between weeks loses value via spoilage.
- Arc reliability differs; low-reliability arcs increase expected losses.
- Demand is scenario-based with probabilities.
- Premium-service stations must meet stricter service levels across scenarios.

## Objective
Minimize expected total cost:
- cross-dock activation + transportation,
- expected spoilage/loss,
- unmet-demand penalties,
- reliability-risk penalties.

## Data description
- `plants.csv`: Upstream plant supply limits (weekly production/dispatch capacity by plant).
- `hubs.csv`: Candidate cross-docks with fixed opening cost and capacity limits (storage and throughput).
- `stations.csv`: Downstream delivery stations with service class flag (`critical_flag` for premium-service requirements).
- `plant_to_hub_arcs.csv`: Feasible plant-to-hub lanes with per-unit transport cost, weekly capacity, and reliability.
- `hub_to_station_arcs.csv`: Feasible hub-to-station lanes with per-unit transport cost, weekly capacity, and reliability.
- `demand_scenarios.csv`: Scenario-based station demand by week with scenario probabilities.
- `model_parameters.csv`: Global model constants (for example spoilage rate, service-level targets, and penalty coefficients).

## Deliverables
Provide:
- selected cross-docks,
- flows by period and scenario,
- unmet demand by station/period/scenario,
- expected cost and service-level metrics for premium-service stations.
