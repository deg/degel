#!/usr/bin/env python3
"""Mutation tests for check.py.  Run:  make test

A checker that only ever passes proves nothing. Each case below breaks exactly
one invariant in the built site and asserts check.py notices, then restores.

This file exists because an earlier round of hand-written mutations passed
completely while check.py had SEVEN silent holes in it — the mutations only
covered the cases the checks already handled. Every hole found then has a case
here, so none of them can come back:

  * self-containment inspected src= only, so an external stylesheet passed
  * the link checker dropped any href containing '#' instead of truncating
  * the waveband scan required class to be the first attribute
  * article checks keyed on path depth and skipped a nested article
  * a Medium link was demanded of every article, failing a site-native one
  * section ids were matched as [a-z]+, so a hyphen faked an adjacency
  * nav presence and nav uniqueness disagreed about what a <nav> is

Mutations are applied to the SOURCES and rebuilt, not to the built HTML, so a
case cannot pass by producing markup the generator would never emit.

No dependencies: stdlib only, matching build.py and the rest of the site.
"""

import pathlib
import shutil
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent
failures = []


def build():
    subprocess.run([sys.executable, "build.py"], cwd=root, capture_output=True)


def check_failures():
    """How many assertions check.py reports as failing right now."""
    r = subprocess.run(
        [sys.executable, "check.py"], cwd=root, capture_output=True, text=True
    )
    return sum(1 for line in r.stdout.splitlines() if line.startswith("  FAIL"))


def mutate(label, rel, transform, expect_caught=True):
    """Apply `transform` to one source file, rebuild, and assert check.py's
    verdict flips (or, for expect_caught=False, that it does NOT — used to
    prove a check is not merely failing on everything)."""
    path = root / rel
    original = path.read_text()
    try:
        path.write_text(transform(original))
        build()
        n = check_failures()
    finally:
        path.write_text(original)
        build()
    ok = (n > 0) if expect_caught else (n == 0)
    verdict = "caught" if n else "passed"
    print(f"  {'ok  ' if ok else 'FAIL'}  {label} ({verdict}, {n} failure(s))")
    if not ok:
        failures.append(label)


def mutate_new_page(label, rel, body, expect_caught=True):
    """Add a whole new source page, rebuild, assert, then remove it."""
    src = root / rel
    out = root / str(pathlib.Path(rel).relative_to("src")).replace(".src.html", ".html")
    try:
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(body)
        build()
        n = check_failures()
    finally:
        shutil.rmtree(src.parent, ignore_errors=True)
        shutil.rmtree(out.parent, ignore_errors=True)
        build()
    ok = (n > 0) if expect_caught else (n == 0)
    print(f"  {'ok  ' if ok else 'FAIL'}  {label} ({'caught' if n else 'passed'}, {n})")
    if not ok:
        failures.append(label)


ARTICLE = """{{META
title: Probe
date: 2026-07-01
blurb: A probe page.
%(extra)s}}
<!DOCTYPE html>
<html lang="en">
<head>
{{INCLUDE:_meta.html}}
<title>{{title}}</title>
<meta name="description" content="{{blurb}}">
<meta property="og:url" content="https://degel.com{{url}}">
<link rel="canonical" href="https://degel.com{{url}}">
{{INCLUDE:_style.html}}
{{INCLUDE:_style-article.html}}
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "Article",
 "headline": "{{title}}", "datePublished": "{{date}}"}
</script>
</head>
<body>
{{INCLUDE:_nav.html}}
<main id="content"><section><div class="wrap">
<div class="article"><p>Body.</p></div>
{{ARTICLE_NAV}}
</div></section></main>
{{INCLUDE:_contact.html}}
{{INCLUDE:_footer.html}}
</body>
</html>
"""


