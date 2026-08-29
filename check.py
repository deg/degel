#!/usr/bin/env python3
"""Post-build checks on the generated pages.  Run:  make check

These exist because the bugs this site actually ships are not the ones a type
checker would catch. Every check below is here because the thing it tests went
wrong at least once:

  * a shared partial silently stopped being included
  * a <nav> inherited the site nav's sticky chrome from a bare element
    selector, rendering a second nav bar mid-page
  * two wave dividers ended up adjacent when the section between them moved
  * a page linked to a URL that did not exist
  * Medium's per-article tracking pixel would have gone out on every essay,
    reporting readers back to Medium and breaking the offline property

Anything requiring a browser (typography, spacing, contrast) is deliberately
out of scope — look at the page for those.

Three checks are about what DEPLOYS rather than about the HTML, and they
share one justification: a page can build, render and pass every other check
while the thing it depends on never reaches the live site. Losing CNAME
unpoints the domain; an uncopied JSON-LD image, or one behind a robots
Disallow, is structured data pointing at nothing; and a clean-source guard
blind to untracked files publishes what the repo cannot rebuild. Nothing
would look wrong in any of the three cases.

The path -> URL mapping is imported from build.py rather than re-derived here:
two copies of it had already drifted apart, and check.py agreeing with its own
bug is worse than having no check at all.

Matching selectors are written to be attribute-order independent. An earlier
version required `class` to come first, which meant a reordered attribute
silently disabled the guard.

No dependencies: stdlib only, matching build.py and the rest of the site.
"""

import json
import pathlib
import re
import sys
import urllib.parse

from build import expected_outputs, page_url

root = pathlib.Path(__file__).resolve().parent
failures = []

# Attribute matching is quote-agnostic. It was not: the pattern required
# double quotes, so <script src='https://...'> -- exactly how Cloudflare hands
# you its snippet -- was invisible to this check entirely. The allowlist below
# would have been theatre without this fix.
SRC_RE = re.compile(r"""src\s*=\s*(["'])(https?://[^"']+)\1""")

# The ONE third party this site is allowed to talk to (website-efe.3).
#
# Round 1's rule was no framework, no CDN, no webfonts, no external requests.
# Analytics breaks the last of those, deliberately and for a stated reason:
# GitHub Pages exposes no logs and no headers, so there is no first-party way
# to know anything about visitors, and Search Console only ever shows traffic
# that came from Google search -- never LinkedIn, which is the busiest way in.
#
# Kept to a single host on purpose. This is an exception, not a relaxation:
# every other external load still fails the build, and test_check.py proves it
# with a mutation that adds a different host.
ALLOWED_HOSTS = {"static.cloudflareinsights.com"}

# <link> relations that describe the page rather than load anything.
NON_FETCHING_REL = {
    "canonical",
    "alternate",
    "author",
    "license",
    "me",
    "prev",
    "next",
    "bookmark",
    "help",
    "search",
    "nofollow",
}


def check(ok, label, detail=""):
    """Record one assertion. Detail is shown only on failure, so a passing
    run stays skimmable."""
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}{'' if ok else '  — ' + detail}")
    if not ok:
        failures.append(label)


def pages():
    """Every built page, home first.

    Derived from build.py's own source walk, not from a glob of this file's
    own devising. The glob it replaced was `index.html` plus `writing/**`, so
    a page at any other path was invisible to every per-page check below AND
    broke check_sitemap, which compared the generated sitemap against it
    (website-efe.16). The service pages would all have landed outside
    `writing/`. Same lesson as page_url: one definition, imported.
    """
    built = [str(p) for p in expected_outputs()]
    return sorted(built, key=lambda p: (p != "index.html", p))


