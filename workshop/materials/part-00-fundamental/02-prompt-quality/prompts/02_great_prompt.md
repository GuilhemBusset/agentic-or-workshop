# Prompt 02 - Great

Create a 3-agent workflow to produce high-quality prompt examples for the single-prompt judge lab.

Goal:
Produce exactly 3 prompts (`mediocre`, `normal`, `great`) in `workshop/materials/part-00-fundamental/02-prompt-quality/prompts/`.
Each prompt must be usable as one input in the lab and show increasing contract quality.

Allowed context:
- `workshop/materials/part-00-fundamental/02-prompt-quality/00-explorer-single-shot-lab.html`
- `workshop/materials/part-00-fundamental/02-prompt-quality/llm_judge_service.py`
- `workshop/materials/part-00-fundamental/02-prompt-quality/skills/prompt-contract-judge/SKILL.md`
- `workshop/materials/part-00-fundamental/02-prompt-quality/skills/prompt-contract-judge/examples.md`

Forbidden context:
- Any file outside `workshop/materials/part-00-fundamental/02-prompt-quality/`
- Internet sources
- Changes to backend scoring logic

Team roles:
1. `PromptWriter`
- Draft 3 prompts with explicit progression from weak to strong.
- Keep prompts aligned with the lab objective: measurable prompt-contract quality.
2. `PromptAnalyzer`
- Evaluate each draft with the prompt-contract-judge skill using:
  - `stage=generic`
  - `mode=review`
  - `strictness=standard`
  - `specificity_bias=60`
  - `evidence_depth=standard`
- Return for each prompt: `completeness`, `ambiguity_risk`, `verification_readiness`, `rework_risk`, and `blocking_issues`.
3. `Curator`
- Decide whether another iteration is required.
- Iterate if any monotonicity rule fails:
  - `completeness`: mediocre < normal < great
  - `verification_readiness`: mediocre < normal < great
  - `rework_risk`: mediocre > normal > great

Required output schema:
- `prompt_files`: list of `{name, goal, prompt_text}`
- `judge_results`: list of `{name, scores, top_blocker, top_improvement}`
- `curator_decision`: `{iterate: bool, rationale: str}`
- `acceptance_checks`: list of pass/fail checks

Acceptance checks:
- Exactly 3 prompts are produced.
- Prompt quality progression is explicit and monotonic.
- The great prompt includes: allowed context, forbidden context, output schema, acceptance checks, and failure handling.
- Curator decision is evidence-based from analyzer output.

Failure handling:
- If required monotonicity contains a tie, set `iterate=true` and request one targeted rewrite pass.
- If analyzer output is missing required fields, stop and return a structured error summary.
