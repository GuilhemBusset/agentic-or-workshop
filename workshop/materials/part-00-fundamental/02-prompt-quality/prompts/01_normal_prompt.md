# Prompt 01 - Normal

Goal: Build the Explorer Paradigm Single Prompt Judge Lab as a single HTML page that lets students write a prompt, send it to a backend LLM judge, and view contract quality scores.

Allowed context:
- `workshop/materials/part-00-fundamental/02-prompt-quality/llm_judge_service.py` (the FastAPI judge backend)
- `workshop/materials/part-00-fundamental/02-prompt-quality/skills/prompt-contract-judge/SKILL.md` (the judge skill definition)
- `workshop/materials/part-00-fundamental/02-prompt-quality/` (target directory for the output file)

Required output schema:
- `files_changed`: list of created/modified files
- `page_structure`: description of layout sections (hero, controls, prompt studio, diagnostics)
- `api_integration`: how the page calls the judge endpoint
- `acceptance_checks`: list of pass/fail checks

Acceptance checks:
- Page has a textarea for prompt input and an "Evaluate Prompt" button.
- Clicking "Evaluate Prompt" sends a POST to `http://127.0.0.1:8008/judge` and displays results.
- Results show completeness, ambiguity risk, verification readiness, and rework risk as visual bars.
- Page renders coverage pills showing which contract elements are present/missing.
- Controls for strictness, specificity bias, and evidence depth are present and better influence the judge.

Failure handling:
- If the judge endpoint is unreachable, show a user-friendly error message in the status area.
