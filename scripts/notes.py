#!/usr/bin/env python3
"""Turn the Markdown notes from the course repositories into Quarto pages.

Usage:
  scripts/notes.py mec1019 SRC_NOTES_DIR DEST_DIR [EXCLUDED_APPLET ...]
  scripts/notes.py mec1002 SRC_REPO_DIR  DEST_DIR
  scripts/notes.py mec1043-1062 SRC_REPO_DIR  DEST_DIR

The fetch-*.sh scripts copy the images and applets and then call this to
write one page per Markdown file. Every applet the notes link to is embedded
live at the point where the notes mention it (an <iframe> that the site's
applet-embed script sizes to its content), with a caption and a link to open
it full screen.
"""
import json
import re
import shutil
import sys
from html import escape, unescape
from pathlib import Path

LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


# ---------------------------------------------------------------- helpers

def front_matter(**fields):
    lines = ["---"] + [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fields.items()] + ["---", ""]
    return "\n".join(lines) + "\n"


def embed(url, caption, title, full=None):
    """Markdown for a live applet: the iframe, then a caption with a full-screen link."""
    caption = caption.strip()
    full = f'[Open full screen ↗]({full or url}){{target="_blank" .applet-open}}'
    return (
        "::: {.applet}\n"
        "```{=html}\n"
        f'<iframe class="applet-frame" src="{escape(url, quote=True)}" title="{escape(title, quote=True)}" loading="lazy"></iframe>\n'
        "```\n"
        f"{caption}{' · ' if caption else ''}{full}\n"
        ":::"
    )


def blank_line_before_lists(lines):
    """GitHub starts a list straight after a line of text; Pandoc needs a blank
    line first, otherwise the list is folded into the paragraph."""
    fixed, in_code = [], False
    item = re.compile(r"^((?:> ?)*)(?:[-*+]|\d+[.)]) ")
    for line in lines:
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
    return fixed


def strip_links(text):
    return LINK.sub(lambda m: m.group(1), text)


# ---------------------------------------------------------------- shared structure

# Every course is shown the same way: numbered chapters grouped into parts,
# with a "Chapter N · Part X: Name" subtitle. The course overview pages are
# gone, so their old addresses redirect to the first chapter.
def chapter_front_matter(title, num, part, aliases=None):
    fields = dict(title=title, subtitle=f"Chapter {num} · {part}", order=num)
    if aliases:
        fields["aliases"] = aliases
    return front_matter(**fields)


def part_of(parts, num):
    """parts: [(first chapter, "Part I: Name"), ...] in order."""
    return [name for first, name in parts if num >= first][-1]


def no_lectures(text):
    """The notes are presented as chapters, not lectures: "Lecture 5" becomes
    "Chapter 5" (the chapters keep the lecture numbers) and "this lecture"
    becomes "this chapter"."""
    text = re.sub(r"\bLectures(?=\s*\[?\d)", "Chapters", text)
    text = re.sub(r"\[Lectures (\d)", r"[Chapters \1", text)
    text = re.sub(r"\bLecture(?=\s*\d)", "Chapter", text)
    text = re.sub(r"\b([Tt])his lecture\b", r"\1his chapter", text)
    text = re.sub(r"\b([Tt])he lecture\b", r"\1he chapter", text)
    text = re.sub(r"\b([Nn])ext lecture\b", r"\1ext chapter", text)
    text = re.sub(r",? regrouped by topic rather than by lecture", ", grouped by topic", text)
    return text


HEADING = re.compile(r"^(#{2,6}) (.+?)\s*$")


def place_inline(text, placements, where):
    """Insert blocks of Markdown at the end of the sections they belong to.

    placements: [(heading, block), ...]. A block goes after the text that
    directly follows the heading (before the next heading of any level); a
    heading ending in "+" takes the whole section, subsections included.
    Blocks for the same place keep their order."""
    lines = text.split("\n")
    heads, fence = [], False
    for i, l in enumerate(lines):
        if l.startswith("```"):
            fence = not fence
        m = None if fence else HEADING.match(l)
        if m:
            heads.append((i, len(m.group(1)), m.group(2)))
    inserts = {}
    for spec, block in placements:
        whole = spec.endswith("+")
        want = spec.rstrip("+").lstrip("# ").strip()
        hit = next((h for h in heads if h[2].startswith(want)), None)
        if hit is None:
            print(f"warning: {where}: no heading {spec!r}; applet placed at the end", file=sys.stderr)
            end = len(lines)
        else:
            later = [h for h in heads if h[0] > hit[0] and (not whole or h[1] <= hit[1])]
            end = later[0][0] if later else len(lines)
        # back up over blank lines and a closing horizontal rule
        while end > 0 and lines[end - 1].strip() in ("", "---"):
            end -= 1
        inserts.setdefault(end, []).append(block)
    out = []
    for i in range(len(lines) + 1):
        for block in inserts.get(i, []):
            out += ["", block, ""]
        if i < len(lines):
            out.append(lines[i])
    return "\n".join(out)


def inline_applet(name, desc, embed_md):
    """An applet placed in the notes: a short lead-in, then the live applet."""
    return f"**Interactive: {name}.** {desc.strip()}\n\n{embed_md}"


# ---------------------------------------------------------------- knowledge checks

def with_checks(course, num, text):
    """Add the chapter's interactive knowledge check (checks/<course>/chNN.yml,
    see scripts/checks.py). It replaces a static "Knowledge Check" section
    where the notes have one, and otherwise goes at the end."""
    from checks import knowledge_check  # needs PyYAML
    kc = knowledge_check(course, num)
    if not kc:
        return text
    static = re.compile(r"^## Knowledge Check\s*\n.*?(?=^## |\Z)", flags=re.S | re.M | re.I)
    if static.search(text):
        return static.sub(lambda m: kc + "\n\n", text, count=1)
    return re.sub(r"(?:\n---\s*)+\Z", "", text.rstrip()) + "\n\n" + kc + "\n"


# ---------------------------------------------------------------- MEC1019

