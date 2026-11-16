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


# ---------------------------------------------------------------- MEC1019

MEC1019_PAGES = re.compile(r"https://nigelk-dev\.github\.io/MEC1019_Sustainable_Processes/notes/applets/")


def mec1019_note(path, excluded):
    lines = path.read_text(encoding="utf-8").splitlines()
    idx = next(i for i, l in enumerate(lines) if l.startswith("# "))
    title = lines[idx][2:].strip()
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
    text = re.sub(r"\n{3,}", "\n\n", text).strip("\n")
    return front_matter(title=title) + text + "\n"


def mec1019(src, dest, excluded):
    for md in sorted(Path(src).glob("*.md")):
        if md.name.lower() == "readme.md":
            continue
        (Path(dest) / md.name).write_text(mec1019_note(md, excluded), encoding="utf-8")


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


def mec1002_lecture(md, lec_dir):
    text = md.read_text(encoding="utf-8")
    inter = lec_dir / "interactive"

    online = re.search(r"^\*\*Interactive version online:\*\* \[([^\]]+)\]", text, flags=re.M)
    num = int(re.search(r"\d+", md.stem).group())
    title = online.group(1).replace(" · ", ": ") if online else f"Lecture {num}"

    # Header block: course title, "## Lecture N", author, online link, manual contents list
    text = re.sub(r"\A# .*\n+## Lecture \d+\n+(\*[^*\n]+\*\n+)?", "", text)
    text = re.sub(r"^\*\*Interactive version online:\*\*.*\n+", "", text, flags=re.M)
    text = re.sub(r"\A---\n+", "", text)
    text = re.sub(r"\A## Contents\n+(?:\d+\. .*\n)+\n*---\n+", "", text)

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

    # 3. "Interactive Elements" sections: each bullet becomes a subsection with
    #    its element embedded under it.
    text = re.sub(r"^These are built: use them online at .*$",
                  "Each element below runs in the page; use *Open full screen* for more room.",
                  text, flags=re.M)

    def bullet(m):
        name, section, desc = m.group(1), m.group(2), m.group(3).strip()
        return f"### {name}\n\n{desc}\n\n" + live("index.html", "", section, name)

    text = re.sub(r"^- \*\*\[([^\]]+)\]\(interactive/index\.html#([\w-]+)\)\.\*\* (.*)$", bullet, text, flags=re.M)

    check = re.sub(r"\[Open full screen ↗\]\([^)]*\)", "", text)
    leftover = re.findall(r"\]\((interactive/[^)]*|https://claude\.ai[^)]*)\)", check)
    if leftover:
        print(f"warning: {md}: links not embedded: {leftover}", file=sys.stderr)

    text = "\n".join(blank_line_before_lists(text.splitlines()))
    text = re.sub(r"\n{3,}", "\n\n", text).strip("\n")
    return front_matter(title=title, order=num) + text + "\n"


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


def mec1043_1062_chapter(md, applets_dir):
    lines = md.read_text(encoding="utf-8").splitlines()
    m = re.match(r"# Chapter (\d+) · (.+)", lines[0])
    num, title = int(m.group(1)), m.group(2).strip()
    lines = lines[1:]

    # Header box: "> **Part I: ...** · Source: Lecture 4" then a prev/contents/next line
    subtitle = f"Chapter {num}"
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and lines[0].startswith(">"):
        l = lines.pop(0)
        if "**Part" in l:
            subtitle += " · " + re.sub(r"^>\s*", "", l).replace("**", "").strip()
    text = "\n".join(blank_line_before_lists(lines))

    # The closing "Suggested interactive applets" table: every row has been
    # built, as the tabs of applets/chNN.html in the same order. Replace the
    # table with one live applet per row.
    page = f"ch{num:02d}.html"
    head, sep, tail = text.partition("\n## Suggested interactive applets\n")
    if sep:
        html = (applets_dir / page).read_text(encoding="utf-8")
        built = mec1043_1062_applets(html)
        rows = re.findall(r"^\| \*\*(.+?)\*\* \| (.*?) \| (.*?) \|\s*$", tail, flags=re.M)
        if len(rows) != len(built):
            print(f"warning: {md.name}: {len(rows)} suggested applets but {len(built)} in {page}", file=sys.stderr)
        embed_page = f"embed-{page}"
        out = ["\n## Interactive applets\n",
               "Each applet runs in the page; use *Open full screen* for more room, "
               f"or open [all of this chapter's applets](applets/{page}){{target=\"_blank\"}} together.\n"]
        for i, ((aid, atitle), row) in enumerate(zip(built, rows), 1):
            name, does, teaches = row
            out.append(f"### Applet {num}.{i} · {name}\n\n{does}\n")
            out.append(embed(f"applets/{embed_page}#{aid}", f"*Teaches:* {teaches}",
                             unescape(atitle), f"applets/{page}#{aid}") + "\n")
        text = head.rstrip() + "\n" + "\n".join(out)

    text = re.sub(r"\n{3,}", "\n\n", text).strip("\n")
    return front_matter(title=title, subtitle=subtitle, order=num) + text + "\n"


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
    for md in sorted(Path(src, "notes").glob("[0-9][0-9]-*.md")):
        (dest / md.name).write_text(mec1043_1062_chapter(md, applets), encoding="utf-8")


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
