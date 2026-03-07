---
name: prompt-contract-judge
description: LLM-based single-prompt judge (Codex / Claude Code) with strict JSON scoring and evidence.
---

# Prompt Contract Judge Skill

Use this skill to evaluate a single prompt contract with tunable judging parameters.

## Trigger
Activate when the user asks to:
- evaluate one prompt for quality/ambiguity/verification,
- compare how parameter changes affect judgment,
- generate actionable rewrite guidance with evidence.

## Required input fields
- `prompt_text`
- `stage` (`generic` | `lp` | `mip`)
- `mode` (`single` | `team` | `review`)
- `specificity_bias` (0-100)
- `thinking_effort` (`low` | `medium` | `high`)
- `strictness` (`relaxed` | `standard` | `strict`)
- `evidence_depth` (`minimal` | `standard` | `detailed`)
- `requirements` booleans for contract expectations

## Required output contract
Return JSON with:
- `completeness` (0-100)
- `ambiguity_risk` (0-100)
- `verification_readiness` (0-100)
- `rework_risk` (0-100)
- `summary`
- `parameter_effects` (array)
- `coverage` object
  - `goal_clarity`
  - `allowed_context`
  - `forbidden_context`
  - `output_schema`
  - `acceptance_checks`
  - `failure_handling`
- `blocking_issues` (array)
- `improvement_actions` (array)
- `evidence` (array of `finding` + `excerpt`)
- `confidence` (`low` | `medium` | `high`)

## Judging rules
1. Judge the single prompt text directly, not relative to a baseline.
2. Penalize unresolved terms such as "best" without a metric.
3. Respect `strictness` and `specificity_bias` when assigning severity.
4. If a required contract element is missing, emit a blocking issue.
5. Respect `evidence_depth` when choosing evidence count:
  - minimal: 1-2 excerpts
  - standard: 3-5 excerpts
  - detailed: 6-8 excerpts
6. If assumptions are inferred, cap confidence at `medium`.

## Execution checklist
1. Parse and validate all required input fields.
2. Evaluate coverage booleans strictly from prompt text content.
3. Compute the four scores consistently with strictness/specificity settings.
4. Emit blocking issues only for concrete, contract-relevant gaps.
5. Provide actionable improvement actions tied to detected gaps.
6. Return schema-valid JSON only, with no extra keys or prose.
