# degel.com — source

The 2026 site for Degel Software Ltd. Launched 2026-08-18. Every page is
built from `src/` and ships fully self-contained — no framework, no CDN,
no webfonts, no external requests.

## Layout

| Path | What |
|---|---|
| `src/` | THE sources. Every `src/**/*.src.html` is a page; `src/_*.html` are shared partials (nav, footer, CSS, script) |
| `src/writing/<slug>/` | one essay per directory. A `{{META}}` block at the top of each supplies title/date/blurb (plus optional `standfirst` and `medium`); the `/writing/` list, the home-page teaser, previous/next, the top back-link, the foot links and `sitemap.xml` are all generated from it, so **adding an essay is: create the directory, write the file** |
| `build.py` | builds the pages (resolves `{{INCLUDE:}}`, then inlines images as data URIs) |
| `check.py` | post-build invariants — `make check`, and `make deploy` runs it first so a failing build cannot publish |
| `test_build.py` | `build.py`'s failure paths (bad `{{META}}`, include cycles, missing partials) against throwaway trees — `make test` |
| `test_check.py` | mutation tests: breaks one invariant in the sources at a time and asserts `check.py` notices. A checker that only ever passes proves nothing |
| `index.html` | built output — fully self-contained, this is what deploys |
| `assets/` | logo/image sources for the build. Inlined as data URIs, so nothing here deploys — except `david.jpg`, which also deploys as a real file because the JSON-LD `Person.image` needs a URL |
| `og.png`, `robots.txt`, `CNAME`, `assets/david.jpg` | deployable artifacts, copied by the deploy recipe rather than built |
| `sitemap.xml` | **generated** by `build.py` from the same walk that emits the pages — never hand-edit |
| `history/pre-2026/` | the retired pre-2026 site, exactly as archived on the live domain (noindexed) |
| `DECISIONS.md` | symlink into the PRIVATE `../website-internal-assets` repo (this repo is public — client-sensitive notes never live here) |

## Workflow

`make` is the front door — `make help` lists targets.

```bash
# edit a source under src/, then:
make build                        # regenerate the pages
make check                        # verify links, canonicals, self-containment
make lint && make test            # ruff, then the build's failure paths
make serve                        # preview at http://localhost:8000

# commit the source change on this branch, then:
make deploy MSG="what changed"    # publish to degel.com via a temp worktree
make check-live                   # verify degel.com serves this exact build
```

Deploy never switches your checkout: it opens `gh-pages` in a temporary
worktree (`.deploy-tmp/`, gitignored), copies the built artifacts
(every page listed in `.build-outputs`, which includes the generated
`sitemap.xml`, plus `og.png`, `robots.txt`, `assets/david.jpg`, `history/`),
commits, pushes, and cleans up. It refuses to run with uncommitted source
changes.

`gh-pages` on `github.com/deg/degel` (public) serves degel.com via GitHub
Pages. Deploys copy the built artifacts only — never `src/` or `build.py`,
and nothing from `assets/` but the portrait. `DECISIONS.md` is a gitignored
symlink into the private `degel-website-internal-assets` repo, same as
`CLAUDE.md` and the agent config — client-sensitive notes must never be
committed here.

Old soft-launch URL `/revamp-2026/` is a redirect stub on `gh-pages` only.
