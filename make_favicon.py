#!/usr/bin/env python3
"""Generate favicon.ico and apple-touch-icon.png from assets/degel-emblem.svg.
Run:  python3 make_favicon.py

The favicon itself is the SVG, inlined into every page's <head> by build.py's
{{IMG:}} directive (src/_meta.html), so the pages stay self-contained and no
browser has to fetch anything to show it. These two files exist for the
clients that cannot use that:

  * favicon.ico        Safari ignores SVG favicons in its tab strip and asks
                       for /favicon.ico instead, as do bookmark and history
                       views in older browsers, and every browser probes the
                       path unprompted. It carried a 404 from launch until this
                       script existed.
  * apple-touch-icon   iOS "Add to Home Screen", and the icon macOS Safari and
                       several messaging apps show for a link. iOS discards
                       transparency and rounds the corners itself, so the
                       emblem is set on a white plate with room around it.

The emblem is the wrench-through-D from the 2001-2015 site. The vector source
is a CorelDRAW 11 export of 2004-01-14 (degel_logo.WMF, in the private
website-internal-assets repo under design/degel-logo-2004/, next to the
faithful full lockup); the six paths that make up the emblem were lifted
from Inkscape's conversion of it. The full lockup, with EGEL and the
"Software S.W.A.T Team" bar, is illegible below 64px, which is why the icon
is the emblem alone -- and the emblem itself carries two deliberate
departures from the 2004 artwork, both for legibility in a tab strip:

  * the shaft is 100 units shorter (150 -> 50). The middle of the wrench was
    compressed along its own axis, so both heads and the bolt keep their
    exact shapes, and the whole emblem fits the tile unclipped with the D at
    ~80% of its width. Fitted whole, the D was 62% and its detail vanished
    at 16px; cropping instead lost the wrench head;
  * the wrench body is azure (#2b7fd6) with a white outline instead of white
    with a #006699 outline, so it pops against the black D on light and dark
    strips alike. The site accent (#0038b8) was too dark against the D.

Coordinates in the SVG are whole units on a 318-unit viewBox (0.16% error,
invisible) and it carries no commentary of its own: every byte of it is
base64-encoded into every page's <head>, so the story lives here instead.

Each ICO size is rendered from the vector separately rather than downscaled
from one big bitmap: at 16px the difference between a rasteriser placing the
wrench's edges and a resampler smearing them is the whole icon.

Dependencies, both BUILD-TIME only and neither used by `make build`:
rsvg-convert (`brew install librsvg`) and Pillow. Like og.png, the outputs are
committed binaries that change about once a decade; regenerating them on
every build would rewrite them in every commit for nothing.
"""

import io
import pathlib
import shutil
import subprocess
import sys

from PIL import Image

root = pathlib.Path(__file__).resolve().parent
SOURCE = root / "assets" / "degel-emblem.svg"
# Largest first: Pillow silently DROPS any requested ICO size larger than the
# image save() is called on, so a 16px base with 32 and 48 appended writes a
# one-frame ICO and reports success. check.py reads the ICO directory back for
# exactly this reason.
ICO_SIZES = (48, 32, 16)
TOUCH_SIZE = 180
TOUCH_INNER = 136  # even, so the plate's margins are equal; iOS rounds the corners


def render(size):
    """The emblem at exactly `size` px square, transparent background.

    Decoded from memory rather than via a temp file: a temp file in the repo
    root left behind by a crash is an untracked file, and the deploy refuses
    to run while one exists.
    """
    # stderr is left alone on purpose: a failing rsvg-convert then says WHY
    # (an SVG parse error, say) instead of just its exit code.
    png = subprocess.run(
        ["rsvg-convert", "-w", str(size), "-h", str(size), str(SOURCE)],
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    return Image.open(io.BytesIO(png)).convert("RGBA")


def main():
    if not SOURCE.exists():
        sys.exit(f"missing {SOURCE.relative_to(root)}")
    if not shutil.which("rsvg-convert"):
        sys.exit("rsvg-convert not found: brew install librsvg")

    frames = [render(s) for s in ICO_SIZES]
    ico = root / "favicon.ico"
    frames[0].save(
        ico,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=frames[1:],
    )
    print(f"wrote {ico.relative_to(root)}: {ICO_SIZES} px, {ico.stat().st_size} bytes")

    plate = Image.new("RGBA", (TOUCH_SIZE, TOUCH_SIZE), (255, 255, 255, 255))
    emblem = render(TOUCH_INNER)
    offset = (TOUCH_SIZE - TOUCH_INNER) // 2
    plate.alpha_composite(emblem, (offset, offset))
    touch = root / "apple-touch-icon.png"
    plate.convert("RGB").save(touch, optimize=True)
    print(
        f"wrote {touch.relative_to(root)}: {TOUCH_SIZE}x{TOUCH_SIZE}, "
        f"{touch.stat().st_size} bytes"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
