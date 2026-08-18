# degel.com — source

The 2026 single-page site for Degel Software Ltd. Launched 2026-08-18.

## Layout

| Path | What |
|---|---|
| `index.src.html` | THE source — all copy and CSS, with `{{IMG:name}}` image placeholders |
| `build.py` | builds `index.html` (inlines images as data URIs) |
| `index.html` | built output — fully self-contained, this is what deploys |
| `assets/` | logo/image sources for the build |
| `og.png`, `robots.txt`, `sitemap.xml`, `CNAME` | deployable root artifacts |
| `history/pre-2026/` | the retired pre-2026 site, exactly as archived on the live domain (noindexed) |
| `private/` | **never deploy** — internal notes incl. `DECISIONS.md` (contains client details) |

## Workflow

```bash
# edit index.src.html, then:
python3 build.py

# deploy (from repo root):
git checkout gh-pages
git checkout <source-branch> -- index.html og.png robots.txt sitemap.xml history
git commit -m "Deploy: <what changed>"
git push origin gh-pages
git checkout <source-branch>
```

`gh-pages` on `github.com/deg/degel` (public) serves degel.com via GitHub
Pages. Deploys copy the built artifacts only — never `index.src.html`,
`assets/`, `build.py`, or anything in `private/`.

Old soft-launch URL `/revamp-2026/` is a redirect stub on `gh-pages` only.
