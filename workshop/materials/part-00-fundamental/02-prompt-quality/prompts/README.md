# Prompt Progression for 02-prompt-quality

What is good/bad in each prompt:
- `00_mediocre_prompt.md`
  - Good: has an intent ("build a web page") and a rough deliverable ("let students type a prompt and see how good it is").
  - Bad: vague adjectives ("nice", "useful", "practical"), no allowed context, no forbidden context, no output schema, no acceptance checks, no failure handling, hand-wavy reference to judge service without API details.
- `01_normal_prompt.md`
  - Good: clear goal, bounded allowed context (3 paths), output schema (4 fields), acceptance checks (5 checks), and basic failure handling (1 case).
  - Bad: no forbidden context and still uses non-measurable terms like "better influence the judge" and "user-friendly".
- `02_great_prompt.md`
  - Good: explicit multi-agent workflow (LayoutBuilder/IntegrationBuilder/QualityReviewer), strict context boundaries (4 allowed, 4 forbidden), structured output schema (5 fields with nested types), 8 measurable acceptance checks (all binary pass/fail), and 3 defined failure paths with specific recovery behaviors.
