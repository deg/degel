#!/usr/bin/env python3
"""Generate index.html from index.src.html.

Replaces {{IMG:name}} placeholders with data URIs. Images are looked up
first in assets/, then in the archived old site's client-logo directory.
Run from the repo root:  python3 build.py
"""
import base64, mimetypes, pathlib, re, sys

root = pathlib.Path(__file__).resolve().parent
src = (root / "index.src.html").read_text()
search_dirs = [root / "assets", root / "history/pre-2026/assets/images/client"]

def sub(m):
    name = m.group(1)
    for d in search_dirs:
        p = d / name
        if p.exists():
            mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
            return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"
    sys.exit(f"missing image: {name}")

out = re.sub(r"\{\{IMG:([^}]+)\}\}", sub, src)
dest = root / "index.html"
dest.write_text(out)
print(f"wrote {dest.name}: {len(out)} bytes, {out.count('{{IMG')} placeholders left")
