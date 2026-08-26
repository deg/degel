#!/usr/bin/env python3
"""Generate the site's HTML pages from the sources under src/.

Every src/**/*.src.html is a page: it is written to the same path with the
leading "src/" and the ".src" both dropped, so the repo root mirrors the live
URL structure (src/writing/index.src.html -> writing/index.html). A file whose
basename starts with "_" is a shared partial and is never emitted on its own.

Two directives, resolved in this order:

  {{INCLUDE:_nav.html}}  splices in a partial, resolved relative to src/ and
                         recursively (so partials may include partials).
  {{IMG:name}}           substitutes a data URI. Images are looked up first in
                         assets/, then in the archived old site's client-logo
                         directory.

Includes run first, so a partial can carry its own images.

The list of generated paths is written to .build-outputs for `make deploy`.
Run from the repo root:  python3 build.py
"""
import base64, mimetypes, pathlib, re, sys

root = pathlib.Path(__file__).resolve().parent
src_root = root / "src"
search_dirs = [root / "assets", root / "history/pre-2026/assets/images/client"]

INCLUDE_RE = re.compile(r"\{\{INCLUDE:([^}]+)\}\}")
IMG_RE = re.compile(r"\{\{IMG:([^}]+)\}\}")
MAX_INCLUDE_DEPTH = 10


def resolve_includes(text, page, stack):
    """Splice {{INCLUDE:}} directives, recursively, guarding against cycles."""
    if len(stack) > MAX_INCLUDE_DEPTH:
        sys.exit(f"{page}: include nesting deeper than {MAX_INCLUDE_DEPTH}: "
                 + " -> ".join(stack))

    def sub(m):
        name = m.group(1)
        if name in stack:
            sys.exit(f"{page}: include cycle: " + " -> ".join(stack + [name]))
        p = src_root / name
        if not p.exists():
            sys.exit(f"{page}: missing partial: {name}")
        body = p.read_text()
        # A directive sits on its own line; the partial file ends with a
        # newline of its own. Drop exactly one so the splice is seamless.
        if body.endswith("\n"):
            body = body[:-1]
        return resolve_includes(body, page, stack + [name])

    return INCLUDE_RE.sub(sub, text)


def resolve_images(text, page):
    def sub(m):
        name = m.group(1)
        for d in search_dirs:
            p = d / name
            if p.exists():
                mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
                return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"
        sys.exit(f"{page}: missing image: {name}")

    return IMG_RE.sub(sub, text)


if not src_root.is_dir():
    sys.exit("no src/ directory — run from the repo root")

outputs = []
for source in sorted(src_root.rglob("*.src.html")):
    rel = source.relative_to(src_root)
    if rel.name.startswith("_"):
        continue
    out = resolve_images(resolve_includes(source.read_text(), rel, []), rel)
    dest = root / rel.with_name(rel.name[: -len(".src.html")] + ".html")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out)
    outputs.append(dest.relative_to(root))
    left = len(INCLUDE_RE.findall(out)) + len(IMG_RE.findall(out))
    print(f"wrote {dest.relative_to(root)}: {len(out)} chars, {left} placeholders left")

if not outputs:
    sys.exit("no pages found under src/")

(root / ".build-outputs").write_text("".join(f"{p}\n" for p in outputs))
print(f"{len(outputs)} page(s); manifest -> .build-outputs")
