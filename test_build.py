#!/usr/bin/env python3
"""Tests for build.py's failure paths.  Run:  make test

check.py inspects the pages a *successful* build produced. It therefore never
exercises any of build.py's guards — on a healthy tree none of them fire. That
gap is not hypothetical: website-efe.10 is a build-level bug that no
post-build check could have seen.

Each test below feeds build.py a deliberately broken source tree and asserts
it exits non-zero with a message naming the problem. A guard that silently
passes is worse than no guard, because the broken page ships.

Every case here was verified by hand while the feature was being built; this
file is what keeps those verifications from being lost.

No dependencies: stdlib only, matching build.py and the rest of the site.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile

BUILD = pathlib.Path(__file__).resolve().parent / "build.py"

MINIMAL_META = "{{META\ntitle: T\ndate: 2026-01-01\nblurb: B\n}}\n"

failures = []


def build_in(tmp):
    """Run the COPY of build.py inside the throwaway tree.

    It must be the copy, not the original: build.py derives its root from
    __file__, not from the working directory, so invoking the original would
    quietly rebuild the real site and every test would pass against it.
    """
    r = subprocess.run(
        [sys.executable, "build.py"], cwd=tmp, capture_output=True, text=True
    )
    return r.returncode, r.stdout + r.stderr


def make_tree(tmp, files):
    """Write {relative path: contents} under tmp, creating parents."""
    for rel, body in files.items():
        p = pathlib.Path(tmp) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)


def expect_failure(label, files, needle):
    """Assert build.py rejects this tree, and says why.

    `needle` is checked so a guard cannot pass the test by failing for some
    unrelated reason — an exit code alone would not prove the right guard ran.
    """
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(BUILD, pathlib.Path(tmp) / "build.py")
        make_tree(tmp, files)
        code, out = build_in(tmp)
    ok = code != 0 and needle in out
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}")
    if not ok:
        failures.append(label)
        print(
            f"          expected exit!=0 and {needle!r}; got exit={code}\n"
            f"          output: {out.strip()[:200]}"
        )


def expect_success(label, files):
    """The suite must be able to distinguish broken trees from sound ones."""
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(BUILD, pathlib.Path(tmp) / "build.py")
        make_tree(tmp, files)
        code, out = build_in(tmp)
    ok = code == 0
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}")
    if not ok:
        failures.append(label)
        print(
            f"          expected exit 0; got {code}\n          output: {out.strip()[:200]}"
        )


def main():
    print("build.py failure paths\n")

    # A control case. Without it, a build.py that failed on everything would
    # pass every other test in this file.
    expect_success(
        "a sound minimal tree builds",
        {"src/index.src.html": "<p>hi</p>\n"},
    )

    expect_failure(
        "missing src/ is refused",
        {"placeholder.txt": "x"},
        "no src/ directory",
    )
    expect_failure(
        "an empty src/ is refused",
        {"src/_partial.html": "<p>only a partial</p>\n"},
        "no pages found",
    )
    expect_failure(
        "an include cycle is caught, not followed until recursion blows up",
        {
            "src/_a.html": "{{INCLUDE:_b.html}}\n",
            "src/_b.html": "{{INCLUDE:_a.html}}\n",
            "src/index.src.html": "{{INCLUDE:_a.html}}\n",
        },
        "include cycle",
    )
    expect_failure(
        "a missing partial fails the build rather than leaving a hole",
        {"src/index.src.html": "{{INCLUDE:_nope.html}}\n"},
        "missing partial",
    )
    expect_failure(
        "a missing image fails rather than shipping a broken src",
        {"src/index.src.html": '<img src="{{IMG:nope.png}}">\n'},
        "missing image",
    )
    expect_failure(
        "a typo'd directive fails rather than shipping literal {{...}}",
        {"src/index.src.html": "<p>{{ARTICLE_LST}}</p>\n"},
        "unresolved directive",
    )
    expect_failure(
        "META missing a required key is refused",
        {"src/writing/x/index.src.html": "{{META\ntitle: T\n}}\n<p>x</p>\n"},
        "META is missing",
    )
    expect_failure(
        "a non-ISO META date is refused, since it feeds Article JSON-LD",
        {
            "src/writing/x/index.src.html": "{{META\ntitle: T\ndate: May 2026\nblurb: B\n}}\n<p>x</p>\n"
        },
        "must be YYYY-MM-DD",
    )
    expect_failure(
        "an HTML entity in META is refused — the value must be safe in HTML "
        "text, attributes and JSON-LD alike",
        {
            "src/writing/x/index.src.html": "{{META\ntitle: A &mdash; B\ndate: 2026-01-01\nblurb: B\n}}\n<p>x</p>\n"
        },
        "write the real character",
    )
    expect_failure(
        "a META line without a colon is refused",
        {
            "src/writing/x/index.src.html": "{{META\ntitle T\ndate: 2026-01-01\nblurb: B\n}}\n<p>x</p>\n"
        },
        "bad META line",
    )
    expect_failure(
        "{{ARTICLE_NAV}} outside an article is refused",
        {"src/index.src.html": "{{ARTICLE_NAV}}\n"},
        "not an article",
    )
    expect_failure(
        "a {{var}} with no META value is refused",
        {"src/writing/x/index.src.html": MINIMAL_META + "<p>{{nosuch}}</p>\n"},
        "no META value",
    )

    print(
        f"\n{'ALL TESTS PASS' if not failures else str(len(failures)) + ' FAILURE(S)'}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
