---
name: data-signal-analysis-team
description: Run a three-agent autonomous data analysis over `workshop/data` using `data-explorer-csv` and produce one markdown report with the most important findings.
---

# Data Signal Analysis Team Skill

Use this skill when the request is to analyze the workshop dataset, not to build or run an optimization model.

## Goal

Produce one autonomous analysis of `workshop/data` that surfaces:
- data structure and coverage,
- key integrity/consistency checks,
- demand/capacity/cost/risk signals relevant to the disaster-relief planning problem,
- the most important data-driven takeaways.

Do not run a team loop. Do not emit JSON artifacts. Do not generate multiple reports.

## Required Tooling

Use MCP server `data-explorer-csv`:
- `describe_csv_schema(file_path)` for schema/profile discovery,
- `query_csv(file_path, query)` for read-only SQL checks.

Rules:
1. Analyze only files under `workshop/data`.
2. One tool call targets one CSV file.
3. SQL must be read-only and reference `csv_data`.

## Three-Agent Internal Workflow

### Agent 1: Scope Agent (`what`)
- Define the exact analysis objective from the exercise statement.
- Select priority files and checks to answer:
  - Is data complete and coherent for the planning context?
  - What are the strongest operational signals (demand, capacity, arc costs, scenario risk)?
- Create a short checklist of required findings before any conclusion.

### Agent 2: Method Agent (`how`)
- Execute schema discovery on relevant CSVs using `describe_csv_schema`.
- Run focused `query_csv` checks to extract evidence.
- At minimum, cover:
  - `towns.csv`: demand base, critical towns, service targets.
  - `depots.csv`: capacities, fixed/opening-related signals.
  - `arcs.csv`: lane availability and shipping cost distribution.
  - `scenarios.csv` and `scenario_demands.csv`: uncertainty scale and probability sanity.
  - `designs.csv`, `scenario_flows.csv`, `scenario_scores.csv`: design behavior and risk/cost outcomes.
- Keep results concise and evidence-backed.

### Agent 3: Verification Agent (`works correctly`)
- Verify that all required checks were actually executed.
- Verify no claim is unsupported by a tool result.
- Verify the final report is a single markdown file and contains only high-value findings.
- Remove weak or redundant observations.

## Required Report Output

Create exactly one file:
- `workshop/materials/part-01-explorer-paradigm/01-data-explorer/skills/data-signal-analysis-team/team_output/data_analysis_report.md`

No additional output files are allowed for this skill run.

## Report Structure (Markdown)

1. `# Autonomous Data Analysis Report`
2. `## Objective and Scope`
3. `## Data Inventory`
4. `## Key Quality and Consistency Checks`
5. `## Core Signals`
6. `## Most Important Findings` (top 5 to 8)
7. `## Caveats`
8. `## Source Evidence` (file + query summary/tool call reference per finding)

## Completion Criteria

The skill is complete only if all conditions are true:
1. The output is a single markdown file at the required path.
2. Findings are grounded in `data-explorer-csv` results.
3. Analysis remains data-focused (no optimization-model design steps).
4. The report highlights the most decision-relevant elements of the dataset.
