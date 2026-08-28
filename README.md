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
| `make_og.py` | regenerates `og.png`, the social card. Run by hand, not by `make build` — the card changes about once a year and rebuilding it would rewrite a 40KB binary in every commit. Needs Pillow and macOS Palatino |
| `inject_archive_noindex.py` | gives every archived page under `history/` a robots `noindex`. Idempotent; re-run after importing another era. What counts as an archived page is imported from `check.py` so the two cannot disagree |
| `test_check.py` | mutation tests: breaks one invariant in the sources at a time and asserts `check.py` notices. A checker that only ever passes proves nothing |
| `index.html` | built output — fully self-contained, this is what deploys |
| `assets/` | logo/image sources for the build. Inlined as data URIs, so nothing here deploys — except `david.jpg`, which also deploys as a real file because the JSON-LD `Person.image` needs a URL |
| `og.png`, `robots.txt`, `CNAME`, `assets/david.jpg` | deployable artifacts, copied by the deploy recipe rather than built |
| `sitemap.xml` | **generated** by `build.py` from the same walk that emits the pages — never hand-edit |
| `docs/` | design rationale too long to sit in `DECISIONS.md` — currently `archive-indexing.md`, why the museum is kept out of search the way it is. Not deployed |
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

Deploy never switches your checkout. It assembles the whole live site in
`.deploy-stage/` (every page listed in `.build-outputs`, which includes the
generated `sitemap.xml`, plus `CNAME`, `og.png`, `robots.txt`,
`assets/david.jpg` and `history/`), opens `gh-pages` in a temporary worktree
(`.deploy-tmp/`), and MIRRORS the staging tree onto it with `--delete` — so a
page whose source is gone comes down off the live site instead of staying
published for good. Then it commits, pushes, and cleans up. It refuses to run
with uncommitted or untracked source changes.

`gh-pages` on `github.com/deg/degel` (public) serves degel.com via GitHub
Pages. Deploys copy the built artifacts only — never `src/` or `build.py`,
and nothing from `assets/` but the portrait. `DECISIONS.md` is a gitignored
symlink into the private `degel-website-internal-assets` repo, same as
`CLAUDE.md` and the agent config — client-sensitive notes must never be
committed here.

`gh-pages` carries one file with no counterpart here: its own `.gitignore`,
which keeps the private symlinked tooling off a public branch. The deploy
mirror excludes it deliberately. (The old `/revamp-2026/` redirect stub is
long gone — deleted in `636c257`.)
