# Prompt Contract Judge: Parameter Reference + Prompt Delta Coach Examples

## Parameters
- `stage`: selects the domain framing the judge should expect in the prompt contract.
- `mode`: selects the collaboration lens used to interpret structure and responsibilities in the prompt.
- `specificity_bias`: controls how strongly the judge penalizes vague or underspecified language.
- `thinking_effort`: controls the depth of reasoning the judge uses when producing its assessment.
- `strictness`: controls grading severity when required contract elements are weak or missing.
- `evidence_depth`: controls how much supporting evidence the judge should return in its output.
- `requirements`: defines which contract elements are currently required for coverage checks.
  - `goal_clarity`: whether an explicit objective/scope is required.
  - `allowed_context`: whether allowed files/data boundaries are required.
  - `forbidden_context`: whether explicit out-of-scope boundaries are required.
  - `output_schema`: whether explicit output fields/shape are required.
  - `acceptance_checks`: whether verifiable completion checks are required.
  - `failure_handling`: whether ambiguity/error handling instructions are required.

## Prompt Examples (Prompt Delta Coach)

### Mode = `single`
```md
Goal: implement Prompt Delta Coach as one direct coding workflow.

Allowed context:
- workshop/materials/part-00-fundamental/02-prompt-quality/00-explorer-single-shot-lab.html

Required output schema:
- files_changed
- implementation_summary
- acceptance_checks

Acceptance checks:
- One end-to-end implementation path is provided.

Failure handling:
- If requirement is unclear, state one assumption and continue.
```

### Mode = `team`
```md
Goal: implement Prompt Delta Coach with a 3-role team workflow.

Team roles:
1. Analyzer
2. Instructor
3. Reviewer

Allowed context:
- workshop/materials/part-00-fundamental/02-prompt-quality/00-explorer-single-shot-lab.html

Required output schema:
- analyzer_output
- instructor_output
- reviewer_output
- merged_change_plan
- acceptance_checks

Acceptance checks:
- Each role output is explicit and non-empty.

Failure handling:
- If role outputs conflict, reviewer decides and records rationale.
```

### Mode = `review`
```md
Goal: review Prompt Delta Coach implementation requirements only.

Allowed context:
- workshop/materials/part-00-fundamental/02-prompt-quality/00-explorer-single-shot-lab.html

Required output schema:
- blocking_issues
- improvement_actions
- acceptance_checks

Acceptance checks:
- Every issue maps to at least one missing contract element.

Failure handling:
- If evidence is insufficient, return a structured insufficiency note.
```

### Specificity Bias (Low)
```md
Build Prompt Delta Coach for the lab.
Keep it practical.
```

### Specificity Bias (High)
```md
Goal: implement Prompt Delta Coach panel in the single-shot judge lab UI.

Allowed context:
- workshop/materials/part-00-fundamental/02-prompt-quality/00-explorer-single-shot-lab.html

Forbidden context:
- Backend scoring logic changes

Required output schema:
- files_changed
- ui_elements_added
- acceptance_checks

Acceptance checks:
- Includes a before/after prompt diff section.
- Includes top 3 blocking issues from latest judge output.
- Includes exactly one next rewrite action linked to weakest metric.

Failure handling:
- If judge payload is missing required fields, show fallback UI and continue.
```

### Strictness = `relaxed`
```md
Goal: add Prompt Delta Coach UI section.

Required output schema:
- summary
- acceptance_checks

Acceptance checks:
- Prompt Delta Coach section exists.
```

### Strictness = `standard`
```md
Goal: add Prompt Delta Coach UI section with contract-aware guidance.

Allowed context:
- workshop/materials/part-00-fundamental/02-prompt-quality/00-explorer-single-shot-lab.html

Required output schema:
- files_changed
- implementation_summary
- acceptance_checks

Acceptance checks:
- Displays before/after prompt diff.
- Displays top 3 blocking issues.
- Displays one next rewrite action.

Failure handling:
- If required input is missing, record assumption and continue.
```

### Strictness = `strict`
```md
Goal: implement Prompt Delta Coach with explicit contract enforcement.

Allowed context:
- workshop/materials/part-00-fundamental/02-prompt-quality/00-explorer-single-shot-lab.html
- workshop/materials/part-00-fundamental/02-prompt-quality/llm_judge_service.py

Forbidden context:
- Changes to judge schema fields
- Hidden dependencies outside allowed context

Required output schema:
- files_changed
- implementation_summary
- contract_coverage_report
- acceptance_checks

Acceptance checks:
- All required Prompt Delta Coach sections are present.
- No judge API contract regressions are introduced.
- Every UI claim maps to an observable field in judge output.

Failure handling:
- If any acceptance check cannot be validated, stop and return explicit blocker list.
```

### Evidence Depth = `minimal`
```md
Goal: implement Prompt Delta Coach and provide minimal evidence.

Required output schema:
- files_changed
- acceptance_checks
- evidence

Acceptance checks:
- Evidence contains 1-2 excerpts.
```

### Evidence Depth = `standard`
```md
Goal: implement Prompt Delta Coach and provide standard evidence.

Required output schema:
- files_changed
- acceptance_checks
- evidence

Acceptance checks:
- Evidence contains 3-5 excerpts.
```

### Evidence Depth = `detailed`
```md
Goal: implement Prompt Delta Coach and provide detailed evidence.

Required output schema:
- files_changed
- acceptance_checks
- evidence

Acceptance checks:
- Evidence contains 6-8 excerpts.
```

### Thinking Effort = `low`
```md
Goal: implement Prompt Delta Coach quickly with concise reasoning.

Required output schema:
- files_changed
- implementation_summary
- acceptance_checks
```

### Thinking Effort = `medium`
```md
Goal: implement Prompt Delta Coach with balanced reasoning depth.

Required output schema:
- files_changed
- implementation_summary
- acceptance_checks
- improvement_actions
```

### Thinking Effort = `high`
```md
Goal: implement Prompt Delta Coach with deep reasoning and explicit traceability.

Required output schema:
- files_changed
- implementation_summary
- acceptance_checks
- parameter_effects
- evidence
```
