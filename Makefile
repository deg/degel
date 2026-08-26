.DEFAULT_GOAL := help

help:  ## list targets
	@grep -E '^[a-z-]+:.*##' Makefile | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

build:  ## regenerate the site's pages from src/
	python3 build.py

serve: build  ## preview locally at http://localhost:8000
	python3 -m http.server 8000

deploy: build  ## publish to degel.com; MSG="what changed" required
	@test -n "$(MSG)" || { echo 'usage: make deploy MSG="what changed"'; exit 1; }
	@git diff --quiet -- src assets build.py || { echo "ERROR: uncommitted source changes — commit them first"; exit 1; }
	git worktree add .deploy-tmp gh-pages
	cp og.png robots.txt sitemap.xml .deploy-tmp/
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