MEC1019_PAGES = re.compile(r"https://nigelk-dev\.github\.io/MEC1019_Sustainable_Processes/notes/applets/")


# Introduction to microcontrollers is written in this repository
# (mec1019/chapters/): one chapter per block of the project overview diagram,
# then an advanced chapter on the RenewableSwitchOver board.
# Only the images and applets come from the course repository; the chapters'
# own images (e.g. the board schematic) are in mec1019/chapters/images/.
MEC1019_CHAPTERS = Path(__file__).resolve().parent.parent / "mec1019" / "chapters"
MEC1019_FILES = ["01-voltage-regulation.md", "02-arduino.md", "03-read-input-voltage.md",
                 "04-switching-circuitry.md", "05-pump-drive-type.md", "06-project-board.md"]
MEC1019_SUBTITLE = "Introduction to microcontrollers"
# The pages that used to be built from the course notes redirect to the
# chapter that now covers their topic.
MEC1019_OLD_PAGES = {
    "01-voltage-regulation.md": ["02-analogwrite-dividers-and-potentiometers", "05-voltage-dividers"],
    "02-arduino.md": ["01-arduino-basics-and-leds"],
    "03-read-input-voltage.md": ["06-potentiometers"],
    "04-switching-circuitry.md": ["07-relays", "08-res-battery-switchover", "finished-circuit"],
    "05-pump-drive-type.md": ["03-loops-pwm-and-alarms"],
}
# The applets still label their sketches by the course notes' parts
# ("Part 6, section 5"). Each part is mapped to the chapter that now has its
# material: the code runner's analogWrite fades (Part 2) are in chapter 5, the
# divider examples in the divider lab (Parts 2 and 5) in chapter 1.
MEC1019_CHAPTER_OF_PART = {1: 2, 2: 5, 3: 2, 5: 3, 6: 3, 7: 4, 8: 4}
MEC1019_APPLET_LABELS = {
    "Part 1 — Arduino basics and LEDs": "Chapter 2 — Getting started with the Arduino",
    "Part 2 — analogWrite": "Chapter 5 — PWM and analogWrite",
    "Part 3 — loops and alarms": "Chapter 2 — loops and alarms",
    "Part 5 — voltage dividers": "Chapter 3 — reading the RES voltage",
    "Part 6 — potentiometers": "Chapter 3 — potentiometers and analogRead",
    "Part 7 — relays": "Chapter 4 — relays",
    "Part 8 and finished circuit": "Chapter 4 — switch-over with relays",
    "Part 8 — RES / battery switch-over": "RES / battery switch-over",
    "Finished circuit notes": "Chapter 4",
    "(Part 2)": "(Chapter 1)",
    "(Part 5)": "(Chapter 1)",
}


def mec1019_part_refs(text):
    """Applet labels: "Part 6, section 5" -> "Chapter 3" (the sections no longer match)."""
    for old, new in MEC1019_APPLET_LABELS.items():
        text = text.replace(old, new)
    return re.sub(r"\bPart (\d)(?:, (?:section \d+|Exercise [\d.]+))?",
                  lambda m: f"Chapter {MEC1019_CHAPTER_OF_PART.get(int(m.group(1)), m.group(1))}", text)


