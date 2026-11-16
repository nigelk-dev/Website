#!/usr/bin/env python3
"""Build the data for the word cloud on the home page.

Reads the course notes that the fetch-*.sh scripts copied into the site
(only the pages listed in the sidebar of _quarto.yml), counts the most used
terms (single words and two-word phrases) in each course, links terms that
often appear in the same paragraph, and writes assets/wordcloud.json.

Usage: scripts/wordcloud.py
If no course notes are present (a build without NOTES_TOKEN), the committed
assets/wordcloud.json is left as it is.
"""
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "wordcloud.json"

COURSES = {
    "mec1019": "MEC1019",
    "mec1002": "MEC1002",
    "mec1043-1062": "MEC1043/1062",
}
PER_COURSE = 22      # terms taken from each course
MAX_EDGES = 4        # strongest links kept per term

STOP = set("""
a about above after again against all also an and any are as at be because been
before being below between both but by can could did do does doing down during each
either etc even every few for from further get gets given gives go goes had has have
having here how however if in into is it its itself just less like made make makes
many may more most much must need needs no nor not now of off on once one only or
other our out over own per same see shown should show shows since so some such than
that the their them then there these they this those through thus to too two three
under until up use used uses using very via was way we well were what when where
which while who why will with within would yes you your also e.g i.e eg ie fig figure
lecture note notes example examples first second next last new one each value values
type types called known open full screen applet applets section page part following
order slide slides time times number set case cases point points result results
different way ways same important main simple below above left right high low
take takes taken find found give gives three four five six side end start step steps
change changes form small large total given equal often usually typically mean means
runs run teaches teach chapter exercise exercises answer answers source try res code runner
question questions solution activity task tasks check lab overview summary course
red green read write
""".split())

FRONT = re.compile(r"\A---\n.*?\n---\n", re.S)
TITLE = re.compile(r'^title:\s*"?(.*?)"?\s*$', re.M)
CLEAN = [
    (re.compile(r"```.*?```", re.S), " "),            # code and raw HTML blocks
    (re.compile(r"\$\$.*?\$\$", re.S), " "),          # display maths
    (re.compile(r"\$[^$\n]*\$"), " "),                # inline maths
    (re.compile(r"<[^>]+>"), " "),                    # HTML tags
    (re.compile(r"!\[[^\]]*\]\([^)]*\)"), " "),       # images (alt text is descriptive, skip)
    (re.compile(r"\]\([^)]*\)"), "] "),               # link targets
    (re.compile(r"\{[^}]*\}"), " "),                  # Pandoc attributes
    (re.compile(r"^:::.*$", re.M), " "),              # fenced divs
]
WORD = re.compile(r"[a-z][a-z\-]*[a-z]|[a-z]")


def pages():
    """(course, path) for every notes page in the sidebar, in sidebar order."""
    seen = []
    for m in re.finditer(r"href:\s*((mec[^/\s]+)/notes/\S+\.md)", (ROOT / "_quarto.yml").read_text()):
        rel, course = m.group(1), m.group(2)
        if course in COURSES and (ROOT / rel).is_file() and rel not in seen:
            seen.append(rel)
            yield course, rel


def paragraphs(text):
    text = FRONT.sub("", text)
    for rx, rep in CLEAN:
        text = rx.sub(rep, text)
    for para in re.split(r"\n\s*\n", text.lower()):
        words = [w for w in WORD.findall(para.replace("’", "'"))]
        if words:
            yield words


def terms(words):
    """Single words and two-word phrases (no stopwords) in one paragraph."""
    out = []
    keep = [w if (len(w) > 2 and w not in STOP) else None for w in words]
    for i, w in enumerate(keep):
        if w:
            out.append(w)
            if i + 1 < len(keep) and keep[i + 1]:
                out.append(w + " " + keep[i + 1])
    return out