def archive_pages():
    """Every page in the retired-site archive, whatever it calls itself.

    The 2001-2015 site used .htm and the 2016-2026 one .html. Missing an
    extension here is not hypothetical: the original noindex injection matched
    .html only, so 32 .htm originals went ten days with no tag at all while
    everything looked done.

    inject_archive_noindex.py imports this rather than re-deriving it, on the
    same principle as page_url: the checker and the thing that satisfies it
    must not be able to disagree about what they are talking about.
    """
    return sorted(
        p
        for p in (root / "history").rglob("*")
        if p.is_file() and p.suffix.lower() in (".html", ".htm", ".shtml")
    )


def is_article(path):
    """A page under writing/ that is not the index. Depth-independent: an
    earlier version keyed on the number of slashes and silently skipped every
    check on a nested article."""
    return path.startswith("writing/") and path != "writing/index.html"


def check_self_contained(path, html):
    """A page that fetches anything at run time breaks the round-1 decision:
    no framework, no CDN, no webfonts, works offline.

    Only RESOURCE loads count. An <a href> to github.com is a link the reader
    may follow, not a request the page makes; the articles legitimately carry
    several. What must not appear is anything the browser fetches on its own:
    src=, <link href=>, CSS url(), @import. An earlier version checked src=
    alone, so an external stylesheet — a webfont, the case this docstring
    names — went straight through.
    """
    offenders = [m.group(2) for m in re.finditer(SRC_RE, html)]
    for tag in re.findall(r"<link\b[^>]*>", html):
        href = re.search(SRC_RE.pattern.replace("src", "href"), tag)
        rel = re.search(r'rel=["\']([^"\']*)["\']', tag)
        # A denylist, not an allowlist: a rel that merely DESCRIBES the page
        # fetches nothing, and everything else is assumed to. A rel invented
        # tomorrow then shows up as a loud false positive rather than a
        # silent miss, which is the right way round for this property.
        if href and not (rel and rel.group(1).lower() in NON_FETCHING_REL):
            offenders.append(href.group(2))
    offenders += re.findall(r"url\(\s*['\"]?(https?://[^)'\"]+)", html)
    offenders += re.findall(r"@import\s+['\"]?(https?://[^;'\"]+)", html)
    offenders = [
        u for u in offenders if urllib.parse.urlparse(u).hostname not in ALLOWED_HOSTS
    ]
    check(not offenders, f"{path}: no external resource loads", str(offenders[:2]))
    check("medium.com/_/stat" not in html, f"{path}: no tracking pixel")


def check_shared_chrome(path, html):
    """Each page must carry the shared partials. A broken {{INCLUDE:}} would
    otherwise ship a page with no navigation and no footer.

    The site nav is asserted by check_one_nav, whose count of exactly one
    covers presence too — two checks over the same element disagreed once,
    one matching a literal string and the other a regex.
    """
    check("<footer>" in html, f"{path}: footer present")
    check('id="contact"' in html, f"{path}: contact block present")


def check_no_unresolved(path, html):
    """Defence in depth only: build.py runs the same test on the same string
    and exits first, so via `make check` this cannot fail. It earns its place
    for a tree left behind by a failed build, or a page written by hand.
    DOTALL so a multi-line block (an unparsed {{META ...}}) is caught too.
    """
    left = sorted(set(re.findall(r"\{\{.*?\}\}", html, re.S)))
    check(not left, f"{path}: no unresolved directives", str(left)[:120])


def check_links_resolve(path, html):
    """Every root-relative href must correspond to a file that exists. Catches
    a renamed slug that left a stale link behind.

    The fragment is stripped, not used to reject the match: an earlier pattern
    excluded '#' from the character class, so every href carrying one — which
    is every link in the site nav — was skipped entirely.
    """
    for href in sorted(set(re.findall(r'href="(/[^"]*)"', html))):
        target_path = href.split("#", 1)[0].split("?", 1)[0]
        if target_path in ("", "/"):
            target = root / "index.html"
        elif target_path.endswith("/"):
            target = root / target_path.lstrip("/") / "index.html"
        else:
            target = root / target_path.lstrip("/")
        check(target.exists(), f"{path}: link {href} resolves")