def mec1019_note(path, excluded):
    lines = path.read_text(encoding="utf-8").splitlines()
    idx = next(i for i, l in enumerate(lines) if l.startswith("# "))
    title = re.sub(r"^Microcontrollers Part \d+ — ", "", lines[idx][2:].strip())
    title = title[:1].upper() + title[1:]
    body = lines[:idx] + lines[idx + 1:]
    body = [l for l in body if not re.match(r"^\*Source: `.*`.*\*\s*$", l)]
    body = [MEC1019_PAGES.sub("applets/", l) for l in body]
    body = [l for l in body if not any(f"applets/{a}" in l for a in excluded)]
    body = blank_line_before_lists(body)

    # Group consecutive blockquote lines so a multi-line "Try it" note is one unit.
    groups, cur = [], []
    for line in body:
        is_quote = line.startswith(">")
        if cur and (is_quote != cur[0].startswith(">")):
            groups.append(cur)
            cur = []
        cur.append(line)
    if cur:
        groups.append(cur)

    embedded = set()
    out = []
    for g in groups:
        first = g[0]
        link = LINK.search(first)
        if first.startswith(">") and re.match(r"^> (▶️|🔧)", first) and link and link.group(2).startswith("applets/"):
            url = link.group(2)
            embedded.add(url.split("#")[0])
            cap_lines = [re.sub(r"^> ?", "", l) for l in g]
            cap_lines[0] = re.sub(r"^(▶️|🔧)\s*", "", cap_lines[0])
            caption = strip_links("\n".join(cap_lines)).strip()
            out.append(embed(url, caption, strip_links(link.group(1))))
        else:
            out.append("\n".join(g))
    text = "\n".join(out)

    # Screenshots that only link to an applet, and the "Interactive applets
    # for this part" box, are redundant once every applet in them is embedded.
    def drop_if_embedded(m):
        urls = {u.split("#")[0] for u in re.findall(r"\]\((applets/[^)\s]+)\)", m.group(0))}
        return "" if urls and urls <= embedded else m.group(0)

    text = re.sub(r"^\[!\[[^\]]*\]\([^)]*\)\]\(applets/[^)]+\)\s*$", drop_if_embedded, text, flags=re.M)
    text = re.sub(r"^> \*\*Interactive applets for this part\*\*\n(?:>.*\n?)*", drop_if_embedded, text, flags=re.M)
    text = re.sub(r" \(from `[^`]+\.(?:pdf|pptx)`\)", "", text)
    text = no_lectures(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip("\n")
    return title, text


def mec1019(src, dest, excluded):
    """src (the course notes) is only used by fetch-mec1019.sh, which copies its
    images and applets into dest before this runs."""
    dest = Path(dest)
    shutil.copytree(MEC1019_CHAPTERS / "images", dest / "images", dirs_exist_ok=True)
    for num, name in enumerate(MEC1019_FILES, 1):
        title, text = mec1019_note(MEC1019_CHAPTERS / name, excluded)
        text = with_checks("mec1019", num, text)
        aliases = [f"/mec1019/notes/{old}.html" for old in MEC1019_OLD_PAGES.get(name, [])]
        fm = chapter_front_matter(title, num, MEC1019_SUBTITLE, aliases)
        (dest / name).write_text(fm + text + "\n", encoding="utf-8")
    for page in list((dest / "applets").glob("*.html")) + list((dest / "applets").glob("*.js")):
        html = page.read_text(encoding="utf-8")
        page.write_text(mec1019_part_refs(html), encoding="utf-8")
    mec1019_runner_extras(dest / "applets")


def _chapter_code(after_heading, chapter="04-switching-circuitry.md"):
    """The first C++ block after a heading in a chapter (Switching circuitry by default)."""
    md = (MEC1019_CHAPTERS / chapter).read_text(encoding="utf-8")
    return re.search(re.escape(after_heading) + r".*?```cpp\n(.*?)\n```", md, re.S).group(1)


def _add_runner_sketch(applets, base, key, code, edits, option_text):
    """Add a variant of the code runner's sketch `base` as `key`: the sketch text
    is `code` (from the chapter) and the step-through program is the base one
    with the (old, new) text `edits` applied."""
    runner, sketches = applets / "code-runner.html", applets / "sketches.js"
    js, html = sketches.read_text(encoding="utf-8"), runner.read_text(encoding="utf-8")
    if f"\n  {key}: {{" in html:
        return
    block = re.search(r"\n  " + base + r": \{.*?\n  \},\n", html, re.S).group(0)
    new = block.replace(f"{base}: {{", f"{key}: {{", 1)
    for old, rep in edits:
        if old not in new:                    # the notes' program changed: leave the runner as it is
            print(f"warning: code runner {base} not in the expected form; {key} not added", file=sys.stderr)
            return
        new = new.replace(old, rep)
    js = re.sub(r'(\n  "' + base + r'": .*?",)\n', lambda m: m.group(1) + f'\n  "{key}": ' + json.dumps(code, ensure_ascii=False) + ",\n",
                js, count=1, flags=re.S)
    html = html.replace(block, block + new[1:], 1)
    html = re.sub(r'(<option value="' + base + r'">[^<]*</option>)', lambda m: m.group(1) +
                  f'\n      <option value="{key}">{option_text}</option>', html, count=1)
    sketches.write_text(js, encoding="utf-8")
    runner.write_text(html, encoding="utf-8")


def mec1019_runner_extras(applets):
    """Whole-number versions of the sketches the chapters now use.

    The course notes' code runner and RES battery-backup simulator use float
    versions of Exercise 3e and the switch-over sketch; the Switching circuitry
    chapter compares the raw analogRead value with a whole-number threshold.
    The sketch text comes from the chapter, so the applets always match it."""
    if not (applets / "code-runner.html").exists():
        return
    _add_runner_sketch(applets, "ex3e", "ex3eint", _chapter_code("### Exercise 3e"), [
        ("title:'Exercise 3e'", "title:'Exercise 3e, integer version'"),
        ("desc:'Move the slider either side of 2.5 V.",
         "desc:'Move the slider either side of 2.5 V: the raw analogRead value is compared with 511, so no float is needed."),
        ("yield* io.at('float vOut = readVolts(kPotPin);');\n      const v = yield* readVoltsShort('A1');\n"
         "      setVars({vOut:f2(v), 'vOut < kThreshold': v < 2.5});\n"
         "      yield* io.at('Serial.println(vOut);'); io.print(f2(v) + '\\n');\n"
         "      yield* io.at('if (vOut < kThreshold) {');\n      if (v < 2.5){",
         "yield* io.at('int reading = analogRead(kPotPin);'); const r = io.analogRead('A1');\n"
         "      setVars({reading:r, kThreshold:511, 'reading < kThreshold': r < 511});\n"
         "      yield* io.at('Serial.println(reading);'); io.print(r + '\\n');\n"
         "      yield* io.at('if (reading < kThreshold) {');\n      if (r < 511){"),
    ], "Exercise 3e — the same with whole numbers (no float)")
    _add_runner_sketch(applets, "p8", "p8int", _chapter_code("### The code"), [
        ("title:'RES / battery switch-over'", "title:'RES / battery switch-over, integer version'"),
        ("pin:'A2', label:'Voltage at A2 (RES after the divider)'", "pin:'A0', label:'Voltage at A0 (RES after the divider)'"),
        ("desc:'Drag the A2 voltage below 2.5 V",
         "desc:'The raw analogRead value is compared with 511 (2.5 V), so no float is needed. Drag the A0 voltage below 2.5 V"),
        ("      yield* io.at('useRes();', 1); yield* useRes();\n", ""),
        ("yield* io.at('float vPin = readVolts(kResPin);');\n      const v = yield* readVoltsShort('A2');\n"
         "      setVars({vPin:f2(v), 'vPin < kThresholdV (2.5)': v < 2.5});\n"
         "      yield* io.at('Serial.println(vPin);'); io.print(f2(v) + '\\n');\n"
         "      yield* io.at('if (vPin < kThresholdV) {');\n      if (v < 2.5){",
         "yield* io.at('int reading = analogRead(kResPin);'); const r = io.analogRead('A0');\n"
         "      setVars({reading:r, kSwitchReading:511, 'reading < kSwitchReading': r < 511});\n"
         "      yield* io.at('Serial.println(reading);'); io.print(r + '\\n');\n"
         "      yield* io.at('if (reading < kSwitchReading) {');\n      if (r < 511){"),
        ("yield* io.at('useRes();', 2)", "yield* io.at('useRes();', 1)"),
    ], "Switch-over — the same with whole numbers (no float)")
    _add_runner_sketch(applets, "p8int", "p8hys", _chapter_code("### Adding hysteresis"), [
        ("title:'RES / battery switch-over, integer version'", "title:'RES / battery switch-over with hysteresis'"),
        ("desc:'The raw analogRead value is compared with 511 (2.5 V), so no float is needed. Drag the A0 voltage below 2.5 V to switch the load to the battery, and back above it to return to the RES.",
         "desc:'Two thresholds: below 470 (2.3 V) the load goes to the battery, above 552 (2.7 V) it goes back to the RES, and in between nothing changes. Drag the A0 voltage slowly across 2.5 V and back."),
        ("      yield* io.at('pinMode(kBatRelay, OUTPUT);'); io.pinMode(13);\n",
         "      yield* io.at('pinMode(kBatRelay, OUTPUT);'); io.pinMode(13);\n"
         "      yield* io.at('if (analogRead(kResPin) < kToRes) {'); const r0 = io.analogRead('A0');\n"
         "      if (r0 < 552){ yield* io.at('useBattery();', 1); yield* useBattery(); }\n"
         "      else { yield* io.at('} else {'); yield* io.at('useRes();', 1); yield* useRes(); }\n"),
        ("      setVars({reading:r, kSwitchReading:511, 'reading < kSwitchReading': r < 511});\n",
         "      setVars({reading:r, kToBattery:470, kToRes:552, 'reading < kToBattery': r < 470, 'reading > kToRes': r > 552});\n"),
        ("      yield* io.at('if (reading < kSwitchReading) {');\n"
         "      if (r < 511){ yield* io.at('useBattery();'); yield* useBattery(); }\n"
         "      else { yield* io.at('} else {'); yield* io.at('useRes();', 1); yield* useRes(); }\n",
         "      yield* io.at('if (reading < kToBattery) {');\n"
         "      if (r < 470){ yield* io.at('useBattery();', 2); yield* useBattery(); }\n"
         "      else { yield* io.at('} else if (reading > kToRes) {');\n"
         "        if (r > 552){ yield* io.at('useRes();', 2); yield* useRes(); } }\n"),
    ], "Switch-over with hysteresis — two thresholds")
    _add_runner_sketch(applets, "ex2d2", "ex2d2int", _chapter_code("## 6. Exercise 7.3", "03-read-input-voltage.md"), [
        ("title:'Exercise 7.3'", "title:'Exercise 7.3, integer version'"),
        ("desc:'Move the slider either side of 2.5 V and watch which branch of the if ... else runs.'",
         "desc:'Move the slider either side of 2.5 V: the raw analogRead value is compared with 511, so no float is needed. Watch which branch of the if ... else runs.'"),
        ("      yield* io.at('float vOut = readVolts(kPotPin);');\n      const v = yield* readVoltsShort('A1');\n"
         "      setVars({vOut:f2(v), 'vOut > kThreshold': v > 2.5});\n"
         "      yield* io.at('Serial.println(vOut);'); io.print(f2(v) + '\\n');\n"
         "      yield* io.at('if (vOut > kThreshold) {');\n      if (v > 2.5){",
         "      yield* io.at('int reading = analogRead(kPotPin);'); const r = io.analogRead('A1');\n"
         "      setVars({reading:r, kThreshold:511, 'reading > kThreshold': r > 511});\n"
         "      yield* io.at('Serial.println(reading);'); io.print(r + '\\n');\n"
         "      yield* io.at('if (reading > kThreshold) {');\n      if (r > 511){"),
    ], "Exercise 7.3 — the same with whole numbers (no float)")
    _add_runner_sketch(applets, "ex2b", "ex2bint", _chapter_code("Exercise 2b brightens", "05-pump-drive-type.md"), [
        ("title:'Exercise 2b'", "title:'Exercise 2b, integer version'"),
        ("desc:'In loop()", "desc:'Whole analogWrite values only, no float. In loop()"),
        ("      yield* io.at('Serial.begin(9600);');\n      yield* io.at('pinMode(kRedPin, OUTPUT);')",
         "      yield* io.at('pinMode(kRedPin, OUTPUT);')"),
        ("        setVars({pwm, 'pwm <= kTopPwm': pwm <= 250, volts: f2(pwm*5/255)});",
         "        setVars({pwm, 'pwm <= kTopPwm': pwm <= 250});"),
        ("        yield* io.at('showPwm(pwm);', 1); yield* this.showPwm(pwm);",
         "        yield* io.at('analogWrite(kRedPin, pwm);', 1); io.aw(10, pwm);\n"
         "        yield* io.delay(500, 'delay(kStepMs);', 1);"),
        ("        setVars({pwm, 'pwm > 0': pwm > 0, volts: f2(pwm*5/255)});",
         "        setVars({pwm, 'pwm > 0': pwm > 0});"),
        ("        yield* io.at('showPwm(pwm);', 2); yield* this.showPwm(pwm);",
         "        yield* io.at('analogWrite(kRedPin, pwm);', 2); io.aw(10, pwm);\n"
         "        yield* io.delay(500, 'delay(kStepMs);', 2);"),
    ], "Exercise 2b — the same with whole numbers (no float)")
    mec1019_res_backup_sketch(applets / "res-backup.html")


def mec1019_res_backup_sketch(page):
    """The RES battery-backup simulator shows a sketch for its settings. Replace
    its float version with the chapter's whole-number one, with the simulator's
    threshold turned into an analogRead value."""
    if not page.exists():
        return
    html = page.read_text(encoding="utf-8")
    m = re.search(r"function code\(th\)\{ return `.*?`; \}", html, re.S)
    if not m:
        print("warning: res-backup.html sketch not in the expected form; left as it is", file=sys.stderr)
        return
    code = _chapter_code("### The code")
    code = re.sub(r"// Below this reading.*?\nconst int      kSwitchReading = 2500L \* 1023 / 5000;",
                  "// Below this reading the RES is too low: ${th.toFixed(1)} V at A0 -> ${rd(th)}.\n"
                  "// Worked out by the compiler, so the sketch uses no float at all.\n"
                  "const int      kSwitchReading = ${mv(th)}L * 1023 / 5000;", code, flags=re.S)
    hys = _chapter_code("### Adding hysteresis")
    hys = re.sub(r"// Two thresholds.*?\nconst int      kToBattery  = 2300L \* 1023 / 5000;   // 2.3 V at A0 -> 470\n"
                 r"const int      kToRes      = 2700L \* 1023 / 5000;   // 2.7 V at A0 -> 552",
                 "// Two thresholds, worked out by the compiler: a dead band either side of ${th.toFixed(1)} V.\n"
                 "const int      kToBattery  = ${mv(th-band)}L * 1023 / 5000;   // ${(th-band).toFixed(1)} V at A0 -> ${rd(th-band)}\n"
                 "const int      kToRes      = ${mv(th+band)}L * 1023 / 5000;   // ${(th+band).toFixed(1)} V at A0 -> ${rd(th+band)}",
                 hys, flags=re.S)
    hys = hys.replace("// Between 470 and 552 nothing changes", "// Between ${rd(th-band)} and ${rd(th+band)} nothing changes")
    if "${mv(th)}L" not in code or "${mv(th-band)}L" not in hys or "${rd(th-band)} and" not in hys:
        print("warning: switch-over sketches not in the expected form; res-backup.html left as it is", file=sys.stderr)
        return
    q = lambda c: c.replace("\\", "\\\\").replace("`", "\\`")
    html = html.replace(m.group(0),
        "const mv = v => Math.round(v*1000), rd = v => Math.floor(mv(v)*1023/5000);\n"
        "function code(th, hys, band){ return hys ? `" + q(hys) + "` : `" + q(code) + "`; }", 1)
    html = html.replace("The slide version compares at 2.5 V; adjust the threshold above to see the generated code change.",
                        "The thresholds are <code>analogRead</code> values worked out by the compiler, so the sketch uses no "
                        "<code>float</code>; change the threshold or tick Hysteresis above to see the generated code change.")
    # hysteresis toggle and dead band, under the threshold slider
    html = html.replace('<p class="note" id="thNote"></p>',
        '<p class="note" id="thNote"></p>\n'
        '    <label><input id="hys" type="checkbox"> Hysteresis (two thresholds)</label>\n'
        '    <label for="band">Dead band either side of the threshold (V): <b id="bandLbl"></b></label>\n'
        '    <input id="band" type="range" min="0.1" max="1" step="0.1" value="0.2">', 1)
    html = html.replace('<div class="stat"><span>pin 12 (RES_relay) / pin 13 (BAT_relay)</span><b id="pins"></b></div>',
        '<div class="stat"><span>pin 12 (kResRelay) / pin 13 (kBatRelay)</span><b id="pins"></b></div>\n'
        '    <div class="stat"><span>Switch-overs on this chart</span><b id="nsw"></b></div>', 1)
    html = html.replace('<span>A0 voltage (RES_volt)</span>', '<span>A0 voltage (reading)</span>', 1)
    # the decision: one threshold, or two with the supply kept in between
    for old, new in (
        ("s.textContent += RES_volt.toFixed(2)+'\\n';", "s.textContent += adc+'\\n';"),
        ("const onBattery = RES_volt < th;",
         "const hys = $('hys').checked, band = +$('band').value;\n"
         "  $('band').disabled = !hys; $('bandLbl').textContent = '±' + band.toFixed(1) + ' V';\n"
         "  if (!hys) onBat = adc < rd(th);\n"
         "  else if (adc < rd(th-band)) onBat = true;\n"
         "  else if (adc > rd(th+band)) onBat = false;\n"
         "  const onBattery = onBat;"),
        ("let t = 0, noise = 0;", "let t = 0, noise = 0, onBat = false;\nif (location.hash === '#hys') document.getElementById('hys').checked = true;"),
        ("$('sRES').classList.toggle('on', !onBattery);",
         "let nsw = 0; for (let i = 1; i < hist.length; i++) if (hist[i][1] !== hist[i-1][1]) nsw++;\n"
         "  $('nsw').textContent = nsw;\n  $('sRES').classList.toggle('on', !onBattery);"),
        ("$('va0').innerHTML = a0>5 ? `<span class=\"bad\">${a0.toFixed(2)} V — over 5 V, change the divider!</span>` : RES_volt.toFixed(2)+' V';",
         "$('va0').innerHTML = a0>5 ? `<span class=\"bad\">${a0.toFixed(2)} V — over 5 V, change the divider!</span>` : RES_volt.toFixed(2)+' V ('+adc+')';"),
        ("drawChart(th);", "drawChart(th, hys ? band : 0);"),
        # a real analogRead jitters by a few counts, which is what makes a single threshold chatter
        ("const adc = Math.min(1023, Math.round(a0/5*1023)),",
         "const adc = Math.max(0, Math.min(1023, Math.round(a0/5*1023 + (Math.random()-0.5)*8))),"),
        ("if (th !== lastTh) { lastTh = th; $('code').textContent = code(th); }",
         "const key = th + '|' + hys + '|' + band;\n"
         "  if (key !== lastTh) { lastTh = key; $('code').textContent = code(th, hys, band); }"),
        ("function drawChart(th){", "function drawChart(th, band){"),
        ("  const yTh = H-pad - th/5*(H-2*pad+10);\n"
         "  g.strokeStyle='#c98a00'; g.setLineDash([6,4]); g.beginPath(); g.moveTo(pad,yTh); g.lineTo(W-5,yTh); g.stroke(); g.setLineDash([]);\n"
         "  g.fillStyle='#c98a00'; g.fillText('threshold', W-70, yTh-5);",
         "  const yOf = v => H-pad - v/5*(H-2*pad+10);\n"
         "  const lines = band ? [[th+band, 'back to RES', -5], [th-band, 'to battery', 14]] : [[th, 'threshold', -5]];\n"
         "  if (band){ g.fillStyle='rgba(201,138,0,.10)'; g.fillRect(pad, yOf(th+band), W-5-pad, yOf(th-band)-yOf(th+band)); }\n"
         "  for (const [v, txt, dy] of lines){ const y = yOf(v);\n"
         "    g.strokeStyle='#c98a00'; g.setLineDash([6,4]); g.beginPath(); g.moveTo(pad,y); g.lineTo(W-5,y); g.stroke(); g.setLineDash([]);\n"
         "    g.fillStyle='#c98a00'; g.fillText(txt, W-80, y+dy); }"),
    ):
        if old not in html:
            print(f"warning: res-backup.html: {old[:40]!r} not found", file=sys.stderr)
        html = html.replace(old, new, 1)
    page.write_text(html, encoding="utf-8")


# ---------------------------------------------------------------- MEC1002

def embed_page_from(html, keep_section=None):
    """A copy of an interactive page for embedding: no page heading or header
    navigation, and (for a multi-element index page) only one section."""
    html = re.sub(r"\s*<header>.*?</header>", "", html, flags=re.S)
    html = re.sub(r"\s*<h1>.*?</h1>", "", html, count=1, flags=re.S)
    if keep_section:
        def keep(m):
            return m.group(0) if m.group(1) == keep_section else ""
        html = re.sub(r'\s*<section id="([^"]+)">.*?</section>', keep, html, flags=re.S)
        html = re.sub(r"(<section[^>]*>)\s*<h2>.*?</h2>", r"\1", html, count=1, flags=re.S)
        html = html.replace("border-top: 1px solid #d0d7de; padding-top: 18px;", "")
    return html


def italic_caption(line):
    """'*Interactive diagram (drag the magnet ...): [link](...). Open it ...*' -> 'Interactive diagram: drag the magnet ...'"""
    t = line.strip().strip("*").strip()
    m = re.match(r"(Interactive [^(:]*?)\s*\((.*)\)\s*:", t, flags=re.S)
    if m:
        return f"*{m.group(1)}:* {m.group(2)}"
    m = re.match(r"(Interactive [^:]*?):\s*\[([^\]]+)\]\(http", t)
    if m:
        return f"*{m.group(1)}:* {m.group(2)}"
    m = re.match(r"(Interactive [^:]*?):", t)
    return f"*{m.group(1)}*" if m else ""


MEC1002_TITLES = {1: "Electromagnetic Induction", 2: "DC Motor Characteristics", 3: "DC Motor Start-up",
                  4: "DC Motor Connections", 5: "DC Motor Control", 6: "Servo Systems",
                  7: "Capacitors and Inductors", 8: "Phasors and Impedance", 9: "AC Power", 10: "Transformers",
                  11: "Three-Phase Power", 12: "Star–Delta Circuits", 13: "Induction Motors",
                  14: "Equivalent Circuit", 15: "Speed–Torque Curve", 16: "Single-Phase Motors",
                  17: "Synchronous Motors", 18: "Motor Starting"}
MEC1002_PARTS = [(1, "Part I: DC Machines"), (7, "Part II: AC Circuits and Transformers"),
                 (11, "Part III: Three-Phase Systems"), (13, "Part IV: AC Motors")]

# Where each element of a chapter's "Interactive Elements" list goes in the
# notes: the heading of the section it belongs with ("+" = after the whole
# section, subsections included).
MEC1002_PLACES = {
    4: {"backemf": "A Note on Back emf", "connections": "Comparison: Series vs Shunt",
        "examples": "Worked Examples+"},
    6: {"servo": "Closed loop", "encoder": "Incremental encoders", "graycode": "Absolute encoders",
        "flywheel": "Worked Example: Sizing a Motor"},
    7: {"squarewave": "Summary", "sinewave": "Sine Wave Description",
        "rlcac": "Inductive reactance", "reactance": "Inductive reactance"},
    8: {"phasorwave": "Leading and Lagging Waves", "joperator": "Rotating through 90",
        "rlcphasor": "Combining Impedances", "impcalc": "Worked Examples+"},
    9: {"instpower": "Inductive circuit", "powertri": "The Power Triangle",
        "pfcorr": "Power Factor Correction", "generator": "Power Factor: Practical Implications"},
    10: {"turns": "The Ideal Transformer+", "referring": "Referring the Secondary",
         "txeff": "Transformer Efficiency+"},
    11: {"threephase": "Three-Phase Power", "stardelta": "Power in a Three-Phase System+",
         "unbalanced": "Star Distributed System", "sdconvert": "Star–Delta Conversions"},
    12: {"dysolver": "Worked Solution+", "lineloss": "Worked Solution+"},
    13: {"rotfield": "Key components", "slipcalc": "Rotation and Slip",
         "sankey": "Power Flow and Losses", "rotortype": "Rotor Types+"},
    14: {"eqsolver": "Simplifying the Model", "tscurve": "Air-gap power and torque", "livesankey": "Power flow"},
    15: {"loadline": "The Speed–Torque Curve", "eqcurve": "Recap: Power and Torque",
         "labelcurve": "The Four Key Torque Points+"},
    16: {"motorload": "Torque Curve with a Load", "affinity": "Torque Curve with a Load",
         "spfield": "Single-Phase Induction Motors", "shaded": "Shaded-Pole Motor"},
    17: {"loadangle": "Load Angle", "syncvsind": "Summary of Motor Types",
         "syncphasor": "Equivalent Circuit and Power+", "syncstart": "Starting a Synchronous Motor"},
    18: {"starting": "Comparison of Starting Methods", "starterflow": "Star–Delta Starter",
         "triac": "TRIAC phase control", "vfdpwm": "Variable Frequency Drive", "thermal": "Power Rating and Duty Cycles",
         "selector": "Motor Selection"},
}


def mec1002_lecture(md, lec_dir):
    text = md.read_text(encoding="utf-8")
    inter = lec_dir / "interactive"

    num = int(re.search(r"\d+", md.stem).group())
    title = MEC1002_TITLES.get(num, f"Chapter {num}")

    # Header block: course title, "## Lecture N", author, online link, manual contents list
    text = re.sub(r"\A# .*\n+## Lecture \d+\n+(\*[^*\n]+\*\n+)?", "", text)
    text = re.sub(r"^\*\*Interactive version online:\*\*.*\n+", "", text, flags=re.M)
    text = re.sub(r"\A---\n+", "", text)
    text = re.sub(r"\A## Contents\n+(?:\d+\. .*\n)+\n*(?:---\n+)?", "", text)
    # The class timetable (lecture and tutorial times) is not part of the notes
    text = re.sub(r"^### Class contact\n.*?(?=^#)", "", text, flags=re.S | re.M)

    made = {}

    def live(name, caption, section=None, title=None):
        """Write interactive/embed-*.html (once) and return the embed markdown.
        "Open full screen" goes to the original page."""
        key = (name, section)
        html = (inter / name).read_text(encoding="utf-8")
        if key not in made:
            out = f"embed-{section or Path(name).stem}.html"
            (inter / out).write_text(embed_page_from(html, section), encoding="utf-8")
            made[key] = f"interactive/{out}"
        t = re.search(r"<title>(.*?)</title>", html, flags=re.S)
        title = title or (unescape(t.group(1).strip()) if t else name)
        full = f"interactive/{name}" + (f"#{section}" if section else "")
        return embed(made[key], caption, title, full)

    # 1. <div data-...> blocks hold a static figure and a link: the GitHub
    #    fallback for a live diagram. Replace each with the live diagram.
    def div_block(m):
        inner = m.group(1)
        f = re.search(r"\]\(interactive/([\w.-]+\.html)\)", inner)
        if not f:
            return m.group(0)
        cap_line = next((l for l in inner.splitlines() if l.startswith("*Interactive")), "")
        return live(f.group(1), italic_caption(cap_line))

    text = re.sub(r"^<div data-[^>]*>\n(.*?)\n</div>[ \t]*$", div_block, text, flags=re.S | re.M)

    # 2. A lone "*Interactive ...: ... interactive/x.html ...*" line.
    def lone(m):
        line = m.group(0)
        f = re.search(r"\]\(interactive/([\w.-]+\.html)\)", line)
        return live(f.group(1), italic_caption(line))

    text = re.sub(r"^\*Interactive [^\n]*\]\(interactive/[\w.-]+\.html\)[^\n]*\*[ \t]*$", lone, text, flags=re.M)

    # 3. The "Interactive Elements" section at the end: each element is moved
    #    into the notes, after the section it belongs with, and the list goes.
    places = MEC1002_PLACES.get(num, {})
    section = re.search(r"^## Interactive Elements\n.*?(?=^## |\Z)", text, flags=re.S | re.M)
    if section:
        items = re.findall(r"^- \*\*\[([^\]]+)\]\(interactive/index\.html#([\w-]+)\)\.\*\* (.*)$",
                           section.group(0), flags=re.M)
        text = text[:section.start()] + text[section.end():]
        placements = []
        for name, sec, desc in items:
            if sec not in places:
                print(f"warning: {md}: no place for element {sec}; put at the end", file=sys.stderr)
            placements.append((places.get(sec, "\0"),
                               inline_applet(name, desc, live("index.html", "", sec, name))))
        text = place_inline(text, placements, md.name)

    check = re.sub(r"\[Open full screen ↗\]\([^)]*\)", "", text)
    leftover = re.findall(r"\]\((interactive/[^)]*|https://claude\.ai[^)]*)\)", check)
    if leftover:
        print(f"warning: {md}: links not embedded: {leftover}", file=sys.stderr)

    text = with_checks("mec1002", num, text)
    text = no_lectures(text)
    text = "\n".join(blank_line_before_lists(text.splitlines()))
    text = re.sub(r"\n---\n(?:[ \t]*\n)*---\n", "\n---\n", text)  # rules left back to back
    text = re.sub(r"\n{3,}", "\n\n", text).strip("\n")
    aliases = ["/mec1002/index.html"] if num == 1 else None
    return chapter_front_matter(title, num, part_of(MEC1002_PARTS, num), aliases) + text + "\n"


def mec1002(src, dest):
    for lec_dir in sorted(Path(dest).glob("Lec*/")):
        # "Back to the notes" links on the full-screen pages: the .md becomes .html
        for page in (lec_dir / "interactive").glob("*.html"):
            html = page.read_text(encoding="utf-8")
            page.write_text(re.sub(r'href="\.\./(Lec\d+)\.md"', r'href="../\1.html"', html), encoding="utf-8")
        md = lec_dir / f"{lec_dir.name}.md"
        if md.exists():
            md.write_text(mec1002_lecture(md, lec_dir), encoding="utf-8")


# ---------------------------------------------------------------- MEC1043/1062

# Added to the copies of the chapter applet pages that are embedded in the
# notes: one applet per frame, so no page header, tab bar, brief or footer.
MEC1043_1062_EMBED_STYLE = (
    '<style id="mec1043-1062-embed">header.top, footer.foot, .brief { display: none !important; }'
    ' main .wrap { padding-block: 12px 12px; }</style>'
)


def mec1043_1062_applets(html):
    """[(id, title), ...] from a chapter applet page's MA.page({... applets: [...]})."""
    return re.findall(r'\{ id: "([^"]+)", short: "[^"]*", title: "([^"]+)"', html)


# Where each applet goes in its chapter, in the order of the chapter's
# "Suggested interactive applets" table (= the tabs of applets/chNN.html): the
# heading of the section it belongs with ("+" = after the whole section).
MEC1043_1062_PLACES = {
    1: ["Decisions by attributes", "Decisions by attributes", "Example: a furnace"],
    2: ["2.1 Truth tables", "2.2 Design example", "2.4 Basic gates", "2.7 Solving"],
    3: ["Worked exercise", "3.4 Points to note", "Potential issues", "Example: pneumatic press"],
    4: ["Multiple outputs", "AND gate response", "Memory (set/reset) responses", "4.3 From logic"],
    5: ["Rules", "5.2 Start logic", "5.3 Timers", "5.3 Timers"],
    6: ["6.1 Example 1+", "Response diagram scenarios", "Logic network development", "6.2 Example 2+"],
    7: ["The scan cycle", "Input unit", "Output unit", "7.2 Advantages"],
    8: ["8.2 Sequence control", "Programming with a step register", "Building the ladder",
        "Finding the minimum", "8.4 Interlocking"],
    9: ["9.1 The ISA-95", "9.2 The information loop", "9.3 SCADA"],
    10: ["10.1 Network topology", "10.2 Transmission media", "10.3 Network components", "10.3 Network components"],
    11: ["Encapsulation", "The layers in detail", "Checksum", "Cyclic Redundancy Check", "11.2 TCP/IP"],
    12: ["How a fieldbus works", "Fieldbus vs Ethernet", "12.2 Profibus", "Fieldbus vs conventional",
         "Fieldbus vs Ethernet"],
    13: ["Worked example: index and dwell", "13.4 The cross-over cam", "13.2 Transfer systems+", "Pacing"],
    14: ["Hopping", "Hopping", "14.1 Operation", "14.4 Conveying velocity+"],
    15: ["Design of the hopper angle", "Cycle time", "15.3 Centrifugal", "15.4 Other hopper feeders"],
    16: ["16.2 Orientation analysis", "Catalogue of passive devices", "Efficiency of orientation", "Wiper blade"],
    17: ["17.2 Powered feedtracks", "Friction effects", "Vertical feedtrack", "17.3 Escapements"],
    18: ["Production time", "Production time", "Effect of buffer size", "Equalising downtime"],
    19: ["19.1 Payback period", "19.2 Example 1", "19.4 Example 2", "19.4 Example 2"],
}


def mec1043_1062_chapter(md, applets_dir, parts):
    lines = md.read_text(encoding="utf-8").splitlines()
    m = re.match(r"# Chapter (\d+) · (.+)", lines[0])
    num, title = int(m.group(1)), m.group(2).strip()
    lines = lines[1:]

    # Header box: "> **Part I: ...** · Source: Lecture 4" then a prev/contents/next line.
    # Keep the part; the lecture it came from is not shown.
    part = None
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and lines[0].startswith(">"):
        l = lines.pop(0)
        p = re.search(r"\*\*(Part [^*]+)\*\*", l)
        if p:
            part = p.group(1).strip()
    if part:
        parts[num] = part
    text = "\n".join(blank_line_before_lists(lines))

    # The closing "Suggested interactive applets" table: every row has been
    # built, as the tabs of applets/chNN.html in the same order. Each applet
    # goes into the notes after the section it belongs with.
    page = f"ch{num:02d}.html"
    head, sep, tail = text.partition("\n## Suggested interactive applets\n")
    if sep:
        html = (applets_dir / page).read_text(encoding="utf-8")
        built = mec1043_1062_applets(html)
        rows = re.findall(r"^\| \*\*(.+?)\*\* \| (.*?) \| (.*?) \|\s*$", tail, flags=re.M)
        if len(rows) != len(built):
            print(f"warning: {md.name}: {len(rows)} suggested applets but {len(built)} in {page}", file=sys.stderr)
        places = MEC1043_1062_PLACES.get(num, [])
        placements = []
        for i, ((aid, atitle), (name, does, teaches)) in enumerate(zip(built, rows)):
            block = inline_applet(name, does, embed(f"applets/embed-{page}#{aid}", f"*Teaches:* {teaches}",
                                                    unescape(atitle), f"applets/{page}#{aid}"))
            placements.append((places[i] if i < len(places) else "\0", block))
        text = place_inline(head.rstrip(), placements, md.name)

    text = with_checks("mec1043-1062", num, text)
    text = no_lectures(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip("\n")
    aliases = ["/mec1043-1062/index.html", "/mm453/index.html"] if num == 1 else None
    return chapter_front_matter(title, num, part or "", aliases) + text + "\n"


def mec1043_1062(src, dest):
    dest = Path(dest)
    applets = dest / "applets"
    for page in sorted(applets.glob("ch[0-9][0-9].html")):
        html = page.read_text(encoding="utf-8")
        # "Chapter notes" link: ../notes/NN-x.md -> the rendered page next to applets/
        html = re.sub(r'"\.\./notes/(\d\d-[\w-]+)\.md"', r'"../\1.html"', html)
        page.write_text(html, encoding="utf-8")
        (applets / f"embed-{page.name}").write_text(
            html.replace("</head>", MEC1043_1062_EMBED_STYLE + "\n</head>", 1), encoding="utf-8")
    index = applets / "index.html"
    if index.exists():
        index.write_text(index.read_text(encoding="utf-8").replace('"../notes/README.md"', '"../../index.html"'),
                         encoding="utf-8")
    parts = {}
    for md in sorted(Path(src, "notes").glob("[0-9][0-9]-*.md")):
        (dest / md.name).write_text(mec1043_1062_chapter(md, applets, parts), encoding="utf-8")


# ---------------------------------------------------------------- module codes

# The site names the courses without their module codes. The course repos use
# them in applet headings and captions ("MEC1002 Lecture 4: ...", "MEC1043/1062
# Applet Lab"), so drop them from every copied page. A code that is part of a
# path, URL or repo name (mec1019/, MEC1019_Sustainable_Processes) is kept.
MODULE_CODE = re.compile(r"(?<![\w/.-])MEC\d{4}(?:/\d{4})?(?![\w/])(?:\s*[:·]\s*|\s+)?")


def drop_module_codes(dest):
    for f in Path(dest).rglob("*"):
        if f.suffix in (".md", ".html", ".js", ".css") and f.is_file():
            text = f.read_text(encoding="utf-8")
            new = MODULE_CODE.sub("", text)
            if new != text:
                f.write_text(new, encoding="utf-8")


if __name__ == "__main__":
    course, src, dest, *rest = sys.argv[1:]
    {"mec1019": lambda: mec1019(src, dest, rest), "mec1002": lambda: mec1002(src, dest),
     "mec1043-1062": lambda: mec1043_1062(src, dest)}[course]()
    drop_module_codes(dest)
