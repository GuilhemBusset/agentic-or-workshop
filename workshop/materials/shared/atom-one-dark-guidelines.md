# Atom One Dark HTML Guidelines

## Scope
Apply these rules to all workshop lab HTML files under `workshop/materials/**`.

## Global Theme Contract
- Use `workshop/materials/shared/atom-one-dark-labs.css` as the shared stylesheet.
- Keep a single visual system across pages: dark canvas, elevated panels, consistent border radius, and One Dark semantic colors.
- Use common tokens:
  - Base: `--bg`, `--panel`, `--line`, `--shadow`
  - Text: `--ink`, `--muted`
  - Semantic: `--accent`, `--accent-2`, `--good`, `--warn`, `--bad`
- Keep interaction affordances consistent:
  - Inputs and buttons use the same dark surface and border language.
  - `:focus-visible` always uses a high-contrast blue outline.
  - Status classes (`.ok`, `.warn`, `.bad`, `.risk-*`) map to green/yellow/red.

## Shared Component Requirements
- **Page shell** (`.app`, `.page`): keep centered responsive layout and spacing.
- **Hero** (`.hero`): use elevated gradient panel with bright heading and muted supporting text.
- **Control surfaces** (`.controls`, `.control-grid`, `.control`): align labels, ranges, selects, and action buttons with identical input styling.
- **Information containers** (`.card`, `.panel`, `.insights`, `.metric`, `.metric-box`): same border, elevation, and text contrast.
- **Status and explainers** (`.status`, `.callout`, `.legend`, `.help-tooltip`, `.stage-explain`): same dark backdrop and muted body text.
- **Badges and pills** (`.chip`, `.pill`, `.stage-pill`): consistent pill geometry and semantic active state.

## Per-File Component Map

### 1) `part-00-fundamental/00-llm-architecture/00-llm-architecture-primer.html`
- Keep graph-focused layout (`.layout`, `.graphs`, `.graph-card`) unchanged.
- Preserve architecture controls (`.profile`, `.switches`, `.switch`) and navigation (`.next-link`) behavior.
- Ensure graph legends and stage pills remain readable in dark mode.

### 2) `part-00-fundamental/01-context-window/00-context-window-lab.html`
- Keep two-column workspace structure (`.grid`, `.comparison`) responsive.
- Preserve simulation controls, metrics cards, and chart readability (`#curve`, `.legend`).
- Keep curated/bloated chips semantically distinct while visually aligned with the shared theme.

### 3) `part-00-fundamental/02-prompt-quality/00-explorer-single-shot-lab.html`
- Preserve split workspace (`.main`) with prompt editor + scoring panel.
- Keep checklist cards (`.checklist`, `.chk`) and score bars (`.bar`, `.bar.risk`) visually consistent with shared semantic colors.
- Maintain priority contrast for actionable controls (`button.primary`, `#evaluateBtn`).

### 4) `part-01-explorer-paradigm/02-visual-explorer/00-visual-explorer-live-lab.html`
- Preserve control dense grid and timeline UX (`.timeline-buttons`, `#timelineRange`).
- Keep network visibility and legibility (`#network`, `.legend`, `.node-label`, `.arc`) under dark surfaces.
- Preserve diagnostics hierarchy (`.cards`, `.metrics`, `.explain`, `.footer`) with shared card styling.

## Application Workflow
1. Ensure each HTML includes:
   - `<link rel="stylesheet" href="../../shared/atom-one-dark-labs.css" />`
2. Keep page-specific layout and behavior CSS in each file.
3. Apply shared theme overrides through the linked stylesheet.
4. Validate all pages still render controls, metrics, and visual outputs clearly on desktop and mobile.
