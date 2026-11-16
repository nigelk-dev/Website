#!/usr/bin/env bash
# Copy the MM453 (Manufacturing Automation for Assembly and Inspection) notes,
# images and Applet Lab from a checkout of nigelk-dev/ManufacturingAutomationNotes
# into mm453/notes/. The slide-pack PDFs, the notes PDF and its book build are
# not used.
#
# scripts/notes.py then writes one page per chapter, with each chapter's
# applets embedded live in place of its "Suggested interactive applets" table.
#
# Usage: scripts/fetch-mm453.sh [path-to-ManufacturingAutomationNotes-checkout]
# Without an argument, the repo is cloned into a temporary directory (it is
# private, so this needs GitHub credentials that can read it).
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
src="${1:-}"
if [[ -z "$src" ]]; then
  src="$(mktemp -d)"
  git clone --depth 1 https://github.com/nigelk-dev/ManufacturingAutomationNotes "$src"
fi
src="$(cd "$src" && pwd)"

dest="$root/mm453/notes"
rm -rf "$dest"
mkdir -p "$dest/applets"

cp -R "$src/notes/images" "$dest/images"
cp "$src"/applets/*.html "$src"/applets/*.css "$src"/applets/*.js "$dest/applets/"

python3 "$root/scripts/notes.py" mm453 "$src" "$dest"

find "$dest" -maxdepth 1 -name '*.md' | sed "s|^$root/||" | sort
