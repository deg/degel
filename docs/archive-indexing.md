# Keeping the /history/ museum out of search results

Why `robots.txt` says `Disallow: /history/` even though that is, in the
general case, the wrong way to keep a page out of an index — and what was
considered instead.

Decided 2026-08-28. Supersedes the recommendation in bead `website-76n`,
which is closed as an accepted risk.

## The goal, stated exactly

> These pages are not secret in any way; we just don't want them to confuse or
> pollute searches for the current Degel pages.
> — David, 2026-08-28

This is narrower than it first looks, and the narrowing decides the argument.

**Not** goals:

- **Secrecy.** The archive is public. So is the repo it lives in
  (`github.com/deg/degel`), where every archived file is crawlable and
  indexable no matter what `degel.com/robots.txt` says. Any plan justified by
  hiding is justified by nothing.
- **Privacy.** `history/pre-2016/staffcontacts.htm` carries five `@degel.com`
  addresses — four former associates and David's own. `robots.txt` binds
  compliant crawlers and nobody else, so it protects none of this. If those
  addresses ever need to go, they need to leave the repo; no robots directive
  is relevant.
- **Blocking humans.** The museum is a deliberate easter egg. A visitor who
  finds the door is welcome.

The **only** goal: a stale 2001–2025 page must never surface as a result for a
query about the current business.

## The constraint everything else follows from

Two facts, and neither is negotiable on this host:

1. **A non-HTML file cannot carry a `noindex`.** The tag lives in `<head>`.
   There is no `<head>` in a PDF.
2. **GitHub Pages cannot send an `X-Robots-Tag` header**, which is the only
   other way to mark a non-HTML file `noindex`. Pages serves static files with
   fixed headers and offers no configuration for them. Verified live: the
   archived resume returns `200` from `server: GitHub.com` with no such
   header, and the domain resolves straight to the Pages IPs, so there is no
   proxy in front that could add one.

The files this applies to, all under `history/`:

| kind | count | examples |
| --- | --- | --- |
| PDF | 7 | `pre-2026/resume.pdf`, `pre-2016/resumes/DavidGoldfarb.pdf`, `Degel-Brochure.pdf` |
| plain text | 4 | `david/todo.txt`, `clients-dontuse.txt` |
| archives / installers | 11 | `.zip`, `.sis` era artifacts |
| other | — | `.asp`, `.css` |

So for those files there is **no index control available at all**. The only
lever is a *crawl* control: `Disallow` stops a compliant crawler fetching
them, which stops their contents reaching a results page. That is a weaker
guarantee than `noindex` — it does not prevent a bare URL being listed — but
it is the only lever that exists.

