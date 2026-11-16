# nigelkent.ie

Personal website built with [Quarto](https://quarto.org) and published to
GitHub Pages at <https://nigelkent.ie>.

Course notes are pulled from their own repositories at build time (on every
push to `main`, daily, or on manual run) and turned into one page per Markdown
file by `scripts/notes.py`, with every interactive applet embedded live where
the notes refer to it:

- **MEC1019: Sustainable Processes** from
  [nigelk-dev/MEC1019_Sustainable_Processes](https://github.com/nigelk-dev/MEC1019_Sustainable_Processes)
  (`scripts/fetch-mec1019.sh`)
- **MEC1002: Electrical Power and Electromechanical Systems** from
  nigelk-dev/ElectricalPowerNotes (`scripts/fetch-mec1002.sh`). That repository
  is private, so the publish workflow needs a repository secret `NOTES_TOKEN`:
  a fine-grained personal access token with read-only *Contents* access to
  ElectricalPowerNotes. Without it the MEC1002 pages are built empty.

## Local preview

```bash
scripts/fetch-mec1019.sh   # copy MEC1019 notes + applets into mec1019/notes/
scripts/fetch-mec1002.sh   # copy MEC1002 notes + interactives into mec1002/notes/
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
