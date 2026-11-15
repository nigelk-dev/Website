#!/usr/bin/env bash
# Copy course files from a checkout of nigelk-dev/MEC1019_Sustainable_Processes
# into mec1019/materials/ with URL-friendly names
# (e.g. "Microcontrollers_part 6 (potentiometers).pdf" -> "microcontrollers-part-6-potentiometers.pdf").
#
# Usage: scripts/fetch-mec1019.sh [path-to-MEC1019-checkout]
# Without an argument, the repo is cloned into a temporary directory.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
src="${1:-}"
if [[ -z "$src" ]]; then
  src="$(mktemp -d)"
  git clone --depth 1 https://github.com/nigelk-dev/MEC1019_Sustainable_Processes "$src"
fi

dest="$root/mec1019/materials"
rm -rf "$dest"
mkdir -p "$dest"

find "$src" -path "$src/.git" -prune -o -type f \( -iname '*.pdf' -o -iname '*.pptx' -o -iname '*.docx' -o -iname '*.ino' -o -iname '*.png' -o -iname '*.jpg' \) -print0 |
while IFS= read -r -d '' f; do
  name="$(basename "$f")"
  ext="${name##*.}"
  stem="${name%.*}"
  slug="$(printf '%s' "$stem" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')"
  cp "$f" "$dest/$slug.$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"
done

ls -1 "$dest"