def elements(html, tag):
    """Every opening `tag`, as (attribute string, position). Attribute order
    is not assumed anywhere it is used."""
    return [(m.group(1), m.start()) for m in re.finditer(rf"<{tag}\b([^>]*)>", html)]


def check_one_nav(path, html):
    """The site nav's chrome is scoped to nav[aria-label="Site"]. If a second
    <nav> ever claims that label, both would render as sticky bars — and zero
    means the page shipped without navigation."""
    labels = [
        m.group(1)
        for attrs, _ in elements(html, "nav")
        for m in [re.search(r'aria-label="([^"]*)"', attrs)]
        if m
    ]
    check(labels.count("Site") == 1, f"{path}: exactly one site nav", str(labels))


def check_waveband_alternation(html):
    """The home page alternates section / waveband / section. Two adjacent
    wavebands render as a doubled divider — which shipped once already.

    Section ids may contain digits and hyphens; an earlier pattern allowed
    only [a-z], so renaming a section to `case-studies` made it invisible and
    faked an adjacency that was not there.
    """
    marks = []
    for tag in ("div", "section"):
        for attrs, pos in elements(html, tag):
            if re.search(r'class="[^"]*\bwaveband\b', attrs):
                marks.append((pos, "waveband"))
            elif tag == "section":
                m = re.search(r'id="([^"]+)"', attrs)
                if m:
                    marks.append((pos, m.group(1)))
    seq = [name for _, name in sorted(marks)]
    adjacent = [i for i in range(len(seq) - 1) if seq[i] == "waveband" == seq[i + 1]]
    check(not adjacent, "index.html: no two wavebands adjacent", " -> ".join(seq))


def check_canonical(path, html):
    """A wrong canonical is invisible on the page and quietly costs the page
    its own identity in search. og:url must agree with it."""
    can = re.search(r'<link rel="canonical" href="([^"]+)">', html)
    check(bool(can), f"{path}: has a canonical")
    if not can:
        return
    expected = "https://degel.com" + page_url(path)
    check(
        can.group(1) == expected,
        f"{path}: canonical is self-referential",
        f"{can.group(1)} != {expected}",
    )
    og = re.search(r'<meta property="og:url" content="([^"]+)">', html)
    check(og and og.group(1) == can.group(1), f"{path}: og:url matches canonical")


def check_article_metadata(path, html):
    """Article JSON-LD must carry the ORIGINAL publication date. Re-dating a
    syndicated post to its republish date forfeits its history.

    The Medium link is bounded, not required: build.py asks only for title,
    date and blurb, and the going-forward workflow publishes here FIRST. An
    earlier version demanded exactly one, which would have failed the deploy
    on the first essay written for this site rather than syndicated to it.
    """
    # Whitespace-tolerant: JSON is not whitespace-significant, and matching a
    # literal '": "' made these fail on a perfectly good page that happened to
    # be written compactly.
    check(
        bool(re.search(r'"@type"\s*:\s*"Article"', html)),
        f"{path}: Article JSON-LD",
    )
    check(
        bool(re.search(r'"datePublished"\s*:\s*"\d{4}-\d{2}-\d{2}"', html)),
        f"{path}: datePublished present",
    )
    medium = re.findall(r'href="https://medium\.com/@DavidEGoldfarb/[^"]+"', html)
    check(len(medium) <= 1, f"{path}: at most one link to the Medium copy", str(medium))


def check_cname_deploys():
    """CNAME is what points degel.com at GitHub Pages. It is not generated and
    not in .build-outputs, so the deploy recipe is the only thing that puts it
    on gh-pages — and for a long time the recipe did not, which nothing would
    have caught: the site would still build, still pass every other check, and
    simply stop answering on the custom domain."""
    mk = (root / "Makefile").read_text()
    copied = [ln for ln in mk.splitlines() if ln.strip().startswith("cp ")]
    check(
        (root / "CNAME").exists(),
        "CNAME exists in the repo",
    )
    check(
        any("CNAME" in ln for ln in copied),
        "the deploy copies CNAME",
        f"cp lines: {copied}",
    )


