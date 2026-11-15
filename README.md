# nigel.kent.ie

Personal website built with [Quarto](https://quarto.org) and published to
GitHub Pages at <https://nigel.kent.ie>.

Course materials for **MEC1019: Sustainable Processes** are pulled from
[nigelk-dev/MEC1019_Sustainable_Processes](https://github.com/nigelk-dev/MEC1019_Sustainable_Processes)
at build time (on every push to `main`, daily, or on manual run).

## Local preview

```bash
scripts/fetch-mec1019.sh   # copy course files into mec1019/materials/
quarto preview
```

## One-time setup

1. **GitHub Pages:** repo *Settings → Pages → Build and deployment → Source:
   GitHub Actions*. Under *Custom domain*, enter `nigel.kent.ie` and, once DNS
   resolves, tick *Enforce HTTPS*.
2. **DNS** (at the registrar for `kent.ie`): add a record
   `nigel  CNAME  nigelk-dev.github.io.`
3. Optional: verify the domain under your GitHub account
   *Settings → Pages → Verified domains*.
