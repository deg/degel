.DEFAULT_GOAL := help

PY := build.py check.py inject_archive_noindex.py make_og.py test_build.py test_check.py

# Where the live site is assembled before it is mirrored onto gh-pages.
STAGE := .deploy-stage

# Everything a page is built FROM. `deploy` refuses to publish while any of it
# is dirty, so that what is live can always be rebuilt from what is committed.
# `history/` is here because the deploy rsyncs it wholesale: an uncommitted
# edit to an archived page goes live with nothing recording what it was.
SOURCE_PATHS := src assets history $(PY)

help:  ## list targets
	@grep -E '^[a-z-]+:.*##' Makefile | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

build:  ## regenerate the site's pages from src/
	python3 build.py

check: build  ## verify the built pages (links, canonicals, self-containment)
	python3 check.py

lint:  ## ruff over the build and check scripts
	ruff check $(PY)
	ruff format --check $(PY)

test: check  ## build.py's failure paths, and check.py's mutation tests
	python3 test_build.py
	python3 test_check.py

serve: build  ## preview locally at http://localhost:8000
	python3 -m http.server 8000

# deploy assembles the ENTIRE live site in $(STAGE) and then mirrors that tree
# onto gh-pages with --delete. Copying file-by-file into the worktree could
# only ever add and overwrite, so a retired page stayed live for good: the
# manifest stopped listing it, nothing copied it, and nothing removed it.
# What is not staged is not on the site (website-efe.10).
#
# Staging BEFORE the worktree exists is also what retires the stray-worktree
# hazard. A bad manifest makes rsync exit 23, which used to abort AFTER
# `git worktree add` and leave .deploy-tmp behind to break the next deploy at
# add-time. Now nothing has been created yet when it fails.
#
# The two rsync excludes are anchored and both are load-bearing. /.git in a
# worktree is a FILE pointing at the real gitdir -- delete it and the worktree
# is gone. /.gitignore exists only on gh-pages, where it is the guard keeping
# the private symlinked tooling off a public branch; it has no counterpart to
# stage, so it is preserved rather than mirrored.
deploy: check  ## publish to degel.com; MSG="what changed" required
	@test -n "$(MSG)" || { echo 'usage: make deploy MSG="what changed"'; exit 1; }
	@test -z "$$(git status --porcelain -- $(SOURCE_PATHS))" || { echo "ERROR: uncommitted or untracked source changes — commit them first"; git status --short -- $(SOURCE_PATHS); exit 1; }
	rm -rf $(STAGE)
	mkdir -p $(STAGE)/assets
	rsync -a --files-from=.build-outputs . $(STAGE)/
	cp CNAME og.png robots.txt resume.pdf $(STAGE)/
	cp assets/david.jpg $(STAGE)/assets/
	rsync -a history/ $(STAGE)/history/
	git worktree remove --force .deploy-tmp 2>/dev/null || true
	rm -rf .deploy-tmp
	git worktree prune
	git worktree add .deploy-tmp gh-pages
	rsync -a --delete --exclude=/.git --exclude=/.gitignore $(STAGE)/ .deploy-tmp/
	cd .deploy-tmp && git add -A && \
	  if git diff --cached --quiet; then echo "nothing to deploy — live already matches"; \
	  else git commit -m "Deploy: $(MSG)" && git push origin gh-pages; fi
	git worktree remove --force .deploy-tmp
	rm -rf $(STAGE)
	@echo "Done. GitHub Pages rebuilds in ~1-10 min; then: make check-live"

check-live:  ## confirm degel.com serves the current local build
	@curl -s "https://degel.com/?cb=$$RANDOM" | cmp -s - index.html \
	  && echo "LIVE matches the local build" \
	  || echo "live differs — Pages build pending, or local build not yet deployed"
