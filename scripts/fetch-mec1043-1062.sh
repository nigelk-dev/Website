#!/usr/bin/env bash
# Copy the MEC1043/1062 (Manufacturing Automation for Assembly and Inspection) notes,
# images and Applet Lab from a checkout of nigelk-dev/ManufacturingAutomationNotes
# into mec1043-1062/notes/. The slide-pack PDFs, the notes PDF and its book build are
# not used.
#
# scripts/notes.py then writes one page per chapter, with each chapter's
# applets embedded live in place of its "Suggested interactive applets" table.
#
# Usage: scripts/fetch-mec1043-1062.sh [path-to-ManufacturingAutomationNotes-checkout]
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

dest="$root/mec1043-1062/notes"
rm -rf "$dest"
mkdir -p "$dest/applets"

cp -R "$src/notes/images" "$dest/images"
cp "$src"/applets/*.html "$src"/applets/*.css "$src"/applets/*.js "$dest/applets/"

python3 "$root/scripts/notes.py" mec1043-1062 "$src" "$dest"

find "$dest" -maxdepth 1 -name '*.md' | sed "s|^$root/||" | sort
