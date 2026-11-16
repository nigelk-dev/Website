#!/usr/bin/env bash
# Copy the Markdown notes, images and interactive applets from a checkout of
# nigelk-dev/MEC1019_Sustainable_Processes into mec1019/notes/ so Quarto can
# render them. The lecture PDFs and PowerPoint are not used.
#
# Each note gets a YAML title (taken from its first "# " heading), its
# "Source: <file>.pdf" line is dropped, and applet links that point at the
# MEC1019 repo's GitHub Pages copy are rewritten to the local applets/ folder.
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

# Sharper replacements for images in the notes (drawn by
# scripts/arduino-ide-svg.py). The image map below says which note image
# each one stands in for.
cp "$root/mec1019/image-overrides/"* "$dest/images/"

python3 - "$src" "$dest" "${excluded_applets[@]}" <<'PY'
import json, pathlib, re, sys

src, dest = map(pathlib.Path, sys.argv[1:3])
excluded = sys.argv[3:]
# Blurry slide screenshots -> redrawn SVGs from mec1019/image-overrides/
image_map = {
    "p1-20.png": "ide-tools-port.svg",                  # Tools > Port
    "p1-19.png": "ide-file-examples-bareminimum.svg",   # File > Examples > 01.Basics > BareMinimum
}
pages_url = re.compile(r"https://nigelk-dev\.github\.io/MEC1019_Sustainable_Processes/notes/applets/")

for md in sorted(src.glob("*.md")):
    if md.name.lower() == "readme.md":
        continue
    lines = md.read_text(encoding="utf-8").splitlines()
    # Title from the first level-1 heading
    idx = next(i for i, l in enumerate(lines) if l.startswith("# "))
    title = lines[idx][2:].strip()
    body = lines[:idx] + lines[idx + 1:]
    # Drop "*Source: `....pdf` ...*" lines and other references to the slide files
    body = [l for l in body if not re.match(r"^\*Source: `.*`.*\*\s*$", l)]
    # Drop list items / "Try it" lines that link to an excluded applet
    body = [l for l in body if not any(f"applets/{a}" in l for a in excluded)]
    # GitHub starts a list straight after a line of text; Pandoc needs a blank
    # line first, otherwise the list is folded into the paragraph.
    fixed, in_code = [], False
    item = re.compile(r"^((?:> ?)*)(?:[-*+]|\d+[.)]) ")
    for line in body:
        if line.lstrip("> ").startswith("```"):
            in_code = not in_code
        m = item.match(line)
        if m and not in_code and fixed:
            prev, quote = fixed[-1], m.group(1)
            prev_text = prev[len(quote):] if prev.startswith(quote) else None
            if (prev_text and prev_text.strip() and not item.match(prev)
                    and not prev_text.startswith((" ", "\t"))):
                fixed.append(quote.rstrip())
        fixed.append(line)
    body = fixed
    text = "\n".join(body).lstrip("\n")
    text = re.sub(r" \(from `[^`]+\.(?:pdf|pptx)`\)", "", text)
    text = pages_url.sub("applets/", text)
    for old_img, new_img in image_map.items():
        text = text.replace(f"(images/{old_img})", f"(images/{new_img})")
    front = f"---\ntitle: {json.dumps(title, ensure_ascii=False)}\n---\n\n"
    (dest / md.name).write_text(front + text + "\n", encoding="utf-8")
PY

find "$dest" -maxdepth 2 -type f | sed "s|^$root/||" | sort
