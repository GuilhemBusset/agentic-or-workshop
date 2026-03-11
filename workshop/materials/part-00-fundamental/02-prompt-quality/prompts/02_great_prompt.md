# Prompt 02 - Great

Build the Explorer Paradigm Single Prompt Judge Lab as a single-file HTML page with inline CSS and JavaScript.

Goal:
Create `workshop/materials/part-00-fundamental/02-prompt-quality/00-explorer-single-shot-lab.html` that lets students write a prompt, send it to a local FastAPI judge backend, and view contract quality diagnostics. The page is a teaching tool for PhD students learning about prompt contract quality in agentic coding workflows.

Allowed context:
- `workshop/materials/part-00-fundamental/02-prompt-quality/llm_judge_service.py` (FastAPI backend -- read for API contract)
- `workshop/materials/part-00-fundamental/02-prompt-quality/skills/prompt-contract-judge/SKILL.md` (judge skill -- read for scoring dimensions)
- `workshop/materials/part-00-fundamental/02-prompt-quality/` (target output directory)
- `workshop/materials/shared/atom-one-dark-labs.css` (shared dark theme -- link as stylesheet)

Forbidden context:
- Do not modify `llm_judge_service.py` or `SKILL.md`
- Do not import external CDN libraries (jQuery, Bootstrap, Tailwind, etc.)
- Do not create additional files beyond the single HTML page
- Do not add any backend routes or change the `/judge` API contract

Team roles:
1. `LayoutBuilder`
   - Build the page structure with these sections: hero banner, controls bar, two-column main (left: Prompt Studio with textarea + contract checklist; right: Contract Diagnostics with metric cards, coverage pills, guidance callout, parameter effects, evidence list), footer.
   - The controls bar must include exactly 8 controls: Stage (select: generic/lp/mip), Lens (select: single/team/review), Specificity Bias (range: 0-100), Thinking Effort (select: low/medium/high), Strictness (select: relaxed/standard/strict), Evidence Depth (select: minimal/standard/detailed), Judge Endpoint (select with local FastAPI option), Actions (Evaluate Prompt button + Load Stage Example button).
   - All CSS must be inline in a `<style>` block. Use CSS custom properties for theming.
   - Include responsive breakpoints: 3 tiers at 1260px, 1100px, 780px.

2. `IntegrationBuilder`
   - Wire the "Evaluate Prompt" button to `POST /judge` at the selected endpoint URL.
   - Request payload must match `JudgeRequest` from `llm_judge_service.py`: `{stage, mode, specificity_bias, thinking_effort, strictness, evidence_depth, prompt_text, requirements}`.
   - Parse the `JudgeResponse` and render: 4 metric bars (completeness, ambiguity_risk, verification_readiness, rework_risk), 6 coverage pills (goal_clarity, allowed_context, forbidden_context, output_schema, acceptance_checks, failure_handling), summary + blocking_issues + improvement_actions in guidance, parameter_effects list, evidence list with finding + excerpt.
   - Implement "Load Stage Example" to populate the textarea with hardcoded preset prompts for each stage.
   - Implement backend detection via `GET /health` to adapt control labels (Codex vs Claude Code).

3. `QualityReviewer`
   - Verify all acceptance checks pass before finalizing.
   - Verify the page loads without console errors when opened in a browser (no JS syntax errors, no missing references).
   - Verify the judge request payload matches the Pydantic schema exactly (field names, types, value ranges).

Required output schema:
- `files_changed`: list of `{path, action}` where action is "created" or "modified"
- `layout_summary`: `{sections: list[str], controls_count: int, responsive_breakpoints: list[str]}`
- `api_integration`: `{endpoint, method, request_fields: list[str], response_fields: list[str]}`
- `acceptance_checks`: list of `{check: str, passed: bool}`
- `quality_review`: `{console_errors: int, schema_mismatches: list[str]}`

Acceptance checks:
- The file `00-explorer-single-shot-lab.html` is a single self-contained HTML file (no external JS dependencies).
- The controls bar contains exactly 8 control groups.
- POST to `/judge` sends a payload with all 8 required fields from `JudgeRequest`.
- All 4 metric scores render as labeled progress bars with percentage values.
- All 6 coverage dimensions render as pills with ok/missing state.
- The checklist contains exactly 6 checkboxes matching the 6 coverage dimensions.
- Responsive layout collapses correctly at each of the 3 breakpoints.
- Status area shows loading state during fetch and error state on failure.

Failure handling:
- If the `/judge` endpoint returns a non-200 status, parse the `detail` field from the error body and display it in the status area. If error body parsing fails, show the HTTP status code.
- If the `/health` endpoint is unreachable during backend detection, default to "codex" backend labeling and continue without error.
- If the judge response JSON is missing expected fields, render available data and show "partial result" in the status area.
