# Disaster Relief Network Planning - Problem Statement

A humanitarian relief agency must supply 12 towns from a network of 6 candidate depots connected by 72 shipping arcs.  
Each town has required demand, and four towns are designated as critical (`T03`, `T04`, `T07`, `T12`) with a minimum service target of 95%.

The agency faces two linked decisions:

1. Operational allocation (transportation): determine shipment quantities from depots to towns to satisfy demand at minimum logistics cost, subject to depot capacities and arc availability.
2. Network design (facility location): decide which depots to open, paying fixed opening costs, and route flows only through opened depots.

Unmet demand is allowed but penalized. Depot capacity can be used only when the depot is open.

Demand is uncertain and represented by 8 scenarios with associated probabilities. The selected network design must perform well across scenarios, balancing expected cost and shortage risk.

The final plan should specify:
- which depots are open,
- how much each open depot ships to each town,
- unmet demand by town and scenario,
- aggregate performance metrics (cost, expected unmet demand, and risk-oriented shortage indicators).
