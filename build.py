#!/usr/bin/env python3
"""Generate the site's HTML pages from the sources under src/.

Every src/**/*.src.html is a page: it is written to the same path with the
leading "src/" and the ".src" both dropped, so the repo root mirrors the live
URL structure (src/writing/index.src.html -> writing/index.html). A file whose
basename starts with "_" is a shared partial and is never emitted on its own.

Directives, resolved in this order:

  {{META ... }}          per-page metadata block (see below). Consumed, not
                         emitted.
  {{INCLUDE:_nav.html}}  splices in a partial, resolved relative to src/ and
                         recursively, so partials may include partials.
  {{ARTICLE_LIST}}       generated: the full /writing/ index list
  {{ARTICLE_TEASER:n}}   generated: the newest n articles, titles only
  {{ARTICLE_NAV}}        generated: previous/next cards for THIS article
  {{ARTICLE_JSONLD}}     generated: the Blog blogPost array
  {{title}} {{blurb}}    this page's own metadata, plus {{date}},
                         {{human_date}}, {{medium}}, {{slug}}, {{url}}
  {{IMG:name}}           a data URI. Images are looked up first in assets/,
                         then in the archived old site's client-logo dir.

Includes run first, so a partial can carry any of the rest.

An article is any src/writing/<slug>/index.src.html with a META block.
Adding one is: create the directory, write the file. The /writing/ list, the
home-page teaser, previous/next, the JSON-LD and sitemap.xml all follow from
the same walk, so none of them can drift from what actually deploys.

The list of generated paths is written to .build-outputs for `make deploy`.
Run from the repo root:  python3 build.py
"""
import base64, mimetypes, pathlib, re, sys

root = pathlib.Path(__file__).resolve().parent
src_root = root / "src"
search_dirs = [root / "assets", root / "history/pre-2026/assets/images/client"]

META_RE = re.compile(r"\{\{META\n(.*?)\n\}\}\n", re.S)
INCLUDE_RE = re.compile(r"\{\{INCLUDE:([^}]+)\}\}")
IMG_RE = re.compile(r"\{\{IMG:([^}]+)\}\}")
VAR_RE = re.compile(r"\{\{([a-z_]+)\}\}")
TEASER_RE = re.compile(r"\{\{ARTICLE_TEASER:(\d+)\}\}")
MAX_INCLUDE_DEPTH = 10
MONTHS = ("January February March April May June July August September "
          "October November December").split()

# META values are substituted verbatim into HTML text, attribute values and
# JSON-LD alike, so they must be plain UTF-8 with no markup-significant
# characters. Write the real character (— " ') rather than an entity.
FORBIDDEN = '<>&"'


def parse_meta(text, page):
    """Pull the {{META}} block off the front of a source. Returns (meta, rest)."""
    m = META_RE.search(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            sys.exit(f"{page}: bad META line (want 'key: value'): {line!r}")
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        bad = [c for c in FORBIDDEN if c in v]
        if bad:
            sys.exit(f"{page}: META '{k}' contains {bad} — write the real "
                     f"character, not an entity, so the value is safe in HTML "
                     f"text, attributes and JSON-LD alike")
        meta[k] = v
    return meta, text[:m.start()] + text[m.end():]


def human_date(iso, page):
    try:
        y, mo, d = (int(x) for x in iso.split("-"))
        return f"{d} {MONTHS[mo - 1]} {y}"
    except (ValueError, IndexError):
        sys.exit(f"{page}: META date must be YYYY-MM-DD, got {iso!r}")


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


# ---------- generated blocks ----------

def article_list(arts):
    out = ['    <ul class="articles">']
    for a in arts:
        out += [
            "      <li>",
            f'        <a href="{a["url"]}">{a["title"]}</a>',
            f'        <p class="eyebrow"><time datetime="{a["date"]}">{a["human_date"]}</time></p>',
            f'        <p>{a["blurb"]}</p>',
            "      </li>",
        ]
    out.append("    </ul>")
    return "\n".join(out)


def article_teaser(arts, n):
    out = ['    <ul class="articles teaser">']
    for a in arts[:n]:
        out += [
            "      <li>",
            f'        <a href="{a["url"]}">{a["title"]}</a>',
            f'        <p class="eyebrow"><time datetime="{a["date"]}">{a["human_date"]}</time></p>',
            "      </li>",
        ]
    out.append("    </ul>")
    return "\n".join(out)


def article_nav(arts, i):
    parts = []
    if i > 0:
        n = arts[i - 1]
        parts.append(f'      <a class="prev" href="{n["url"]}">'
                     f'<span class="dir">&larr; Newer</span>{n["title"]}</a>')
    if i < len(arts) - 1:
        o = arts[i + 1]
        parts.append(f'      <a class="next" href="{o["url"]}">'
                     f'<span class="dir">Older &rarr;</span>{o["title"]}</a>')
    return ('    <nav class="article-nav" aria-label="More essays">\n'
            + "\n".join(parts) + "\n    </nav>")


def article_jsonld(arts):
    rows = [f'    {{"@type": "BlogPosting", "headline": "{a["title"]}", '
            f'"datePublished": "{a["date"]}", '
            f'"url": "https://degel.com{a["url"]}"}}' for a in arts]
    return ",\n".join(rows)


def write_sitemap(pages, arts):
    """Generated from the same walk that emits the pages, so it cannot drift."""
    dates = {a["url"]: a["date"] for a in arts}
    rows = []
    for rel in pages:
        url = "/" + str(rel.parent).replace(".", "").lstrip("/")
        url = "/" if url in ("/", "") else url.rstrip("/") + "/"
        lastmod = dates.get(url)
        rows.append(f"  <url><loc>https://degel.com{url}</loc>"
                    + (f"<lastmod>{lastmod}</lastmod>" if lastmod else "")
                    + "</url>")
    (root / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows) + "\n</urlset>\n")
    return len(rows)


