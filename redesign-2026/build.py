#!/usr/bin/env python3
"""Generate index.html from index.src.html.

Replaces {{IMG:name}} placeholders with data URIs. Images are looked up
first in redesign-2026/assets/, then in the legacy assets/images/client/.
Run from the repo root:  python3 redesign-2026/build.py
"""
import base64, mimetypes, pathlib, re, sys

root = pathlib.Path(__file__).resolve().parent.parent
src = (root / "redesign-2026/index.src.html").read_text()
search_dirs = [root / "redesign-2026/assets", root / "assets/images/client"]

def sub(m):
    name = m.group(1)
    for d in search_dirs:
        p = d / name
        if p.exists():
            mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
            return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"
    sys.exit(f"missing image: {name}")

out = re.sub(r"\{\{IMG:([^}]+)\}\}", sub, src)
dest = root / "redesign-2026/index.html"
dest.write_text(out)
print(f"wrote {dest}: {len(out)} bytes, {out.count('{{IMG')} placeholders left")
