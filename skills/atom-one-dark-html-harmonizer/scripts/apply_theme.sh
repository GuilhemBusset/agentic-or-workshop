#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
THEME_FILE="$REPO_ROOT/workshop/materials/shared/atom-one-dark-labs.css"

if [[ ! -f "$THEME_FILE" ]]; then
  echo "ERROR: Missing theme file: $THEME_FILE" >&2
  exit 1
fi

mapfile -t HTML_FILES < <(rg --files "$REPO_ROOT/workshop/materials" -g '*.html' | sort)

if [[ ${#HTML_FILES[@]} -eq 0 ]]; then
  echo "No HTML files found under workshop/materials"
  exit 0
fi

updated=0
skipped=0

for file in "${HTML_FILES[@]}"; do
  if rg -q 'atom-one-dark-labs\.css' "$file"; then
    echo "SKIP   $file"
    skipped=$((skipped + 1))
    continue
  fi

  rel_path="$(realpath --relative-to="$(dirname "$file")" "$THEME_FILE")"
  theme_link="  <link rel=\"stylesheet\" href=\"$rel_path\" />"

  tmp_file="$(mktemp)"
  if rg -q '</style>' "$file"; then
    awk -v link="$theme_link" '
      {
        print
        if (!inserted && $0 ~ /<\/style>/) {
          print link
          inserted = 1
        }
      }
    ' "$file" > "$tmp_file"
  else
    awk -v link="$theme_link" '
      {
        if (!inserted && $0 ~ /<\/head>/) {
          print link
          inserted = 1
        }
        print
      }
    ' "$file" > "$tmp_file"
  fi

  mv "$tmp_file" "$file"
  echo "PATCH  $file"
  updated=$((updated + 1))
done

echo "Applied theme link to $updated file(s); skipped $skipped already-themed file(s)."