Being precise about this matters, because the loose phrasing ("Disallow keeps
them out of the index") is exactly the error that makes bead `website-76n`
look correct.

## What is actually in place

Four independent layers. Each has been proposed for removal at least once,
which is why `check.py::check_archive_stays_out_of_search` now asserts all
four.

1. **No crawlable link.** The museum's door is the footer's copyright years,
   attached by JavaScript (`src/_script.html`), so no `<a href>` to
   `/history/` exists in any deployed page. A crawler is never handed the URL.
   **This is the layer doing the real work** — everything below is what
   happens if it fails.
2. **`Disallow: /history/`.** The only control covering the meta-incapable
   files above.
3. **`noindex, nofollow` on all 68 archived pages.** Dormant while layer 2
   stands: a crawler forbidden to fetch a page can never read a tag inside it.
   It is contingency armour for the day `robots.txt` regresses, not an active
   control — see "the honest accounting" below.
4. **The sitemap never lists an archive URL.**

## Options considered

### A. Leave it as it was (2026-08-18 to 2026-08-28) — rejected

Layers 1, 2 and 4 in place; layer 3 believed complete but **not**. The launch
injection matched `*.html` and missed the 32 `.htm` originals of the
2001–2015 site, so nearly half the archive carried no tag at all while
everything looked done. Rejected because the belief was false.

### B. Drop `Disallow`, complete the `noindex` (bead `website-76n`) — rejected

The bead's reasoning is correct as far as it goes, and worth restating fairly:
`Disallow` blocks *crawling*, not *indexing*; a crawler forbidden to fetch a
page can never read the `noindex` that would keep it out; so if anyone links
to `degel.com/history/`, Google can list a bare titleless URL — the exact
outcome the arrangement is meant to prevent, reached by the mechanism meant
to prevent it. This is also Google's own published guidance.

Rejected because of what it costs. Removing `Disallow` makes the seven PDFs
and four `.txt` files fetchable, and they cannot say `noindex`. They would be
indexed **with their contents**. `degel.com/history/pre-2026/resume.pdf` — a
2017 resume that `website-yg5.5` recommends retiring permanently and that
`website-34n` exists because of — could rank for "David Goldfarb".

Compare the two failure modes against the stated goal:

| | worst case | is it pollution? |
| --- | --- | --- |
| **keep `Disallow`** | a bare, titleless `/history/` URL, and only if something links to it | no — no stale content reaches a results page |
| **drop `Disallow`** | stale PDFs indexed in full | yes — precisely the thing to avoid |

The bead trades a guarantee for the HTML pages, which are already covered by
layer 1, in exchange for exposing the one asset class that has no defence.

### C. `User-agent: Googlebot` group with `Allow: /history/` — rejected

Let the search engines in so they read the `noindex`, keep everyone else out.
Fails on robots.txt semantics plus the same PDF problem: a crawler obeys only
the single most specific matching group and groups never merge (RFC 9309), so
a Googlebot group containing only an `Allow` leaves Googlebot with **no
`Disallow` rules at all**. The PDFs become fully crawlable for the one
crawler that matters most.

### D. Narrow the `Disallow` to the meta-incapable files — rejected

`Disallow: /history/*.pdf$` and friends, leaving archive HTML crawlable so its
`noindex` does active work. The strongest of the rejected options, and closer
than C.

Rejected for two reasons. Wildcard and `$` support is a Google/Bing extension,
optional under RFC 9309, so the rule is advisory for everyone else. More
importantly, crawling the archive HTML is how a crawler would *discover* the
PDF URLs in the first place — they are linked from `ourteam.html` and
friends — and `nofollow` has been a hint rather than a directive since 2019.
It moves the bare-URL risk onto the worst possible asset class while making
discovery of that class more likely.

### E. Delete the meta-incapable files from the archive — rejected

Removes the constraint entirely and would allow option B cleanly. Rejected
because the archive's whole value is being verbatim; the `.sis` installers and
brochures were deliberately kept at launch as era artifacts. Worth revisiting
**only** for the two stale resumes, which are a separate question that
`website-yg5.5` owns — not an indexing decision.

### F. Put Cloudflare in front of the domain — rejected

A proxy could inject `X-Robots-Tag: noindex` on `/history/*` and dissolve the
constraint. Rejected as disproportionate: a DNS change and a permanent
third-party dependency in the serving path, for a site whose first design
decision was that it depends on nothing.

### G. Chosen: keep `Disallow`, complete the `noindex`, guard all four layers

- `robots.txt` unchanged.
- `noindex, nofollow` added to the 32 pages that lacked it, by
  `inject_archive_noindex.py` — committed this time, because the previous
  injection was an ad-hoc step nobody kept, which is why the gap existed.
- `check.py::check_archive_stays_out_of_search` asserts all four layers, and
  `test_check.py` breaks each one to prove the check notices.

## The honest accounting

Two things this arrangement does **not** claim:

- **Bead 76n's mechanism argument is correct and unrebutted.** With
  `Disallow` in place, a linked-to `/history/` URL can appear as a bare
  listing. That risk is **accepted**, not solved. It is accepted because the
  thing at risk is a titleless URL with no content, the alternative risks
  stale content ranking, and layer 1 means nothing links there in the first
  place.
- **Layer 3 is dormant.** While layer 2 stands, no compliant engine will ever
  fetch a page to read those 68 tags. They exist for the day someone deletes
  a line from `robots.txt` — which is precisely what 76n proposed, and why the
  check asserts both.

## What would reopen this

- **Search Console data** (`website-efe.2`). Nobody has ever looked at whether
  `/history/` is in the index. It is the one empirical fact that would move
  this from reasoning to evidence, and it changes nothing about the
  recommendation in the meantime — G is better than A under either answer.
- **A bare `/history/` URL actually appearing** in results. Then the accepted
  risk has materialised, and the fix is available and cheap: drop `Disallow`
  and accept the PDF exposure, or delete the PDFs first.
- **Moving off GitHub Pages** to any host that can set response headers. The
  entire constraint disappears; `X-Robots-Tag: noindex` on `/history/*` plus
  an allowed crawl is strictly better than anything above.
- **A crawlable link to the museum** ever being wanted. That retires layer 1,
  and the whole analysis should be redone rather than patched.

## Who argued what

- **2026-08-18, launch session.** Designed layers 1, 2 and 3 together, and got
  layer 1 exactly right: *"no crawlable href exists in the HTML, so search
  engines never discover /history/ from this site while humans get a
  hover-revealed door"* (commit `6d39e8b`). Layer 3 was specified for every
  page and delivered for about half.
- **2026-08-19, review session.** Filed `website-76n`. Correctly identified
  that layers 2 and 3 conflict for search engines. Argued from a half-built
  design and did not account for layer 1 or for the meta-incapable files.
- **2026-08-28.** Both prior positions reviewed against the repo. The original
  design was right but unfinished; the review was right about the mechanism
  and wrong about the remedy. Finished the design, guarded it, closed the bead.