def singular(t):
    """Fold simple plurals so 'motors' and 'motor' count together."""
    def one(w):
        if len(w) > 4 and w.endswith("ies"):
            return w[:-3] + "y"
        if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
            return w[:-1]
        return w
    return " ".join(one(w) for w in t.split())


def main():
    found = list(pages())
    if not found:
        print("wordcloud: no course notes found; keeping", OUT.relative_to(ROOT))
        return

    count = {c: Counter() for c in COURSES}          # term -> occurrences per course
    page_count = defaultdict(Counter)                # term -> occurrences per page
    para_terms = []                                  # set of terms in each paragraph
    titles = {}
    surface = defaultdict(Counter)                   # folded term -> spellings seen

    for course, rel in found:
        text = (ROOT / rel).read_text(encoding="utf-8")
        m = TITLE.search(FRONT.match(text).group(0)) if FRONT.match(text) else None
        titles[rel] = m.group(1) if m else Path(rel).stem
        for words in paragraphs(text):
            ts = []
            for t in terms(words):
                f = singular(t)
                surface[f][t] += 1
                ts.append(f)
            count[course].update(ts)
            for t in ts:
                page_count[t][rel] += 1
            para_terms.append(set(ts))

    total = Counter()
    for c in count.values():
        total.update(c)

    # Two-word phrases are rarer than single words; weight them up a little so
    # "induction motor" can win over "induction".
    def score(t, c):
        n = count[c][t]
        return n * (2.6 if " " in t else 1.0)

    chosen = {}
    for c in COURSES:
        ranked = sorted(count[c], key=lambda t: -score(t, c))
        picked = []
        for t in ranked:
            if len(picked) >= PER_COURSE:
                break
            if count[c][t] < 3 or t in chosen:
                continue
            # Skip a word already covered by a chosen phrase, and a phrase
            # that is just its own commoner word repeated.
            if " " not in t and any(t in p.split() and count[c][p] * 2.2 > count[c][t] for p in picked):
                continue
            if " " in t and any(w in [x for x in picked if " " not in x] and count[c][w] > count[c][t] * 2.2
                                for w in t.split()):
                continue
            picked.append(t)
        for t in picked:
            chosen[t] = c

    nodes = []
    index = {}
    for t, c in chosen.items():
        share = {k: count[k][t] for k in COURSES if count[k][t]}
        home = max(share, key=share.get)
        best = page_count[t].most_common(1)[0][0]
        label = surface[t].most_common(1)[0][0]
        index[t] = len(nodes)
        nodes.append({
            "t": label,
            "n": total[t],
            "c": home,
            "also": sorted(k for k, v in share.items() if k != home and v >= 3),
            "url": "/" + best[:-3] + ".html",
            "page": titles[best],
        })

    # Links: terms that share paragraphs, scored by how much more often they
    # meet than chance would suggest (normalised co-occurrence).
    co = Counter()
    for ts in para_terms:
        hit = sorted(index[t] for t in ts if t in index)
        for i in range(len(hit)):
            for j in range(i + 1, len(hit)):
                co[hit[i], hit[j]] += 1
    strength = {}
    for (a, b), n in co.items():
        if n >= 2:
            strength[a, b] = n / math.sqrt(nodes[a]["n"] * nodes[b]["n"])
    best_for = defaultdict(list)
    for (a, b), s in strength.items():
        best_for[a].append((s, b))
        best_for[b].append((s, a))
    edges = {}
    for a, lst in best_for.items():
        for s, b in sorted(lst, reverse=True)[:MAX_EDGES]:
            edges[min(a, b), max(a, b)] = round(s, 3)

    data = {
        "courses": {c: {"name": COURSES[c], "href": f"/{c}/index.html"} for c in COURSES},
        "nodes": nodes,
        "links": [[a, b, s] for (a, b), s in sorted(edges.items())],
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wordcloud: {len(nodes)} terms, {len(edges)} links from {len(found)} pages -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
