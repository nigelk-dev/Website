# nigelkent.ie

Personal website built with [Quarto](https://quarto.org) and published to
GitHub Pages at <https://nigelkent.ie>.

Course notes are pulled from their own repositories at build time (on every
push, daily, or on manual run; only `main` is deployed) and turned into one page per Markdown
file by `scripts/notes.py`, with every interactive applet embedded live where
the notes refer to it:

- **MEC1019: Sustainable Processes** (Introduction to microcontrollers) from
  the `notes/` folder of nigelk-dev/MEC1019_Sustainable_Processes
  (`scripts/fetch-mec1019.sh`)
- **MEC1002: Electrical Power and Electromechanical Systems** from
  nigelk-dev/ElectricalPowerNotes (`scripts/fetch-mec1002.sh`)
- **MEC1043/1062: Manufacturing Automation for Assembly and Inspection** from
  nigelk-dev/ManufacturingAutomationNotes (`scripts/fetch-mec1043-1062.sh`). Each
  chapter's "Suggested interactive applets" table is replaced by the built
  applets from its `applets/chNN.html` page, one live frame per applet.

On the site every course is shown as numbered chapters (in the sidebar and in
each page's "Chapter N · ..." subtitle), with no mention of lectures. Electrical
drives and Manufacturing Automation group their chapters into parts.

Introduction to microcontrollers is structured around its project instead: the
*Project Overview* page (`mec1019/project-overview.qmd`) shows the system
diagram, and there is one chapter per block of it (voltage measurement, the
Arduino, read input voltage, switching circuitry, pump drive type), built on a
breadboard with a relay module and an L298N module. A sixth, advanced chapter
covers the RenewableSwitchOver board and its schematic; the first five don't
mention it. The chapters are the Markdown files `notes/01-...md` to
`notes/06-...md` in the course repository, with their images, applets and the
scripts that draw their diagrams alongside: `images/...` and `applets/...`
links, and a line starting `> ▶️` or `> 🔧` with an applet link becomes a live
embedded applet. Edit the chapters there; `scripts/notes.py` builds the pages
from them, adds the knowledge checks, and redirects the old chapter addresses.

For the other two courses, each applet is embedded in the notes after the
section it illustrates; `scripts/notes.py` holds where each one goes
(`MEC1002_PLACES`, `MEC1043_1062_PLACES`). The old course overview addresses
redirect to each course's first chapter (for Introduction to microcontrollers,
to the Project Overview).

All three repositories are private, so the publish workflow needs a repository
secret `NOTES_TOKEN`: a fine-grained personal access token with read-only
*Contents* access to all three. Without it the course pages are built empty.

The home page shows a moving word cloud of the most used terms in the three
sets of notes (`assets/wordcloud.js`). `scripts/wordcloud.py` counts the terms
in the copied notes and writes `assets/wordcloud.json`; the workflow runs it
after the fetch steps. A snapshot is committed so the cloud still shows on a
build without the notes.

## Knowledge checks

Every chapter ends with an interactive knowledge check. The questions live in
this repository, one file per chapter: `checks/<course>/chNN.yml`
(`mec1019`, `mec1002`, `mec1043-1062`). Edit those files to change them.
For Electrical drives they **replace** the static "Knowledge Check" sections
in the ElectricalPowerNotes repository, so changes made there no longer show
on the site.

Question types: multiple choice (`mcq`), select all that apply (`multi`),
calculations with a tolerance, worked solution and random **New numbers**
(`numeric`), fill in the blanks, typed or chosen from a list, also inside code
(`cloze`), put in order (`order`), Boolean expressions checked by truth table
(`boolean`), and explain-then-reveal (`reveal`). Hands-on types work like
the course applets: set sliders and switches to hit a target on live gauges,
lamps and plots (`tune`), drag a cursor along a graph (`graph`), click to fill
a truth table (`truthtable`), and paint a timing diagram (`timing`). The
checks are styled in the Applet Lab design. The format of each is
described at the top of `scripts/checks.py`, and the existing files are good
examples to copy.

Check your edits before pushing (the publish workflow runs the same check and
stops if a question is broken):

```bash
python3 scripts/checks.py
```

## Local preview

```bash
scripts/fetch-mec1019.sh   # copy MEC1019 notes + applets into mec1019/notes/
scripts/fetch-mec1002.sh   # copy MEC1002 notes + interactives into mec1002/notes/
scripts/fetch-mec1043-1062.sh  # copy MEC1043/1062 notes + Applet Lab into mec1043-1062/notes/
scripts/wordcloud.py       # refresh the home page word cloud data
quarto preview
```

## One-time setup

1. **GitHub Pages:** repo *Settings → Pages → Build and deployment → Source:
   GitHub Actions*. Under *Custom domain*, enter `nigelkent.ie` and, once DNS
   resolves, tick *Enforce HTTPS*.
2. **DNS** (at the registrar for `nigelkent.ie`):
   - Apex `nigelkent.ie` — four `A` records:
     `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - Optional IPv6 — four `AAAA` records:
     `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`
   - `www` — `CNAME` to `nigelk-dev.github.io.` (GitHub then redirects
     `www.nigelkent.ie` to `nigelkent.ie`)
3. Optional: verify the domain under your GitHub account
   *Settings → Pages → Verified domains*.
