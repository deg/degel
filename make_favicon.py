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
website-internal-assets repo under design/degel-logo-2004/); the six paths
that make up the emblem were lifted from Inkscape's conversion of it, with
their coordinates rounded to 0.1 unit. The full lockup, with EGEL and the
"Software S.W.A.T Team" bar, is illegible below 64px, which is why the icon
is the emblem alone.

Each ICO size is rendered from the vector separately rather than downscaled
from one big bitmap: at 16px the difference between a rasteriser placing the
wrench's edges and a resampler smearing them is the whole icon.

Dependencies, both BUILD-TIME only and neither used by `make build`:
rsvg-convert (`brew install librsvg`) and Pillow. Like og.png, the outputs are
committed binaries that change about once a decade; regenerating them on
every build would rewrite them in every commit for nothing.
"""

import pathlib
import subprocess
import sys

from PIL import Image

root = pathlib.Path(__file__).resolve().parent
SOURCE = root / "assets" / "degel-emblem.svg"
ICO_SIZES = (16, 32, 48)
TOUCH_SIZE = 180
TOUCH_INSET = 0.12  # of the side, each edge; iOS crops the corners round


def render(size):
    """The emblem at exactly `size` px square, transparent background."""
    out = subprocess.run(
        ["rsvg-convert", "-w", str(size), "-h", str(size), str(SOURCE)],
        capture_output=True,
        check=True,
    ).stdout
    tmp = root / f".favicon-{size}.png"
    tmp.write_bytes(out)
    try:
        return Image.open(tmp).convert("RGBA").copy()
    finally:
        tmp.unlink()


def main():
    if not SOURCE.exists():
        sys.exit(f"missing {SOURCE.relative_to(root)}")
    if subprocess.run(["which", "rsvg-convert"], capture_output=True).returncode:
        sys.exit("rsvg-convert not found: brew install librsvg")

    # Largest first: Pillow silently DROPS any requested size larger than the
    # image it is called on, so a 16px base with 32 and 48 appended writes a
    # one-frame ICO and reports success. check.py reads the ICO directory back
    # for exactly this reason.
    frames = [render(s) for s in sorted(ICO_SIZES, reverse=True)]
    ico = root / "favicon.ico"
    frames[0].save(
        ico,
        format="ICO",
        sizes=[(s, s) for s in sorted(ICO_SIZES, reverse=True)],
        append_images=frames[1:],
    )
    print(f"wrote {ico.relative_to(root)}: {ICO_SIZES} px, {ico.stat().st_size} bytes")

    inner = round(TOUCH_SIZE * (1 - 2 * TOUCH_INSET))
    plate = Image.new("RGBA", (TOUCH_SIZE, TOUCH_SIZE), (255, 255, 255, 255))
    emblem = render(inner)
    offset = (TOUCH_SIZE - inner) // 2
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
