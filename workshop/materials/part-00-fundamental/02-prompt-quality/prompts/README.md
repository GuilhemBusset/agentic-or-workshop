# Prompt Progression for 02-prompt-quality

What is good/bad in each prompt:
- `00_mediocre_prompt.md`
  - Good: has an intent and a rough deliverable.
  - Bad: vague terms, no output schema, no acceptance checks, no failure handling, no forbidden context.
- `01_normal_prompt.md`
  - Good: clear goal, bounded allowed context, output schema, acceptance checks, and basic failure handling.
  - Bad: no forbidden context and still uses non-measurable terms like "better".
- `02_great_prompt.md`
  - Good: explicit multi-agent workflow (writer/analyzer/curator), strict context boundaries, required schema, measurable monotonic checks, and defined failure paths.
