#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
THEME_FILE="$REPO_ROOT/workshop/materials/shared/atom-one-dark-labs.css"

mapfile -t HTML_FILES < <(rg --files "$REPO_ROOT/workshop/materials" -g '*.html' | sort)

if [[ ! -f "$THEME_FILE" ]]; then
  echo "FAIL: Missing shared theme file: $THEME_FILE"
  exit 1
fi

missing_link=0
for file in "${HTML_FILES[@]}"; do
  if rg -q 'atom-one-dark-labs\.css' "$file"; then
    echo "OK   link present: $file"
  else
    echo "FAIL link missing: $file"
    missing_link=$((missing_link + 1))
  fi
done

declare -a REQUIRED_SELECTORS=(
  ":root"
  ".hero"
  ".card"
  ".panel"
  ".controls"
  ".control-grid"
  ".status"
  ".chip"
  ".pill"
  "#network"
  ".bar.risk"
)

missing_selector=0
for selector in "${REQUIRED_SELECTORS[@]}"; do
  if rg -q -F "$selector" "$THEME_FILE"; then
    echo "OK   selector covered: $selector"
  else
    echo "FAIL selector missing: $selector"
    missing_selector=$((missing_selector + 1))
  fi
done

check_patterns() {
  local file="$1"
  shift
  local -a patterns=("$@")
  local missing=0

  for pattern in "${patterns[@]}"; do
    if rg -q -F "$pattern" "$file"; then
      echo "OK   component preserved ($pattern): $file"
    else
      echo "FAIL component missing ($pattern): $file"
      missing=$((missing + 1))
    fi
  done

  return "$missing"
}

component_failures=0

llm_file="$REPO_ROOT/workshop/materials/part-00-fundamental/00-llm-architecture/00-llm-architecture-primer.html"
if [[ -f "$llm_file" ]]; then
  if ! check_patterns "$llm_file" "class=\"hero\"" "class=\"layout\"" "class=\"profile\"" "id=\"graphA\"" "id=\"graphB\""; then
    component_failures=$((component_failures + 1))
  fi
fi

context_file="$REPO_ROOT/workshop/materials/part-00-fundamental/01-context-window/00-context-window-lab.html"
if [[ -f "$context_file" ]]; then
  if ! check_patterns "$context_file" "class=\"hero\"" "class=\"grid\"" "class=\"comparison\"" "id=\"curve\"" "id=\"curatedMetrics\""; then
    component_failures=$((component_failures + 1))
  fi
fi

prompt_file="$REPO_ROOT/workshop/materials/part-00-fundamental/02-prompt-quality/00-explorer-single-shot-lab.html"
if [[ -f "$prompt_file" ]]; then
  if ! check_patterns "$prompt_file" "class=\"hero\"" "class=\"controls\"" "class=\"prompt-card\"" "class=\"checklist\"" "id=\"evaluateBtn\""; then
    component_failures=$((component_failures + 1))
  fi
fi

visual_file="$REPO_ROOT/workshop/materials/part-01-explorer-paradigm/02-visual-explorer/00-visual-explorer-live-lab.html"
if [[ -f "$visual_file" ]]; then
  if ! check_patterns "$visual_file" "class=\"hero\"" "class=\"control-grid\"" "id=\"network\"" "id=\"constraintCards\"" "class=\"explain\""; then
    component_failures=$((component_failures + 1))
  fi
fi

if [[ $missing_link -gt 0 || $missing_selector -gt 0 || $component_failures -gt 0 ]]; then
  echo "Theme evaluation failed: missing_link=$missing_link missing_selector=$missing_selector component_failures=$component_failures"
  exit 1
fi

echo "Theme evaluation passed for ${#HTML_FILES[@]} HTML file(s)."
