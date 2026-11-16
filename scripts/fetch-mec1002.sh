#!/usr/bin/env bash
# Copy the MEC1002 (Electrical Power and Electromechanical Systems) lecture
# notes, images and interactive elements from a checkout of
# nigelk-dev/ElectricalPowerNotes into mec1002/notes/. The lecture PDFs and the
# Lecture 5 Moodle package are not used.
#
# scripts/notes.py then turns each LecN/LecN.md into a page, with every
# interactive element embedded live where the notes refer to it.
#
# Usage: scripts/fetch-mec1002.sh [path-to-ElectricalPowerNotes-checkout]
# Without an argument, the repo is cloned into a temporary directory (it is
# private, so this needs GitHub credentials that can read it).
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
src="${1:-}"
if [[ -z "$src" ]]; then
  src="$(mktemp -d)"
  git clone --depth 1 https://github.com/nigelk-dev/ElectricalPowerNotes "$src"
fi
src="$(cd "$src" && pwd)"

dest="$root/mec1002/notes"
rm -rf "$dest"
mkdir -p "$dest"

cp -R "$src/shared" "$dest/shared"
for lec in "$src"/Lec*/; do
  name="$(basename "$lec")"
  mkdir -p "$dest/$name"
  cp "$lec/$name.md" "$dest/$name/"
  for sub in images interactive; do
    [[ -d "$lec/$sub" ]] && cp -R "$lec/$sub" "$dest/$name/$sub"
  done
done

python3 "$root/scripts/notes.py" mec1002 "$src" "$dest"

find "$dest" -name '*.md' | sed "s|^$root/||" | sort
