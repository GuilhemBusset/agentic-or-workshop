---
name: atom-one-dark-html-harmonizer
description: Standardize repository HTML pages to a shared Atom One Dark visual system. Use when asked to align look and feel across multiple HTML files, generate per-page UI component guidelines, apply a consistent theme stylesheet, and verify compliance across all HTML labs.
---

# Atom One Dark HTML Harmonizer

Apply a consistent One Dark visual language across all lab HTML files while preserving each page's layout and behavior.

## Required Inputs
- Shared stylesheet: `workshop/materials/shared/atom-one-dark-labs.css`
- Component guideline reference: `references/component-guidelines.md`

## Workflow

1. Inventory target files:
```bash
rg --files workshop/materials -g '*.html'
```

2. Confirm shared theme file exists:
```bash
test -f workshop/materials/shared/atom-one-dark-labs.css
```

3. Apply theme link to each HTML file (idempotent):
```bash
bash skills/atom-one-dark-html-harmonizer/scripts/apply_theme.sh
```

4. Run compliance checks:
```bash
bash skills/atom-one-dark-html-harmonizer/scripts/evaluate_theme.sh
```

5. If evaluation reports missing coverage, patch shared CSS selectors or HTML link insertion and rerun step 4.

## Rules
- Preserve each page's content and JS behavior.
- Do not remove existing page-specific layout selectors unless replacing them with equivalent behavior.
- Keep color semantics stable: `ok/good`, `warn`, `bad/risk`.
- Keep controls and hero sections visually consistent across all pages.

## Reporting
Report:
- Which files were updated.
- Which component families were normalized.
- Evaluation result summary and any residual gaps.
