"""Render a labeled contact sheet of a face atlas, one PNG per sheet.

A face atlas is a grid of 512px cells that composite on top of each other, so a raw
look at the PNG tells you almost nothing: a mouth cell is a few hundred pixels of lip
floating in an empty square. This composites every cell over its race's body cell and
labels it `row.col`, which is the only way to check a layer table against the art. The
row/column splits in FACE_LAYERS were found this way - Terran row 5 turned out to hold
hats, eyewear AND headsets, and Ximni row 3 holds masks and mouths.

    python _tools/face_contact_sheet.py                # every stock sheet
    python _tools/face_contact_sheet.py ter --row 1    # one row, big
    python _tools/face_contact_sheet.py ter --crop eyes

Writes into _tools/out/contact/ unless --out says otherwise. Dev-only; nothing in the
library imports it.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None

CELL = 512

#: alias -> sheet basename under data/graphics. Mirrors allFaceFiles.txt; kept here
#: rather than parsed so the tool works against a checkout with no engine install.
SHEETS = {
    "ter": "Terran_Big-revised", "tor": "Torgoth_Set", "ska": "Skaraan_Set",
    "kra": "Krailen_Set", "zim": "Zimni_Set", "arv": "Arvonian",
}

#: Tight crops for the regions worth looking at closely, in cell pixels.
CROPS = {
    "eyes": (185, 120, 405, 340),
    "mouth": (225, 185, 405, 345),
    "head": (100, 0, 420, 320),
    # Kralien and Torgoth are drawn in three-quarter profile with a large cranium, so
    # their eyes and mouth sit well below where a front-on "head" crop looks.
    "lowface": (150, 210, 420, 440),
    "full": (0, 0, CELL, CELL),
}

BG = (24, 24, 30, 255)
LABEL = (255, 255, 110, 255)


def graphics_dir():
    """The engine's data/graphics, found by walking up from this file.

    `__file__` is reliable here because this is a dev tool run from a checkout, never
    the embedded interpreter - the fs.py rule about __file__ is about production code.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    for up in range(6):
        cand = os.path.join(here, *([".."] * up), "..", "..", "graphics")
        cand = os.path.normpath(cand)
        if os.path.isdir(cand) and os.path.exists(os.path.join(cand, "allFaceFiles.txt")):
            return cand
    return None


def load_sheet(alias, gfx):
    name = SHEETS.get(alias)
    if name is None:
        raise SystemExit(f"unknown alias {alias!r}; known: {', '.join(sorted(SHEETS))}")
    path = os.path.join(gfx, name + ".png")
    if not os.path.exists(path):
        raise SystemExit(f"missing sheet {path}")
    return Image.open(path).convert("RGBA")


def cells(im):
    w, h = im.size
    return w // CELL, h // CELL


def filled(im, col, row):
    """True when a cell has any meaningful alpha.

    The threshold is 8, not 0: several cells carry a faint halo of alpha 8-40 left over
    from the artist's extraction, which getbbox() reports as content and would make an
    empty grid slot look occupied.
    """
    a = im.getchannel("A").crop((col * CELL, row * CELL, (col + 1) * CELL, (row + 1) * CELL))
    return a.getextrema()[1] > 8


def contact(im, alias, rows, crop, thumb, per_row, body_col):
    box = CROPS[crop]
    cols, nrows = cells(im)
    body = im.crop((body_col * CELL, 0, (body_col + 1) * CELL, CELL))
    items = []
    for r in rows:
        for c in range(cols):
            if not filled(im, c, r):
                continue
            base = Image.new("RGBA", (CELL, CELL), BG)
            if r > 0:
                base.alpha_composite(body)
            base.alpha_composite(im.crop((c * CELL, r * CELL, (c + 1) * CELL, (r + 1) * CELL)))
            items.append((f"{r}.{c}", base.crop(box)))
    if not items:
        return None
    n = min(per_row, len(items))
    down = (len(items) + n - 1) // n
    out = Image.new("RGBA", (n * thumb, down * (thumb + 18)), BG)
    d = ImageDraw.Draw(out)
    for i, (label, img) in enumerate(items):
        gx, gy = i % n, i // n
        out.paste(img.resize((thumb, thumb), Image.LANCZOS), (gx * thumb, gy * (thumb + 18) + 18))
        d.text((gx * thumb + 4, gy * (thumb + 18) + 3), f"{alias} {label}", fill=LABEL)
    return out.convert("RGB")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("alias", nargs="*", help="aliases to render (default: all six)")
    ap.add_argument("--row", type=int, action="append", help="only this row; repeatable")
    ap.add_argument("--crop", default="full", choices=sorted(CROPS))
    ap.add_argument("--thumb", type=int, default=150)
    ap.add_argument("--per-row", type=int, default=8)
    ap.add_argument("--body-col", type=int, default=0, help="which row-0 cell to composite over")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    gfx = graphics_dir()
    if gfx is None:
        raise SystemExit("could not find data/graphics - run from an sbs_utils checkout "
                         "inside a Cosmos install")
    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "contact")
    os.makedirs(out_dir, exist_ok=True)

    aliases = args.alias or list(SHEETS)
    for alias in aliases:
        im = load_sheet(alias, gfx)
        cols, nrows = cells(im)
        print(f"{alias:5s} {SHEETS[alias]:22s} {im.size[0]}x{im.size[1]} = {cols} cols x {nrows} rows")
        for r in range(nrows):
            marks = "".join("X" if filled(im, c, r) else "." for c in range(cols))
            print(f"        row {r}: {marks}  ({marks.count('X')})")
        rows = args.row if args.row else list(range(nrows))
        sheet = contact(im, alias, rows, args.crop, args.thumb, args.per_row, args.body_col)
        if sheet is None:
            continue
        suffix = args.crop if args.crop != "full" else "all"
        if args.row:
            suffix += "-r" + "".join(str(r) for r in args.row)
        path = os.path.join(out_dir, f"{alias}_{suffix}.png")
        sheet.save(path)
        print(f"        -> {path}")


if __name__ == "__main__":
    main(sys.argv[1:])