def check_deploy_guard_sees_untracked():
    """The deploy refuses to publish while the sources are dirty, so that what
    is live can always be rebuilt from what is committed. That guard was
    written with `git diff`, which compares TRACKED files only — a brand-new
    file walked straight past it.

    It is not merely untidy. The deploy would copy the new file to gh-pages
    while main had no record of it; a fresh clone would then be missing it and
    fail check_jsonld_images_deploy, which fails `make check`, which `deploy`
    depends on — every future deploy blocked from a tree that looks clean.
    `git status --porcelain` reports modified AND untracked, and still honours
    .gitignore, which is exactly the wanted semantics.
    """
    mk = (root / "Makefile").read_text()
    guard = [ln for ln in mk.splitlines() if "commit them first" in ln]
    check(len(guard) == 1, "the deploy has a clean-source guard", f"found: {guard}")
    if len(guard) == 1:
        check(
            "git status --porcelain" in guard[0],
            "the deploy's clean-source guard sees untracked files",
            f"guard: {guard[0].strip()}",
        )


def check_jsonld_images_deploy():
    """Every image any page's JSON-LD claims under degel.com must be a file
    that actually reaches the live site, and that Google is allowed to fetch.
    Three ways this fails silently, and the second one nearly shipped:

      * the file is not in the repo at all;
      * it is in the repo but only the deploy recipe can put it on gh-pages —
        assets/ is not in .build-outputs, so an uncopied file 404s while every
        page still builds and every other check still passes;
      * it deploys fine but robots.txt forbids crawling its path, so the
        structured data points at something no indexer will ever read.

    The portrait was very nearly declared at its /history/ URL, which deploys
    but is Disallowed — valid JSON, valid HTML, and worth nothing.

    Every page, not just the home page: the entities are cross-linked by @id
    precisely so that later pages can reference and extend them, and a page
    added tomorrow must not escape the check by not existing today.
    """
    blocks = []
    for path in pages():
        blocks += re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            pathlib.Path(path).read_text(),
            re.S,
        )
    urls = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "image" and isinstance(v, str):
                    urls.append(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for b in blocks:
        walk(json.loads(b))

    mk = (root / "Makefile").read_text()
    copied = [ln for ln in mk.splitlines() if ln.strip().startswith("cp ")]
    disallowed = re.findall(
        r"^Disallow:\s*(\S+)", (root / "robots.txt").read_text(), re.M
    )

    # Deduped: a shared partial declaring one would otherwise report it seven
    # times and bury everything else.
    for url in dict.fromkeys(urls):
        if not url.startswith("https://degel.com/"):
            continue
        rel = url[len("https://degel.com/") :]
        check((root / rel).exists(), f"JSON-LD image exists in the repo: {rel}")
        check(
            any(rel in ln for ln in copied),
            f"the deploy copies the JSON-LD image: {rel}",
            f"cp lines: {copied}",
        )
        check(
            not any(("/" + rel).startswith(d) for d in disallowed),
            f"robots.txt lets crawlers fetch the JSON-LD image: {rel}",
            f"Disallow: {disallowed}",
        )


def check_archive_stays_out_of_search():
    """The /history/ museum must not pollute searches for the current site.

    Not a secrecy requirement -- the archive is public, and so is the repo it
    lives in. The requirement is only that stale 2001-2025 pages never surface
    as results for Degel queries. Four separate things hold that up, and each
    has already been proposed for removal at least once, so each is asserted
    here. The full argument, including the options rejected and why, is in
    docs/archive-indexing.md.

    1. robots.txt Disallows /history/. This is the one that cannot go. Seven
       PDFs, four .txt files and the .zip/.sis/.asp era artifacts cannot carry
       a meta tag, and GitHub Pages cannot send X-Robots-Tag -- so not being
       fetched is the only thing keeping their CONTENT out of a results page.
       Drop the line and a 2017 resume becomes indexable, in full.
    2. Every archived page carries a robots noindex. Dormant while (1) stands,
       since a crawler that may not fetch a page can never read a tag inside
       it. It is contingency armour for the day (1) regresses.
    3. The sitemap never advertises an archive URL.
    4. No deployed page links to /history/ with a crawlable href. This is the
       layer doing the actual work: the museum's door is attached by JS, so a
       crawler is never handed the URL in the first place. A plain <a> added
       here would undo more than the other three protect.
    """
    disallowed = re.findall(
        r"^Disallow:\s*(\S+)", (root / "robots.txt").read_text(), re.M
    )
    check(
        any(d.rstrip("/") == "/history" for d in disallowed),
        "robots.txt still Disallows /history/",
        f"Disallow lines: {disallowed}",
    )

    archive = archive_pages()
    missing = [
        str(p.relative_to(root))
        for p in archive
        if not re.search(rb"""name\s*=\s*["']robots["']""", p.read_bytes(), re.I)
    ]
    check(
        archive and not missing,
        f"all {len(archive)} archived pages carry a robots meta",
        f"missing: {missing}",
    )

    xml = (root / "sitemap.xml").read_text()
    check(
        "/history" not in xml,
        "the sitemap does not advertise the archive",
    )

    # Scoped to real elements, and this matters more than it looks. The
    # museum's door is `window.location.href = '/history/'` inside a <script>,
    # which a loose /href\s*=/ scan flags as a link -- flagging the one
    # mechanism that makes the archive undiscoverable. Reading attributes off
    # the tags themselves cannot reach into script CONTENT, so the JS door is
    # invisible here and a real <a> is not. Do not "fix" this into a plain
    # text search.
    #
    # Same-origin only: an outbound link to some other site's /history/ path
    # is a link the reader may follow, not a door into ours.
    linked = []
    for path in pages():
        html = pathlib.Path(path).read_text()
        for tag in ("a", "link", "area"):
            for attrs, _ in elements(html, tag):
                m = re.search(r"""href\s*=\s*["']([^"']+)["']""", attrs)
                if not m:
                    continue
                bare = m.group(1).split("#", 1)[0]
                for prefix in (
                    "/history",
                    "history",
                    "./history",
                    "https://degel.com/history",
                ):
                    if bare.startswith(prefix):
                        linked.append(f"{path}: {m.group(1)}")
                        break
    check(
        not linked,
        "no deployed page links to the archive with a crawlable href",
        str(linked[:3]),
    )


def check_deploy_retires_pages():
    """A page removed from src/ must actually come down off the live site.

    It could not, for as long as the deploy copied file-by-file into the
    gh-pages worktree: `rsync --files-from` only adds and overwrites, the
    manifest simply stopped listing the retired page, and `git add -A` saw a
    file still sitting there. Nothing anywhere deleted it. A retired page
    stayed published for good, and every check still passed.

    Two halves, and both are asserted because either alone leaves the bug:

      * the deploy must MIRROR the staging tree with --delete rather than
        copy into the worktree, so that what is not staged is not on the
        site. This is the half that can actually take a page down;
      * the manifest and the tree must agree, so a page nothing generated
        cannot ride along into the staging tree.

    build.py's own half -- unlinking the outputs of a source that is gone --
    is proven behaviourally in test_build.py, by retiring a page in a
    throwaway tree and looking. Asserting it here by grepping build.py for a
    function name would test the spelling, not the behaviour.
    """
    mk = (root / "Makefile").read_text()
    mirror = [
        ln
        for ln in mk.splitlines()
        if "rsync" in ln and "--delete" in ln and ".deploy-tmp" in ln
    ]
    check(
        len(mirror) == 1,
        "the deploy mirrors onto gh-pages with --delete",
        f"matching rsync lines: {mirror}",
    )
    if mirror:
        # Anchored, because /.git in a worktree is a file pointing at the real
        # gitdir: mirroring over it destroys the worktree mid-deploy.
        #
        # Tokenised, not a substring test. `--exclude=/.gitignore` CONTAINS
        # `--exclude=/.git`, so `in` would report the guard present on a line
        # that had lost it — which is how the first version of this check
        # passed its own mutation test.
        check(
            "--exclude=/.git" in mirror[0].split(),
            "the mirror cannot delete the worktree's own .git",
            mirror[0].strip(),
        )

    # The manifest and the tree must agree. If they do not, something was
    # generated by a build whose manifest is gone -- a fresh clone is the
    # case build.py's own pruning cannot cover, since it has no record of
    # what the previous build wrote.
    listed = {
        ln.strip()
        for ln in (root / ".build-outputs").read_text().splitlines()
        if ln.strip()
    }
    missing = sorted(p for p in listed if not (root / p).exists())
    check(not missing, "every manifest entry exists on disk", str(missing))

    # And the reverse, which the --delete mirror made dangerous: the manifest
    # is the deploy's whole idea of what the site contains. A page build.py
    # produces but the manifest omits is no longer merely uncopied -- it is
    # absent from the staging tree, so the mirror DELETES it from the live
    # site.
    unlisted = sorted({str(p) for p in expected_outputs()} - listed)
    check(
        not unlisted,
        "the manifest lists every page build.py produces",
        f"a deploy would take these down: {unlisted}",
    )
    # pages() is now derived from src/, so comparing it to the manifest can
    # only catch a stale MANIFEST -- never a stale FILE. Stale files need a
    # look at the disk: any .html that build.py would not produce, outside
    # the hand-written archive, is something a previous build left behind.
    should_exist = {str(p) for p in expected_outputs()}
    # src/ holds the SOURCES, whose names end .src.html and so match *.html;
    # history/ is the hand-written archive, which build.py never produced;
    # .deploy-* are the transient staging tree and worktree.
    strays = sorted(
        rel
        for rel in (str(f.relative_to(root)) for f in root.rglob("*.html"))
        if not rel.startswith(("src/", "history/", ".deploy"))
        and rel not in should_exist
    )
    check(
        not strays,
        "no output on disk that build.py would not produce",
        f"stray pages: {strays}",
    )


def check_sitemap():
    """The sitemap is generated, so this guards the generator: every listed
    URL must exist, and every built page must be listed."""
    xml = (root / "sitemap.xml").read_text()
    listed = set(re.findall(r"<loc>https://degel\.com(/[^<]*)</loc>", xml))
    built = {page_url(p) for p in pages()}
    check(
        listed == built,
        "sitemap lists exactly the built pages",
        f"only in sitemap: {listed - built}; only built: {built - listed}",
    )


def main():
    """Returns a shell exit code so `make check` — and therefore `make
    deploy`, which depends on it — fails on a broken build."""
    print("checking built pages\n")
    for path in pages():
        html = pathlib.Path(path).read_text()
        check_self_contained(path, html)
        check_shared_chrome(path, html)
        check_no_unresolved(path, html)
        check_links_resolve(path, html)
        check_one_nav(path, html)
        check_canonical(path, html)
        if is_article(path):
            check_article_metadata(path, html)
    check_waveband_alternation(pathlib.Path("index.html").read_text())
    check_cname_deploys()
    check_deploy_guard_sees_untracked()
    check_jsonld_images_deploy()
    check_archive_stays_out_of_search()
    check_deploy_retires_pages()
    check_sitemap()
    print(
        f"\n{'ALL CHECKS PASS' if not failures else str(len(failures)) + ' FAILURE(S)'}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
