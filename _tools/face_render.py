"""Composite face strings to a PNG sheet, the way the engine does, so they can be LOOKED at.

Every other check on the face system is structural - does it round-trip, is the cell in
range - and none of them can tell you that the hat is being drawn where the chin is. This
renders real face strings against the real atlases so the layer tables can be verified by
eye, which is the only verification that actually settles it.

The compositing rule is face.js's drawLayer, not a reinvention: crop the cell, and for a
non-white tint multiply the color through and mask back to the sprite's own alpha.

    python _tools/face_render.py                      # 8 random faces per race
    python _tools/face_render.py --expressions        # one face, every expression
    python _tools/face_render.py --migrate            # old strings, before and after
    python _tools/face_render.py --face "ter #fff 0 0;ter #fff 1 1;"

Writes into _tools/out/render/. Dev-only.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))

from face_contact_sheet import SHEETS, graphics_dir  # noqa: E402

from sbs_utils.fs import test_set_exe_dir  # noqa: E402

test_set_exe_dir()
from sbs_utils import faces  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

BG = (24, 24, 30, 255)
_atlas = {}


def atlas(alias, gfx):
    if alias not in _atlas:
        name = SHEETS.get(alias)
        if name is None:
            return None
        path = os.path.join(gfx, name + ".png")
        _atlas[alias] = Image.open(path).convert("RGBA") if os.path.exists(path) else None
    return _atlas[alias]


def parse_color(text):
    h = (text or "fff").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return (255, 255, 255)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def render(face_string, gfx, size=256):
    """One face string -> an RGBA image, or None if no layer could be drawn."""
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    drew = False
    for lay in faces._parse_face_layers(face_string):
        sheet = atlas(lay["alias"], gfx)
        if sheet is None:
            continue
        grid = faces.FACE_SHEETS.get(lay["alias"])
        if grid is None:
            continue
        cols, rows = grid
        cw, ch = sheet.width / cols, sheet.height / rows
        sx, sy = lay["col"] * cw + lay["ox"], lay["row"] * ch + lay["oy"]
        box = (int(round(sx)), int(round(sy)), int(round(sx + cw)), int(round(sy + ch)))
        if box[0] < 0 or box[1] < 0 or box[2] > sheet.width or box[3] > sheet.height:
            continue
        cell = sheet.crop(box).resize((size, size), Image.LANCZOS)
        rgb = parse_color(lay["color"])
        if rgb != (255, 255, 255):
            # multiply the tint through, then mask back to the sprite's own alpha
            tint = Image.new("RGBA", cell.size, rgb + (255,))
            lit = Image.new("RGBA", cell.size, (0, 0, 0, 0))
            lit.paste(Image.blend(cell, tint, 0.0), (0, 0))
            px = cell.load()
            tp = lit.load()
            for y in range(cell.height):
                for x in range(cell.width):
                    r, g, b, a = px[x, y]
                    tp[x, y] = (r * rgb[0] // 255, g * rgb[1] // 255, b * rgb[2] // 255, a)
            cell = lit
        out.alpha_composite(cell)
        drew = True
    return out if drew else None


def grid_sheet(items, gfx, size=200, per_row=8):
    """[(label, face_string)] -> one labeled contact image."""
    n = min(per_row, max(1, len(items)))
    down = (len(items) + n - 1) // n
    out = Image.new("RGBA", (n * size, down * (size + 18)), BG)
    d = ImageDraw.Draw(out)
    for i, (label, face) in enumerate(items):
        img = render(face, gfx, size)
        gx, gy = i % n, i // n
        if img is not None:
            cell = Image.new("RGBA", (size, size), BG)
            cell.alpha_composite(img)
            out.paste(cell, (gx * size, gy * (size + 18) + 18))
        d.text((gx * size + 4, gy * (size + 18) + 3), label[:34], fill=(255, 255, 110, 255))
    return out.convert("RGB")


#: A few real pre-redraw strings from the missions, for the migration comparison.
OLD_FACES = [
    ("URSULA", "ter #964b00 8 1;ter #968b00 3 0;ter #968b00 4 0;ter #968b00 5 2;"
               "ter #fff 3 5;ter #964b00 8 4;"),
    ("Harkin", "ter #964b00 8 1;ter #fff 3 5;"),
    ("Akana", "ter #acb057 0 0;ter #acb057 3 1;ter #acb057 1 3;ter #fff 12 0 14 -2;"
              "ter #fff 1 4;ter #ffffff 11 0 12 4;"),
    ("Evans", "ter #ffffff 0 0;ter #ffffff 1 1;ter #ffffff 2 2;ter #3D2314 8 0 6 -2;"
              "ter #fff 12 0 14 -2;ter #fff 0 7;ter #3D2314 9 0 12 4;"),
    ("station8", "ter #492816 0 0;ter #492816 0 2;ter #492816 1 2;ter #1E1a33 7 3 6 -2;"
                 "ter #fff 14 0 14 -2;ter #fff 2 4;ter #fff 13 1 20 4;"),
]


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--expressions", action="store_true")
    ap.add_argument("--migrate", action="store_true")
    ap.add_argument("--face", action="append", help="render one face string; repeatable")
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--size", type=int, default=200)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    gfx = graphics_dir()
    if gfx is None:
        raise SystemExit("could not find data/graphics")
    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "out", "render")
    os.makedirs(out_dir, exist_ok=True)

    def save(name, items, per_row=8):
        path = os.path.join(out_dir, name + ".png")
        grid_sheet(items, gfx, args.size, per_row).save(path)
        print("->", path)

    if args.face:
        save("faces", [(f"{i}", f) for i, f in enumerate(args.face)], per_row=4)
        return 0
    if args.expressions:
        for race in faces.FACE_LAYERS:
            names = faces.face_expressions(race)
            if not names:
                print(f"{race}: no expressions")
                continue
            base = faces.random_face(race)
            save(f"expr_{race}",
                 [(e, faces.face_expression(base, e)) for e in names],
                 per_row=len(names))
        return 0
    if args.migrate:
        items = []
        for label, old in OLD_FACES:
            items.append((label + " (new)", faces.face_migrate(old)))
        save("migrated", items, per_row=len(items))
        return 0
    for race in faces.FACE_LAYERS:
        save(race, [(f"{race} {i}", faces.random_face(race)) for i in range(args.count)])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
