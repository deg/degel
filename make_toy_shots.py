#!/usr/bin/env python3
"""Retake the Toys page's card pictures from the live sites.

    python3 make_toy_shots.py                  # all three
    python3 make_toy_shots.py nscheme          # just one (automata, cpemulator, nscheme)

Writes assets/toy-<name>.webp, 800x500 (16:10, the card's aspect-ratio in
src/_style-toys.html), which the build inlines into toys/index.html. Rebuild and
deploy afterwards as for any other change.

The pictures are screenshots of the real sites, so they go stale whenever a toy
changes its page, and nothing notices. The first set was taken by throwaway
scripts on 2026-11-17, and nscheme's page turned into a REPL the same evening
(website-63c). This file is those scripts, kept, so the next retake is a rerun.

What each picture shows, and how it is taken:

- cpemulator: Zork I after "open mailbox" and "read leaflet". Zork is not on the
  emulator's starting disk, so ZORK1.COM and ZORK1.DAT are uploaded through the
  page's own file input, from a CPeMulator checkout (--cpm-software, by default
  ../CPeMulator/software beside this repo). The crop keeps the left of the
  terminal, where the text is, and leaves out the scrollbar.
- nscheme: the "Exact numbers" example, evaluated, in a narrow viewport so the
  code reads larger at card size.
- automata: four of the catalogue's own animated tiles in a 2x2 mosaic, to show
  the variety in one picture. Each tile is trimmed a little so its rounded
  corners do not show page background at the seams.

Needs Playwright for Python and Pillow. If Playwright's own browser build is not
installed (its version moves with every Playwright upgrade), the newest
chrome-headless-shell already in the Playwright cache is used instead. Like
make_og.py this is run by hand, never by `make build`: it depends on three live
sites, and the pictures change only when a toy does.
"""

import argparse
import glob
import io
import os
import pathlib
import sys

from PIL import Image
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
OUT = (800, 500)
SCALE = 2  # device pixels per CSS pixel; captured at 2x, then scaled down to OUT
TOYS = ("automata", "cpemulator", "nscheme")


def launch(p):
    try:
        return p.chromium.launch()
    except PlaywrightError:
        pattern = os.path.expanduser(
            "~/Library/Caches/ms-playwright/chromium_headless_shell-*/"
            "chrome-headless-shell-*/chrome-headless-shell"
        )
        found = sorted(glob.glob(pattern))
        if not found:
            sys.exit("no Chromium for Playwright: run `playwright install chromium`")
        return p.chromium.launch(executable_path=found[-1])


def new_page(browser, width, height):
    return browser.new_page(
        viewport={"width": width, "height": height}, device_scale_factor=SCALE
    )


def png(data):
    return Image.open(io.BytesIO(data)).convert("RGB")


def save(img, name):
    path = ROOT / "assets" / f"toy-{name}.webp"
    img.resize(OUT, Image.LANCZOS).save(path, "WEBP", quality=82, method=6)
    print(f"wrote {path.relative_to(ROOT)}: {path.stat().st_size} bytes")


def term_has(page, text, timeout=30000):
    page.wait_for_function(
        "t => document.querySelector('#term').innerText.includes(t)",
        arg=text,
        timeout=timeout,
    )


def cpemulator(browser, software):
    zork = [software / "ZORK1.COM", software / "ZORK1.DAT"]
    missing = [str(f) for f in zork if not f.exists()]
    if missing:
        sys.exit(f"not found: {', '.join(missing)} (see --cpm-software)")
    page = new_page(browser, 1200, 900)
    page.goto("https://cpemulator.degel.com/")
    term_has(page, "A>")
    page.set_input_files("#add-input", [str(f) for f in zork])
    page.click("#term")  # focus the terminal; NOT Escape, which CP/M would read

    def say(text, expect):
        page.keyboard.type(text, delay=40)
        page.keyboard.press("Enter")
        term_has(page, expect)
        page.wait_for_timeout(500)  # let the screen finish drawing

    say("ZORK1", "There is a small mailbox here.")
    say("open mailbox", "reveals a leaflet")
    say("read leaflet", "should be without one")
    box = page.locator("#term").bounding_box()
    # The left 77% of the terminal holds the text (Zork wraps at 64 columns);
    # the height follows from 16:10.
    w = round(box["width"] * 0.77)
    clip = {"x": box["x"], "y": box["y"], "width": w, "height": w * 10 / 16}
    save(png(page.screenshot(clip=clip)), "cpemulator")


def nscheme(browser):
    page = new_page(browser, 720, 760)
    page.goto("https://nscheme.degel.com/")
    page.wait_for_function(
        "!document.querySelector('#evaluate').disabled", timeout=60000
    )
    page.select_option("#examples", "Exact numbers")
    page.click("#evaluate")
    page.wait_for_function(
        "document.body.innerText.includes('3.142857')", timeout=30000
    )
    page.wait_for_timeout(300)
    # From just above the title down, at 16:10 of the full width.
    clip = {"x": 0, "y": 33, "width": 720, "height": 450}
    save(png(page.screenshot(clip=clip)), "nscheme")


def automata(browser):
    page = new_page(browser, 1200, 900)
    page.goto("https://automata.degel.com/")
    page.wait_for_timeout(6000)  # the tiles animate; let the spirals form
    tiles = []
    for demo in ("hodgepodge", "snowflakes", "wireworld", "mandelbrot"):
        tile = page.locator(f'canvas[data-demo="{demo}"]')
        tile.scroll_into_view_if_needed()
        img = png(tile.screenshot())
        w, h = img.size
        dx, dy = 8 * SCALE, 5 * SCALE  # trims the rounded corners, keeps 16:10
        tiles.append(img.crop((dx, dy, w - dx, h - dy)))
    w, h = tiles[0].size
    gap = 4 * SCALE
    mosaic = Image.new("RGB", (2 * w + gap, 2 * h + gap), (20, 26, 51))  # tile ground
    for i, tile in enumerate(tiles):
        mosaic.paste(tile, ((i % 2) * (w + gap), (i // 2) * (h + gap)))
    save(mosaic, "automata")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("toys", nargs="*", help=f"any of {', '.join(TOYS)}; default all")
    ap.add_argument(
        "--cpm-software",
        type=pathlib.Path,
        default=ROOT.parent / "CPeMulator" / "software",
        help="directory holding ZORK1.COM and ZORK1.DAT",
    )
    args = ap.parse_args()
    unknown = set(args.toys) - set(TOYS)
    if unknown:
        ap.error(f"unknown toy: {', '.join(sorted(unknown))}")
    wanted = args.toys or TOYS
    with sync_playwright() as p:
        browser = launch(p)
        if "automata" in wanted:
            automata(browser)
        if "cpemulator" in wanted:
            cpemulator(browser, args.cpm_software)
        if "nscheme" in wanted:
            nscheme(browser)
        browser.close()


if __name__ == "__main__":
    main()
