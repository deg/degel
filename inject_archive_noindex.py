#!/usr/bin/env python3
"""Give every archived page under history/ a robots noindex tag.

Idempotent: a page that already declares a robots meta is left exactly as it
was, so this can be re-run after importing another era.

It exists as a committed script because the last injection was an ad-hoc step
that nobody kept. It reached the pages of history/pre-2026/ and the .html
conversions in history/pre-2016/, and missed the 32 .htm originals beside
them -- a gap that then sat unnoticed for ten days. check.py now fails if any
archived page lacks the tag; this is the tool that fixes what it reports.

WHY THE TAG IS THERE AT ALL, given robots.txt Disallows /history/ and a
crawler that may not fetch a page can never read a tag inside it: it is
contingency armour, not an active control. See docs/archive-indexing.md.

Bytes in, bytes out. These files are 2001-2015 hand-written HTML in assorted
encodings; decoding them to str risks mangling text this repo is supposed to
preserve verbatim. The inserted tag is pure ASCII, which is valid in every
encoding involved.

What counts as an archived page is imported from check.py, not restated
here, so the tool and the check that grades it cannot disagree -- the same
reason check.py imports page_url from build.py.

Run from the repo root:  python3 inject_archive_noindex.py
"""

import re
import sys

from check import archive_pages

TAG = b'<meta name="robots" content="noindex, nofollow">'
HAS_ROBOTS = re.compile(rb"""name\s*=\s*["']robots["']""", re.I)
HEAD_CLOSE = re.compile(rb"</head\s*>", re.I)
HTML_OPEN = re.compile(rb"<html\b[^>]*>", re.I)


def inject(raw):
    """Return the page with the tag added, or None if it already has one.

    Three shapes turn up in the archive, and the third is why this is not a
    one-line regex:

      * a normal page, or an SSI fragment whose <html><head> came from an
        include it no longer has -- either way there is a </head> to sit in
        front of;
      * a frameset document, which has no head at all and needs one made;
      * a bare markup fragment (an old left-hand nav), where the tag goes
        first and the parser puts it in the head it implies.
    """
    if HAS_ROBOTS.search(raw):
        return None
    m = HEAD_CLOSE.search(raw)
    if m:
        return raw[: m.start()] + TAG + b"\n" + raw[m.start() :]
    m = HTML_OPEN.search(raw)
    if m:
        return raw[: m.end()] + b"\n<head>" + TAG + b"</head>" + raw[m.end() :]
    return TAG + b"\n" + raw


def main():
    changed = 0
    for p in archive_pages():
        out = inject(p.read_bytes())
        if out is not None:
            p.write_bytes(out)
            changed += 1
            print(f"  + {p}")
    total = len(archive_pages())
    print(
        f"{changed} page(s) given a noindex tag; {total} archived page(s) now carry one"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
