# Component Guidelines

## Shared component model
- Shell: `.app`, `.page`
- Hero: `.hero`
- Controls: `.controls`, `.control-grid`, `.control`, form controls
- Content cards: `.card`, `.panel`, `.insights`, `.metrics`, `.metric`, `.metric-box`
- Status/explainer: `.status`, `.legend`, `.help-tooltip`, `.callout`, `.stage-explain`
- Badge primitives: `.chip`, `.pill`, `.stage-pill`

## Per-file requirements

### `00-llm-architecture-primer.html`
- Keep graph composition selectors: `.graphs`, `.graph-card`, `.graph-wrap`.
- Keep profile interaction selectors: `.profile`, `.switch`, `.stage-row`, `.stage-pill`.

### `00-context-window-lab.html`
- Keep control/result split selectors: `.grid`, `.comparison`, `.controls`, `.results`.
- Preserve chart readability for `#curve` and `.legend`.

### `00-explorer-single-shot-lab.html`
- Keep prompt workspace selectors: `.prompt-card`, `.checklist`, `.chk`, `.cards`, `.insights`.
- Preserve risk bar semantic selectors: `.bar`, `.bar.risk`, `.risk`.

### `00-visual-explorer-live-lab.html`
- Keep dense simulation selectors: `.control-grid`, `.timeline-buttons`, `.network-wrap`.
- Preserve diagnostics selectors: `.cards`, `.metrics`, `.explain`, `.footer`, `.legend`.
- Preserve network readability selectors: `#network`, `.node-label`, `.arc`, `.town-ring`.

## Token policy
Use shared theme tokens from `atom-one-dark-labs.css`; do not introduce unrelated per-page palettes unless functionally required.
