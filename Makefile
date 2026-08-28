.DEFAULT_GOAL := help

PY := build.py check.py inject_archive_noindex.py test_build.py test_check.py

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

deploy: check  ## publish to degel.com; MSG="what changed" required
	@test -n "$(MSG)" || { echo 'usage: make deploy MSG="what changed"'; exit 1; }
	@test -z "$$(git status --porcelain -- $(SOURCE_PATHS))" || { echo "ERROR: uncommitted or untracked source changes — commit them first"; git status --short -- $(SOURCE_PATHS); exit 1; }
	git worktree add .deploy-tmp gh-pages
	cp CNAME og.png robots.txt .deploy-tmp/
	mkdir -p .deploy-tmp/assets
	cp assets/david.jpg .deploy-tmp/assets/
	rsync -a --files-from=.build-outputs . .deploy-tmp/
	rsync -a --delete history/ .deploy-tmp/history/
	cd .deploy-tmp && git add -A && \
	  if git diff --cached --quiet; then echo "nothing to deploy — live already matches"; \
	  else git commit -m "Deploy: $(MSG)" && git push origin gh-pages; fi
	git worktree remove .deploy-tmp
	@echo "Done. GitHub Pages rebuilds in ~1-10 min; then: make check-live"

check-live:  ## confirm degel.com serves the current local build
	@curl -s "https://degel.com/?cb=$$RANDOM" | cmp -s - index.html \
	  && echo "LIVE matches the local build" \
	  || echo "live differs — Pages build pending, or local build not yet deployed"
