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
| `DECISIONS.md` | symlink into the PRIVATE `../website-internal-assets` repo (this repo is public — client-sensitive notes never live here) |

## Workflow

`make` is the front door — `make help` lists targets.

```bash
# edit index.src.html, then:
make build                        # regenerate index.html
make serve                        # preview at http://localhost:8000

# commit the source change on this branch, then:
make deploy MSG="what changed"    # publish to degel.com via a temp worktree
make check-live                   # verify degel.com serves this exact build
```

Deploy never switches your checkout: it opens `gh-pages` in a temporary
worktree (`.deploy-tmp/`, gitignored), copies the built artifacts
(`index.html`, `og.png`, `robots.txt`, `sitemap.xml`, `history/`),
commits, pushes, and cleans up. It refuses to run with uncommitted
source changes.

`gh-pages` on `github.com/deg/degel` (public) serves degel.com via GitHub
Pages. Deploys copy the built artifacts only — never `index.src.html`,
`assets/`, or `build.py`. `DECISIONS.md` is a gitignored symlink into the
private `degel-website-internal-assets` repo, same as `CLAUDE.md` and the
agent config — client-sensitive notes must never be committed here.

Old soft-launch URL `/revamp-2026/` is a redirect stub on `gh-pages` only.