def main():
    print("check.py mutation tests\n")
    print(f"  baseline: {check_failures()} failure(s) — must be 0\n")

    # --- self-containment: every form of external resource load ---
    for label, inject in [
        (
            "external stylesheet (webfont)",
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">\n',
        ),
        (
            "preconnect to a third party",
            '<link rel="preconnect" href="https://fonts.gstatic.com">\n',
        ),
        ("remote favicon", '<link rel="icon" href="https://example.com/f.png">\n'),
        ("remote script", '<script src="https://cdn.example.com/x.js"></script>\n'),
        (
            "CSS url()",
            "<style>body{background:url(https://example.com/b.png)}</style>\n",
        ),
        ("CSS @import", '<style>@import "https://example.com/x.css";</style>\n'),
        (
            "Medium tracking pixel",
            '<img src="https://medium.com/_/stat?event=post.clientViewed">\n',
        ),
    ]:
        mutate(label, "src/_meta.html", lambda s, i=inject: s + i)

    # A <link> whose rel merely describes the page fetches nothing. Flagging
    # those would make the check unusable — every page carries a canonical.
    # (Injecting a second canonical would trip check_canonical instead, which
    # is a different assertion; rel="alternate" isolates this one.)
    mutate(
        "a non-fetching rel is NOT flagged",
        "src/_meta.html",
        lambda s: s + '<link rel="alternate" href="https://example.com/feed.xml">\n',
        expect_caught=False,
    )

    # --- links ---
    mutate(
        "dead link, no fragment",
        "src/_nav.html",
        lambda s: s.replace('href="/writing/"', 'href="/writing/gone/"'),
    )
    mutate(
        "dead link WITH a fragment",
        "src/_nav.html",
        lambda s: s.replace('href="/writing/"', 'href="/writing/gone/#top"'),
    )

    # --- shared chrome ---
    mutate(
        "footer missing",
        "src/_footer.html",
        lambda s: s.replace("<footer>", "<footerX>"),
    )
    mutate(
        "contact block missing",
        "src/_contact.html",
        lambda s: s.replace('id="contact"', 'id="contactX"'),
    )
    mutate(
        "a second nav claims the Site label",
        "src/_footer.html",
        lambda s: '<nav aria-label="Site"></nav>\n' + s,
    )
    mutate(
        "site nav carries an extra class (must still be recognised)",
        "src/_nav.html",
        lambda s: s.replace(
            '<nav aria-label="Site">', '<nav class="x" aria-label="Site">'
        ),
        expect_caught=False,
    )

    # --- canonical ---
    mutate(
        "canonical points at the wrong page",
        "src/writing/index.src.html",
        lambda s: s.replace(
            'href="https://degel.com/writing/"', 'href="https://degel.com/oops/"'
        ),
    )

    # --- wavebands ---
    mutate(
        "two wavebands adjacent",
        "src/index.src.html",
        lambda s: s.replace(
            '<section id="writing">',
            '<div class="waveband divider"></div><section id="writing">',
        ),
    )
    mutate(
        "waveband with class NOT first (must still be seen)",
        "src/index.src.html",
        lambda s: s.replace(
            '<div class="waveband divider on-tintb" aria-hidden="true">',
            '<div aria-hidden="true" class="waveband divider on-tintb">',
        ).replace('<section id="writing">', ""),
    )
    mutate(
        "hyphenated section id (must NOT fake an adjacency)",
        "src/index.src.html",
        lambda s: s.replace('<section id="writing">', '<section id="case-studies">'),
        expect_caught=False,
    )

    # --- deploy config ---
    # The regression this guards: for months the recipe copied og.png and
    # robots.txt and not CNAME, and nothing anywhere would have noticed.
    mutate(
        "the deploy dropping CNAME is caught",
        "Makefile",
        lambda s: s.replace("cp CNAME og.png", "cp og.png"),
    )

    # The JSON-LD portrait: three independent ways it can point at nothing,
    # none of which changes how a single page looks or builds.
    mutate(
        "JSON-LD image naming a file that is not in the repo is caught",
        "src/index.src.html",
        lambda s: s.replace(
            '"image": "https://degel.com/assets/david.jpg"',
            '"image": "https://degel.com/assets/nobody.jpg"',
        ),
    )
    mutate(
        "the deploy dropping the JSON-LD image is caught",
        "Makefile",
        lambda s: s.replace("\tcp assets/david.jpg .deploy-tmp/assets/\n", ""),
    )
    # This is the one that nearly shipped: the file deploys, the URL resolves
    # for a human, and no indexer is permitted to fetch it.
    mutate(
        "a JSON-LD image behind a robots.txt Disallow is caught",
        "robots.txt",
        lambda s: s.replace(
            "Disallow: /history/", "Disallow: /history/\nDisallow: /assets/"
        ),
    )
    # A different deployed file, copied by a different recipe line, must still
    # pass — the check must not be keyed to one hard-coded path.
    mutate(
        "a JSON-LD image at the repo root (must pass)",
        "src/index.src.html",
        lambda s: s.replace(
            '"image": "https://degel.com/assets/david.jpg"',
            '"image": "https://degel.com/og.png"',
        ),
        expect_caught=False,
    )
    # Not just the home page. The entities are cross-linked by @id so that
    # later pages can reference them, which means later pages will carry
    # JSON-LD of their own.
    mutate_new_page(
        "a broken JSON-LD image on a page other than the home page is caught",
        "src/writing/probe/index.src.html",
        (ARTICLE % {"extra": ""}).replace(
            '"datePublished": "{{date}}"',
            '"datePublished": "{{date}}",\n "image": "https://degel.com/assets/nobody.jpg"',
        ),
    )

    # --- articles ---
    mutate_new_page(
        "nested article still gets its metadata checked",
        "src/writing/2026/probe/index.src.html",
        (ARTICLE % {"extra": ""}).replace(
            '"datePublished": "{{date}}"', '"datePublished": "nonsense"'
        ),
    )
    mutate_new_page(
        "article written here first, never on Medium (must pass)",
        "src/writing/probe/index.src.html",
        ARTICLE % {"extra": ""},
        expect_caught=False,
    )
    # JSON is not whitespace-significant. An earlier version matched the
    # literal '"@type": "Article"', so a compactly written block false-failed
    # on a page that was perfectly correct.
    mutate_new_page(
        "compact JSON-LD, no space after the colon (must pass)",
        "src/writing/probe/index.src.html",
        (ARTICLE % {"extra": ""})
        .replace('"@type": "Article",', '"@type":"Article",')
        .replace('"datePublished": "{{date}}"', '"datePublished":"{{date}}"'),
        expect_caught=False,
    )
    # ...but loosening the pattern must not stop it catching a real fault.
    mutate_new_page(
        "a non-ISO datePublished is still caught",
        "src/writing/probe/index.src.html",
        (ARTICLE % {"extra": ""}).replace(
            '"datePublished": "{{date}}"', '"datePublished": "July 2026"'
        ),
    )

    print(
        f"\n{'ALL TESTS PASS' if not failures else str(len(failures)) + ' FAILURE(S)'}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
