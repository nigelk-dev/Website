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


# Introduction to microcontrollers: one chapter per block of the project
# overview diagram, then an advanced chapter on the RenewableSwitchOver board.
# The chapters, their images and the applets are in the course repository's
# notes/ folder, as the other courses' notes are in theirs.
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
    """src is the course repository's notes/ folder; fetch-mec1019.sh has
    already copied its images and applets into dest."""
    src, dest = Path(src), Path(dest)
    for num, name in enumerate(MEC1019_FILES, 1):
        title, text = mec1019_note(src / name, excluded)
        text = with_checks("mec1019", num, text)
        aliases = [f"/mec1019/notes/{old}.html" for old in MEC1019_OLD_PAGES.get(name, [])]
        fm = chapter_front_matter(title, num, MEC1019_SUBTITLE, aliases)
        (dest / name).write_text(fm + text + "\n", encoding="utf-8")


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