# ---------- build ----------

if not src_root.is_dir():
    sys.exit("no src/ directory — run from the repo root")

sources = [s for s in sorted(src_root.rglob("*.src.html"))
           if not s.relative_to(src_root).name.startswith("_")]
if not sources:
    sys.exit("no pages found under src/")

# Pass 1: read every source and pull its metadata.
pages = []
for s in sources:
    rel = s.relative_to(src_root)
    meta, body = parse_meta(s.read_text(), rel)
    if meta:
        meta.setdefault("slug", rel.parent.name)
        for k in ("title", "date", "blurb"):
            if k not in meta:
                sys.exit(f"{rel}: META is missing '{k}'")
        meta["url"] = "/" + str(rel.parent) + "/"
        meta["human_date"] = human_date(meta["date"], rel)
    pages.append({"rel": rel, "body": body, "meta": meta})

# The article registry: every /writing/ page that carries metadata, newest
# first. This one list drives the index, the teaser, prev/next and the
# sitemap, so adding an article updates all of them.
articles = sorted((p["meta"] for p in pages
                   if p["meta"] and p["rel"].parts[0] == "writing"),
                  key=lambda a: a["date"], reverse=True)

# Pass 2: expand and write.
outputs = []
for p in pages:
    rel, meta = p["rel"], p["meta"]
    t = resolve_includes(p["body"], rel, [])
    t = t.replace("{{ARTICLE_LIST}}", article_list(articles))
    t = t.replace("{{ARTICLE_JSONLD}}", article_jsonld(articles))
    t = TEASER_RE.sub(lambda m: article_teaser(articles, int(m.group(1))), t)
    if "{{ARTICLE_NAV}}" in t:
        if meta not in articles:
            sys.exit(f"{rel}: {{{{ARTICLE_NAV}}}} on a page that is not an article")
        t = t.replace("{{ARTICLE_NAV}}", article_nav(articles, articles.index(meta)))
    if meta:
        def var(m):
            k = m.group(1)
            if k not in meta:
                sys.exit(f"{rel}: no META value for {{{{{k}}}}}")
            return meta[k]
        t = VAR_RE.sub(var, t)
    t = resolve_images(t, rel)

    dest = root / rel.with_name(rel.name[: -len(".src.html")] + ".html")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(t)
    outputs.append(dest.relative_to(root))
    left = len(re.findall(r"\{\{", t))
    print(f"wrote {dest.relative_to(root)}: {len(t)} chars, {left} placeholders left")

n = write_sitemap(outputs, articles)
outputs.append(pathlib.Path("sitemap.xml"))
(root / ".build-outputs").write_text("".join(f"{p}\n" for p in outputs))
print(f"{len(outputs)-1} page(s), {len(articles)} article(s); "
      f"sitemap.xml: {n} URLs; manifest -> .build-outputs")
