#!/usr/bin/env bash
# Copy the Markdown notes, images and interactive applets from a checkout of
# nigelk-dev/MEC1019_Sustainable_Processes into mec1019/notes/ so Quarto can
# render them. The lecture PDFs and PowerPoint are not used.
#
# scripts/notes.py then writes one page per note, with every applet embedded
# live where the notes refer to it.
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
src="$(cd "$src" && pwd)/notes"

dest="$root/mec1019/notes"
rm -rf "$dest"
mkdir -p "$dest/applets"

cp -R "$src/images" "$dest/images"
# Applets with their CSS/JS and any vendored libraries (e.g. vendor/katex/);
# skip the Python helper that generates sketches.js.
cp -R "$src/applets/." "$dest/applets/"
find "$dest/applets" -type f -name '*.py' -delete

# Applets from the MEC1019 repo that this site leaves out. Lines in the notes
# that link to them are dropped below.
excluded_applets=(led-resistor.html)
for a in "${excluded_applets[@]}"; do rm -f "$dest/applets/$a"; done

python3 "$root/scripts/notes.py" mec1019 "$src" "$dest" "${excluded_applets[@]}"

find "$dest" -maxdepth 2 -type f | sed "s|^$root/||" | sort
